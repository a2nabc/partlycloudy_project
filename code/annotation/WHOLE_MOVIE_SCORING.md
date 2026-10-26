# Whole-movie v2 scoring

Run `qwen_whole_movie_scores.py` from the project root. Outputs go to
`outputs/qwen_whole_movie_scores_v2_no_context/`; prior v1 results are preserved.

V2 uses six-second clips starting every three seconds, plus a final six-second
clip ending at the movie end when the stride does not land there. For the
313.812-second movie this gives 104 clips, ending with 307.812–313.812 seconds.
`clip_start_s = focus_start_s` and `clip_end_s = focus_end_s` throughout.
There is no added context. The model judges the entire supplied clip.

Each clip receives one video-based response at 2 fps, describing actions and
reactions and independently scoring Mental, Pain, Social, and Control from
0–4, with evidence or an explanation of absence for every condition. These are
provisional retrieval scores, not calibrated probabilities. Manual annotation
files are never read by this pipeline.

```bash
python code/annotation/qwen_whole_movie_scores.py prepare
python code/annotation/qwen_whole_movie_scores.py validate
sbatch code/annotation/run_whole_movie_v2.sbatch
```

Preparation checks the exact full-movie schedule, gap-free coverage through
the end, encoded durations (within 0.1 seconds for frame rounding), and full
decoding of every clip. It saves `coverage_validation.json`. Inference repeats
validation before importing GPU dependencies or loading the model.

`scores.jsonl` retains the exact prompt, raw response, parsed JSON, and validated
scores for each completed clip, including parse failures. Writes are flushed
and synced per clip. Repeating `infer` resumes missing clips. A lock prevents
concurrent inference writers. An interrupted final JSONL append is backed up
to `interrupted_appends.bin` before recovery; completed responses are preserved.

The batch job processes every missing clip and runs `rank` only after inference
succeeds. Ranking also independently refuses any incomplete run. Invalid model
responses remain in the raw results and are counted and excluded from rankings;
they are not silently regenerated. `ranked_candidates.csv` contains up to ten
nonoverlapping candidates per condition with scores of at least two. Human
review columns are blank and are not inference inputs.

CPU regression checks:

```bash
python -m unittest discover -s code/annotation -p 'test_whole_movie_scores.py' -v
```
