#!/usr/bin/env python3
"""Compare predicted face time from two frame_labels.csv files.

Requires matplotlib. No model inference, movie decoding, or GPU needed.
Each sample represents [time_s, min(time_s + 1/fps, movie_duration)).
Unknown and failed samples are retained separately, never counted as absent.
"""
import argparse
import csv
import json
import math
from pathlib import Path


def summarize(path, fps, duration):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f'{path}: empty frame table')
    totals = dict.fromkeys(('present', 'absent', 'uncertain', 'failed', 'not_run'), 0.0)
    times = []
    ids = []
    for row in rows:
        label = row['label']
        t = float(row['time_s'])
        if label not in totals or not math.isfinite(t) or not 0 <= t < duration:
            raise ValueError(f'{path}: invalid label or timestamp: {row}')
        ids.append(int(row['frame_id']))
        times.append(t)
        totals[label] += min(1 / fps, duration - t)
    if len(set(ids)) != len(ids):
        raise ValueError(f'{path}: duplicate frame IDs')
    expected_count = math.ceil(duration * fps)
    if len(times) != expected_count or any(abs(t - i/fps) > 1e-6 for i,t in enumerate(times)):
        raise ValueError(f'{path}: expected the complete chronological {fps:g}-fps grid; retain not_run rows')
    return {'source': str(path.resolve()), 'frame_count': len(rows),
            'seconds': totals, 'face_percent_of_movie': 100*totals['present']/duration}, list(zip(ids,times))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--single', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--fps', type=float, default=2)
    parser.add_argument('--duration', type=float, default=313.812,
                        help='Source movie duration in seconds; default matches this pilot')
    parser.add_argument('--out-dir', type=Path, default=Path('outputs/comparison/faces'))
    args = parser.parse_args()
    if any(not math.isfinite(x) or x <= 0 for x in (args.fps,args.duration)):
        parser.error('fps and duration must be positive finite numbers')
    single, grid = summarize(args.single,args.fps,args.duration)
    context, other_grid = summarize(args.context,args.fps,args.duration)
    if grid != other_grid:
        parser.error('The two files must contain matching frame IDs and timestamps')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2,4.8))
    values = [single['seconds']['present'],context['seconds']['present']]
    bars = ax.bar(['Single image','With context'], values, width=.52,
                  color=['#286F9B','#D98235'])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x()+bar.get_width()/2, value+args.duration*.025,
                f'{value:g} s\n({value/args.duration:.1%} of movie)',
                ha='center',va='bottom',fontsize=11)
    ax.set_ylim(0,args.duration)
    ax.set_ylabel('Seconds labelled face-present')
    ax.set_title('Predicted face presence',loc='left',fontweight='bold',pad=20)
    ax.spines[['top','right']].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True,alpha=.2)
    unknown = lambda r: sum(r['seconds'][k] for k in ('uncertain','failed','not_run'))
    fig.text(.12,.035,
        f'Movie: {args.duration:g} s | Sampling: {args.fps:g} fps\n'
        f'Unknown/failed/unprocessed: single {unknown(single):g} s; context {unknown(context):g} s.\n'
        'Model predictions, not detection accuracy. No clip padding or gap filling.',
        fontsize=9,color='#444444',va='bottom')
    fig.subplots_adjust(left=.12,right=.97,top=.85,bottom=.25)
    args.out_dir.mkdir(parents=True,exist_ok=True)
    for extension in ('png','pdf'):
        path=args.out_dir/f'face_seconds_comparison.{extension}'
        fig.savefig(path,dpi=220)
        print(path.resolve())
    plt.close(fig)
    report={'fps':args.fps,'movie_duration_s':args.duration,'single':single,'context':context}
    (args.out_dir/'face_seconds_summary.json').write_text(json.dumps(report,indent=2))
    print(f'Single: {values[0]:g} seconds; context: {values[1]:g} seconds.')


if __name__ == '__main__':
    main()
