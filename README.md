# Partly Cloudy fMRI Encoding Project

Explore video-model features and human annotations for Partly Cloudy, with the longer-term aim of relating them to fMRI responses.

## Directory map

```text
code/
  annotation/  Current evidence-first Qwen pilot and protocol README
  xclip/       X-CLIP film inference, plotting, and baseline report generator
  legacy/      Unique historical extraction and pilot inference scripts
moviestimulus/ One verified project-local source movie
notes/         Manual annotations, current summaries, future human review
  archive/     Historical X-CLIP reports and preflight inventory
outputs/       Retained raw JSONL, manifest, active clips, generated data
```

Run commands from this directory. Script roots resolve from `Path(__file__).resolve().parents[2]`; do not move scripts to a different depth without updating that expression.

- Movie: `moviestimulus/partly_cloudy_sd_nocredits.mov` (313.812 seconds).
- Original manual labels: `notes/manual_annotations.csv`.
- Clip manifest: `outputs/clips_offset_minus10s/manifest.csv` (19 events; movie time = manual onset minus 10 seconds).
- Active event clips: `outputs/clips_offset_minus10s/*.mp4`, retained because X-CLIP reads them.

## Whole-movie v2 run

The [whole-movie workflow](code/annotation/WHOLE_MOVIE_SCORING.md) uses six-second
clips with a three-second stride, including a final clip reaching the movie end,
with no added context. One video response per clip describes actions and
reactions and gives evidence for all four conditions. Preparation validates full
coverage and decodability before GPU inference; inference resumes completed
responses and ranking requires the full run. Outputs are isolated in
`outputs/qwen_whole_movie_scores_v2_no_context/`.

## Current annotation workflow

The supplied [protocol](code/annotation/README.md) and `code/annotation/qwen_evidence_pilot.py` are the current entry point. They use 19 anchor intervals with four seconds of surrounding context and eight unannotated windows. The model describes visible evidence first, then proposes Mental, Pain, Social, Control, or Unclear. This is a different task from the historical independent 0–3 Qwen ratings; the cleanup did not change either protocol.

```bash
# Login node: requires ffmpeg and ffprobe.
python code/annotation/qwen_evidence_pilot.py prepare
# GPU compute node only; use the project model environment.
export HF_HOME=/scratch/work/bernada4/hf_cache
python code/annotation/qwen_evidence_pilot.py infer --limit 10
# Inspect parsing of those results before resuming the other 17.
python code/annotation/qwen_evidence_pilot.py infer
# CPU: create the blind review sheet, then complete it manually.
python code/annotation/qwen_evidence_pilot.py review
python code/annotation/qwen_evidence_pilot.py compare
```

Outputs are isolated in `outputs/annotation_pilot/`, including `candidates.csv` and `qwen_3b_evidence.jsonl`. Human review belongs in `notes/annotation_review.csv`; review refuses to overwrite an existing sheet. Keep candidate manifests and raw replies together. No preparation, review generation, or GPU inference was run during cleanup; no annotation-pilot results or human review sheet existed at cleanup time.

## Retained historical experiments

All paths below are relative to `outputs/`. Raw JSONL files were preserved byte for byte, including failed or unparseable model replies.

| Experiment | Retained raw results | Records |
| --- | --- | ---: |
| Qwen baseline, 2 fps | `qwen2_5_vl_3b_pilot.jsonl` | 19 |
| Qwen, no surrounding context, 2 fps | `qwen_context_0s_2fps.jsonl` | 5 |
| Qwen, 4-second context, 2 fps | `qwen_context_4s_2fps.jsonl` | 5 |
| X-CLIP baseline, 8 frames/event | `xclip_base_19_events.jsonl` | 19 |
| X-CLIP original 2-second windows, **8 frames** | `xclip_movie_timeline.jsonl`; `xclip_wording_check.jsonl` | 312; 19 |
| X-CLIP 6-second windows, 16 frames | `xclip_movie_timeline_6s_16f.jsonl`; `xclip_wording_check_16f.jsonl` | 308; 19 |
| X-CLIP 8-second windows, 8 frames | `xclip_movie_timeline_8s_8f.jsonl`; `xclip_wording_check_8f.jsonl` | 306; 19 |

The requested “2 s/2 frames” configuration is not present: the original JSONL records eight frames at 4 Hz in a two-second window. No results were relabeled or discarded to resolve this discrepancy. Historical Qwen's 2 fps is a sampling rate, not a two-frame clip.

## X-CLIP and regeneration

Current inference entry point: `python code/xclip/xclip_film_analysis.py --help`. GPU inference uses `--phase annotations` or `--phase timeline`, with matched `--frames 8` or `--frames 16`; timeline window length is set by `--window-seconds`.

Regenerate derived artifacts on CPU from retained JSONL:

```bash
python code/xclip/plot_xclip_film.py --window-seconds 6 --frames 16
python code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8
python code/xclip/summarize_xclip.py
```

Plots and score CSVs go to `outputs/`; generated Markdown/TeX reports go to `outputs/reports/`, preserving the historical reports in `notes/archive/`. Plotting also accepts `--output-dir` and `--report-dir`. The two newer CSVs were verified byte-identical after regeneration before their redundant copies were deleted.

The original `xclip_timeline.png`, `xclip_timeline.pdf`, and `xclip_timeline_scores.csv` remain: the original unsuffixed JSONL lacks `movie_duration_s`, and the current renderer does not accept that older input format. Their exact regeneration was not verified.

Historical context clips were removed after checking their recorded timestamps against the manifest. See [legacy documentation](code/legacy/README.md) for CPU-only restoration without rerunning inference. The 19 active clips remain; their extraction utility is retained in `code/legacy/extract_examples.py`.

## Version control and cleanup record

Generated movie clips, model weights, caches, output plots, derived timeline CSVs, and generated reports are ignored. The entire `outputs/` tree and runtime logs are ignored, including raw JSONL, generated manifests, ranking CSVs, and review links. Source code and documentation are versioned; the existing movie-event annotations in `notes/manual_annotations.csv` remain tracked. No participant or fMRI data are included.

[Cleanup inventory](notes/repository_cleanup.md) records before/after trees with sizes, every move/deletion and its reason, retained raw results, validation checks, and Git status. [Current X-CLIP summary](notes/xclip_summary.md) links the historical reports.

See [experiment commands and ranking filters](notes/experiment_commands.md) for v2/v3/v5 reproduction, historical experiments, Slurm settings, and provenance limits.
