> Historical preflight snapshot. Its missing-file and path findings were resolved by the cleanup; see ../../README.md.

# Annotation pilot preflight — 2026-09-26

Inspected on login4.triton.aalto.fi. No existing files moved or deleted.

## Existing layout

- code/pilot_tests/: five existing extraction, Qwen, and X-CLIP scripts.
- code/xclip/: film analysis and plotting scripts.
- code/annotation/: created; supplied pilot script and README are missing.
- moviestimulus/: one source movie.
- outputs/: existing clips, manifests, JSONL, CSV, PDF, and PNG results; preserved.
- notes/: manual_annotations.csv and five existing reports/tables.

## Validated inputs

- Movie: `/scratch/work/bernada4/partlycloudy_project/moviestimulus/partly_cloudy_sd_nocredits.mov`; ffprobe duration 313.812000 seconds.
- Manifest: `/scratch/work/bernada4/partlycloudy_project/outputs/clips_offset_minus10s/manifest.csv`; 19 unique events, all clip files present.
- All rows match notes/manual_annotations.csv with a -10 second movie offset.
- Category counts: control 3, social 5, pain 7, mental 4.
- All event intervals are within the movie duration.
- No exact duplicate files found among 65 existing non-Git files.

## Existing path discrepancies

- All five scripts under code/pilot_tests/ resolve their root to code/ rather than the repository root (parents[1] or parent.parent). Their default notes/output paths therefore differ from actual locations.
- extract_examples.py and qwen_context_test.py now resolve their movie path from parents[2] to the verified project-local moviestimulus/partly_cloudy_sd_nocredits.mov.
- Both code/xclip/ scripts use parents[2], correctly resolving the repository root.
- Git already records code/extract_examples.py as deleted and an existing code/pilot_tests/extract_examples.py as modified. No new move was performed.

## Protocol and pending work

- Existing Qwen definitions: mental = inferred thoughts, beliefs, intentions, or feelings; pain = physically painful event; social = interaction without a strong focus on inferred mental states; control = scenery/physical events without a specific character event as focus.
- Existing Qwen ratings are independent integers 0–3. The missing evidence-pilot protocol cannot yet be checked against these definitions.
- Need original qwen_evidence_pilot.py and its README.md before prepare, 10-candidate GPU inference, parse validation, remaining 17 candidates, or blind review generation.
- Intended new output directory: outputs/annotation_pilot/.
- Compare remains pending completed human review.
- Existing ignore rules preserved, including the user removal of the blanket CSV ignore; model weights and cache patterns added.
