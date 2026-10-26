# Evidence-first video annotation pilot

## Question

Can a model identify *different* kinds of scenes in *Partly Cloudy* after it
first records observable actions and reactions? The X-CLIP similarity curves
mostly rose and fell together, so their peaks alone do not supply separate
Mental, Pain, Social, and Control clips.

## What this pilot does

`qwen_evidence_pilot.py` creates 27 candidates: the 19 manually annotated
intervals with four seconds of surrounding video on either side, and eight
eight-second, nonoverlapping windows sampled across parts of the movie with a
one-second buffer from those
intervals. The latter are **unannotated**, not Control negatives.

For each candidate Qwen2.5-VL-3B-Instruct samples the video at 2 fps. Its first
pass describes visible actions, reactions, relevant sequence, and uncertainty,
without category names. A second, text-only pass considers that description and
proposes Mental, Pain, Social, Control, or Unclear. This is a *new task*, so its
labels are not directly comparable with the earlier Qwen 0–3 scores or X-CLIP
logits. The human label is stored in the candidate manifest but never sent to
Qwen or shown in the first human review sheet.

`Unclear` is a useful output. A plausible proposed label is not proof that
the model actually saw the relevant event; check the clip and its description.
The text-only second pass can inherit a mistaken or incomplete description.

## Run on Triton

Copy this directory to `<project>/code/annotation/`. The script expects the
existing `outputs/clips_offset_minus10s/manifest.csv` and movie at
`moviestimulus/partly_cloudy_sd_nocredits.mov`. From the project root:

```bash
export HF_HOME=/scratch/work/bernada4/hf_cache
python code/annotation/qwen_evidence_pilot.py prepare
# Request or enter a GPU compute node before inference.
python code/annotation/qwen_evidence_pilot.py infer --limit 10
python code/annotation/qwen_evidence_pilot.py infer
python code/annotation/qwen_evidence_pilot.py review
# After reviewing all 27 rows:
python code/annotation/qwen_evidence_pilot.py compare
```

`prepare` and `review` need ffmpeg/ffprobe or Python respectively; `infer`
needs a GPU, PyTorch, Transformers, and Qwen's video processing dependencies.
`infer` appends one result per completed candidate, so rerunning resumes. It
retains raw replies even when JSON parsing fails. A second `review` call refuses
to replace an existing human review sheet.

The generated files live under `outputs/annotation_pilot/`; the blank review
columns are in `notes/annotation_review.csv`. The original human labels stay
hidden in that sheet until `compare` joins them from the candidate manifest.
Existing pilot outputs are left alone. Keep the candidate manifest and raw JSONL together when reporting this
run, because the prompt, fps, and exact clips determine what was measured.

## Review before scaling up

Watch all 27 candidate clips. For every row, fill `reviewed_label` with one of
Mental, Pain, Social, Control, or Unclear; fill `evidence_visible` with yes/no,
and note a mistimed focus, misdescribed action, or overlapping categories in
`review_notes`. `compare` reports model and reviewed categories against the 19
original manual labels. For the eight unannotated windows, use only the
independently reviewed labels.

Decide whether the descriptions are accurate and whether the proposed labels
separate the four conditions. Only after this check should the workflow be
expanded across the movie. Do not select one high-scoring window per condition
from four curves that largely track the same visual changes.