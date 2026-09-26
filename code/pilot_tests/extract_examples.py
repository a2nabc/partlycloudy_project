#!/usr/bin/env python3
"""Extract the 19 hand-coded Partly Cloudy events from the shared movie.

Run from the project repository with:
    python code/extract_events.py

The CSV contains the original onsets from mov_localizer.m. Those onsets
include a 10-second fixation period before the movie. Subtract 10 seconds
to locate each event in the movie file; generate_logs.m uses the same
conversion. --offset-seconds allows the conversion to be changed when
checking a different movie file.
"""

import argparse
import csv
import subprocess
from pathlib import Path

DEFAULT_MOVIE = Path(
    "/m/nbe/project/partlycloudy/moviestimulus/partly_cloudy_sd_nocredits.mov"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def video_duration(movie: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(movie),
        ],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--movie", type=Path, default=DEFAULT_MOVIE)
    parser.add_argument(
        "--annotations", type=Path,
        default=PROJECT_ROOT / "notes" / "manual_annotations.csv",
    )
    parser.add_argument(
        "--offset-seconds", type=float, default=-10.0,
        help="Seconds added to each original onset to obtain movie time (default: -10)",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    movie = args.movie.expanduser().resolve()
    annotations = args.annotations.expanduser().resolve()
    if not movie.is_file():
        parser.error(f"Movie not found: {movie}")
    if not annotations.is_file():
        parser.error(f"Annotation CSV not found: {annotations}")

    offset_tag = f"{args.offset_seconds:+g}".replace("+", "plus").replace("-", "minus")
    output_dir = args.output_dir or PROJECT_ROOT / "outputs" / f"clips_offset_{offset_tag}s"
    output_dir.mkdir(parents=True, exist_ok=True)
    movie_length = video_duration(movie)

    with annotations.open(newline="") as source:
        reader = csv.DictReader(source)
        required = {"condition", "onset_s", "duration_s"}
        if not required.issubset(reader.fieldnames or []):
            parser.error(f"CSV needs these columns: {', '.join(sorted(required))}")
        rows = list(reader)

    if len(rows) != 19:
        parser.error(f"Expected 19 events; found {len(rows)} in {annotations}")

    events = []
    for index, row in enumerate(rows, start=1):
        try:
            original_onset = float(row["onset_s"])
            duration = float(row["duration_s"])
        except ValueError as exc:
            parser.error(f"Invalid number on CSV event {index}: {exc}")
        start = original_onset + args.offset_seconds
        end = start + duration
        if duration <= 0 or start < 0 or end > movie_length + 0.05:
            parser.error(
                f"Event {index} ({row['condition']}) is outside the movie: "
                f"{start:g}–{end:g} s; movie lasts {movie_length:g} s. "
                "Check the offset and movie version."
            )
        name = f"{index:02d}_{row['condition']}_{start:g}-{end:g}s.mp4"
        events.append((index, row["condition"], original_onset, duration,
                       start, end, output_dir / name))

    for index, condition, original, duration, start, end, destination in events:
        if not destination.exists() or args.overwrite:
            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(movie), "-ss", str(start), "-t", str(duration),
                "-map", "0:v:0", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-movflags", "+faststart", str(destination),
            ]
            subprocess.run(command, check=True)
        print(f"{index:02d} {condition:7s} CSV {original:g}s -> movie {start:g}–{end:g}s")

    manifest = output_dir / "manifest.csv"
    with manifest.open("w", newline="") as target:
        writer = csv.writer(target)
        writer.writerow([
            "event_id", "condition", "baseonset_s", "offset_s",
            "movie_onset_s", "duration_s", "movie_end_s", "filename",
        ])
        for index, condition, original, duration, start, end, destination in events:
            writer.writerow([
                index, condition, original, args.offset_seconds,
                start, duration, end, destination.name,
            ])
    print(f"Saved {len(events)} clips and {manifest}")


if __name__ == "__main__":
    main()
