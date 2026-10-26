#!/usr/bin/env python3
"""Summarize X-CLIP results and plot a movie timeline.

Place in code/xclip/. After both inference phases finish, run:
    python code/xclip/plot_xclip_film.py

Default reads the 8-second, 8-frame results. For another run pass the same
--window-seconds and --frames used for xclip_film_analysis.py.
"""

import argparse
import csv
import json
import math
import os
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LABELS = ("mental", "pain", "social", "control")
GROUPS = ("original", "balanced_a", "balanced_b")


def read_jsonl(path: Path, key: str) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; finish its inference phase first")
    with path.open() as source:
        records = [json.loads(line) for line in source if line.strip()]
    ids = [int(row[key]) for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {key} values in {path}")
    return sorted(records, key=lambda row: int(row[key]))


def scores_array(timeline: list[dict], group: str, label: str) -> np.ndarray:
    return np.asarray([row["scores"][group][label] for row in timeline], dtype=float)


def normalized(values: np.ndarray) -> np.ndarray:
    sd = float(values.std())
    if sd == 0:
        raise ValueError("A score curve has zero variation; inspect the raw results")
    return (values - values.mean()) / sd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-partial", action="store_true",
                        help="For debugging: report incomplete inference without interpreting it")
    parser.add_argument("--window-seconds", type=int, default=8)
    parser.add_argument("--frames", type=int, choices=(8, 16), default=8)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs",
                        help="Directory for regenerable plots and CSVs")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "outputs" / "reports",
                        help="Directory for generated Markdown reports")
    args = parser.parse_args()
    if args.window_seconds <= 0:
        parser.error("--window-seconds must be positive")
    suffix = f"{args.window_seconds}s_{args.frames}f"
    annotations = ROOT / "outputs" / f"xclip_wording_check_{args.frames}f.jsonl"
    timeline_path = ROOT / "outputs" / f"xclip_movie_timeline_{suffix}.jsonl"
    report = args.report_dir / f"xclip_film_report_{suffix}.md"
    csv_path = args.output_dir / f"xclip_timeline_scores_{suffix}.csv"
    png = args.output_dir / f"xclip_timeline_{suffix}.png"
    pdf = args.output_dir / f"xclip_timeline_{suffix}.pdf"
    events = read_jsonl(annotations, "event_id")
    timeline = read_jsonl(timeline_path, "window_id")
    if [int(row["event_id"]) for row in events] != list(range(1, 20)):
        if not args.allow_partial:
            parser.error("Expected all 19 annotation results")
    if [int(row["window_id"]) for row in timeline] != list(range(len(timeline))):
        parser.error("Timeline windows are incomplete or out of order")
    if not timeline:
        parser.error("Timeline has no windows")
    settings = timeline[0]["settings"]
    if (settings["window_seconds"] != args.window_seconds
            or settings["frames_per_clip"] != args.frames):
        parser.error("Timeline settings differ from the requested run")
    if any(row["settings"] != settings or row["model"] != timeline[0]["model"]
           for row in timeline):
        parser.error("Timeline contains mixed settings or models")
    duration = float(timeline[0]["movie_duration_s"])
    expected = math.floor((duration - args.window_seconds)
                          / settings["stride_seconds"]) + 1
    if len(timeline) != expected and not args.allow_partial:
        parser.error(f"Expected {expected} complete windows; found {len(timeline)}")
    if events and any(row["model"] != timeline[0]["model"] for row in events):
        parser.error("Annotation and timeline checkpoints do not match")
    if any(set(row["scores"]) != set(GROUPS) for row in events + timeline):
        parser.error("Missing a description set in the saved scores")

    centers = np.asarray([(float(row["start_s"]) + float(row["end_s"])) / 2
                          for row in timeline])
    time_start = np.asarray([float(row["start_s"]) for row in timeline])
    curves = {(group, label): scores_array(timeline, group, label)
              for group in GROUPS for label in LABELS}
    z = {key: normalized(values) for key, values in curves.items()}
    spans = {label: [(float(row["movie_onset_s"]),
                      float(row["movie_onset_s"]) + float(row["duration_s"]))
                     for row in events if row["human_condition"] == label]
             for label in LABELS}

    # Four synchronized panels: one for each semantic description.
    fig, axes = plt.subplots(4, 1, figsize=(13, 9), sharex=True, layout="constrained")
    styles = {
        "original": ("#858585", ":", "Original wording"),
        "balanced_a": ("#3166aa", "-", "Balanced A"),
        "balanced_b": ("#d57932", "--", "Balanced B"),
    }
    for ax, label in zip(axes, LABELS):
        for start, end in spans[label]:
            ax.axvspan(start, end, color="#a9cda8", alpha=.45, lw=0)
        for group in GROUPS:
            color, linestyle, name = styles[group]
            ax.plot(centers, z[group, label], color=color, ls=linestyle,
                    lw=1.35, label=name)
        ax.axhline(0, color="#36495b", lw=.6, alpha=.45)
        ax.set_ylabel(label.title() + "\n(z-score)", rotation=0,
                      ha="right", va="center", labelpad=24)
        ax.grid(axis="x", alpha=.17)
    axes[0].legend(loc="upper right", ncol=3, fontsize=9)
    axes[-1].set_xlabel("Movie time (seconds)")
    axes[-1].set_xlim(0, max(float(row["end_s"]) for row in timeline))
    fig.suptitle("X-CLIP video-text similarity across Partly Cloudy\n"
                 "Green bands: human-annotated intervals; "
                 "each curve is standardized across the film", fontsize=13)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=175)
    fig.savefig(pdf)
    plt.close(fig)

    with csv_path.open("w", newline="") as target:
        columns = ["window_id", "start_s", "end_s"]
        columns += [f"{group}_{label}" for group in GROUPS for label in LABELS]
        columns += [f"{group}_{label}_z" for group in GROUPS for label in LABELS]
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        for i, record in enumerate(timeline):
            row = {k: record[k] for k in ("window_id", "start_s", "end_s")}
            for group in GROUPS:
                for label in LABELS:
                    row[f"{group}_{label}"] = record["scores"][group][label]
                    row[f"{group}_{label}_z"] = round(float(z[group, label][i]), 5)
            writer.writerow(row)

    lines = [
        f"# X-CLIP across Partly Cloudy: {args.window_seconds}-second windows, "
        f"{args.frames} frames", "",
        f"{len(events)} annotated clips; {len(timeline)} {args.window_seconds}-second "
        f"windows starting {settings['stride_seconds']} second(s) apart. "
        f"Each window contains {args.frames} frames spread across its duration "
        f"from a {settings['timeline_sampling_hz']}-Hz grid.",
        f"Pretrained checkpoint: `{timeline[0]['model']}`; no fine-tuning.", "",
        "The two balanced wordings were chosen after seeing that the original "
        "Control description dominated the pilot. This is an exploratory "
        "sensitivity check, not an independent validation set.", "",
        "## Wording check on manually selected clips", "",
        "| Description set | Human category ranks first | Control ranks first | "
        "Events whose top category changes vs original |", "|:---|---:|---:|---:|",
    ]
    original_top = [max(LABELS, key=row["scores"]["original"].get) for row in events]
    for group in GROUPS:
        top = [max(LABELS, key=row["scores"][group].get) for row in events]
        human_top = sum(name == row["human_condition"] for name, row in zip(top, events))
        lines.append(f"| {group} | {human_top}/{len(events)} | "
                     f"{Counter(top)['control']}/{len(events)} | "
                     f"{sum(a != b for a,b in zip(original_top, top))}/{len(events)} |")
    lines.extend([
        "", "## Scores across movie time", "",
        f"![X-CLIP movie timeline]({os.path.relpath(png, report.parent)})", "",
        "Values in the plot are standardized separately for each description "
        "and wording set across the movie. Zero is that curve's own movie average; "
        "positive values are above its average. Do not compare these z-scores "
        "numerically with Qwen's 0--3 generated ratings.", "",
        "| Human interval | Windows centered inside it | Original: inside - outside | "
        "Balanced A | Balanced B |",
        "|:---|---:|---:|---:|---:|",
    ])
    for label in LABELS:
        inside = np.zeros(len(timeline), dtype=bool)
        for start, end in spans[label]:
            inside |= (centers >= start) & (centers < end)
        if not inside.any() or inside.all():
            raise ValueError(f"No valid inside/outside comparison for {label}")
        deltas = [z[group, label][inside].mean() - z[group, label][~inside].mean()
                  for group in GROUPS]
        lines.append(f"| {label.title()} | {inside.sum()} | "
                     + " | ".join(f"{value:+.2f}" for value in deltas) + " |")
    lines += [
        "", "**How to read the last table.** A positive value means the "
        "description's similarity is higher, on average, in windows centered "
        "within the manual intervals than at other movie times. These are "
        "descriptive differences, not statistical significance tests. The "
        "other movie times are not verified negatives, and sliding windows "
        "overlap. A long window centered within an annotation may include "
        "movie content outside that interval. The manual labels may also "
        "overlap in meaning.", "",
        f"Full raw logits and z-scores: [{csv_path.name}]({os.path.relpath(csv_path, report.parent)}).", "",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines))
    print(f"Saved {report}, {csv_path}, {png}, and {pdf}")


if __name__ == "__main__":
    main()
