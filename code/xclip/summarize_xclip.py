#!/usr/bin/env python3
"""Make human-readable and Overleaf tables from X-CLIP's 19-event JSONL.

Run after python code/legacy/xclip_video_pilot.py has completed all 19 clips:
    python code/xclip/summarize_xclip.py

For a preliminary table from fewer clips:
    python code/xclip/summarize_xclip.py --allow-partial
"""

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "outputs/xclip_base_19_events.jsonl"
OUT = ROOT / "outputs" / "reports"
LABELS = ("mental", "pain", "social", "control")


def read_records(path: Path) -> list[dict]:
    records = {}
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            event_id = int(record["event_id"])
            if event_id in records:
                raise ValueError(f"Duplicate event {event_id} at line {line_number}")
            human = record["human_condition"]
            scores = record["similarity_logits"]
            if human not in LABELS or set(scores) != set(LABELS):
                raise ValueError(f"Invalid labels for event {event_id}")
            if not all(math.isfinite(float(scores[label])) for label in LABELS):
                raise ValueError(f"Non-finite score for event {event_id}")
            records[event_id] = record
    return [records[event_id] for event_id in sorted(records)]


def fields(record: dict) -> tuple[str, str, dict, str, float, int]:
    scores = {name: float(record["similarity_logits"][name]) for name in LABELS}
    human = record["human_condition"]
    best = max(LABELS, key=scores.get)
    margin = scores[human] - max(scores[name] for name in LABELS if name != human)
    rank = 1 + sum(scores[name] > scores[human] for name in LABELS if name != human)
    onset = float(record["movie_onset_s"])
    end = onset + float(record["duration_s"])
    return human, f"{onset:g}--{end:g}", scores, best, margin, rank


def make_markdown(records: list[dict]) -> str:
    ranks = Counter()
    top = Counter()
    lines = [
        f"# X-CLIP pilot: {len(records)} manually annotated Partly Cloudy events",
        "",
        "Model: `microsoft/xclip-base-patch32`; eight evenly spaced video frames per clip.",
        "Four fixed candidate text descriptions were used for every clip; see the JSONL for their exact wording.",
        "Values are video--text similarity logits, **not probabilities or independent category ratings**.",
        "Bold marks the human-annotated category. `Top` is the model's highest of the four.",
        "`Margin` = human-category score minus the highest alternative (positive means human category ranked first).",
        "",
        "| Event | Movie time (s) | Human | Mental | Pain | Social | Control | Top | Margin |",
        "|---:|:---|:---|---:|---:|---:|---:|:---|---:|",
    ]
    for record in records:
        human, time, scores, best, margin, rank = fields(record)
        ranks[rank] += 1
        top[best] += 1
        cell = {label: f"{scores[label]:.2f}" for label in LABELS}
        cell[human] = f"**{cell[human]}**"
        lines.append(
            f"| {int(record['event_id'])} | {time.replace('--', '–')} | {human.title()} | "
            + " | ".join(cell[label] for label in LABELS)
            + f" | {best.title()} | {margin:+.2f} |"
        )
    lines.extend([
        "", "## Brief reading", "",
        f"- Human category ranked first for {ranks[1]}/{len(records)} clips.",
        "- Highest model score by category: "
        + ", ".join(f"{label.title()} {top[label]}" for label in LABELS) + ".",
        "- A first-place rank is relative to these four particular text descriptions. "
        "A small margin is a near tie, not strong evidence of a match.",
        "- The 19 manually selected intervals are a small, non-exhaustive sample; "
        "unannotated moments are not automatically Control.",
        "",
    ])
    return "\n".join(lines)


def make_latex(records: list[dict]) -> str:
    lines = [
        "% Paste into Overleaf. Requires \\usepackage{booktabs} in the preamble.",
        "\\begin{table}[htbp]",
        "\\centering\\scriptsize",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabular}{rllrrrrlr}",
        "\\toprule",
        "Event & Time (s) & Human & Mental & Pain & Social & Control & Top & Margin \\\\ ",
        "\\midrule",
    ]
    for record in records:
        human, time, scores, best, margin, _ = fields(record)
        cell = {label: f"{scores[label]:.2f}" for label in LABELS}
        cell[human] = "\\textbf{" + cell[human] + "}"
        lines.append(
            f"{int(record['event_id'])} & {time} & {human.title()} & "
            + " & ".join(cell[label] for label in LABELS)
            + f" & {best.title()} & {margin:+.2f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\caption{X-CLIP video--text similarity logits for the annotated events. "
        "Eight frames were sampled uniformly within each clip. Bold indicates "
        "the human category; Top is the largest of the four logits. Margin is "
        "the human-category logit minus the highest alternative. Values are "
        "relative similarity scores, not calibrated probabilities.}",
        "\\label{tab:xclip-partly-cloudy}",
        "\\end{table}",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"X-CLIP JSONL not found: {args.input}")
    records = read_records(args.input)
    ids = {int(record["event_id"]) for record in records}
    missing = sorted(set(range(1, 20)) - ids)
    if missing and not args.allow_partial:
        parser.error(
            f"Missing events {missing}. First finish with "
            "python code/legacy/xclip_video_pilot.py, or use --allow-partial."
        )
    if any(event_id not in range(1, 20) for event_id in ids):
        parser.error("Found an event ID outside 1--19")
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "partial" if missing else "19_events"
    md = OUT / f"xclip_{suffix}_report.md"
    tex = OUT / f"xclip_{suffix}_table.tex"
    md.write_text(make_markdown(records))
    tex.write_text(make_latex(records))
    print(f"Wrote {len(records)} events to {md} and {tex}")
    if missing:
        print(f"Still missing events: {missing}")


if __name__ == "__main__":
    main()
