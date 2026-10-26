# Historical scripts

These unique scripts are retained for reproducibility, not used by the current evidence-first annotation workflow. All project roots now resolve correctly from this directory. No byte-identical duplicates were found.

| Script | Purpose and status |
| --- | --- |
| `extract_examples.py` | Extract the 19 manually annotated event clips; still useful for restoration. Defaults to a -10-second offset; reads `notes/manual_annotations.csv`. Rewrites its manifest when run, so preserve any manual manifest changes first. |
| `qwen_video_pilot.py` | Historical independent 0–3 ratings at 2 fps. GPU required; opens the baseline JSONL in write mode. Do not rerun against the retained result without backing it up. |
| `qwen_context_test.py` | Historical 0/4-second context experiment at 2 fps. GPU entry point, resumable results; recreates missing clips before inference. |
| `xclip_video_pilot.py` | Original X-CLIP 19-event baseline, resumable; GPU required. Current film analysis and CPU summaries live in `code/xclip/`. |

## Restore historical context clips on CPU

Run the following from the repository root. It reads the retained raw timing records and uses the same extraction options as `qwen_context_test.py`; it does not load a model or change any JSONL. The exact cut boundaries were checked against the original manifest during cleanup.

```python
import json
import subprocess
from pathlib import Path

movie = Path("moviestimulus/partly_cloudy_sd_nocredits.mov")
for context in (0, 4):
    directory = Path(f"outputs/context_clips_{context}s_2fps")
    directory.mkdir(parents=True, exist_ok=True)
    source = Path(f"outputs/qwen_context_{context}s_2fps.jsonl")
    for line in source.read_text().splitlines():
        row = json.loads(line)
        clip = directory / row["clip"]
        if clip.exists():
            continue
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(movie), "-ss", str(row["movie_start_s"]),
            "-t", str(row["movie_end_s"] - row["movie_start_s"]),
            "-map", "0:v:0", "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "20", str(clip),
        ], check=True)
```

Video encoding bytes may vary with ffmpeg versions; the source movie, cut intervals, and encoder options are retained.
