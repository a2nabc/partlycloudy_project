# X-CLIP pilot: 19 manually annotated Partly Cloudy events

Model: `microsoft/xclip-base-patch32`; eight evenly spaced video frames per clip.
Four fixed candidate text descriptions were used for every clip; see the JSONL for their exact wording.
Values are video--text similarity logits, **not probabilities or independent category ratings**.
Bold marks the human-annotated category. `Top` is the model's highest of the four.
`Margin` = human-category score minus the highest alternative (positive means human category ranked first).

| Event | Movie time (s) | Human | Mental | Pain | Social | Control | Top | Margin |
|---:|:---|:---|---:|---:|---:|---:|:---|---:|
| 1 | 14–20 | Control | 16.65 | 17.95 | 19.02 | **21.42** | Control | +2.40 |
| 2 | 38–48 | Control | 20.41 | 20.79 | 21.77 | **25.81** | Control | +4.04 |
| 3 | 52–58 | Social | 15.07 | 14.63 | **15.71** | 17.32 | Control | -1.60 |
| 4 | 60–68 | Control | 10.65 | 10.61 | 10.57 | **10.52** | Mental | -0.13 |
| 5 | 76–86 | Social | 5.68 | 6.17 | **6.28** | 5.89 | Social | +0.11 |
| 6 | 86–88 | Social | 13.34 | 13.53 | **14.03** | 18.11 | Control | -4.08 |
| 7 | 100–106 | Social | 10.56 | 10.97 | **11.10** | 13.76 | Control | -2.66 |
| 8 | 112–114 | Pain | 11.21 | **12.44** | 12.01 | 16.51 | Control | -4.07 |
| 9 | 114–118 | Social | 5.87 | 8.16 | **7.57** | 13.13 | Control | -5.56 |
| 10 | 124–130 | Pain | 11.78 | **12.86** | 13.49 | 18.88 | Control | -6.02 |
| 11 | 146–150 | Pain | 4.18 | **6.76** | 6.38 | 12.44 | Control | -5.68 |
| 12 | 172–180 | Mental | **6.89** | 7.58 | 7.35 | 12.66 | Control | -5.77 |
| 13 | 182–184 | Pain | 11.79 | **12.50** | 13.29 | 16.36 | Control | -3.86 |
| 14 | 196–202 | Pain | 8.90 | **10.32** | 11.19 | 16.02 | Control | -5.69 |
| 15 | 214–218 | Pain | 7.03 | **6.16** | 6.80 | 7.36 | Control | -1.19 |
| 16 | 240–248 | Mental | **11.32** | 12.45 | 12.69 | 15.63 | Control | -4.31 |
| 17 | 260–270 | Mental | **8.68** | 10.87 | 9.79 | 14.87 | Control | -6.19 |
| 18 | 276–294 | Mental | **7.28** | 8.16 | 8.61 | 13.79 | Control | -6.51 |
| 19 | 302–304 | Pain | 2.36 | **4.22** | 5.24 | 7.57 | Control | -3.35 |

## Brief reading

- Human category ranked first for 3/19 clips.
- Highest model score by category: Mental 1, Pain 0, Social 1, Control 17.
- A first-place rank is relative to these four particular text descriptions. A small margin is a near tie, not strong evidence of a match.
- The 19 manually selected intervals are a small, non-exhaustive sample; unannotated moments are not automatically Control.
