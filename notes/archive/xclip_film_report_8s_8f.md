# X-CLIP across Partly Cloudy: 8-second windows, 8 frames

19 annotated clips; 306 8-second windows starting 1 second(s) apart. Each window contains 8 frames spread across its duration from a 4-Hz grid.
Pretrained checkpoint: `microsoft/xclip-base-patch32`; no fine-tuning.

The two balanced wordings were chosen after seeing that the original Control description dominated the pilot. This is an exploratory sensitivity check, not an independent validation set.

## Wording check on manually selected clips

| Description set | Human category ranks first | Control ranks first | Events whose top category changes vs original |
|:---|---:|---:|---:|
| original | 3/19 | 17/19 | 0/19 |
| balanced_a | 4/19 | 18/19 | 3/19 |
| balanced_b | 4/19 | 14/19 | 6/19 |

## Scores across movie time

Plot omitted during cleanup; regenerate with `python code/xclip/plot_xclip_film.py --window-seconds 8 --frames 8`.

Values in the plot are standardized separately for each description and wording set across the movie. Zero is that curve's own movie average; positive values are above its average. Do not compare these z-scores numerically with Qwen's 0--3 generated ratings.

| Human interval | Windows centered inside it | Original: inside - outside | Balanced A | Balanced B |
|:---|---:|---:|---:|---:|
| Mental | 44 | -0.48 | -0.45 | -0.49 |
| Pain | 26 | -0.51 | -0.46 | -0.43 |
| Social | 28 | -0.34 | -0.33 | -0.39 |
| Control | 24 | +0.71 | +0.99 | +0.88 |

**How to read the last table.** A positive value means the description's similarity is higher, on average, in windows centered within the manual intervals than at other movie times. These are descriptive differences, not statistical significance tests. The other movie times are not verified negatives, and sliding windows overlap. A long window centered within an annotation may include movie content outside that interval. The manual labels may also overlap in meaning.

Full raw logits and z-scores: `outputs/xclip_timeline_scores_8s_8f.csv`.
