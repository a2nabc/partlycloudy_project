# Repository cleanup — 2026-09-26

Completed on Triton in `/scratch/work/bernada4/partlycloudy_project`. No GPU inference was run. Hidden files were inspected; `.git/` internals are excluded from file inventories. No AGENTS.md was found.

## Decisions and preserved data

- No byte-identical duplicates were found by SHA-256 across the working files. No unique source or raw result was deleted.
- Four historical scripts moved to code/legacy/; the CPU X-CLIP summarizer moved to code/xclip/. All five now resolve the repository root correctly with parents[2].
- Current annotation files were present at this inspection and remain unchanged. Existing category definitions were not altered.
- The original timeline is 2 seconds / 8 frames according to its JSONL, not the requested 2 seconds / 2 frames. No matching 2-frame result exists in this tree.
- Kept the original unsuffixed plot/PDF/CSV because the old JSONL schema is incompatible with the current renderer and exact regeneration was not verified.
- Kept all 19 active clips; current X-CLIP inference reads them. Deleted context clips are used only by the archived Qwen context experiment, which can recreate them from the movie and saved intervals.
- No human review files or annotation-pilot outputs existed at cleanup time; their future locations remain visible to Git.
- Narrowed outputs ignore rules so raw JSONL and manifests are visible; generated artifacts remain ignored. Existing non-output ignore rules were preserved.
- The pre-existing deletion of code/extract_examples.py was left alone. Git deletion/untracked pairs for other paths reflect unstaged moves, not discarded code.

Deleted 16 derived files, freeing 13,884,345 bytes (13.88 MB).

## Every moved path

| Before | After | Reason |
| --- | --- | --- |
| `code/pilot_tests/extract_examples.py` | `code/legacy/extract_examples.py` | Unique historical extraction or inference script retained for reproducibility; project-root paths corrected. |
| `code/pilot_tests/qwen_context_test.py` | `code/legacy/qwen_context_test.py` | Unique historical extraction or inference script retained for reproducibility; project-root paths corrected. |
| `code/pilot_tests/qwen_video_pilot.py` | `code/legacy/qwen_video_pilot.py` | Unique historical extraction or inference script retained for reproducibility; project-root paths corrected. |
| `code/pilot_tests/xclip_video_pilot.py` | `code/legacy/xclip_video_pilot.py` | Unique historical extraction or inference script retained for reproducibility; project-root paths corrected. |
| `code/pilot_tests/summarize_xclip.py` | `code/xclip/summarize_xclip.py` | CPU report generator retained with X-CLIP tools. |
| `notes/xclip_19_events_report.md` | `notes/archive/xclip_19_events_report.md` | Historical X-CLIP report retained in archive. |
| `notes/xclip_19_events_table.tex` | `notes/archive/xclip_19_events_table.tex` | Historical X-CLIP report retained in archive. |
| `notes/xclip_film_report.md` | `notes/archive/xclip_film_report.md` | Historical X-CLIP report retained in archive. |
| `notes/xclip_film_report_6s_16f.md` | `notes/archive/xclip_film_report_6s_16f.md` | Historical X-CLIP report retained in archive. |
| `notes/xclip_film_report_8s_8f.md` | `notes/archive/xclip_film_report_8s_8f.md` | Historical X-CLIP report retained in archive. |
| `notes/annotation_pilot_inventory.md` | `notes/archive/annotation_pilot_inventory.md` | Historical preflight snapshot; superseded by current README and cleanup inventory. |
| `README.Md` | `README.md` | Normalize README filename and replace outdated project overview. |

Archived Markdown image references were adjusted for the new location. New generated reports go to outputs/reports/, so they do not overwrite archived reports. README.Md was renamed and rewritten as README.md.

## Every deleted path

| Deleted file | Bytes | Reason |
| --- | ---: | --- |
| `outputs/xclip_timeline_scores_6s_16f.csv` | 67451 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 6 --frames 16; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/xclip_timeline_6s_16f.png` | 711013 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 6 --frames 16; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/xclip_timeline_6s_16f.pdf` | 49188 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 6 --frames 16; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/xclip_timeline_scores_8s_8f.csv` | 67086 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/xclip_timeline_8s_8f.png` | 618341 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/xclip_timeline_8s_8f.pdf` | 48947 | Regenerated successfully with code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8; CSV is byte-identical to regenerated data. Source JSONL retained. |
| `outputs/context_clips_0s_2fps/01_context.mp4` | 947323 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_0s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_0s_2fps/03_context.mp4` | 760732 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_0s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_0s_2fps/08_context.mp4` | 172311 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_0s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_0s_2fps/10_context.mp4` | 898741 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_0s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_0s_2fps/17_context.mp4` | 1017860 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_0s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_4s_2fps/01_context.mp4` | 1810306 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_4s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_4s_2fps/03_context.mp4` | 1736176 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_4s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_4s_2fps/08_context.mp4` | 1076633 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_4s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_4s_2fps/10_context.mp4` | 1881305 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_4s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |
| `outputs/context_clips_4s_2fps/17_context.mp4` | 2020932 | Unused historical context clip; exact movie start/end and filename preserved in outputs/qwen_context_4s_2fps.jsonl; extraction command retained in code/legacy/qwen_context_test.py. No current annotation/X-CLIP script uses this directory. |

Removed these now-empty directories: `code/pilot_tests/`, `outputs/context_clips_0s_2fps/`, `outputs/context_clips_4s_2fps/`.

## Retained raw results and protected inputs

| Path | Bytes | Records | SHA-256 (unchanged) |
| --- | ---: | ---: | --- |
| `moviestimulus/partly_cloudy_sd_nocredits.mov` | 96646276 | — | `f0abad58551c9588e44103e8ea394da9d262da6d0e3d345351319020bcd1fcc0` |
| `notes/manual_annotations.csv` | 263 | 19 | `77ec684350fe560aef9184c5b622703c060bdb9b1bb0c4e9f76272986f490572` |
| `outputs/clips_offset_minus10s/manifest.csv` | 1208 | 19 | `13bf461d8b6232e2ba9c19f2ed3672fcb340b0b912e6380e8e73196ee20a5160` |
| `outputs/qwen2_5_vl_3b_pilot.jsonl` | 6573 | 19 | `8902642c25bf86ea8002f3aed182de53be4bac0aa53e5156955cec202a4e6c3e` |
| `outputs/qwen_context_0s_2fps.jsonl` | 2937 | 5 | `04f32a6a71a5c1c89fa82deb3cb09bb7af6d8ced6b9d76d0b973b2564c82c1cd` |
| `outputs/qwen_context_4s_2fps.jsonl` | 2958 | 5 | `cf3b969261ac508219830a53bfda8b362907921c42ac49c4cabae08b584edbe7` |
| `outputs/xclip_base_19_events.jsonl` | 14570 | 19 | `157956c6f17eb5f3a109a17de46ecc53bcbb065b52691c34ca517e5e13e22029` |
| `outputs/xclip_movie_timeline.jsonl` | 529320 | 312 | `a21285f5e0e9844d6745ba41742891c8a60a5c8530e4ee7741999ea392b32a9c` |
| `outputs/xclip_movie_timeline_6s_16f.jsonl` | 577193 | 308 | `53fcf8eb590fab9c23d0e8fea64e75b1c04a0ff9bdc8f9aa44abdffc66de117e` |
| `outputs/xclip_movie_timeline_8s_8f.jsonl` | 551211 | 306 | `841e7357f5e4386a5781f30fb476b0ed10ceca8af48d6909886eb5c8d4fcafbe` |
| `outputs/xclip_wording_check.jsonl` | 31929 | 19 | `f959fbca2fc7cad51168e8cff550a8ef0a18a8c95e6fdbda67178bfcbdbe9c2a` |
| `outputs/xclip_wording_check_16f.jsonl` | 34947 | 19 | `3da8541e4a7be8a688cff29a29a7941fb15a17c26e0cdf1c63e713db4edad6d8` |
| `outputs/xclip_wording_check_8f.jsonl` | 33525 | 19 | `8b749888067b76222746aad1ff8953b49a63eb9179fcbb9b137b93d2baab9d73` |

## Before tree with sizes

```text
partlycloudy_project/
  .gitignore  (535 bytes)
  README.Md  (342 bytes)
  code/
    annotation/
      README.md  (3597 bytes)
      qwen_evidence_pilot.py  (16482 bytes)
    pilot_tests/
      extract_examples.py  (4865 bytes)
      qwen_context_test.py  (10057 bytes)
      qwen_video_pilot.py  (3610 bytes)
      summarize_xclip.py  (6700 bytes)
      xclip_video_pilot.py  (4960 bytes)
    xclip/
      plot_xclip_film.py  (10298 bytes)
      xclip_film_analysis.py  (11979 bytes)
  moviestimulus/
    partly_cloudy_sd_nocredits.mov  (96646276 bytes)
  notes/
    annotation_pilot_inventory.md  (2584 bytes)
    manual_annotations.csv  (263 bytes)
    xclip_19_events_report.md  (2567 bytes)
    xclip_19_events_table.tex  (2225 bytes)
    xclip_film_report.md  (1815 bytes)
    xclip_film_report_6s_16f.md  (1962 bytes)
    xclip_film_report_8s_8f.md  (1947 bytes)
  outputs/
    clips_offset_minus10s/
      01_control_14-20s.mp4  (1042273 bytes)
      02_control_38-48s.mp4  (1200685 bytes)
      03_social_52-58s.mp4  (866109 bytes)
      04_control_60-68s.mp4  (1054536 bytes)
      05_social_76-86s.mp4  (1236140 bytes)
      06_social_86-88s.mp4  (231614 bytes)
      07_social_100-106s.mp4  (662303 bytes)
      08_pain_112-114s.mp4  (205777 bytes)
      09_social_114-118s.mp4  (511483 bytes)
      10_pain_124-130s.mp4  (994583 bytes)
      11_pain_146-150s.mp4  (482309 bytes)
      12_mental_172-180s.mp4  (961706 bytes)
      13_pain_182-184s.mp4  (317000 bytes)
      14_pain_196-202s.mp4  (1035252 bytes)
      15_pain_214-218s.mp4  (641130 bytes)
      16_mental_240-248s.mp4  (938547 bytes)
      17_mental_260-270s.mp4  (1181832 bytes)
      18_mental_276-294s.mp4  (2412767 bytes)
      19_pain_302-304s.mp4  (674453 bytes)
      manifest.csv  (1208 bytes)
    context_clips_0s_2fps/
      01_context.mp4  (947323 bytes)
      03_context.mp4  (760732 bytes)
      08_context.mp4  (172311 bytes)
      10_context.mp4  (898741 bytes)
      17_context.mp4  (1017860 bytes)
    context_clips_4s_2fps/
      01_context.mp4  (1810306 bytes)
      03_context.mp4  (1736176 bytes)
      08_context.mp4  (1076633 bytes)
      10_context.mp4  (1881305 bytes)
      17_context.mp4  (2020932 bytes)
    qwen2_5_vl_3b_pilot.jsonl  (6573 bytes)
    qwen_context_0s_2fps.jsonl  (2937 bytes)
    qwen_context_4s_2fps.jsonl  (2958 bytes)
    xclip_base_19_events.jsonl  (14570 bytes)
    xclip_movie_timeline.jsonl  (529320 bytes)
    xclip_movie_timeline_6s_16f.jsonl  (577193 bytes)
    xclip_movie_timeline_8s_8f.jsonl  (551211 bytes)
    xclip_timeline.pdf  (49431 bytes)
    xclip_timeline.png  (779581 bytes)
    xclip_timeline_6s_16f.pdf  (49188 bytes)
    xclip_timeline_6s_16f.png  (711013 bytes)
    xclip_timeline_8s_8f.pdf  (48947 bytes)
    xclip_timeline_8s_8f.png  (618341 bytes)
    xclip_timeline_scores.csv  (68895 bytes)
    xclip_timeline_scores_6s_16f.csv  (67451 bytes)
    xclip_timeline_scores_8s_8f.csv  (67086 bytes)
    xclip_wording_check.jsonl  (31929 bytes)
    xclip_wording_check_16f.jsonl  (34947 bytes)
    xclip_wording_check_8f.jsonl  (33525 bytes)
```

## After tree with sizes

```text
partlycloudy_project/
  .gitignore  (710 bytes)
  README.md  (5781 bytes)
  code/
    annotation/
      README.md  (3597 bytes)
      qwen_evidence_pilot.py  (16482 bytes)
    legacy/
      README.md  (2345 bytes)
      extract_examples.py  (4857 bytes)
      qwen_context_test.py  (10042 bytes)
      qwen_video_pilot.py  (3617 bytes)
      xclip_video_pilot.py  (4955 bytes)
    xclip/
      plot_xclip_film.py  (10670 bytes)
      summarize_xclip.py  (6740 bytes)
      xclip_film_analysis.py  (11936 bytes)
  moviestimulus/
    partly_cloudy_sd_nocredits.mov  (96646276 bytes)
  notes/
    archive/
      annotation_pilot_inventory.md  (2704 bytes)
      xclip_19_events_report.md  (2567 bytes)
      xclip_19_events_table.tex  (2225 bytes)
      xclip_film_report.md  (1818 bytes)
      xclip_film_report_6s_16f.md  (2015 bytes)
      xclip_film_report_8s_8f.md  (2000 bytes)
    manual_annotations.csv  (263 bytes)
    repository_cleanup.md  (size omitted for this self-referential report)
    xclip_summary.md  (1160 bytes)
  outputs/
    clips_offset_minus10s/
      01_control_14-20s.mp4  (1042273 bytes)
      02_control_38-48s.mp4  (1200685 bytes)
      03_social_52-58s.mp4  (866109 bytes)
      04_control_60-68s.mp4  (1054536 bytes)
      05_social_76-86s.mp4  (1236140 bytes)
      06_social_86-88s.mp4  (231614 bytes)
      07_social_100-106s.mp4  (662303 bytes)
      08_pain_112-114s.mp4  (205777 bytes)
      09_social_114-118s.mp4  (511483 bytes)
      10_pain_124-130s.mp4  (994583 bytes)
      11_pain_146-150s.mp4  (482309 bytes)
      12_mental_172-180s.mp4  (961706 bytes)
      13_pain_182-184s.mp4  (317000 bytes)
      14_pain_196-202s.mp4  (1035252 bytes)
      15_pain_214-218s.mp4  (641130 bytes)
      16_mental_240-248s.mp4  (938547 bytes)
      17_mental_260-270s.mp4  (1181832 bytes)
      18_mental_276-294s.mp4  (2412767 bytes)
      19_pain_302-304s.mp4  (674453 bytes)
      manifest.csv  (1208 bytes)
    qwen2_5_vl_3b_pilot.jsonl  (6573 bytes)
    qwen_context_0s_2fps.jsonl  (2937 bytes)
    qwen_context_4s_2fps.jsonl  (2958 bytes)
    xclip_base_19_events.jsonl  (14570 bytes)
    xclip_movie_timeline.jsonl  (529320 bytes)
    xclip_movie_timeline_6s_16f.jsonl  (577193 bytes)
    xclip_movie_timeline_8s_8f.jsonl  (551211 bytes)
    xclip_timeline.pdf  (49431 bytes)
    xclip_timeline.png  (779581 bytes)
    xclip_timeline_scores.csv  (68895 bytes)
    xclip_wording_check.jsonl  (31929 bytes)
    xclip_wording_check_16f.jsonl  (34947 bytes)
    xclip_wording_check_8f.jsonl  (33525 bytes)
```

## Checks

```text
Syntax OK: code/annotation/qwen_evidence_pilot.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/annotation/qwen_evidence_pilot.py --help
Syntax OK: code/legacy/extract_examples.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/legacy/extract_examples.py --help
Syntax OK: code/legacy/qwen_context_test.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/legacy/qwen_context_test.py --help
Syntax OK: code/legacy/qwen_video_pilot.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python -c import runpy; runpy.run_path('code/legacy/qwen_video_pilot.py', run_name="cleanup_import_check")
Syntax OK: code/legacy/xclip_video_pilot.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/legacy/xclip_video_pilot.py --help
Syntax OK: code/xclip/plot_xclip_film.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/xclip/plot_xclip_film.py --help
Syntax OK: code/xclip/summarize_xclip.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/xclip/summarize_xclip.py --help
Syntax OK: code/xclip/xclip_film_analysis.py
PASS: /appl/scibuilder-mamba/aalto-rhel9/prod/software/scicomp-python-env/2025.2/b4b5f8e/bin/python code/xclip/xclip_film_analysis.py --help
All script project roots and existing default movie/manifest/input paths resolve.
SHA-256 unchanged: 13 protected files (10 JSONL, movie, manual annotations, manifest).
All retained raw JSONL parses as JSON; model replies preserved without alteration.
19 manifest rows match manual labels, offsets, durations, and retained clip paths.
Git ignore checks: sources, raw JSONL, manifests, review/manual CSV visible; clips, plots, derived CSV, weights and caches ignored.
6s/16f and 8s/8f plotting ran on CPU in /tmp; both score CSVs byte-identical before deletion.
No GPU inference, model download, staging, or commit performed.
```

`git diff --check` passed. Active source/README searches found no stale parents[1], parent.parent, old movie location, or code/pilot_tests references. Historical inventory deliberately retains its dated observations.

## Git status before

```text
M .gitignore
 D code/extract_examples.py
 M code/pilot_tests/extract_examples.py
 M code/pilot_tests/xclip_video_pilot.py
?? code/annotation/
?? code/pilot_tests/qwen_context_test.py
?? code/pilot_tests/summarize_xclip.py
?? code/xclip/
?? notes/annotation_pilot_inventory.md
?? notes/xclip_19_events_report.md
?? notes/xclip_19_events_table.tex
?? notes/xclip_film_report.md
?? notes/xclip_film_report_6s_16f.md
?? notes/xclip_film_report_8s_8f.md
```

## Git status after

```text
M .gitignore
 D README.Md
 D code/extract_examples.py
 D code/pilot_tests/extract_examples.py
 D code/pilot_tests/qwen_video_pilot.py
 D code/pilot_tests/xclip_video_pilot.py
?? README.md
?? code/annotation/
?? code/legacy/
?? code/xclip/
?? notes/archive/
?? notes/repository_cleanup.md
?? notes/xclip_summary.md
?? outputs/
```

No staging or commits were performed. Raw outputs appear as untracked because the previous blanket ignore rule was removed.
