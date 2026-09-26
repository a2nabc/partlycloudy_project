#!/usr/bin/env python3
"""Zero-shot video/text similarity on the 19 Partly Cloudy event clips.

Copy to code/xclip_video_pilot.py. Run on a Triton GPU node:
    export HF_HOME=/scratch/work/bernada4/hf_cache
    python code/xclip_video_pilot.py

X-CLIP produces similarity logits for four fixed text descriptions. It does
not generate the descriptions, classify with a trained four-class head, or
produce independent 0--3 scores. Comparisons are meaningful within this
model and these particular text descriptions, not numerically against Qwen.
"""

import argparse
import av
import csv
import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoProcessor


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "outputs/clips_offset_minus10s/manifest.csv"
CLIP_DIR = MANIFEST.parent
OUTPUT = ROOT / "outputs/xclip_base_19_events.jsonl"
MODEL_ID = "microsoft/xclip-base-patch32"
NUM_FRAMES = 8

# Written before seeing model results. These are candidate descriptions,
# not labels supplied to the model for each individual clip.
DESCRIPTIONS = {
    "mental": "A character reacts to another character's feelings or intentions.",
    "pain": "A character experiences physical pain or injury.",
    "social": "Characters interact with each other.",
    "control": "Clouds and scenery move in the sky without a character interaction.",
}


def sample_frames(path: Path, n: int) -> tuple[list[np.ndarray], list[float | None]]:
    """Decode the clip and choose evenly spaced frames including its ends."""
    with av.open(str(path)) as container:
        frames = [frame for frame in container.decode(video=0)]
    if not frames:
        raise ValueError(f"No decoded video frames: {path}")
    indices = np.linspace(0, len(frames) - 1, num=n).round().astype(int)
    selected = [frames[i] for i in indices]
    return (
        [frame.to_ndarray(format="rgb24") for frame in selected],
        [None if frame.time is None else round(float(frame.time), 4)
         for frame in selected],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=19,
                        help="Run first N events (default: all 19)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 19:
        parser.error("--limit must be between 1 and 19")
    if not torch.cuda.is_available():
        parser.error("Run on a Triton GPU compute node")
    if not MANIFEST.exists():
        parser.error(f"Missing {MANIFEST}")
    with MANIFEST.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 19:
        parser.error(f"Expected 19 rows; found {len(rows)}")
    rows.sort(key=lambda row: int(row["event_id"]))
    for row in rows[:args.limit]:
        if not (CLIP_DIR / row["filename"]).is_file():
            parser.error(f"Missing clip: {CLIP_DIR / row['filename']}")

    completed = set()
    if OUTPUT.exists():
        with OUTPUT.open() as source:
            for line in source:
                if line.strip():
                    completed.add(int(json.loads(line)["event_id"]))
    pending = [row for row in rows[:args.limit]
               if int(row["event_id"]) not in completed]
    if not pending:
        print(f"All requested events already present in {OUTPUT}")
        return

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).to("cuda").eval()
    with OUTPUT.open("a") as target, torch.inference_mode():
        for row in pending:
            path = CLIP_DIR / row["filename"]
            frames, times = sample_frames(path, NUM_FRAMES)
            inputs = processor(
                text=list(DESCRIPTIONS.values()), videos=frames,
                return_tensors="pt", padding=True,
            ).to("cuda")
            result = model(**inputs)
            values = result.logits_per_video[0].float().cpu().tolist()
            scores = dict(zip(DESCRIPTIONS, (round(x, 5) for x in values)))
            ranking = sorted(scores, key=scores.get, reverse=True)
            record = {
                "event_id": int(row["event_id"]),
                "human_condition": row["condition"],
                "movie_onset_s": float(row["movie_onset_s"]),
                "duration_s": float(row["duration_s"]),
                "clip": path.name, "model": MODEL_ID,
                "sampling": "8 frames uniformly spaced over each annotated clip",
                "frame_times_in_clip_s": times,
                "candidate_descriptions": DESCRIPTIONS,
                "similarity_logits": scores,
                "ranking": ranking,
            }
            target.write(json.dumps(record) + "\n")
            target.flush()
            print(f"{int(row['event_id']):02d} human={row['condition']:7s} "
                  f"ranked={','.join(ranking)} logits={scores}", flush=True)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
