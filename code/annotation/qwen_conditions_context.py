#!/usr/bin/env python3
"""Detect candidate Mental, Pain, Social and Control events from target images with context."""
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

CONDITIONS = ('mental', 'pain', 'social', 'control')
VERSION = 'conditions-context-2'
DEFINITION_SOURCE = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4733571/'
PROMPT = """Examine this silent cartoon sequence. One image is marked TARGET.
Use the neighbouring images to interpret the action or reaction occurring AT
THE TARGET TIME. Events only before or after that time do not count as present
at the target. If their timing or meaning cannot be resolved, choose uncertain.
Clouds and animals are characters, even when their faces are not visible.
Judge these four conditions using the following definitions, adapted from the
movie coding in Jacoby et al. (2016):

MENTAL: The event invites the viewer to infer a character's thoughts, beliefs,
intentions, or emotional interpretation of a situation. Identify what the
character appears to think or feel about the event and the observable basis.
A facial expression by itself is not sufficient to invent a belief or intention.
PAIN: A character is undergoing a physically painful event. Identify the bodily
harmful contact, action, or bodily reaction that supports this. Emotional upset,
fear of possible future injury, or merely holding a dangerous object is not
by itself a physically painful event. Exaggerated cartoon injury can count.
SOCIAL: Characters interact, with the focus on the interaction rather than
mental/emotional interpretation. Identify who acts toward whom and what happens.
Merely appearing together or being near each other is not enough.
PHYSICAL_SCENE_BASELINE: Scenery or general physical activity with no particular character's
individual event as the focus. Characters may appear in a background or wide
shot. General flock flight or a landscape can qualify when no individual
character event is the focus. The category concerns scene content, never
agency, coordinated movement, leadership, or power over another character.
It is not a default when the other conditions are absent.

First describe the visible action and immediate reaction briefly. Then decide
present, absent, or uncertain for EACH condition. Do not force one winner or
assume a positive label is required. If multiple conditions are present, give
specific support for each; scenery alone does not support the physical-scene baseline while a
character event is the focus. Explain ambiguity rather than guessing. Never use
remembered plot information or infer sounds from these silent images.
Use absent when the category's event is clearly not occurring. Use uncertain
only when the supplied images leave its occurrence, meaning, or timing unclear.
No characters in a clear scenery-only view is evidence of absence of character
events, not automatically a reason for uncertainty. Coordinated group movement
alone does not establish mental-state inference or an interpersonal interaction.
Return one JSON object, with no frame IDs, scores, intervals, or Markdown.
Required keys are description, mental, pain, social, physical_scene_baseline.
description is a short string. Each condition MUST have exactly the two keys
"label" and "evidence". "label" must contain ONE of the strings "present",
"absent", "uncertain". "evidence" explains that ONE decision at the target time.
NEVER use present/absent/uncertain as object keys or list arguments for several
alternative answers. Resolve the decision; choose uncertain if unresolved.
Do not output placeholder labels. Follow the JSON schema below.
"""
OUTPUT_SCHEMA = {
    'type': 'object',
    'required': ['description', 'mental', 'pain', 'social', 'physical_scene_baseline'],
    'additionalProperties': False,
    'properties': {'description': {'type':'string'}, **{
        c: {'type':'object','required':['label','evidence'],'additionalProperties':False,
            'properties':{'label':{'type':'string','enum':['present','absent','uncertain']},
                          'evidence':{'type':'string'}}}
        for c in ('mental','pain','social','physical_scene_baseline')}}}
PROMPT += '\n' + json.dumps(OUTPUT_SCHEMA)
RETRY_VERSION = 'schema-free-retry-2'
EVIDENCE_PLACEHOLDER = '<REPLACE WITH VISUAL EVIDENCE FOR THIS DECISION>'
# Preserve the original first-attempt prompt/hash for existing runs. Only the
# format-repair attempt omits the schema that the model sometimes copies.
RETRY_PROMPT = PROMPT.removesuffix('\n' + json.dumps(OUTPUT_SCHEMA)).replace(
    'Do not output placeholder labels. Follow the JSON schema below.',
    'Return actual observations and decisions about the images. Do not describe '
    'the output format. Do not output a JSON schema or placeholder labels.')


def retry_instruction(error, raw=''):
    instruction = (f'The previous answer failed validation: {error}. Re-examine the images '
            'and return a fresh COMPLETE JSON answer about the TARGET image. '
            'Write a visible-event description as text, then your four decisions. '
            'Do not return a schema: type, properties, required, enum, and '
            'additionalProperties are formatting instructions, not observations. Each '
            'condition must contain "label" and "evidence" only. Select exactly '
            'one label, never separate present/absent explanations. Use the '
            'physical_scene_baseline definition, not agency or movement control. '
            'Do not change a negative decision merely to obtain a positive one.')
    # Repair only unambiguous shorthand answers. Never invent a decision or
    # manufacture evidence from the general scene description.
    try:
        text = raw.strip()
        fence = re.fullmatch(r'(`{1,3})(?:json)?\s*\n(.*?)\n\1', text, re.DOTALL | re.IGNORECASE)
        data = json.loads(fence.group(2).strip() if fence else text)
        keys = ('mental', 'pain', 'social', 'physical_scene_baseline')
        if (isinstance(data, dict) and isinstance(data.get('description'), str)
                and all(isinstance(data.get(c), str) and
                        data[c] in ('present', 'absent', 'uncertain') for c in keys)):
            template = dict(description=data['description'], **{
                c: {'label':data[c], 'evidence':EVIDENCE_PLACEHOLDER} for c in keys})
            instruction += ('\nYour previous answer supplied labels but omitted their evidence. '
                'Complete the following object, preserving those labels and replacing EVERY '
                'placeholder with a short explanation based on the TARGET and context images. '
                'For absent explain what is absent; for uncertain explain what is ambiguous. '
                'Return the completed object, not plain strings for the conditions.\n'
                + json.dumps(template))
    except (ValueError, TypeError):
        pass
    return instruction


def context_frames(frames, target, seconds):
    """Use the global timeline, never the reporting-group boundaries."""
    return [r for r in frames
            if abs(r['time_s'] - target['time_s']) <= seconds + 1e-8]


def make_content(frames, target, out, settings, feedback=''):
    selected = context_frames(frames, target, settings['context_seconds'])
    content = []
    for row in selected:
        marker = 'TARGET' if row['frame_id'] == target['frame_id'] else 'CONTEXT'
        content.extend([
            {'type': 'text', 'text': f'{marker}: movie time {row["time_s"]:.3f} seconds'},
            {'type': 'image', 'image': (out / row['image']).as_uri(),
             'max_pixels': settings['max_pixels']}])
    content.append({'type': 'text', 'text': RETRY_PROMPT if feedback else PROMPT})
    if feedback:
        content.append({'type':'text', 'text':feedback})
    return content, selected



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


def validate(raw):
    text = raw.strip()
    fence = re.fullmatch(r'(`{1,3})(?:json)?\s*\n(.*?)\n\1', text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(2).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('Expected one JSON object')
    if data.get('type') == 'object' and 'properties' in data:
        raise ValueError('Returned a JSON schema instead of observations and labels')
    if not isinstance(data.get('description'), str) or not data['description'].strip():
        raise ValueError('Missing visible-event description')
    if 'physical_scene_baseline' in data:
        if 'control' in data:
            raise ValueError('Use physical_scene_baseline only; do not duplicate it as control')
        data['control'] = data.pop('physical_scene_baseline')
    for category in CONDITIONS:
        item = data.get(category)
        if isinstance(item, dict) and set(item) != {'label', 'evidence'}:
            raise ValueError(f'{category} must have only label and evidence keys; received {sorted(item)}')
        if not isinstance(item, dict) or item.get('label') not in ('present','absent','uncertain'):
            raise ValueError(f'Missing or invalid label for {category}')
        if not isinstance(item.get('evidence'), str) or not item['evidence'].strip():
            raise ValueError(f'Missing evidence for {category}')
        if EVIDENCE_PLACEHOLDER in item['evidence']:
            raise ValueError(f'Unfilled evidence placeholder for {category}')
    return data


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


def export_review(movie,out,frames,fps,duration,padding):
    spans=[]
    for category in CONDITIONS:
        for label in ('present','uncertain'):
            spans.extend(dict(category=category,label=label,**s)
                         for s in intervals(projected(frames,category),fps,duration,label))
    for i in sorted({r['clip_id'] for r in frames}):
        group=[r for r in frames if r['clip_id']==i]
        a,b=group[0]['time_s'],min(duration,group[-1]['time_s']+1/fps)
        spans.append(dict(category='source',label='inspection_only',start_s=a,end_s=b,duration_s=b-a,
                          first_frame_id=group[0]['frame_id'],last_frame_id=group[-1]['frame_id']))
    manifest=[]
    for i,s in enumerate(spans,1):
        a,b=max(0,s['start_s']-padding),min(duration,s['end_s']+padding)
        folder=out/'clips'/s['category']/s['label'];folder.mkdir(parents=True,exist_ok=True)
        video=folder/f'{i:04d}_{s["start_s"]:.3f}-{s["end_s"]:.3f}s.mp4'
        item=dict(s,export_start_s=a,export_end_s=b,video=str(video.relative_to(out)),export_status='ok',error='')
        try:
            run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(movie),'-ss',str(a),'-t',str(b-a),
                 '-map','0:v:0','-an','-vf','scale=ceil(iw/2)*2:ceil(ih/2)*2',
                 '-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)])
        except subprocess.CalledProcessError as exc:
            item.update(export_status='failed',error=exc.stderr or str(exc))
        manifest.append(item)
    write_csv(out/'review_clips.csv',manifest,['category','label','start_s','end_s','duration_s',
        'first_frame_id','last_frame_id','export_start_s','export_end_s','video','export_status','error'])
    page=['<!doctype html><meta charset="utf-8"><title>Condition pilot</title>',
          '<style>body{font:16px system-ui;max-width:1000px;margin:30px auto}video{width:620px;max-width:100%}img{width:180px}td{padding:8px;vertical-align:top}</style>',
          '<h1>Candidate condition intervals</h1>',
          '<p>Mental, Pain, Social and Control: experimental model labels, not verified annotations. Source segments are for inspection, not detections.</p>',
          f'<p>Videos include up to {padding:g}s padding. Padding and inference context are not part of predicted intervals. See summary.json and review_flags.csv for coverage and definition conflicts.</p>']
    for item in manifest:
        page.append(f'<h2>{item["category"]} / {item["label"]}: {item["start_s"]:.2f}–{item["end_s"]:.2f}s</h2>')
        if item['export_status']=='ok':
            page.append(f'<video controls preload="none" src="{item["video"]}"></video>')
        else:page.append('<p>Export failed: '+html.escape(item['error'])+'</p>')
    page.append('<h2>All targets</h2><table>')
    for r in frames:
        text=r.get('description','')
        if r['label']=='complete':
            text+='\n'+'\n'.join(f'{c}: {r["decisions"][c]["label"]} — {r["decisions"][c]["evidence"]}' for c in CONDITIONS)
        else:text+=r['label']+': '+r['evidence']
        page.append(f'<tr><td>{r["frame_id"]}, {r["time_s"]:.2f}s</td><td><img loading="lazy" src="{r["image"]}"></td><td style="white-space:pre-wrap">{html.escape(text)}</td></tr>')
    page.append('</table>');(out/'review.html').write_text('\n'.join(page),encoding='utf-8')
    return sum(r['export_status']=='failed' for r in manifest)



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
    for row in frames:
        path = out / f'responses/frame_{row["frame_id"]:06d}.json'
        if not path.exists():
            continue
        try:
            rec = json.loads(path.read_text())
            if rec.get('frame_ids') != [row['frame_id']]:
                raise ValueError('Saved target ID mismatch')
            if rec.get('generated_tokens',0) >= token_limit:
                raise ValueError('Output token limit reached')
            data = validate(rec.get('raw_response',''))
            row.update(label='complete', description=data['description'], decisions=data, evidence='')
        except (ValueError,KeyError,TypeError) as exc:
            row.update(label='failed', evidence=str(exc))


def save_outputs(out, frames, settings):
    detailed, wide, merged, uncertain, flags = [], [], [], [], []
    for r in frames:
        item = dict(frame_id=r['frame_id'],time_s=r['time_s'],status=r['label'],
                    description=r.get('description',''),image=r['image'])
        for category in CONDITIONS:
            decision = r['decisions'][category] if r['label']=='complete' else {'label':r['label'],'evidence':r['evidence']}
            item[category] = decision['label']
            detailed.append(dict(frame_id=r['frame_id'],time_s=r['time_s'],category=category,
                label=decision['label'],evidence=decision['evidence'],description=r.get('description',''),image=r['image']))
        wide.append(item)
        if item['control']=='present' and any(item[c]=='present' for c in ('mental','pain','social')):
            flags.append(dict(frame_id=r['frame_id'],time_s=r['time_s'],
                issue='Control co-occurs with a character-related category; manually check definitions'))
    write_csv(out/'frame_labels.csv',wide,['frame_id','time_s','status',*CONDITIONS,'description','image'])
    write_csv(out/'condition_evidence.csv',detailed,['frame_id','time_s','category','label','evidence','description','image'])
    by_category = {}
    for category in CONDITIONS:
        rows = projected(frames,category)
        by_category[category] = dict(Counter(r['label'] for r in rows))
        for label,destination in [('present',merged),('uncertain',uncertain)]:
            spans = [dict(category=category,**span) for span in intervals(rows,settings['fps'],settings['duration_s'],label)]
            destination.extend(spans)
    fields=['category','start_s','end_s','duration_s','first_frame_id','last_frame_id']
    write_csv(out/'condition_intervals.csv',merged,fields)
    write_csv(out/'uncertain_intervals.csv',uncertain,fields)
    write_csv(out/'review_flags.csv',flags,['frame_id','time_s','issue'])
    coverage=[]
    for i in sorted({r['clip_id'] for r in frames}):
        c=Counter(r['label'] for r in frames if r['clip_id']==i)
        coverage.append(dict(clip_id=i,complete=c['complete'],failed=c['failed'],not_run=c['not_run']))
    write_csv(out/'clip_status.csv',coverage,['clip_id','complete','failed','not_run'])
    counts=Counter(r['label'] for r in frames)
    atomic_json(out/'summary.json',dict(target_status=dict(counts),conditions=by_category,
        definition_conflicts=len(flags),errors=dict(Counter(r['evidence'] for r in frames if r['label']=='failed')),
        interpretation='Candidate condition detections, not calibrated probabilities or validated original event annotations.'))
    return counts


def projected(frames, category):
    return [dict(r, label=r['decisions'][category]['label'],
                 evidence=r['decisions'][category]['evidence'])
            if r['label'] == 'complete' else dict(r) for r in frames]

def select_pilot(pending, count):
    if count == 0 or count >= len(pending):
        return pending
    if count == 1:
        return [pending[len(pending)//2]]
    return [pending[round(j*(len(pending)-1)/(count-1))] for j in range(count)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--resume', type=Path, help='Continue a condition run, skipping validated targets')
    modes.add_argument('--reuse-frames', type=Path, help='Start a fresh analysis using images from an older run')
    p.add_argument('--movie', type=Path)
    p.add_argument('--out', type=Path, default=Path('outputs/condition_pilot_context'))
    p.add_argument('--model', default='Qwen/Qwen2.5-VL-3B-Instruct')
    p.add_argument('--fps', type=float, default=2)
    p.add_argument('--clip-seconds', type=float, default=30)
    p.add_argument('--max-pixels', type=int, default=448*448)
    p.add_argument('--max-new-tokens', type=int, default=1024)
    p.add_argument('--review-padding', type=float, default=1)
    p.add_argument('--context-seconds', type=float, default=2,
                   help='Neighbouring images within this many seconds before and after each target')
    p.add_argument('--frames-per-request', type=int, choices=[1], default=1,
                   help='One target decision per request; neighbouring context images are added separately')
    p.add_argument('--limit-frames', type=int, default=0, help='Process this many pending frames; 0 means all')
    p.add_argument('--pilot-targets', type=int, default=0,
                   help='Process this many targets evenly across the pending timeline; 0 means all')
    p.add_argument('--export-only', action='store_true', help='Use with --resume to rebuild review outputs without a GPU')
    args = p.parse_args()
    if args.export_only and not args.resume:
        p.error('--export-only requires --resume')
    if (not all(math.isfinite(x) for x in (args.fps,args.clip_seconds,args.review_padding,args.context_seconds))
            or args.fps <= 0 or args.clip_seconds <= 0 or args.review_padding < 0
            or args.context_seconds < 0
            or args.max_pixels < 28*28 or args.max_new_tokens < 1 or args.limit_frames < 0 or args.pilot_targets < 0):
        p.error('Invalid sampling or generation options')
    if args.pilot_targets and args.limit_frames:
        p.error('Choose --pilot-targets or --limit-frames, not both')
    if args.resume:
        out = args.resume.expanduser().resolve()
        settings = json.loads((out / 'settings.json').read_text())
        if settings.get('version') != VERSION:
            p.error('Different method: use --reuse-frames to start a new context run without mixing old decisions.')
        if settings.get('prompt_sha256') != hashlib.sha256(PROMPT.encode()).hexdigest():
            p.error('Prompt changed: use --reuse-frames to avoid mixing different analyses')
        movie = Path(args.movie or settings['movie']).expanduser().resolve()
        frames = load_frames(out, settings)
        restore(frames, out, settings['max_new_tokens'])
        print('Resuming with saved model, context, resolution, sampling, and generation settings.', flush=True)
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
                    'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest(), 'definition_source':DEFINITION_SOURCE,
                    'decision_mode':'joint four labels; present/absent/uncertain; target time', 'conditions':CONDITIONS}
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
    pending = select_pilot(pending, args.pilot_targets)
    atomic_json(out/'planned_targets.json', {'frame_ids':[r['frame_id'] for r in pending],
        'times_s':[r['time_s'] for r in pending], 'pilot_targets':args.pilot_targets})
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
        def infer(row, feedback=''):
            content, selected = make_content(frames, row, out, settings, feedback)
            messages = [{'role':'user','content':content}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            images, videos = process_vision_info(messages)
            inputs = processor(text=[text], images=images, videos=videos, return_tensors='pt', padding=True)
            if 'pixel_values' not in inputs or inputs['image_grid_thw'].shape[0] != len(selected):
                raise RuntimeError('Encoded image count does not match the target/context sequence')
            n = inputs.input_ids.shape[-1]
            config = getattr(model.config, 'text_config', model.config)
            limit = getattr(config, 'max_position_embeddings', None)
            if limit and n + settings['max_new_tokens'] > limit:
                raise RuntimeError('Context limit exceeded; use a smaller --context-seconds in a new run')
            with torch.inference_mode():
                output = model.generate(**inputs.to('cuda'), generation_config=generation)
            generated = output[0,n:]
            return processor.decode(generated,skip_special_tokens=True), len(generated), {
                'input_tokens':int(n), 'image_grid_thw':inputs['image_grid_thw'].tolist(),
                'context_frame_ids':[r['frame_id'] for r in selected],
                'context_times_s':[r['time_s'] for r in selected],
                'target_frame_id':row['frame_id']}
        try:
            for index,row in enumerate(pending,1):
                record = {'frame_ids':[row['frame_id']], 'parser':'four_conditions', 'attempts':[]}
                feedback = ''
                for attempt in range(3):
                    raw = ''
                    try:
                        raw,count,info = infer(row, feedback)
                        record.update(raw_response=raw,generated_tokens=count,**info)
                        record['attempts'].append({'raw_response':raw,'generated_tokens':count,
                            'retry_instruction':feedback,
                            'retry_version':RETRY_VERSION if feedback else None,
                            'prompt_sha256':hashlib.sha256(
                                (RETRY_PROMPT if feedback else PROMPT).encode()).hexdigest()})
                        if count >= settings['max_new_tokens']:
                            raise ValueError('Output token limit reached')
                        data = validate(raw)
                        row.update(label='complete',description=data['description'],decisions=data,evidence='')
                        record.pop('error',None)
                        break
                    except ValueError as exc:
                        record['error'] = str(exc)
                        row.update(label='failed',features='',evidence=str(exc))
                        feedback = retry_instruction(str(exc), raw)
                        # A retry is format-only and never triggered by a negative label.
                    except Exception as exc:
                        fatal = f'{type(exc).__name__}: {exc}'
                        record['error'] = fatal
                        row.update(label='failed',features='',evidence=fatal)
                        break
                atomic_json(out/f'responses/frame_{row["frame_id"]:06d}.json',record)
                counts = save_outputs(out,frames,settings)
                if row['label']=='failed':
                    print(f'Frame {row["frame_id"]} FAILED: {row["evidence"]}',flush=True)
                    if not fatal:
                        print('Invalid response saved; continuing to the next target.',flush=True)
                if index % 10 == 0 or index == len(pending):
                    print(f'{index}/{len(pending)} pending frames processed; {dict(counts)}',flush=True)
                if fatal:
                    break
        except KeyboardInterrupt:
            fatal = 'Interrupted; completed frames saved. Resume using the same output folder.'
        finally:
            save_outputs(out,frames,settings)
            del model
            torch.cuda.empty_cache()
    print('Exporting condition-positive, uncertain, and source inspection clips...',flush=True)
    export_errors = export_review(movie,out,frames,settings['fps'],settings['duration_s'],settings['review_padding'])
    counts = save_outputs(out,frames,settings)
    print(f'Open {out}/review.html\nFrame counts: {dict(counts)}; export failures: {export_errors}',flush=True)
    if fatal or counts['failed'] or export_errors:
        if not fatal and not counts['not_run']:
            print('All targets attempted. Some outputs need attention; failed targets remain failed, not absent. '
                  'Resume to retry failed targets.',flush=True)
        raise SystemExit(f'Incomplete: failed={counts["failed"]}, not_run={counts["not_run"]}, export_errors={export_errors}. {fatal or ""}')
    if counts['not_run']:
        print(f'Partial run: {counts["not_run"]} frames remain. Continue with --resume {out}',flush=True)


if __name__ == '__main__':
    main()
