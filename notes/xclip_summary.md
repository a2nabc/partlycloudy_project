# Current X-CLIP summary

X-CLIP results are exploratory video–text similarity logits, not probabilities or independent category ratings. The alternative wordings were chosen after seeing the initial Control bias, so these runs are sensitivity checks rather than independent validation.

All ten historical raw inference JSONLs (Qwen and X-CLIP) remain under `outputs/`; the experiment table in [README](../README.md) gives their paths and record counts. The original timeline used **2-second windows and 8 frames**, not 2 frames. The later timelines used 6 seconds/16 frames and 8 seconds/8 frames.

Historical reports are preserved:

- [19-event baseline](archive/xclip_19_events_report.md) and [LaTeX table](archive/xclip_19_events_table.tex)
- [Original 2-second timeline](archive/xclip_film_report.md)
- [6-second, 16-frame timeline](archive/xclip_film_report_6s_16f.md)
- [8-second, 8-frame timeline](archive/xclip_film_report_8s_8f.md)

Current work uses the [evidence-first Qwen protocol](../code/annotation/README.md), with blind human review before interpreting anchor-label agreement. Cleanup did not change category definitions or run inference.
