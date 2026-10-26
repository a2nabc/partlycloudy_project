#!/usr/bin/env python3
"""Whole-movie, evidence-first candidate scoring for Partly Cloudy.

From the project root:
  python code/annotation/qwen_whole_movie_scores.py prepare
  # On a GPU node:
  python code/annotation/qwen_whole_movie_scores.py infer
  python code/annotation/qwen_whole_movie_scores.py rank

The manual annotation manifest is deliberately never opened. This is a
candidate retrieval experiment, not a calibrated probability estimator.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import fcntl
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOVIE = ROOT / "moviestimulus/partly_cloudy_sd_nocredits.mov"
OUT = ROOT / "outputs/qwen_whole_movie_scores_v2_no_context"
WINDOWS = OUT / "windows.csv"
RESULTS = OUT / "scores.jsonl"
RANKED = OUT / "ranked_candidates.csv"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
FOCUS = 6.0
STRIDE = 3.0
FPS = 2.0
LABELS = ("Mental", "Pain", "Social", "Control")
VERSION = 2

# Provisional operational rubric. Check against the actual annotation paper
# before interpreting model scores as the four original human conditions.
RUBRIC = {
    "Mental": "Visible behavior strongly calls for interpreting a character's thoughts, beliefs, intentions, or feelings.",
    "Pain": "A character visibly undergoes a physically painful event or shows its immediate reaction.",
    "Social": "Characters visibly interact; assess the interaction itself even if Mental or Pain also applies.",
    "Control": "A clearly observable physical/scenery event is visible without a specific character-related event; an unannotated interval is not automatically Control.",
}
PROMPT = """Watch this entire silent animated clip. Judge the entire supplied clip.
Describe visible actions in order and visible reactions, then independently
score all four conditions using only evidence visible in this video.
Do not infer an event merely from a character's presence.
Give each condition an integer 0–4: 0 = absent/no visible evidence,
1 = weak/ambiguous, 2 = plausible with some visible evidence,
3 = strong clear evidence, 4 = exceptionally clear defining example.
All four may be 0; several may be high. Do not normalize across conditions.
{rubric}
Return JSON only with this structure:
{{"actions":"...", "visible_reactions":"...", "uncertain_details":"...",
"scores":{{"Mental":0,"Pain":0,"Social":0,"Control":0}},
"evidence":{{"Mental":"...","Pain":"...","Social":"...","Control":"..."}},
"uncertainty":"low, medium, or high"}}.
For EVERY condition give visible evidence or explain its absence or ambiguity.
Ground scores in observed actions and reactions. Do not use external knowledge.
"""
FIELDS = ("window_id", "focus_start_s", "focus_end_s", "clip_start_s",
          "clip_end_s", "clip", "movie", "settings_hash")


def film_duration(movie):
    run = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(movie)],
                         check=True, capture_output=True, text=True)
    return float(run.stdout.strip())


def settings_hash(movie, duration):
    payload = [VERSION, str(movie), round(duration, 4), FOCUS, STRIDE,
               FPS, MODEL_ID, RUBRIC, PROMPT]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def windows_for(movie, duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Movie duration must be positive")
    starts = [i * STRIDE for i in range(math.floor(max(0, duration - FOCUS) / STRIDE) + 1)]
    final = max(0.0, duration - FOCUS)
    if final - starts[-1] > 0.00001:
        starts.append(final)
    config = settings_hash(movie, duration)
    rows = []
    for i, start in enumerate(starts):
        end = min(duration, start + FOCUS)
        rows.append({"window_id": f"window_{i:04d}", "focus_start_s": f"{start:.4f}",
                     "focus_end_s": f"{end:.4f}",
                     "clip_start_s": f"{start:.4f}",
                     "clip_end_s": f"{end:.4f}",
                     "clip": f"clips/window_{i:04d}.mp4", "movie": str(movie),
                     "settings_hash": config})
    return rows


def read_windows():
    if not WINDOWS.is_file():
        raise FileNotFoundError(f"Run prepare first: {WINDOWS}")
    with WINDOWS.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or list(rows[0]) != list(FIELDS):
        raise ValueError("Invalid window manifest")
    if len({r["window_id"] for r in rows}) != len(rows) or len({r["settings_hash"] for r in rows}) != 1:
        raise ValueError("Duplicate IDs or mixed settings in window manifest")
    return rows


def prepare(movie):
    if not movie.is_file():
        raise FileNotFoundError(movie)
    movie = movie.resolve()
    rows = windows_for(movie, film_duration(movie))
    if WINDOWS.exists():
        if read_windows() != rows:
            raise ValueError("Existing run has different windows or settings; keep it and use a new output directory")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        with WINDOWS.open("w", newline="") as f:
            writer = csv.DictWriter(f, FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    (OUT / "clips").mkdir(exist_ok=True)
    for r in rows:
        path = OUT / r["clip"]
        if path.is_file() and path.stat().st_size:
            continue
        temporary = path.with_suffix(".partial.mp4")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-ss", r["clip_start_s"], "-i", str(movie), "-t",
                        str(float(r["clip_end_s"]) - float(r["clip_start_s"])),
                        "-map", "0:v:0", "-an", "-c:v", "libx264", "-threads", "4", "-preset",
                        "veryfast", "-crf", "20", str(temporary)], check=True)
        temporary.replace(path)
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Empty clip: {path}")
    validate_clips(rows)
    print(f"Prepared {len(rows)} overlapping windows spanning 0–{rows[-1]['focus_end_s']} s in {WINDOWS}")


def validate_clips(rows):
    movie = Path(rows[0]["movie"])
    duration = film_duration(movie)
    if rows != windows_for(movie, duration):
        raise ValueError("Manifest differs from the full-movie v2 schedule")
    covered = 0.0
    durations = []
    for r in rows:
        start, end = float(r["clip_start_s"]), float(r["clip_end_s"])
        if start > covered + 0.0001 or end <= start:
            raise ValueError(f"Coverage gap or invalid interval: {r['window_id']}")
        covered = max(covered, end)
        path = OUT / r["clip"]
        actual = film_duration(path)
        # Encoded durations can differ by one frame at the cut boundary.
        if abs(actual - (end - start)) > 0.1:
            raise ValueError(f"Incorrect clip duration: {path}: {actual}")
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                        "-map", "0:v:0", "-f", "null", "-"], check=True,
                       capture_output=True)
        durations.append(actual)
    if abs(covered - duration) > 0.0001:
        raise ValueError("Clips do not reach the movie end")
    report = {"validated": True, "settings_hash": rows[0]["settings_hash"],
              "movie_duration_s": duration, "clip_count": len(rows),
              "coverage_start_s": float(rows[0]["clip_start_s"]),
              "coverage_end_s": covered, "gaps": [],
              "decoded_all_clips": True, "encoded_durations_s": durations}
    (OUT / "coverage_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Validated {len(rows)} decodable clips covering 0–{covered:.4f} s", flush=True)


def parse_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def validated_scores(data):
    if not isinstance(data, dict) or not isinstance(data.get("scores"), dict) or not isinstance(data.get("evidence"), dict):
        return None
    if any(type(data["scores"].get(k)) is not int or not 0 <= data["scores"][k] <= 4
           or not isinstance(data["evidence"].get(k), str) for k in LABELS):
        return None
    if any(not isinstance(data.get(k), str) or not data[k].strip()
           for k in ("actions", "visible_reactions", "uncertain_details")):
        return None
    if any(not data["evidence"][k].strip() for k in LABELS):
        return None
    if data.get("uncertainty") not in ("low", "medium", "high"):
        return None
    return data


def recover_interrupted_append():
    if not RESULTS.exists():
        return
    data = RESULTS.read_bytes()
    if not data or data.endswith(b"\n"):
        return
    boundary = data.rfind(b"\n") + 1
    tail = data[boundary:]
    try:
        json.loads(tail)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Preserve interrupted bytes before removing only the incomplete tail.
        with (OUT / "interrupted_appends.bin").open("ab") as backup:
            backup.write(tail + b"\n")
            backup.flush()
            os.fsync(backup.fileno())
        with RESULTS.open("r+b") as f:
            f.truncate(boundary)
            f.flush()
            os.fsync(f.fileno())
    else:
        with RESULTS.open("ab") as f:
            f.write(b"\n")
            f.flush()
            os.fsync(f.fileno())


def completed(rows):
    found = {}
    if RESULTS.exists():
        with RESULTS.open() as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                key = item["window_id"]
                if key in found or item.get("settings_hash") != rows[0]["settings_hash"] or item.get("model") != MODEL_ID:
                    raise ValueError("Duplicate result or incompatible run settings")
                found[key] = item
    if set(found) - {r["window_id"] for r in rows}:
        raise ValueError("Result IDs absent from window manifest")
    return found


def infer():
    rows = read_windows()
    validate_clips(rows)  # Must pass before importing/loading GPU dependencies.
    recover_interrupted_append()
    done = completed(rows)
    pending = [r for r in rows if r["window_id"] not in done]
    if not pending:
        print(f"Nothing pending; {len(done)}/{len(rows)} results")
        return
    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    if not torch.cuda.is_available():
        raise RuntimeError("Run inference on a GPU compute node")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID, dtype=torch.float16, device_map={"": 0},
        attn_implementation="sdpa", low_cpu_mem_usage=True).eval()
    processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=360 * 420)

    def ask(content):
        messages = [{"role": "user", "content": content}]
        video = any(part["type"] == "video" for part in content)
        inputs = processor.apply_chat_template(
            messages, **({"fps": FPS} if video else {}), add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=900, do_sample=False)
        return processor.decode(output[0, inputs["input_ids"].shape[-1]:],
                                skip_special_tokens=True).strip()

    rubric = "\n".join(f"{k}: {v}" for k, v in RUBRIC.items())
    with RESULTS.open("a") as f:
        for r in pending:
            prompt = PROMPT.format(rubric=rubric)
            raw = ask([{"type": "video", "path": str(OUT / r["clip"])},
                       {"type": "text", "text": prompt}])
            parsed = parse_json(raw)
            scores = validated_scores(parsed)
            record = {"window_id": r["window_id"], "settings_hash": r["settings_hash"],
                      "model": MODEL_ID, "fps": FPS, "rubric": RUBRIC,
                      "prompt": prompt, "raw_response": raw, "parsed_response": parsed,
                      "scoring": scores, "parse_valid": scores is not None}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            print(f"Saved {r['window_id']}: {scores['scores'] if scores else 'parse error'}", flush=True)
    print(f"Results: {RESULTS}")


def rank(top, minimum):
    rows = read_windows()
    result = completed(rows)
    if len(result) < len(rows):
        raise ValueError(f"Only {len(result)}/{len(rows)} scored; ranking requires the full run")
    invalid = [key for key, item in result.items() if not validated_scores(item.get("scoring"))]
    print(f"Full run: {len(result)} responses; {len(invalid)} invalid responses excluded from ranking")
    chosen = []
    for label in LABELS:
        valid = [(r, result[r["window_id"]]["scoring"])
                 for r in rows if r["window_id"] in result
                 and validated_scores(result[r["window_id"]]["scoring"])]
        valid.sort(key=lambda item: (-item[1]["scores"][label], float(item[0]["focus_start_s"])))
        accepted = []
        for r, score in valid:
            if score["scores"][label] < minimum:
                break
            start, end = float(r["focus_start_s"]), float(r["focus_end_s"])
            if any(start < float(old["focus_end_s"]) and end > float(old["focus_start_s"])
                   for old, _ in accepted):
                continue
            accepted.append((r, score))
            if len(accepted) == top:
                break
        for position, (r, score) in enumerate(accepted, 1):
            chosen.append({"category": label, "rank": position, "score": score["scores"][label],
                           "evidence": score["evidence"][label], "window_id": r["window_id"],
                           "focus_start_s": r["focus_start_s"], "focus_end_s": r["focus_end_s"],
                           "clip": str((OUT / r["clip"]).resolve()),
                           "observation": json.dumps(result[r["window_id"]]["parsed_response"]),
                           "reviewed_label": "", "review_notes": ""})
    with RANKED.open("w", newline="") as f:
        writer = csv.DictWriter(f, chosen[0].keys() if chosen else
            ("category", "rank", "score", "evidence", "window_id", "focus_start_s",
             "focus_end_s", "clip", "observation", "reviewed_label", "review_notes"))
        writer.writeheader()
        writer.writerows(chosen)
    print(f"Ranked {len(result)}/{len(rows)} scored windows; {len(chosen)} review rows in {RANKED}")
    for label in LABELS:
        print(f"{label}: {sum(x['category'] == label for x in chosen)} distinct candidates")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--movie", type=Path, default=MOVIE)
    p = sub.add_parser("infer")
    sub.add_parser("validate")
    p = sub.add_parser("rank")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--min-score", type=int, default=2)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.movie)
    elif args.command == "infer":
        with (OUT / "inference.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            infer()
    elif args.command == "validate":
        validate_clips(read_windows())
    else:
        if args.top < 1 or not 0 <= args.min_score <= 4:
            parser.error("--top must be positive and --min-score must be 0–4")
        rank(args.top, args.min_score)


if __name__ == "__main__":
    main()
