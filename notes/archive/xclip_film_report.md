# X-CLIP across Partly Cloudy: wording check and movie timeline

19 annotated clips; 312 two-second windows, starting one second apart. Each window contains eight frames at 4 Hz.
The same pretrained X-CLIP checkpoint was used without fine-tuning.

The two balanced wordings were chosen after seeing that the original Control description dominated the pilot. This is an exploratory sensitivity check, not an independent validation set.

## Wording check on manually selected clips

| Description set | Human category ranks first | Control ranks first | Events whose top category changes vs original |
|:---|---:|---:|---:|
| original | 3/19 | 17/19 | 0/19 |
| balanced_a | 4/19 | 18/19 | 3/19 |
| balanced_b | 4/19 | 14/19 | 6/19 |

## Scores across movie time

![X-CLIP movie timeline](../../outputs/xclip_timeline.png)

Values in the plot are standardized separately for each description and wording set across the movie. Zero is that curve's own movie average; positive values are above its average. Do not compare these z-scores numerically with Qwen's 0--3 generated ratings.

| Human interval | Windows centered inside it | Original: inside - outside | Balanced A | Balanced B |
|:---|---:|---:|---:|---:|
| Mental | 44 | -0.33 | -0.32 | -0.35 |
| Pain | 26 | -0.46 | -0.43 | -0.48 |
| Social | 28 | -0.19 | -0.19 | -0.27 |
| Control | 24 | +0.63 | +0.86 | +0.80 |

**How to read the last table.** A positive value means the description's similarity is higher, on average, in windows centered within the manual intervals than at other movie times. These are descriptive differences, not statistical significance tests. The other movie times are not verified negatives, and sliding windows overlap. The manual labels may also overlap in meaning.

Full raw logits and z-scores: `outputs/xclip_timeline_scores.csv`.
