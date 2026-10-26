#!/usr/bin/env python3
"""Test whether surrounding movie context helps Qwen score annotated events.

Run on a Triton GPU node:
    python code/legacy/qwen_context_test.py --context-seconds 0
    python code/legacy/qwen_context_test.py
    python code/legacy/qwen_context_test.py --all-events

The first two commands test the same five events (Control 1, Social 3,
Pain 8 and 10, Mental 17) with and without context using a matched prompt.
The third processes all 19 with context. Existing results are retained;
an interrupted run can be resumed with the same command.
"""

import argparse
import csv
import json
import subprocess
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOVIE = (
    Path(__file__).resolve().parents[2]
    / "moviestimulus" / "partly_cloudy_sd_nocredits.mov"
)
MANIFEST = ROOT / "outputs/clips_offset_minus10s/manifest.csv"
BASELINE = ROOT / "outputs/qwen2_5_vl_3b_pilot.jsonl"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
PILOT_IDS = (1, 3, 8, 10, 17)

# Keep the original category definitions, so the main change is extra context
# and an explicit indication of which portion should be scored.
PROMPT = """Examine this short silent animated clip. Based on its visible events,
describe what happens in one sentence. Then rate EACH feature independently
from 0 (absent) to 3 (strongly present). Do not assume one feature must win.

Mental: The scene leads the viewer to infer a character's thoughts, beliefs,
intentions, or feelings.
Pain: A character experiences a physically painful event.
Social: Characters interact without a strong focus on inferred mental states.
Control: Scenery or other physical events, with no specific character-related
event as the focus.

IMPORTANT: The video may include context around an annotated event. Score ONLY
what happens from {focus_start:.1f} to {focus_end:.1f} seconds within this clip.
If earlier/later frames are present, use them to understand that central
event, not to score unrelated events. Do not assume any category is present.

Return JSON only, with keys description, mental, pain, social, control.
The four scores must be integers from 0 to 3. It is okay for all four to be 0.
"""


def probe_duration(movie: Path) -> float:
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(movie)],
        check=True, capture_output=True, text=True,
    )
    return float(run.stdout.strip())


def parse_scores(reply: str) -> dict | None:
    """Keep raw text even if the model does not produce usable JSON."""
    try:
        scores = json.loads(reply)
    except json.JSONDecodeError:
        return None
    if not isinstance(scores, dict):
        return None
    if not all(type(scores.get(key)) is int and 0 <= scores[key] <= 3
               for key in ("mental", "pain", "social", "control")):
        return None
    return scores


def baseline_scores() -> dict[int, dict]:
    if not BASELINE.is_file():
        return {}
    found = {}
    with BASELINE.open() as source:
        for line in source:
            if not line.strip():
                continue
            record = json.loads(line)
            scores = parse_scores(record.get("raw_response", ""))
            if scores is not None:
                found[int(record["event_id"])] = scores
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--movie", type=Path, default=DEFAULT_MOVIE)
    parser.add_argument("--all-events", action="store_true")
    parser.add_argument("--context-seconds", type=float, default=4.0)
    parser.add_argument("--fps", type=float, default=2.0)
    args = parser.parse_args()
    if args.context_seconds < 0 or args.fps <= 0:
        parser.error("--context-seconds must be nonnegative and --fps positive")
    if not torch.cuda.is_available():
        parser.error("Run this script on a Triton GPU compute node")
    if not args.movie.is_file():
        parser.error(f"Movie not found: {args.movie}")
    if not MANIFEST.is_file():
        parser.error(f"Manifest not found: {MANIFEST}")

    with MANIFEST.open(newline="") as source:
        rows = list(csv.DictReader(source))
    by_id = {int(row["event_id"]): row for row in rows}
    if len(rows) != 19 or len(by_id) != 19:
        parser.error("Expected 19 unique events in the manifest")
    selected_ids = sorted(by_id) if args.all_events else PILOT_IDS
    movie_duration = probe_duration(args.movie)

    # Name results by the actual context and frame rate to prevent mix-ups.
    tag = f"{args.context_seconds:g}s_{args.fps:g}fps".replace(".", "p")
    clip_dir = ROOT / "outputs" / f"context_clips_{tag}"
    output = ROOT / "outputs" / f"qwen_context_{tag}.jsonl"
    clip_dir.mkdir(parents=True, exist_ok=True)

    events = []
    for event_id in selected_ids:
        row = by_id[event_id]
        focus_movie_start = float(row["movie_onset_s"])
        focus_movie_end = focus_movie_start + float(row["duration_s"])
        start = max(0.0, focus_movie_start - args.context_seconds)
        end = min(movie_duration, focus_movie_end + args.context_seconds)
        if not 0 <= start <= focus_movie_start < focus_movie_end <= end <= movie_duration:
            parser.error(f"Invalid timestamps for event {event_id}")
        clip = clip_dir / f"{event_id:02d}_context.mp4"
        if not clip.is_file():
            # Accurate decoding/cutting: seek after input, then re-encode video.
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(args.movie), "-ss", str(start), "-t", str(end - start),
                 "-map", "0:v:0", "-an", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "20", str(clip)],
                check=True,
            )
        events.append((event_id, row, clip, start, end,
                       focus_movie_start - start, focus_movie_end - start))

    completed = {}
    if output.exists():
        with output.open() as source:
            for line in source:
                if line.strip():
                    record = json.loads(line)
                    completed[int(record["event_id"])] = record
    pending = [event for event in events if event[0] not in completed]

    if pending:
        print(f"Loading {MODEL_ID}; {len(pending)} event(s) to run.", flush=True)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_ID, dtype=torch.float16, device_map={"": 0},
            attn_implementation="sdpa", low_cpu_mem_usage=True,
        ).eval()
        processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=360 * 420)
        with output.open("a") as target:
            for event_id, row, clip, start, end, focus_start, focus_end in pending:
                message = [{"role": "user", "content": [
                    {"type": "video", "path": str(clip)},
                    {"type": "text", "text": PROMPT.format(
                        focus_start=focus_start, focus_end=focus_end)},
                ]}]
                inputs = processor.apply_chat_template(
                    message, fps=args.fps, add_generation_prompt=True,
                    tokenize=True, return_dict=True, return_tensors="pt",
                ).to("cuda")
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs, max_new_tokens=220, do_sample=False)
                reply_tokens = generated[0, inputs["input_ids"].shape[-1]:]
                reply = processor.decode(
                    reply_tokens, skip_special_tokens=True).strip()
                record = {
                    "event_id": event_id, "human_condition": row["condition"],
                    "movie_start_s": start, "movie_end_s": end,
                    "focus_start_in_clip_s": focus_start,
                    "focus_end_in_clip_s": focus_end, "clip": clip.name,
                    "context_seconds": args.context_seconds,
                    "model": MODEL_ID, "fps": args.fps,
                    "raw_response": reply, "scores": parse_scores(reply),
                }
                target.write(json.dumps(record) + "\n")
                target.flush()
                completed[event_id] = record
                print(f"{event_id:02d} {row['condition']}: {reply}", flush=True)
                del inputs, generated, reply_tokens
                torch.cuda.empty_cache()

    previous = baseline_scores()
    short_tag = f"0s_{args.fps:g}fps".replace(".", "p")
    short_output = ROOT / "outputs" / f"qwen_context_{short_tag}.jsonl"
    matched_short = {}
    if short_output.exists() and short_output != output:
        with short_output.open() as source:
            for line in source:
                if line.strip():
                    record = json.loads(line)
                    matched_short[int(record["event_id"])] = record.get("scores")
    print("\nScores for the human category (Control score in parentheses):")
    for event_id in selected_ids:
        row = by_id[event_id]
        label = row["condition"]
        old = previous.get(event_id)
        new = completed.get(event_id, {}).get("scores")
        matched = matched_short.get(event_id)
        old_text = "--" if old is None else f"{old[label]} (C{old['control']})"
        matched_text = "--" if matched is None else f"{matched[label]} (C{matched['control']})"
        new_text = "--" if new is None else f"{new[label]} (C{new['control']})"
        print(f"{event_id:02d} {label:7s} original={old_text:8s} matched short={matched_text:8s} this run={new_text}")
    print(f"\nSaved context results: {output}")
    print("Compare matched short (0s) with 4s context to assess the effect of added frames.")
    print("The original pilot used a different prompt; keep it as a reference only.")


if __name__ == "__main__":
    main()
