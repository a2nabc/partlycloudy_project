#!/usr/bin/env python3
"""Organize Qwen v3 ranked clips into folders for manual review."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/qwen_whole_movie_scores_v3_cartoon"
RANKED = OUT / "ranked_candidates.csv"
CATEGORIES = {"Mental", "Pain", "Social", "Control"}

counts = {category: 0 for category in CATEGORIES}

with RANKED.open(newline="") as file:
    for row in csv.DictReader(file):
        category = row["category"]
        if category not in CATEGORIES:
            raise ValueError(f"Unexpected category: {category}")

        source = OUT / "clips" / f"{row['window_id']}.mp4"
        if not source.is_file():
            raise FileNotFoundError(source)

        folder = OUT / category.lower()
        folder.mkdir(exist_ok=True)

        start = round(float(row["focus_start_s"]))
        end = round(float(row["focus_end_s"]))
        name = (
            f"rank_{int(row['rank']):02d}_"
            f"{row['window_id']}_{start:03d}-{end:03d}s.mp4"
        )
        destination = folder / name

        # A relative link keeps working if the whole project folder is moved.
        link_target = Path("..") / "clips" / source.name
        if destination.is_symlink():
            if destination.resolve() != source.resolve():
                raise FileExistsError(f"Link points to a different file: {destination}")
        elif destination.exists():
            raise FileExistsError(f"File already exists: {destination}")
        else:
            destination.symlink_to(link_target)

        counts[category] += 1

for category in ("Mental", "Pain", "Social", "Control"):
    print(f"{category.lower()}/: {counts[category]} ranked clips")