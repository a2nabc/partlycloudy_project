#!/usr/bin/env python3
"""Compare X-CLIP descriptions on 19 events and across the movie.

Place this file in code/xclip/. On a Triton GPU node:
    export HF_HOME=/scratch/work/bernada4/hf_cache
    python code/xclip/xclip_film_analysis.py --phase annotations
    python code/xclip/xclip_film_analysis.py --phase timeline --limit 10
    python code/xclip/xclip_film_analysis.py --phase timeline

Default: eight-second windows starting every second, eight frames spread
across each window, and the checkpoint trained on eight frames. For a later
16-frame comparison, add --frames 16 to BOTH phases; this selects the
separate X-CLIP checkpoint trained with 16 frames. Output names are distinct
by window length/frame count, and interrupted runs resume from JSONL.
"""

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

import av
import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "outputs/clips_offset_minus10s/manifest.csv"
CLIP_DIR = MANIFEST.parent
MOVIE = ROOT / "moviestimulus/partly_cloudy_sd_nocredits.mov"
MODELS = {
    8: "microsoft/xclip-base-patch32",
    16: "microsoft/xclip-base-patch32-16-frames",
}
LABELS = ("mental", "pain", "social", "control")
FRAME_RATE = 4
STRIDE_SECONDS = 1
RESIZE = (256, 192)  # same aspect ratio as the 768 x 576 movie

# Original wording is retained to measure how much the first pilot depended
# on its scene-specific Control description. The two alternatives have a
# similar grammatical structure and avoid explicitly mentioning clouds/sky.
DESCRIPTIONS = {
    "original": {
        "mental": "A character reacts to another character's feelings or intentions.",
        "pain": "A character experiences physical pain or injury.",
        "social": "Characters interact with each other.",
        "control": "Clouds and scenery move in the sky without a character interaction.",
    },
    "balanced_a": {
        "mental": "An animated scene involving a character's thoughts or feelings.",
        "pain": "An animated scene involving a character's physical pain.",
        "social": "An animated scene involving characters interacting.",
        "control": "An animated scene involving scenery or physical movement.",
    },
    "balanced_b": {
        "mental": "In this scene, a character shows an intention or emotion.",
        "pain": "In this scene, a character shows a reaction to physical harm.",
        "social": "In this scene, characters engage with one another.",
        "control": "In this scene, the focus is on objects or movement in the environment.",
    },
}
def movie_duration(movie: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(movie)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def annotation_frames(clip: Path, frame_count: int) -> tuple[list[np.ndarray], list[float]]:
    with av.open(str(clip)) as container:
        frames = list(container.decode(video=0))
    if not frames:
        raise ValueError(f"No decoded frames in {clip}")
    indices = np.linspace(0, len(frames) - 1, frame_count).round().astype(int)
    selected = [frames[i] for i in indices]
    images = [np.asarray(Image.fromarray(frame.to_ndarray(format="rgb24"))
                         .resize(RESIZE, Image.Resampling.BICUBIC))
              for frame in selected]
    times = [round(float(frame.time), 4) if frame.time is not None else None
             for frame in selected]
    return images, times


def movie_frame_grid(movie: Path) -> np.ndarray:
    """Decode the movie once to a 4 Hz frame grid (about 185 MB in RAM)."""
    width, height = RESIZE
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(movie),
        "-an", "-vf", f"fps={FRAME_RATE},scale={width}:{height}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    bytes_per_frame = width * height * 3
    if not result.stdout or len(result.stdout) % bytes_per_frame:
        raise ValueError("Unexpected ffmpeg raw-video output length")
    frames = np.frombuffer(result.stdout, dtype=np.uint8).reshape(
        -1, height, width, 3)
    print(f"Decoded {len(frames)} frames at {FRAME_RATE} Hz.", flush=True)
    return frames


def read_completed(path: Path, phase: str, source_movie: str | None,
                   model_id: str, settings: dict) -> dict[int, dict]:
    found = {}
    if path.exists():
        with path.open() as source:
            for line in source:
                if not line.strip():
                    continue
                record = json.loads(line)
                key = int(record["event_id"] if phase == "annotations" else record["window_id"])
                if key in found:
                    raise ValueError(f"Duplicate result for {key} in {path}")
                if (record.get("descriptions") != DESCRIPTIONS
                        or record.get("model") != model_id
                        or record.get("settings") != settings
                        or record.get("source_movie") != source_movie):
                    raise ValueError(f"Settings in {path} differ from this script; use a new output file")
                found[key] = record
    return found


def score(model, processor, frames: list[np.ndarray]) -> dict[str, dict[str, float]]:
    text = [DESCRIPTIONS[group][label]
            for group in DESCRIPTIONS for label in LABELS]
    inputs = processor(text=text, videos=frames, padding=True,
                       return_tensors="pt").to("cuda")
    with torch.inference_mode():
        logits = model(**inputs).logits_per_video[0].float().cpu().tolist()
    if len(logits) != len(text):
        raise ValueError(f"Expected {len(text)} logits, got {len(logits)}")
    result = {}
    for index, group in enumerate(DESCRIPTIONS):
        block = logits[index * len(LABELS):(index + 1) * len(LABELS)]
        result[group] = {label: round(value, 5)
                         for label, value in zip(LABELS, block)}
    return result


def window_indices(start_s: int, window_seconds: int, frame_count: int) -> np.ndarray:
    """Choose frame nearest the center of each equally sized time segment."""
    grid_count = window_seconds * FRAME_RATE
    within_window = np.floor((np.arange(frame_count) + 0.5)
                             * grid_count / frame_count).astype(int)
    return start_s * FRAME_RATE + within_window


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("annotations", "timeline"))
    parser.add_argument("--movie", type=Path, default=MOVIE,
                        help="Movie file for timeline inference")
    parser.add_argument("--window-seconds", type=int, default=8,
                        help="Timeline window duration in seconds (default: 8)")
    parser.add_argument("--frames", type=int, choices=MODELS, default=8,
                        help="8 (default) or 16; selects the matching checkpoint")
    parser.add_argument("--limit", type=int,
                        help="Process this many events/windows for a quick first run")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        parser.error("Run on a Triton GPU node")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    if args.window_seconds <= 0 or args.window_seconds * FRAME_RATE < args.frames:
        parser.error("Window must contain at least as many 4-Hz grid frames as --frames")

    model_id = MODELS[args.frames]
    settings = {
        "frames_per_clip": args.frames,
        "annotation_sampling": f"{args.frames} uniformly spaced frames per annotated clip",
        "timeline_sampling_hz": FRAME_RATE,
        "window_seconds": args.window_seconds if args.phase == "timeline" else None,
        "stride_seconds": STRIDE_SECONDS,
        "timeline_sampling": "one frame near the center of each equal-duration segment",
        "resize_width_height": list(RESIZE),
    }
    output = (ROOT / "outputs" /
              (f"xclip_wording_check_{args.frames}f.jsonl" if args.phase == "annotations"
               else f"xclip_movie_timeline_{args.window_seconds}s_{args.frames}f.jsonl"))
    if args.phase == "annotations":
        with MANIFEST.open(newline="") as source:
            rows = list(csv.DictReader(source))
        if len(rows) != 19:
            parser.error(f"Expected 19 annotations in {MANIFEST}")
        rows.sort(key=lambda row: int(row["event_id"]))
        candidates = [(int(row["event_id"]), row) for row in rows]
    else:
        if not args.movie.is_file():
            parser.error(f"Movie unavailable on this node: {args.movie}; pass --movie")
        duration = movie_duration(args.movie)
        n_windows = math.floor((duration - args.window_seconds) / STRIDE_SECONDS) + 1
        if n_windows <= 0:
            parser.error("Movie is shorter than one window")
        candidates = [(i, i * STRIDE_SECONDS)
                      for i in range(n_windows)]
    if args.limit is not None:
        candidates = candidates[:args.limit]

    output.parent.mkdir(parents=True, exist_ok=True)
    source_movie = str(args.movie.resolve()) if args.phase == "timeline" else None
    completed = read_completed(output, args.phase, source_movie, model_id, settings)
    pending = [(key, data) for key, data in candidates if key not in completed]
    if not pending:
        print(f"No pending items. Results: {output}")
        return
    if args.phase == "annotations":
        for _, row in pending:
            if not (CLIP_DIR / row["filename"]).is_file():
                parser.error(f"Missing clip: {CLIP_DIR / row['filename']}")

    grid = movie_frame_grid(args.movie) if args.phase == "timeline" else None
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).to("cuda").eval()
    with output.open("a") as target:
        for key, data in pending:
            if args.phase == "annotations":
                clip = CLIP_DIR / data["filename"]
                frames, times = annotation_frames(clip, args.frames)
                record = {
                    "event_id": key, "human_condition": data["condition"],
                    "movie_onset_s": float(data["movie_onset_s"]),
                    "duration_s": float(data["duration_s"]),
                    "frame_times_in_clip_s": times, "clip": clip.name,
                }
            else:
                start = data
                indices = window_indices(start, args.window_seconds, args.frames)
                if int(indices[-1]) >= len(grid):
                    raise ValueError(f"Insufficient frames for window {key}")
                frames = [grid[int(index)].copy() for index in indices]
                record = {
                    "window_id": key, "start_s": float(start),
                    "end_s": float(start + args.window_seconds),
                    "movie_duration_s": duration,
                    "frame_times_in_movie_s": [round(index / FRAME_RATE, 3)
                                               for index in indices],
                }
            record.update({
                "model": model_id, "descriptions": DESCRIPTIONS,
                "settings": settings, "source_movie": source_movie,
                "scores": score(model, processor, frames),
            })
            target.write(json.dumps(record) + "\n")
            target.flush()
            print(f"{args.phase} {key + (0 if args.phase == 'annotations' else 1)}/"
                  f"{len(candidates)} saved", flush=True)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
