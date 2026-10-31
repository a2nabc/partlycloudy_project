#!/usr/bin/env python3
"""Convert ranked candidate focus intervals to MATLAB timing files.

Uses only the Python standard library; additionally writes .mat when SciPy
is installed. The generated .m script can create the same .mat in MATLAB.
No scores, labels, or intervals are selected, relabelled, or merged.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile


DATASETS = {
    'v2': 'qwen_whole_movie_scores_v2_no_context/ranked_candidates.csv',
    'v3': 'qwen_whole_movie_scores_v3_cartoon/ranked_candidates.csv',
    'v5_other3': 'qwen_whole_movie_scores_v5_2s_6fps/ranked_top20_min7_other3.csv',
    'v5_other10': 'qwen_whole_movie_scores_v5_2s_6fps/ranked_top20_min7_other10.csv',
}


def read_candidates(path, offset=0.0):
    if not math.isfinite(offset):
        raise ValueError('Movie offset must be finite.')
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'category', 'focus_start_s', 'focus_end_s', 'window_id'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Missing required columns: ' + ', '.join(sorted(required - set(reader.fieldnames or []))))
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'CSV row {line}: malformed row.')
            category = row['category'].strip().lower()
            if not re.fullmatch(r'[a-z][a-z0-9_]*', category):
                raise ValueError(f'CSV row {line}: invalid category {category!r}.')
            start, end = float(row['focus_start_s']), float(row['focus_end_s'])
            if not all(math.isfinite(x) for x in (start, end)) or start < 0 or end <= start:
                raise ValueError(f'CSV row {line}: expected finite 0 <= start < end.')
            if not math.isfinite(start + offset):
                raise ValueError(f'CSV row {line}: offset causes overflow.')
            rows.append(dict(source_row=line, original=row, category=category,
                             start=start, end=end, onset=start + offset, duration=end-start))
    if not rows:
        raise ValueError('Input contains no candidate rows.')
    return rows


def group_candidates(rows):
    categories = list(dict.fromkeys(r['category'] for r in rows))
    preferred = ['mental', 'pain', 'social', 'control', 'faces']
    categories.sort(key=lambda x: (preferred.index(x) if x in preferred else len(preferred), x))
    return {c: sorted((r for r in rows if r['category'] == c),
                      key=lambda r: (r['start'], r['end'], r['source_row'])) for c in categories}


def overlap_pairs(rows):
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            overlap = min(a['end'], b['end']) - max(a['start'], b['start'])
            if overlap > 0:
                pairs.append(dict(source_rows=[a['source_row'], b['source_row']],
                                  categories=[a['category'], b['category']],
                                  window_ids=[a['original']['window_id'], b['original']['window_id']],
                                  overlap_seconds=overlap))
    return pairs


def matlab_text(groups, offset):
    lines = [
        '% Generated candidate WINDOW timings, not validated event boundaries.',
        '% Units: seconds. Source origin: beginning of source movie.',
        '% No HRF shift, filtering, relabelling, or overlap merging applied.',
        '% Reviewed labels are retained in candidate_events.csv, not applied.',
        '% These timings do NOT describe a newly assembled clip-presentation run.',
        f'movie_offset_seconds = {offset:.15g};',
        "timing_reference = 'source_movie_start_plus_offset';",
        "names = {}; onsets = {}; durations = {};",
        "conds = struct('names', {}, 'onsets', {}, 'durs', {});",
    ]
    for i, (category, rows) in enumerate(groups.items(), 1):
        vector = lambda field: '[' + ' '.join(f'{r[field]:.15g}' for r in rows) + ']'
        lines += [f"names{{{i}}} = '{category}';",
                  f'onsets{{{i}}} = {vector("onset")};',
                  f'durations{{{i}}} = {vector("duration")};',
                  f'conds({i}).names = names{{{i}}};',
                  f'conds({i}).onsets = onsets{{{i}}};',
                  f'conds({i}).durs = durations{{{i}}};']
    lines += ["save(fullfile(fileparts(mfilename('fullpath')), 'conditions.mat'), ...",
              "    'names', 'onsets', 'durations', 'conds', 'movie_offset_seconds', 'timing_reference');", '']
    return '\n'.join(lines)


def write_mat(path, groups, offset):
    try:
        import numpy as np
        from scipy.io import savemat
    except ImportError:
        return False
    n = len(groups)
    names, onsets, durations = (np.empty((1, n), dtype=object) for _ in range(3))
    conds = np.empty((1, n), dtype=[('names', object), ('onsets', object), ('durs', object)])
    for i, (category, rows) in enumerate(groups.items()):
        names[0, i] = category
        onsets[0, i] = np.array([[r['onset'] for r in rows]])
        durations[0, i] = np.array([[r['duration'] for r in rows]])
        conds[0, i] = (category, onsets[0, i], durations[0, i])
    savemat(str(path), dict(names=names, onsets=onsets, durations=durations,
                           conds=conds, movie_offset_seconds=offset,
                           timing_reference='source_movie_start_plus_offset'))
    return True


def export(source, output, offset=0.0):
    rows = read_candidates(source, offset)
    groups = group_candidates(rows)
    fields = ['source_csv_row', 'export_condition', 'export_onset_s', 'export_duration_s']
    if set(fields) & set(rows[0]['original']):
        raise ValueError('Input already has reserved export columns.')
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory is not empty; choose a new directory to preserve existing files.')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'conditions.m').write_text(matlab_text(groups, offset), encoding='utf-8')
    # Original columns are kept verbatim, including review fields and evidence.
    with (output / 'candidate_events.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + list(rows[0]['original']))
        writer.writeheader()
        for items in groups.values():
            for r in items:
                writer.writerow(dict(r['original'], source_csv_row=r['source_row'],
                                     export_condition=r['category'], export_onset_s=r['onset'],
                                     export_duration_s=r['duration']))
    mat_written = write_mat(output / 'conditions.mat', groups, offset)
    report = dict(source=str(Path(source).resolve()),
                  source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                  source_time_reference='Assumed source movie seconds; confirm against windows.csv / generating script.',
                  movie_offset_seconds=offset, hrf_shift_applied=False,
                  selection='All input rows; category column used; reviewed_label not applied.',
                  timing_meaning='Candidate focus-window boundaries, not within-window event detections.',
                  category_counts={c: len(items) for c, items in groups.items()},
                  blank_review_labels=sum(not r['original'].get('reviewed_label', '').strip() for r in rows),
                  overlaps=overlap_pairs(rows), mat_written=mat_written)
    (output / 'conversion_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def batch_export(project_root, datasets, output_root=None, offset=0.0):
    """Each invocation creates a unique run folder, including a status manifest."""
    if not math.isfinite(offset):
        raise ValueError('Movie offset must be finite.')
    project_root = Path(project_root).expanduser().resolve()
    if not (project_root / 'outputs').is_dir():
        raise ValueError(f'Project outputs directory not found: {project_root / "outputs"}')
    output_root = Path(output_root).expanduser() if output_root else project_root / 'outputs' / 'matlab_timings'
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = Path(tempfile.mkdtemp(prefix=f'run_{stamp}_', dir=output_root)).resolve()
    results = {}
    for key in dict.fromkeys(datasets):
        source = project_root / 'outputs' / DATASETS[key]
        destination = run_dir / key
        if not source.is_file():
            results[key] = dict(status='missing', source=str(source))
            continue
        try:
            report = export(source, destination, offset)
            results[key] = dict(status='ok', source=str(source), output=str(destination),
                                category_counts=report['category_counts'],
                                mat_written=report['mat_written'],
                                overlap_pairs=len(report['overlaps']))
        except (ValueError, OSError) as error:
            results[key] = dict(status='failed', source=str(source), error=str(error))
    manifest = dict(project_root=str(project_root), movie_offset_seconds=offset,
                    run_directory=str(run_dir), datasets=results)
    (run_dir / 'batch_report.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_csv', nargs='?', type=Path,
                        help='Optional single CSV; omit to process the configured project datasets.')
    parser.add_argument('--output-dir', type=Path,
                        help='Batch mode: parent for unique run folders. Single CSV: exact empty destination.')
    parser.add_argument('--project-root', type=Path,
                        help='Path to partlycloudy_project. Defaults to the parent of this script\'s code folder.')
    parser.add_argument('--datasets', nargs='+', choices=list(DATASETS),
                        help='Batch datasets to process; defaults to all four.')
    parser.add_argument('--movie-offset-seconds', type=float, default=0.0,
                        help='Movie start relative to analysis time zero; default 0 retains movie-relative times. Not an HRF delay.')
    args = parser.parse_args()
    try:
        if args.input_csv is None:
            root = args.project_root
            if root is None:
                script_dir = Path(__file__).resolve().parent
                if script_dir.name != 'code':
                    raise ValueError('Place the script directly in the project code folder or provide --project-root.')
                root = script_dir.parent
            manifest = batch_export(root, args.datasets or list(DATASETS),
                                    args.output_dir, args.movie_offset_seconds)
            for key, result in manifest['datasets'].items():
                print(f'{key}: {result["status"]}')
                if result['status'] == 'ok':
                    print('  Counts:', result['category_counts'])
                    print('  Output:', result['output'])
                    if not result['mat_written']:
                        print('  SciPy unavailable; run conditions.m in MATLAB to create conditions.mat.')
                else:
                    print(' ', result.get('error', result['source']))
            print('Run report:', str(Path(manifest['run_directory']) / 'batch_report.json'))
            if any(r['status'] != 'ok' for r in manifest['datasets'].values()):
                parser.exit(1, 'Some requested inputs were missing or failed; see the report. Successful exports were retained.\n')
            return
        if args.datasets or args.project_root:
            raise ValueError('--datasets and --project-root apply only to batch mode (omit the positional CSV).')
        if args.output_dir is None:
            raise ValueError('Single-CSV mode requires --output-dir.')
        report = export(args.input_csv, args.output_dir, args.movie_offset_seconds)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Error: {error}\n')
    print(json.dumps({k: report[k] for k in ('category_counts', 'blank_review_labels', 'mat_written')}, indent=2))
    print(f'Overlapping row pairs: {len(report["overlaps"])}; retained and listed in conversion_report.json.')
    if not report['mat_written']:
        print('SciPy unavailable: run conditions.m in MATLAB to create conditions.mat.')


if __name__ == '__main__':
    main()
