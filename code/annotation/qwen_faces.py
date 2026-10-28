#!/usr/bin/env python3
"""Classify sampled cartoon frames and export face-positive review videos."""
import argparse
import csv
import html
import json
import math
import re
import os
import shutil
import hashlib
from collections import Counter
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROMPT = 'Examine this ONE cartoon image carefully. Does it show at least one recognizable FACE?\nCount human and baby faces, animal and bird faces, and faces belonging to clouds,\nobjects, plants, or imaginary creatures. A stylized cloud with eyes and a mouth\ncounts as a face even though it has no human head. Profile and closed-eye faces\ncount when recognizable. A body or back of a head alone does not count.\nReturn ONE JSON object, no frame IDs or list:\n{"label": "present OR absent OR uncertain", "features": [], "evidence": "brief visual reason"}\nChoose exactly one label: present, absent, uncertain.\nUse present for a visible face, absent if no face is visible, uncertain if you\ncannot tell. Do not default to absent just because a face is nonhuman or small.\nFor present, list visible facial features using these names: eye, mouth, nose,\nbeak, face_outline. Include at least one of eye/mouth/nose/beak. Describe the\nfeatures actually seen. For absent or uncertain, explain what is visible instead.\nDo not infer from the story; inspect this image only.'
VERSION = 3
FEATURES = {'eye', 'mouth', 'nose', 'beak', 'face_outline'}


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def write_csv(path, rows, fields):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def validate(raw, ids, single=False):
    text = raw.strip()
    fence = re.fullmatch(r'(`{1,3})(?:json)?\s*\n(.*?)\n\1', text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(2).strip()
    data = json.loads(text)
    if single and len(ids) == 1 and isinstance(data, dict) and 'label' in data:
        data = {'frames': [dict(data, frame_id=ids[0])]}
    rows = data if isinstance(data, list) else data.get('frames') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError('Expected a frames list')
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Frame row must be an object')
        i = row.get('frame_id')
        if type(i) is not int or i not in ids or i in found:
            raise ValueError(f'Unexpected or duplicated frame_id: {i}')
        if row.get('label') not in ('present', 'absent', 'uncertain'):
            raise ValueError(f'Invalid label for frame {i}')
        features = row.get('features')
        if not isinstance(features, list) or any(not isinstance(f, str) or f not in FEATURES for f in features):
            raise ValueError(f'Invalid features for frame {i}')
        if row['label'] == 'present' and not (set(features) - {'face_outline'}):
            raise ValueError(f'Present label lacks facial features for frame {i}')
        if not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
            raise ValueError(f'Missing evidence for frame {i}')
        found[i] = row
    if set(found) != set(ids):
        raise ValueError('Missing frame labels')
    return found


def intervals(frames, fps, duration, label):
    """Each label covers [sample time, next sample time), not exact transitions."""
    result = []
    for row in frames:
        if row['label'] != label:
            continue
        start, end = row['time_s'], min(duration, row['time_s'] + 1/fps)
        if result and row['frame_id'] == result[-1]['last_frame_id'] + 1:
            result[-1].update(end_s=end, last_frame_id=row['frame_id'])
        else:
            result.append(dict(start_s=start, end_s=end,
                               first_frame_id=row['frame_id'], last_frame_id=row['frame_id']))
    for row in result:
        row['duration_s'] = row['end_s'] - row['start_s']
    return result


def export_review(movie, out, frames, fps, duration, padding):
    """Export once per completed run (or partial run after a fatal error)."""
    manifest = []
    groups = []
    for clip_id in sorted({r.get('clip_id', 1) for r in frames}):
        members = [r for r in frames if r.get('clip_id', 1) == clip_id]
        a, b = members[0]['time_s'], min(duration, members[-1]['time_s'] + 1/fps)
        groups.append(dict(start_s=a, end_s=b, duration_s=b-a,
                           first_frame_id=members[0]['frame_id'], last_frame_id=members[-1]['frame_id']))
    for label, folder in [('present', 'face_clips'), ('uncertain', 'uncertain_clips'),
                          ('inspection_only', 'source_clips')]:
        (out / folder).mkdir(exist_ok=True)
        spans = groups if label == 'inspection_only' else intervals(frames, fps, duration, label)
        for i, row in enumerate(spans, 1):
            a, b = max(0, row['start_s']-padding), min(duration, row['end_s']+padding)
            filename = f'{folder}/{i:03d}_{row["start_s"]:.3f}-{row["end_s"]:.3f}s.mp4'
            item = dict(row, label=label, video=filename, export_start_s=a,
                        export_end_s=b, export_status='ok', error='')
            try:
                run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                     '-i', str(movie), '-ss', str(a), '-t', str(b-a), '-map', '0:v:0',
                     '-an', '-vf', 'scale=ceil(iw/2)*2:ceil(ih/2)*2',
                     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                     '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out / filename)])
            except subprocess.CalledProcessError as exc:
                item.update(export_status='failed', error=exc.stderr or str(exc))
            manifest.append(item)
    write_csv(out / 'review_clips.csv', manifest,
              ['label', 'start_s', 'end_s', 'duration_s', 'first_frame_id', 'last_frame_id',
               'export_start_s', 'export_end_s', 'video', 'export_status', 'error'])
    page = ['<!doctype html><meta charset="utf-8"><title>Face review</title>',
            '<style>body{font:16px system-ui;max-width:1000px;margin:30px auto}video{width:640px;max-width:100%}article{margin:30px 0}img{width:180px}td{padding:8px}</style>',
            '<h1>Face detection review</h1>',
            '<p>inspection_only videos are source segments for checking missed faces or failures. They are NOT positive detections.</p>',
            f'<p>Videos include up to {padding:g}s context on each side. Context is not a positive prediction. Times below refer to the original movie. No audio.</p>',
            '<p>Sampling-based estimates, not verified annotations. Failed and unprocessed frames are not negative detections. See frame_labels.csv for full coverage.</p>']
    if not any(item['label'] in ('present', 'uncertain') for item in manifest):
        page.append('<p>No present or uncertain intervals were produced. Check coverage before concluding there are no faces.</p>')
    for item in manifest:
        page.append(f'<article><h2>{item["label"]}: {item["start_s"]:.2f}–{item["end_s"]:.2f}s</h2>')
        if item['export_status'] == 'ok':
            page.append(f'<video controls preload="none" src="{item["video"]}"></video>')
        else:
            page.append('<p>Export failed: ' + html.escape(item['error']) + '</p>')
        page.append(f'<p>Video begins at movie time {item["export_start_s"]:.2f}s.</p></article>')
    page.append('<h2>All sampled frames</h2><p>Inspect absent labels here to look for missed faces.</p><table>')
    for row in frames:
        page.append(f'<tr><td>{row["frame_id"]}<br>{row["time_s"]:.2f}s<br>{row["label"]}</td>'
                    f'<td><a href="{row["image"]}"><img loading="lazy" src="{row["image"]}"></a></td>'
                    f'<td>{html.escape(row["evidence"])}</td></tr>')
    page.append('</table>')
    (out / 'review.html').write_text('\n'.join(page), encoding='utf-8')
    return sum(x['export_status'] == 'failed' for x in manifest)


def rebuild(run_dir, movie_override=None):
    """Recover saved model responses without loading Qwen or changing the old run."""
    run_dir = run_dir.expanduser().resolve()
    settings = json.loads((run_dir / 'settings.json').read_text())
    movie = Path(movie_override or settings['movie']).expanduser().resolve()
    if not movie.is_file():
        raise SystemExit(f'Movie not found: {movie}; supply --movie with its current path')
    fps, duration = float(settings['fps']), float(settings['duration_s'])
    with (run_dir / 'frame_labels.csv').open(newline='', encoding='utf-8') as handle:
        frames = list(csv.DictReader(handle))
    for row in frames:
        row.update(frame_id=int(row['frame_id']), clip_id=int(row['clip_id']),
                   time_s=float(row['time_s']), label='not_run', features='', evidence='')
        row['image'] = '../' + row['image']
    by_id = {r['frame_id']: r for r in frames}
    diagnostics = []
    for path in sorted((run_dir / 'responses').glob('*.json')):
        record = json.loads(path.read_text())
        ids = record['frame_ids']
        try:
            if any(type(i) is not int or i not in by_id for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('Invalid frame IDs in saved request')
            if record.get('generated_tokens', 0) >= settings['max_new_tokens']:
                raise ValueError('Saved answer reached output token limit')
            labels = validate(record.get('raw_response', ''), ids, single=record.get('parser') == 'single')
            for i in ids:
                item = labels[i]
                by_id[i].update(label=item['label'], features=' | '.join(item['features']), evidence=item['evidence'])
            diagnostics.append(dict(response=path.name, status='recovered', error=''))
        except ValueError as exc:
            for i in ids:
                if type(i) is int and i in by_id:
                    by_id[i].update(label='failed', evidence=str(exc))
            diagnostics.append(dict(response=path.name, status='failed', error=str(exc)))
    out = run_dir / ('recovered_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out.mkdir()
    write_csv(out / 'frame_labels.csv', frames,
              ['frame_id', 'time_s', 'clip_id', 'label', 'features', 'evidence', 'image'])
    for label, filename in [('present', 'face_intervals.csv'), ('uncertain', 'uncertain_intervals.csv')]:
        write_csv(out / filename, intervals(frames, fps, duration, label),
                  ['start_s', 'end_s', 'duration_s', 'first_frame_id', 'last_frame_id'])
    coverage = []
    for clip_id in sorted({r['clip_id'] for r in frames}):
        group = [r for r in frames if r['clip_id'] == clip_id]
        coverage.append(dict(clip_id=clip_id, **{label: sum(r['label'] == label for r in group)
            for label in ['present', 'absent', 'uncertain', 'failed', 'not_run']}))
    write_csv(out / 'clip_status.csv', coverage,
              ['clip_id', 'present', 'absent', 'uncertain', 'failed', 'not_run'])
    write_csv(out / 'recovery_status.csv', diagnostics, ['response', 'status', 'error'])
    (out / 'recovery.json').write_text(json.dumps({'source_run': str(run_dir), 'movie': str(movie)}, indent=2))
    errors = export_review(movie, out, frames, fps, duration, settings.get('review_padding', 1))
    counts = {label: sum(r['label'] == label for r in frames)
              for label in ['present', 'absent', 'uncertain', 'failed', 'not_run']}
    print(f'Recovered results: {out}\nFrame counts: {counts}\nVideo export failures: {errors}', flush=True)
    if errors or counts['failed'] or counts['not_run']:
        print('Partial results only: inspect clip_status.csv. Unprocessed frames still require inference.')

def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def load_frames(out, settings):
    paths = sorted((out / 'frames').glob('frame_*.jpg'))
    if len(paths) != settings['frame_count']:
        raise ValueError('Frame extraction is incomplete. Start a new run instead of resuming.')
    frames = []
    for i, path in enumerate(paths, 1):
        if path.name != f'frame_{i:06d}.jpg':
            raise ValueError('Missing or misnumbered frame image')
        time_s = (i-1)/settings['fps']
        if time_s < settings['duration_s']:
            frames.append(dict(frame_id=i, time_s=time_s,
                clip_id=int(time_s//settings['clip_seconds'])+1,
                label='not_run', features='', evidence='', image=str(path.relative_to(out))))
    return frames


def restore(frames, out, token_limit):
    """Replay durable per-image responses, not a possibly interrupted CSV write."""
    for row in frames:
        path = out / f'responses/frame_{row["frame_id"]:06d}.json'
        if not path.exists():
            continue
        try:
            rec = json.loads(path.read_text())
            if rec.get('frame_ids') != [row['frame_id']]:
                raise ValueError('Saved frame ID mismatch')
            if rec.get('generated_tokens', 0) >= token_limit:
                raise ValueError('Output token limit reached')
            label = validate(rec.get('raw_response', ''), rec['frame_ids'], single=True)[row['frame_id']]
            row.update(label=label['label'], features=' | '.join(label['features']), evidence=label['evidence'])
        except (ValueError, KeyError, TypeError) as exc:
            row.update(label='failed', evidence=str(exc))


def save_outputs(out, frames, settings):
    write_csv(out / 'frame_labels.csv', frames,
              ['frame_id', 'time_s', 'clip_id', 'label', 'features', 'evidence', 'image'])
    for label, filename in [('present', 'face_intervals.csv'), ('uncertain', 'uncertain_intervals.csv')]:
        write_csv(out / filename, intervals(frames, settings['fps'], settings['duration_s'], label),
                  ['start_s', 'end_s', 'duration_s', 'first_frame_id', 'last_frame_id'])
    coverage = []
    for i in sorted({r['clip_id'] for r in frames}):
        counts = Counter(r['label'] for r in frames if r['clip_id'] == i)
        coverage.append(dict(clip_id=i, **{k: counts[k] for k in ['present','absent','uncertain','failed','not_run']}))
    write_csv(out / 'clip_status.csv', coverage, ['clip_id','present','absent','uncertain','failed','not_run'])
    counts = Counter(r['label'] for r in frames)
    errors = Counter(r['evidence'] for r in frames if r['label'] == 'failed')
    summary = {'counts': dict(counts), 'errors': dict(errors),
               'warning': 'No positive detections. Inspect source_clips and frames; this is not proof of no faces.' if not counts['present'] else ''}
    atomic_json(out / 'summary.json', summary)
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--resume', type=Path, help='Continue a v3 run, skipping validated frames')
    modes.add_argument('--reuse-frames', type=Path, help='Start a fresh analysis using images from an older run')
    modes.add_argument('--rebuild-from', type=Path, help='Reparse an older run without inference')
    p.add_argument('--movie', type=Path)
    p.add_argument('--out', type=Path, default=Path('outputs/face_pilot_review'))
    p.add_argument('--model', default='Qwen/Qwen2.5-VL-3B-Instruct')
    p.add_argument('--fps', type=float, default=2)
    p.add_argument('--clip-seconds', type=float, default=30)
    p.add_argument('--max-pixels', type=int, default=448*448)
    p.add_argument('--max-new-tokens', type=int, default=512)
    p.add_argument('--review-padding', type=float, default=1)
    p.add_argument('--frames-per-request', type=int, choices=[1], default=1,
                   help='One image per request avoids model-generated frame ID errors')
    p.add_argument('--limit-frames', type=int, default=0, help='Process this many pending frames; 0 means all')
    p.add_argument('--export-only', action='store_true', help='Use with --resume to rebuild review outputs without a GPU')
    args = p.parse_args()
    if args.rebuild_from:
        rebuild(args.rebuild_from, args.movie)
        return
    if args.export_only and not args.resume:
        p.error('--export-only requires --resume')
    if (not all(math.isfinite(x) for x in (args.fps,args.clip_seconds,args.review_padding))
            or args.fps <= 0 or args.clip_seconds <= 0 or args.review_padding < 0
            or args.max_pixels < 28*28 or args.max_new_tokens < 1 or args.limit_frames < 0):
        p.error('Invalid sampling or generation options')
    if args.resume:
        out = args.resume.expanduser().resolve()
        settings = json.loads((out / 'settings.json').read_text())
        if settings.get('version') != VERSION:
            p.error('Older run: use --reuse-frames instead. Its negative labels need rechecking with the revised method.')
        if settings.get('prompt_sha256') != hashlib.sha256(PROMPT.encode()).hexdigest():
            p.error('Prompt changed: use --reuse-frames to avoid mixing different analyses')
        movie = Path(args.movie or settings['movie']).expanduser().resolve()
        frames = load_frames(out, settings)
        restore(frames, out, settings['max_new_tokens'])
        print('Resuming with saved model, resolution, sampling, and generation settings.', flush=True)
    else:
        source = args.reuse_frames.expanduser().resolve() if args.reuse_frames else None
        old = json.loads((source / 'settings.json').read_text()) if source else None
        if args.movie is None and old is None:
            p.error('--movie is required for a fresh run')
        movie = Path(args.movie or old['movie']).expanduser().resolve()
        if not movie.is_file():
            p.error(f'Movie not found: {movie}')
        meta = json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'stream=duration:format=duration','-of','json',str(movie)]).stdout)
        if not meta.get('streams'):
            p.error('No video stream')
        value = meta['streams'][0].get('duration')
        duration = float(value if value and value != 'N/A' else meta['format']['duration'])
        if not math.isfinite(duration) or duration <= 0:
            p.error('Invalid movie duration')
        if old:
            if abs(duration-old['duration_s']) > 0.1:
                p.error('Movie duration differs from the source run')
            args.fps = float(old['fps'])
        out = args.out.expanduser().resolve() / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (out / 'frames').mkdir(parents=True)
        (out / 'responses').mkdir()
        print(f'Output: {out}', flush=True)
        settings = {**vars(args), 'movie':str(movie), 'duration_s':duration, 'version':VERSION,
                    'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest()}
        if source:
            # Copy images so the new review folder remains portable and independent.
            paths = sorted((source / 'frames').glob('frame_*.jpg'))
            with (source / 'frame_labels.csv').open(newline='') as f:
                expected = len(list(csv.DictReader(f)))
            if len(paths) != expected:
                p.error('Source frame extraction is incomplete; start fresh with --movie')
            for path in paths:
                shutil.copy2(path, out / 'frames' / path.name)
        else:
            print(f'Extracting images at {args.fps:g} fps...', flush=True)
            run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(movie),'-map','0:v:0','-an',
                 '-vf',f'setpts=PTS-STARTPTS,fps=fps={args.fps}:start_time=0:round=near',
                 '-q:v','2',str(out/'frames/frame_%06d.jpg')])
        settings['frame_count'] = len(list((out/'frames').glob('frame_*.jpg')))
        atomic_json(out/'settings.json', settings)
        (out/'prompt.txt').write_text(PROMPT)
        frames = load_frames(out, settings)
    if not movie.is_file() or not frames:
        p.error('Movie missing or no sampled frames')
    save_outputs(out, frames, settings)
    pending = [r for r in frames if r['label'] in ('not_run','failed')]
    print(f'Output: {out}\n{len(frames)-len(pending)} validated frames skipped; {len(pending)} pending.', flush=True)
    if args.limit_frames:
        pending = pending[:args.limit_frames]
    fatal = None
    if pending and not args.export_only:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration, GenerationConfig
        from qwen_vl_utils import process_vision_info
        if not torch.cuda.is_available():
            raise SystemExit('No CUDA GPU. Re-enter a GPU allocation and use --resume with the output folder above.')
        # Fix processor choice explicitly rather than inheriting a changing fast default.
        processor = AutoProcessor.from_pretrained(settings['model'], use_fast=False)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(settings['model'],
            dtype=torch.float16, device_map={'':0}, attn_implementation='sdpa').eval()
        generation = GenerationConfig(do_sample=False, max_new_tokens=settings['max_new_tokens'],
            eos_token_id=model.generation_config.eos_token_id,
            pad_token_id=model.generation_config.pad_token_id,
            bos_token_id=model.generation_config.bos_token_id)
        def infer(row):
            messages = [{'role':'user','content':[
                {'type':'image','image':(out/row['image']).as_uri(),'max_pixels':settings['max_pixels']},
                {'type':'text','text':PROMPT}]}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            images, videos = process_vision_info(messages)
            inputs = processor(text=[text], images=images, videos=videos, return_tensors='pt', padding=True)
            if 'pixel_values' not in inputs or inputs['image_grid_thw'].shape[0] != 1:
                raise RuntimeError('Expected exactly one encoded image; stopping rather than classifying text only')
            n = inputs.input_ids.shape[-1]
            with torch.inference_mode():
                output = model.generate(**inputs.to('cuda'), generation_config=generation)
            generated = output[0,n:]
            return processor.decode(generated,skip_special_tokens=True), len(generated), {
                'input_tokens':int(n), 'image_grid_thw':inputs['image_grid_thw'].tolist()}
        consecutive_failures = 0
        try:
            for index,row in enumerate(pending,1):
                record = {'frame_ids':[row['frame_id']], 'parser':'single', 'attempts':[]}
                for attempt in range(2):
                    try:
                        raw,count,info = infer(row)
                        record.update(raw_response=raw,generated_tokens=count,**info)
                        record['attempts'].append({'raw_response':raw,'generated_tokens':count})
                        if count >= settings['max_new_tokens']:
                            raise ValueError('Output token limit reached')
                        label = validate(raw,record['frame_ids'],single=True)[row['frame_id']]
                        row.update(label=label['label'],features=' | '.join(label['features']),evidence=label['evidence'])
                        record.pop('error',None)
                        break
                    except ValueError as exc:
                        record['error'] = str(exc)
                        row.update(label='failed',features='',evidence=str(exc))
                        # A retry is format-only and never triggered by a negative label.
                    except Exception as exc:
                        fatal = f'{type(exc).__name__}: {exc}'
                        record['error'] = fatal
                        row.update(label='failed',features='',evidence=fatal)
                        break
                atomic_json(out/f'responses/frame_{row["frame_id"]:06d}.json',record)
                counts = save_outputs(out,frames,settings)
                consecutive_failures = consecutive_failures+1 if row['label']=='failed' else 0
                if row['label']=='failed':
                    print(f'Frame {row["frame_id"]} FAILED: {row["evidence"]}',flush=True)
                if index % 10 == 0 or index == len(pending):
                    print(f'{index}/{len(pending)} pending frames processed; {dict(counts)}',flush=True)
                if consecutive_failures >= 3:
                    fatal = 'Three consecutive invalid responses. Stopped; inspect responses/ before resuming.'
                if fatal:
                    break
        except KeyboardInterrupt:
            fatal = 'Interrupted; completed frames saved. Resume using the same output folder.'
        finally:
            save_outputs(out,frames,settings)
            del model
            torch.cuda.empty_cache()
    print('Exporting positive, uncertain, and source inspection clips...',flush=True)
    export_errors = export_review(movie,out,frames,settings['fps'],settings['duration_s'],settings['review_padding'])
    counts = save_outputs(out,frames,settings)
    print(f'Open {out}/review.html\nFrame counts: {dict(counts)}; export failures: {export_errors}',flush=True)
    if not counts['present']:
        print('NO POSITIVE DETECTIONS: inspect source_clips and sampled frames; negative predictions are not verified.',flush=True)
    if fatal or counts['failed'] or export_errors:
        raise SystemExit(f'Incomplete: failed={counts["failed"]}, not_run={counts["not_run"]}, export_errors={export_errors}. {fatal or ""}')
    if counts['not_run']:
        print(f'Partial run: {counts["not_run"]} frames remain. Continue with --resume {out}',flush=True)


if __name__ == '__main__':
    main()
