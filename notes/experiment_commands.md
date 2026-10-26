# Experiment commands in the current Triton workspace

Run from the repository root. Keep the current script paths: roots are derived
from their depth. Movie and generated results are local prerequisites, not Git
assets. CPU extraction/validation needs ffmpeg and ffprobe. GPU inference uses
the project Python environment with PyTorch, Transformers, video dependencies,
and cached model weights. X-CLIP plotting also needs NumPy and Matplotlib.
The saved Slurm files encode the Triton environment and paths; adapt those
paths when running elsewhere.

Commands below reproduce the configurations in the current source. Historical
shell commands and job files were not all retained, so these are not claims of
an exact recovered submission history. No inference was rerun for this commit.

## Extraction and earlier pilots

```bash
python code/legacy/extract_examples.py --offset-seconds -10
python code/legacy/qwen_video_pilot.py
python code/legacy/qwen_context_test.py --context-seconds 0 --fps 2
python code/legacy/qwen_context_test.py --context-seconds 4 --fps 2
python code/legacy/xclip_video_pilot.py --limit 19
```

Extraction reads the existing 19 movie-event labels in
`notes/manual_annotations.csv`, writes `outputs/clips_offset_minus10s/`, and
uses movie time = annotated onset minus 10 seconds. The Qwen baseline uses
Qwen2.5-VL-3B-Instruct, 2 fps and independent 0–3 scores; it overwrites its
baseline JSONL. Context pilots default to five selected events; `--all-events`
changes that experiment. See the legacy README for clip restoration.
The evidence-first 19 anchors plus eight unannotated windows use the separate
prepare/infer/review/compare commands in the main and annotation READMEs.

## Whole-movie Qwen v2 and v3

Both use Qwen/Qwen2.5-VL-3B-Instruct, 6-second clips, 3-second stride,
2 fps, no added context, and a final window ending at 313.812 seconds
(104 windows). Generation is deterministic (`do_sample=False`), capped at
900 new tokens. V2 scores 0–4; v3 scores 0–10 with a cartoon-aware rubric.
The version-specific prompts and rubrics are retained in each script.

```bash
python code/annotation/qwen_whole_movie_scores.py prepare
python code/annotation/qwen_whole_movie_scores.py validate
sbatch code/annotation/run_whole_movie_v2.sbatch
# The v2 job runs infer then rank --top 10 --min-score 2 (defaults).

python code/annotation/qwen_whole_movie_scores_v3.py prepare
python code/annotation/qwen_whole_movie_scores_v3.py validate
# Run infer on a GPU node with the project environment:
python code/annotation/qwen_whole_movie_scores_v3.py infer
python code/annotation/qwen_whole_movie_scores_v3.py rank --top 10 --min-score 2
python code/annotation/organize_ranked_v3.py
```

Outputs are `outputs/qwen_whole_movie_scores_v2_no_context/` and
`outputs/qwen_whole_movie_scores_v3_cartoon/`. Ranking requires all responses,
excludes invalid responses, sorts descending score then start time, and greedily
selects nonoverlapping windows per category. The v3 organizer creates relative
clip symlinks in mental/pain/social/control folders. Equivalent v2 folders exist
locally but no separate v2 organizer was found. No v3 Slurm file was found.
The v2 job requests one V100 32 GB GPU, four CPUs, 32 GB RAM, two hours;
it uses cached weights offline and assumes an already configured Python environment.

## Whole-movie Qwen v5 and both ranking filters

V5 uses the same Qwen model, 2-second clips, 1-second stride, 6 fps,
0–10 scores, and 600 deterministic generation tokens. The full 313.812-second
movie yields 313 windows including the final 311.812–313.812-second clip.

```bash
sbatch run_qwen_v5_2s.sbatch
# Equivalent stages; infer must run on a GPU node:
python code/annotation/qwen_whole_movie_scores_v5_2s.py prepare
python code/annotation/qwen_whole_movie_scores_v5_2s.py validate
python code/annotation/qwen_whole_movie_scores_v5_2s.py infer
python code/annotation/qwen_whole_movie_scores_v5_2s.py rank --top 20 --min-score 7 --max-other 10
python code/annotation/qwen_whole_movie_scores_v5_2s.py rank --top 20 --min-score 7 --max-other 3
python code/annotation/organize_ranked_v5.py
```

The saved job requests one V100 32 GB GPU, four CPUs, 16 GB RAM and four
hours, loads `scicomp-python-env/2025.2`, and sets scratch HF_HOME. It runs
prepare, infer and both ranks. Outputs live under
`outputs/qwen_whole_movie_scores_v5_2s_6fps/`.

| Filter | Eligibility | Ranking CSV | Review folder |
| --- | --- | --- | --- |
| other10 | Target >= 7; every other score <= 10 (full score range) | `ranked_top20_min7_other10.csv` | `review_other10/` |
| other3 | Target >= 7; every other score <= 3 | `ranked_top20_min7_other3.csv` | `review_other3/` |

Each selects up to 20 nonoverlapping windows per category, independently.
Ties use lower maximum other score, then lower sum of other scores, then
earlier start. Overlap suppression applies within each category, so a clip can
occur in multiple categories under other10. Invalid responses are excluded
and a complete inference run is required. The organizer makes relative links
under each review folder's mental/pain/social/control directories.

Local job 20654124 (2026-10-02) records 313 responses, nine invalid excluded.
Other10 yielded Mental/Pain/Social/Control counts 20/7/20/20 (67 total);
other3 yielded 3/0/0/20 (23 total). These counts describe saved local results,
not a new validation run. The log and ranking outputs remain excluded.

## JSON parsing and repair provenance

The scripts retain JSON parsing, validation, and interrupted-append recovery.
The local v3 run contains `scores.jsonl.before_format_repair` alongside
`scores.jsonl`; no standalone JSON-format repair utility or repair command was
found in the current workspace. The exact historical repair cannot be
reproduced from a retained utility. Neither result file is committed, and no
repair or rewrite was performed during this publication.

## X-CLIP experiments

```bash
python code/xclip/xclip_film_analysis.py --phase annotations --frames 8
python code/xclip/xclip_film_analysis.py --phase timeline --window-seconds 2 --frames 8
python code/xclip/xclip_film_analysis.py --phase annotations --frames 16
python code/xclip/xclip_film_analysis.py --phase timeline --window-seconds 6 --frames 16
python code/xclip/xclip_film_analysis.py --phase timeline --window-seconds 8 --frames 8
python code/xclip/plot_xclip_film.py --window-seconds 6 --frames 16
python code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8
python code/xclip/summarize_xclip.py
```

Inference runs on GPU. Eight frames selects `microsoft/xclip-base-patch32`;
16 selects `microsoft/xclip-base-patch32-16-frames`. Timeline stride is one
second and decoded sampling is 4 Hz. The original 2-second run used eight
frames, not two. Current commands reproduce configurations; historical
unsuffixed output names/schema differ, as documented in the main README.
No X-CLIP Slurm files were present. Archived reports and the current summary
are small documentation; raw JSONL, plots and reports under outputs remain
local. CPU plotting/summarization requires those excluded local results.
