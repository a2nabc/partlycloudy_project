#!/usr/bin/env python3
"""Retrieve cartoon event candidates across the entire Partly Cloudy movie.

From the project root:
    python code/annotation/qwen_whole_movie_scores_v5_2s.py prepare
    # On a GPU node, with HF_HOME pointing to scratch:
    python code/annotation/qwen_whole_movie_scores_v5_2s.py infer
    python code/annotation/qwen_whole_movie_scores_v5_2s.py rank

The manual annotation manifest is never opened. Scores are retrieval aids,
not probabilities or replacements for direct human review.
"""

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOVIE = ROOT / "moviestimulus/partly_cloudy_sd_nocredits.mov"
OUT = ROOT / "outputs/qwen_whole_movie_scores_v5_2s_6fps"
WINDOWS = OUT / "windows.csv"
RESULTS = OUT / "scores.jsonl"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
FOCUS = 2.0
STRIDE = 1.0
FPS = 6.0
LABELS = ("Mental", "Pain", "Social", "Control")
VERSION = 5

RUBRIC = {
    "Mental": (
        "Visible events lead the viewer to infer what a character thinks, "
        "believes, expects, or intends. A smile, surprise, distress, or "
        "ordinary purposeful movement alone is not strong evidence."
    ),
    "Pain": (
        "A character visibly undergoes a physically painful event or shows "
        "its immediate reaction. Cartoon pain can involve exaggerated recoil, "
        "flailing, an open-mouthed cry, or a changed body after contact; a "
        "realistic injury is not required. Fear or crying alone is insufficient."
    ),
    "Social": (
        "Characters visibly interact or respond to one another by directed "
        "actions such as exchanging, playing, helping, avoiding, or comforting. "
        "The expressive cloud and bird are both characters. Mere co-presence "
        "or flight near another character is insufficient."
    ),
    "Control": (
        "A clearly visible event whose focus is not a specific character-related "
        "event, such as a wide view of clouds or distant birds flying without "
        "an individual's action or reaction in focus. This does not mean a "
        "character controls its body, flight, or surroundings."
    ),
}

PROMPT = """Watch the entire supplied silent two-second cartoon clip. Judge only
what is actually visible within it. The expressive cloud, bird, and other
animated creatures are characters.

Briefly describe actions in chronological order, including physical contact
and each immediate visible reaction. Do not invent actions between frames.
Separate what is visible from what is uncertain.

Independently score the four conditions using these definitions:
{rubric}

Use integers from 0 to 10: 0 = absent; 1-3 = weak or ambiguous;
4-6 = plausible; 7-9 = clear and strong; 10 = defining example.
If your evidence says a condition is absent, score it 0, not 1 or 2.
More than one condition may have evidence, but do not infer evidence from
the mere presence of a character. Do not score Control for an animated
character's ability to fly or move. Do not score Pain for fear alone.
Do not score Mental highly for a smile alone. Do not assume story events
that are not visible in this clip.

Return ONLY a concise JSON object with these fields:
"actions" (string), "visible_reactions" (string),
"uncertain_details" (string; use "none" if needed),
"scores" (object with integer keys Mental, Pain, Social, Control),
"evidence" (object with nonempty string keys Mental, Pain, Social, Control),
"uncertainty" (one of "low", "medium", "high").
For every condition, state the visible evidence or why it is absent or
ambiguous. Do not copy definitions as evidence. Keep each string short.
"""

FIELDS = (
    "window_id", "focus_start_s", "focus_end_s", "clip_start_s",
    "clip_end_s", "clip", "movie", "settings_hash",
)
RANK_FIELDS = (
    "category", "rank", "score", "max_other_score", "all_scores",
    "evidence", "window_id", "focus_start_s", "focus_end_s", "clip",
    "observation", "reviewed_label", "review_notes",
)


def film_duration(movie):
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(movie)],
        check=True, capture_output=True, text=True,
    )
    return float(run.stdout.strip())


def settings_hash(movie, duration):
    payload = [VERSION, str(movie), round(duration, 4), FOCUS, STRIDE,
               FPS, MODEL_ID, RUBRIC, PROMPT]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def time_tag(seconds):
    if abs(seconds - round(seconds)) < 1e-6:
        return f"{round(seconds):03d}"
    return f"{seconds:07.3f}"


def windows_for(movie, duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Movie duration must be positive")
    starts = [i * STRIDE for i in range(
        math.floor(max(0, duration - FOCUS) / STRIDE) + 1
    )]
    final = max(0.0, duration - FOCUS)
    if final - starts[-1] > 0.00001:
        starts.append(final)
    config = settings_hash(movie, duration)
    rows = []
    for i, start in enumerate(starts):
        end = min(duration, start + FOCUS)
        rows.append({
            "window_id": f"window_{i:04d}",
            "focus_start_s": f"{start:.4f}",
            "focus_end_s": f"{end:.4f}",
            "clip_start_s": f"{start:.4f}",
            "clip_end_s": f"{end:.4f}",
            "clip": (
                f"clips/window_{i:04d}_{time_tag(start)}-"
                f"{time_tag(end)}s.mp4"
            ),
            "movie": str(movie),
            "settings_hash": config,
        })
    return rows


def read_windows():
    if not WINDOWS.is_file():
        raise FileNotFoundError(f"Run prepare first: {WINDOWS}")
    with WINDOWS.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or tuple(rows[0]) != FIELDS:
        raise ValueError("Invalid window manifest")
    if (len({r["window_id"] for r in rows}) != len(rows)
            or len({r["settings_hash"] for r in rows}) != 1):
        raise ValueError("Duplicate IDs or mixed settings in window manifest")
    return rows


def validate_clips(rows):
    movie = Path(rows[0]["movie"])
    duration = film_duration(movie)
    if rows != windows_for(movie, duration):
        raise ValueError("Manifest differs from the complete v5 schedule")
    covered = 0.0
    encoded_durations = []
    for r in rows:
        start, end = float(r["clip_start_s"]), float(r["clip_end_s"])
        if start > covered + 0.0001 or end <= start:
            raise ValueError(f"Coverage gap or invalid interval: {r['window_id']}")
        covered = max(covered, end)
        path = OUT / r["clip"]
        actual = film_duration(path)
        if abs(actual - (end - start)) > 0.1:
            raise ValueError(f"Incorrect clip duration: {path}: {actual}")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
             "-map", "0:v:0", "-f", "null", "-"],
            check=True, capture_output=True,
        )
        encoded_durations.append(actual)
    if abs(covered - duration) > 0.0001:
        raise ValueError("Clips do not reach the movie end")
    report = {
        "validated": True, "settings_hash": rows[0]["settings_hash"],
        "movie_duration_s": duration, "clip_count": len(rows),
        "coverage_start_s": float(rows[0]["clip_start_s"]),
        "coverage_end_s": covered, "gaps": [],
        "decoded_all_clips": True, "encoded_durations_s": encoded_durations,
    }
    (OUT / "coverage_validation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(f"Validated {len(rows)} decodable clips covering 0–{covered:.4f} s",
          flush=True)


def prepare(movie):
    if not movie.is_file():
        raise FileNotFoundError(movie)
    movie = movie.resolve()
    rows = windows_for(movie, film_duration(movie))
    if WINDOWS.exists():
        if read_windows() != rows:
            raise ValueError(
                "Existing run has different settings; use a new OUT directory"
            )
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
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", r["clip_start_s"], "-i", str(movie),
             "-t", str(float(r["clip_end_s"]) - float(r["clip_start_s"])),
             "-map", "0:v:0", "-an", "-c:v", "libx264", "-threads", "4",
             "-preset", "veryfast", "-crf", "20", str(temporary)],
            check=True,
        )
        temporary.replace(path)
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Empty clip: {path}")
    validate_clips(rows)
    print(f"Prepared {len(rows)} windows in {WINDOWS}")


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
    if (not isinstance(data, dict)
            or not isinstance(data.get("scores"), dict)
            or not isinstance(data.get("evidence"), dict)):
        return None
    result = data.copy()
    for key in ("actions", "visible_reactions", "uncertain_details"):
        if isinstance(result.get(key), list):
            result[key] = " ".join(
                str(item).strip() for item in result[key] if str(item).strip()
            )
        if not isinstance(result.get(key), str) or not result[key].strip():
            return None
    if any(type(result["scores"].get(k)) is not int
           or not 0 <= result["scores"][k] <= 10
           or not isinstance(result["evidence"].get(k), str)
           or not result["evidence"][k].strip() for k in LABELS):
        return None
    if result.get("uncertainty") not in ("low", "medium", "high"):
        return None
    return result


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
                if (key in found
                        or item.get("settings_hash") != rows[0]["settings_hash"]
                        or item.get("model") != MODEL_ID):
                    raise ValueError("Duplicate result or incompatible settings")
                found[key] = item
    if set(found) - {r["window_id"] for r in rows}:
        raise ValueError("Result IDs absent from manifest")
    return found


def infer():
    rows = read_windows()
    validate_clips(rows)
    recover_interrupted_append()
    done = completed(rows)
    pending = [r for r in rows if r["window_id"] not in done]
    if not pending:
        print(f"Nothing pending; {len(done)}/{len(rows)} responses saved")
        return
    import torch
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    if not torch.cuda.is_available():
        raise RuntimeError("Run inference on a GPU compute node")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID, dtype=torch.float16, device_map={"": 0},
        attn_implementation="sdpa", low_cpu_mem_usage=True,
    ).eval()
    processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=360 * 420)
    rubric = "\n".join(f"{k}: {v}" for k, v in RUBRIC.items())
    prompt = PROMPT.format(rubric=rubric)

    with RESULTS.open("a") as f:
        for r in pending:
            messages = [{"role": "user", "content": [
                {"type": "video", "path": str(OUT / r["clip"])},
                {"type": "text", "text": prompt},
            ]}]
            inputs = processor.apply_chat_template(
                messages, fps=FPS, add_generation_prompt=True,
                tokenize=True, return_dict=True, return_tensors="pt",
            ).to("cuda")
            with torch.inference_mode():
                output = model.generate(
                    **inputs, max_new_tokens=600, do_sample=False,
                )
            raw = processor.decode(
                output[0, inputs["input_ids"].shape[-1]:],
                skip_special_tokens=True,
            ).strip()
            parsed = parse_json(raw)
            scoring = validated_scores(parsed)
            record = {
                "window_id": r["window_id"], "settings_hash": r["settings_hash"],
                "model": MODEL_ID, "fps": FPS, "rubric": RUBRIC,
                "prompt": prompt, "raw_response": raw,
                "parsed_response": parsed, "scoring": scoring,
                "parse_valid": scoring is not None,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            print(f"Saved {r['window_id']}: "
                  f"{scoring['scores'] if scoring else 'invalid response'}",
                  flush=True)
    print(f"Results: {RESULTS}")


def rank(top, minimum, max_other):
    rows = read_windows()
    result = completed(rows)
    if len(result) < len(rows):
        raise ValueError(
            f"Only {len(result)}/{len(rows)} responses saved; rank after infer"
        )
    invalid = [key for key, item in result.items()
               if not validated_scores(item.get("scoring"))]
    print(f"Full run: {len(result)} responses; {len(invalid)} invalid excluded")
    chosen = []
    for label in LABELS:
        valid = [
            (r, validated_scores(result[r["window_id"]].get("scoring")))
            for r in rows
        ]
        valid = [(r, score) for r, score in valid if score is not None]
        valid.sort(key=lambda item: (
            -item[1]["scores"][label],
            max(item[1]["scores"][other] for other in LABELS if other != label),
            sum(item[1]["scores"][other] for other in LABELS if other != label),
            float(item[0]["focus_start_s"]),
        ))
        accepted = []
        for r, score in valid:
            target = score["scores"][label]
            if target < minimum:
                break
            other_max = max(score["scores"][other]
                            for other in LABELS if other != label)
            if other_max > max_other:
                continue
            start, end = float(r["focus_start_s"]), float(r["focus_end_s"])
            if any(start < float(old["focus_end_s"])
                   and end > float(old["focus_start_s"])
                   for old, _ in accepted):
                continue
            accepted.append((r, score))
            if len(accepted) == top:
                break
        for position, (r, score) in enumerate(accepted, 1):
            chosen.append({
                "category": label,
                "rank": position,
                "score": score["scores"][label],
                "max_other_score": max(score["scores"][other]
                                       for other in LABELS if other != label),
                "all_scores": json.dumps(score["scores"]),
                "evidence": score["evidence"][label],
                "window_id": r["window_id"],
                "focus_start_s": r["focus_start_s"],
                "focus_end_s": r["focus_end_s"],
                "clip": str((OUT / r["clip"]).resolve()),
                "observation": json.dumps(
                    result[r["window_id"]]["parsed_response"],
                    ensure_ascii=False,
                ),
                "reviewed_label": "", "review_notes": "",
            })
    ranked = OUT / f"ranked_top{top}_min{minimum}_other{max_other}.csv"
    with ranked.open("w", newline="") as f:
        writer = csv.DictWriter(f, RANK_FIELDS)
        writer.writeheader()
        writer.writerows(chosen)
    print(f"Saved {len(chosen)} review rows to {ranked}")
    for label in LABELS:
        print(f"{label}: {sum(x['category'] == label for x in chosen)} candidates")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--movie", type=Path, default=MOVIE)
    sub.add_parser("infer")
    sub.add_parser("validate")
    p = sub.add_parser("rank")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--min-score", type=int, default=7)
    p.add_argument("--max-other", type=int, default=3)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.movie)
    elif args.command == "infer":
        if not WINDOWS.is_file():
            raise FileNotFoundError(f"Run prepare first: {WINDOWS}")
        with (OUT / "inference.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            infer()
    elif args.command == "validate":
        validate_clips(read_windows())
    else:
        if (args.top < 1 or not 0 <= args.min_score <= 10
                or not 0 <= args.max_other <= 10):
            parser.error("--top must be positive; scores must be 0–10")
        rank(args.top, args.min_score, args.max_other)


if __name__ == "__main__":
    main()
