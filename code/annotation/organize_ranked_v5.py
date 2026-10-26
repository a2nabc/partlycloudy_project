#!/usr/bin/env python3
"""Create review folders for both Qwen v5 rankings."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/qwen_whole_movie_scores_v5_2s_6fps"

RANKINGS = {
    "ranked_top20_min7_other3.csv": "review_other3",
    "ranked_top20_min7_other10.csv": "review_other10",
}
CATEGORIES = ("Mental", "Pain", "Social", "Control")

for csv_name, review_name in RANKINGS.items():
    csv_path = OUT / csv_name
    review_dir = OUT / review_name
    counts = {category: 0 for category in CATEGORIES}

    # Create all four folders, including categories with zero candidates.
    for category in CATEGORIES:
        (review_dir / category.lower()).mkdir(parents=True, exist_ok=True)

    with csv_path.open(newline="") as file:
        for row in csv.DictReader(file):
            category = row["category"]
            if category not in CATEGORIES:
                raise ValueError(f"Unexpected category: {category}")

            # Use the filename from the CSV, but find it in this run's clips folder.
            source = OUT / "clips" / Path(row["clip"]).name
            if not source.is_file():
                raise FileNotFoundError(source)

            folder = review_dir / category.lower()
            destination = folder / f"rank_{int(row['rank']):02d}_{source.name}"

            # From review_other3/mental/, go up twice to reach clips/.
            link_target = Path("..") / ".." / "clips" / source.name

            if destination.is_symlink():
                if destination.resolve() != source.resolve():
                    raise FileExistsError(f"Incorrect existing link: {destination}")
            elif destination.exists():
                raise FileExistsError(f"File already exists: {destination}")
            else:
                destination.symlink_to(link_target)

            counts[category] += 1

    print(f"\n{review_name}/")
    for category in CATEGORIES:
        print(f"  {category.lower()}/: {counts[category]} clips")