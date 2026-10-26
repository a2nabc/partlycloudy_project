#!/usr/bin/env python3
"""Prepare and review an evidence-first Partly Cloudy annotation pilot.

Run from the project root on Triton:
  python code/annotation/qwen_evidence_pilot.py prepare
  python code/annotation/qwen_evidence_pilot.py infer --limit 10  # GPU node
  python code/annotation/qwen_evidence_pilot.py infer             # resume all
  python code/annotation/qwen_evidence_pilot.py review
  python code/annotation/qwen_evidence_pilot.py compare  # after human review

The first pass describes the visible sequence without category names. A second,
text-only pass proposes one label or Unclear. Both raw replies are retained for
human review. Existing Qwen and X-CLIP outputs are never modified.
"""

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOVIE = ROOT / "moviestimulus/partly_cloudy_sd_nocredits.mov"
MANIFEST = ROOT / "outputs/clips_offset_minus10s/manifest.csv"
OUT = ROOT / "outputs/annotation_pilot"
CANDIDATES = OUT / "candidates.csv"
RESULTS = OUT / "qwen_3b_evidence.jsonl"
REVIEW = ROOT / "notes/annotation_review.csv"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
CONTEXT = 4.0
UNCODED_SECONDS = 8.0
UNCODED_COUNT = 8
UNCODED_BUFFER = 1.0
FPS = 2.0
LABELS = {"Mental", "Pain", "Social", "Control", "Unclear"}

OBSERVE = """Watch this silent animated video. Describe the visible sequence;
do not assign a psychological or research category. Focus on {focus_start:.2f}
to {focus_end:.2f} seconds within this video. The surrounding frames clarify
what leads to and follows that interval. If something is hard to see, say so.
Return JSON only with these string keys:
"actions_in_focus" (who visibly does what), "visible_reaction" (what visibly
changes afterward), "context_sequence" (relevant before/after events), and
"uncertain_details" (what the frames cannot establish). Keep each concise.
"""

CLASSIFY = """You are reviewing a description of a silent animated scene.
Judge the marked interval from the evidence supplied. Propose ONE primary label:
Mental = the scene notably invites inference about a character's thoughts,
beliefs, intentions, or feelings, supported by visible cues;
Pain = a character visibly experiences a physically painful event or its
immediate reaction;
Social = characters visibly interact, without the main emphasis on an inferred
mental state or a physically painful event;
Control = scenery or physical events are the main focus, with no specific
character-related event as the focus;
Unclear = evidence is insufficient or competing labels cannot be separated.
Do not guess a label from the presence of clouds or characters alone. The
description may omit or misread details. If that matters, choose Unclear.
Return JSON only: {{"primary_label":"...", "evidence":"one brief sentence",
"alternative_label":"... or empty string", "uncertainty":"low, medium, or high"}}.
Description: {description}
"""

FIELDS = ("candidate_id", "source_type", "event_id", "human_condition",
          "focus_start_s", "focus_end_s", "clip_start_s", "clip_end_s",
          "clip", "movie")


def duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", str(path)],
                       check=True, capture_output=True, text=True)
    return float(p.stdout.strip())


def read_candidates() -> list[dict]:
    if not CANDIDATES.is_file():
        raise FileNotFoundError(f"Run 'prepare' first: {CANDIDATES}")
    with CANDIDATES.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 19 + UNCODED_COUNT or len({r["candidate_id"] for r in rows}) != len(rows):
        raise ValueError("Candidate manifest must have 27 unique rows")
    return rows


def select_uncoded(spans: list[tuple[float, float]], movie_end: float) -> list[float]:
    """Choose separate windows across gaps in the annotated intervals."""
    possible = []
    for second in range(math.floor(movie_end - UNCODED_SECONDS) + 1):
        start, end = float(second), second + UNCODED_SECONDS
        if all(end <= a - UNCODED_BUFFER or start >= b + UNCODED_BUFFER
               for a, b in spans):
            possible.append(start)
    selected = []
    for i in range(UNCODED_COUNT):
        eligible = [s for s in possible if all(
            s + UNCODED_SECONDS <= prior or prior + UNCODED_SECONDS <= s
            for prior in selected)]
        if not eligible:
            raise ValueError("Too few nonoverlapping unannotated windows")
        # Spread selections along the film, deterministically.
        target = i * (movie_end - UNCODED_SECONDS) / (UNCODED_COUNT - 1)
        selected.append(min(eligible, key=lambda s: (abs(s - target), s)))
    return sorted(selected)


def prepare(movie: Path) -> None:
    if not movie.is_file() or not MANIFEST.is_file():
        raise FileNotFoundError(f"Need movie {movie} and manifest {MANIFEST}")
    movie = movie.resolve()
    movie_end = duration(movie)
    with MANIFEST.open(newline="") as f:
        events = sorted(csv.DictReader(f), key=lambda x: int(x["event_id"]))
    if len(events) != 19 or [int(r["event_id"]) for r in events] != list(range(1, 20)):
        raise ValueError("Expected event IDs 1 through 19 in the original manifest")
    spans = [(float(r["movie_onset_s"]),
              float(r["movie_onset_s"]) + float(r["duration_s"])) for r in events]
    rows = []
    for event, (start, end) in zip(events, spans):
        if not 0 <= start < end <= movie_end:
            raise ValueError(f"Invalid event timestamp: {event['event_id']}")
        cid = f"event_{int(event['event_id']):02d}"
        rows.append(dict(candidate_id=cid, source_type="manual_event",
                         event_id=event["event_id"], human_condition=event["condition"],
                         focus_start_s=start, focus_end_s=end,
                         clip_start_s=max(0., start - CONTEXT),
                         clip_end_s=min(movie_end, end + CONTEXT),
                         clip=f"clips/{cid}.mp4", movie=str(movie)))
    for i, start in enumerate(select_uncoded(spans, movie_end), 1):
        cid = f"uncoded_{i:02d}"
        rows.append(dict(candidate_id=cid, source_type="unannotated",
                         event_id="", human_condition="", focus_start_s=start,
                         focus_end_s=start + UNCODED_SECONDS,
                         clip_start_s=start, clip_end_s=start + UNCODED_SECONDS,
                         clip=f"clips/{cid}.mp4", movie=str(movie)))
    if CANDIDATES.exists():
        old = read_candidates()
        # Compare numeric text by value because csv formatting may differ.
        if old != [{k: str(r[k]) for k in FIELDS} for r in rows]:
            raise ValueError(f"Existing {CANDIDATES} differs. Preserve this run; use a new directory for new settings.")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        with CANDIDATES.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "clips").mkdir(exist_ok=True)
    for r in rows:
        clip = OUT / r["clip"]
        if clip.exists() and clip.stat().st_size > 0:
            continue
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(movie), "-ss", str(r["clip_start_s"]),
                        "-t", str(r["clip_end_s"] - r["clip_start_s"]),
                        "-map", "0:v:0", "-an", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "20", str(clip)], check=True)
        if not clip.exists() or clip.stat().st_size == 0:
            raise ValueError(f"Empty clip: {clip}")
    print(f"Prepared {len(rows)} candidates in {CANDIDATES}")


def parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def completed_results() -> dict[str, dict]:
    found = {}
    if RESULTS.exists():
        with RESULTS.open() as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    cid = row["candidate_id"]
                    if cid in found:
                        raise ValueError(f"Duplicate result: {cid}")
                    if row.get("model") != MODEL_ID or row.get("fps") != FPS or row.get("version") != 1:
                        raise ValueError("Prior results have different model/settings")
                    found[cid] = row
    return found


def infer(limit: int | None) -> None:
    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    if not torch.cuda.is_available():
        raise RuntimeError("Inference needs a Triton GPU compute node")
    candidates = read_candidates()
    done = completed_results()
    pending = [r for r in candidates if r["candidate_id"] not in done]
    if limit is not None:
        pending = pending[:limit]
    if not pending:
        print(f"No pending candidates. Results: {RESULTS}")
        return
    for r in pending:
        if not (OUT / r["clip"]).is_file():
            raise FileNotFoundError(f"Missing {OUT / r['clip']}; run prepare")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID, dtype=torch.float16, device_map={"": 0},
        attn_implementation="sdpa", low_cpu_mem_usage=True).eval()
    processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=360 * 420)

    def ask(content: list[dict]) -> str:
        messages = [{"role": "user", "content": content}]
        sampling = {"fps": FPS} if any(item["type"] == "video" for item in content) else {}
        inputs = processor.apply_chat_template(messages, **sampling,
                    add_generation_prompt=True, tokenize=True,
                    return_dict=True, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            answer = model.generate(**inputs, max_new_tokens=230, do_sample=False)
        return processor.decode(answer[0, inputs["input_ids"].shape[-1]:],
                                skip_special_tokens=True).strip()

    with RESULTS.open("a") as f:
        for r in pending:
            offset = float(r["clip_start_s"])
            prompt = OBSERVE.format(focus_start=float(r["focus_start_s"]) - offset,
                                    focus_end=float(r["focus_end_s"]) - offset)
            raw_observation = ask([{"type": "video", "path": str(OUT / r["clip"])},
                                   {"type": "text", "text": prompt}])
            observation = parse_json(raw_observation)
            # Classification receives only the model's observation, never the
            # video filename, original manual condition, or movie timestamps.
            raw_label = ask([{"type": "text", "text": CLASSIFY.format(
                description=json.dumps(observation if observation is not None
                                       else {"unparsed_observation": raw_observation}))}])
            label = parse_json(raw_label)
            if label is not None and label.get("primary_label") not in LABELS:
                label = None
            record = {"candidate_id": r["candidate_id"], "model": MODEL_ID,
                      "fps": FPS, "version": 1, "movie": r["movie"],
                      "clip": r["clip"], "observation_prompt": prompt,
                      "classification_prompt": CLASSIFY,
                      "raw_observation": raw_observation, "observation": observation,
                      "raw_classification": raw_label, "classification": label}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            print(f"Saved {r['candidate_id']}: "
                  f"{label.get('primary_label') if label else 'parse error'}", flush=True)
    print(f"Results: {RESULTS}")


def review() -> None:
    if REVIEW.exists():
        raise FileExistsError(f"Preserving existing human review: {REVIEW}")
    candidates, results = read_candidates(), completed_results()
    if set(results) != {r["candidate_id"] for r in candidates}:
        raise ValueError("Finish all 27 inference candidates before making the review sheet")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    fields = ("candidate_id", "source_type", "event_id",
              "focus_start_s", "focus_end_s", "clip", "model_action",
              "model_reaction", "model_context", "model_uncertain_details",
              "proposed_label", "model_evidence", "model_uncertainty",
              "reviewed_label", "evidence_visible", "review_notes")
    with REVIEW.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in candidates:
            m = results[r["candidate_id"]]
            o, c = m["observation"] or {}, m["classification"] or {}
            writer.writerow({"candidate_id": r["candidate_id"],
                "source_type": r["source_type"], "event_id": r["event_id"],
                "focus_start_s": r["focus_start_s"], "focus_end_s": r["focus_end_s"],
                "clip": str((OUT / r["clip"]).resolve()),
                "model_action": o.get("actions_in_focus", ""),
                "model_reaction": o.get("visible_reaction", ""),
                "model_context": o.get("context_sequence", ""),
                "model_uncertain_details": o.get("uncertain_details", ""),
                "proposed_label": c.get("primary_label", ""),
                "model_evidence": c.get("evidence", ""),
                "model_uncertainty": c.get("uncertainty", ""),
                "reviewed_label": "", "evidence_visible": "", "review_notes": ""})
    print(f"Review all candidate clips and fill the final three columns: {REVIEW}")


def compare() -> None:
    """Report agreement only after the blinded review sheet is complete."""
    if not REVIEW.is_file():
        raise FileNotFoundError(f"Complete the review sheet first: {REVIEW}")
    with REVIEW.open(newline="") as f:
        reviewed = list(csv.DictReader(f))
    candidates = read_candidates()
    if [r["candidate_id"] for r in reviewed] != [r["candidate_id"] for r in candidates]:
        raise ValueError("Review rows differ from the candidate manifest")
    if any(r["reviewed_label"] not in LABELS or
           r["evidence_visible"].strip().lower() not in {"yes", "no"}
           for r in reviewed):
        raise ValueError("Fill reviewed_label and evidence_visible (yes/no) in every row")
    anchors = [(r, c) for r, c in zip(reviewed, candidates)
               if c["source_type"] == "manual_event"]
    print("Category | human anchor count | model agrees with human | review agrees with human")
    for label in ("Mental", "Pain", "Social", "Control"):
        group = [(r, c) for r, c in anchors if c["human_condition"].lower() == label.lower()]
        model_agree = sum(r["proposed_label"] == label for r, _ in group)
        review_agree = sum(r["reviewed_label"] == label for r, _ in group)
        print(f"{label:7s} | {len(group):2d} | {model_agree:2d} | {review_agree:2d}")
    print("\nCandidate | original human | model | reviewed | evidence visible")
    for r, c in zip(reviewed, candidates):
        print(f"{r['candidate_id']:12s} | {c['human_condition'] or '(unannotated)':13s} | "
              f"{r['proposed_label'] or '(parse error)':13s} | "
              f"{r['reviewed_label']:8s} | {r['evidence_visible']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--movie", type=Path, default=MOVIE)
    run = sub.add_parser("infer")
    run.add_argument("--limit", type=int)
    sub.add_parser("review")
    sub.add_parser("compare")
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.movie)
    elif args.phase == "infer":
        if args.limit is not None and args.limit < 1:
            parser.error("--limit must be positive")
        infer(args.limit)
    elif args.phase == "review":
        review()
    else:
        compare()


if __name__ == "__main__":
    main()