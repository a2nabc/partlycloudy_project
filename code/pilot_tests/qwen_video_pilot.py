#!/usr/bin/env python3
"""Zero-shot pilot: one human-annotated clip from each of four conditions.

Requires a GPU and a Transformers release with native Qwen2.5-VL video input.
Run from the project repository: python code/qwen_video_pilot.py
"""

import csv
import json
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration


ROOT = Path(__file__).resolve().parents[1]
CLIP_DIR = ROOT / "outputs" / "clips_offset_minus10s"
MANIFEST = CLIP_DIR / "manifest.csv"
OUTPUT = ROOT / "outputs" / "qwen2_5_vl_3b_pilot.jsonl"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
FPS = 2

PROMPT = """Examine this short silent animated clip. Based on its visible events,
describe what happens in one sentence. Then rate EACH feature independently
from 0 (absent) to 3 (strongly present). Do not assume one feature must win.

Mental: The scene leads the viewer to infer a character's thoughts, beliefs,
intentions, or feelings.
Pain: A character experiences a physically painful event.
Social: Characters interact without a strong focus on inferred mental states.
Control: Scenery or other physical events, with no specific character-related
event as the focus.

Return JSON only, with keys description, mental, pain, social, control.
The four scores must be integers from 0 to 3. It is okay for all four to be 0.
"""


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("Run on a Triton GPU compute node: CUDA is unavailable.")

    with MANIFEST.open(newline="") as source:
        rows = list(csv.DictReader(source))
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,  # V100 supports FP16; not BF16.
        device_map={"": 0},
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    ).eval()
    processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=360 * 420)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as target:
        for row in rows:
            condition = row["condition"]
            clip = CLIP_DIR / row["filename"]
            if not clip.is_file():
                raise FileNotFoundError(clip)

            # The model sees the pixels and the definitions, not the human label.
            messages = [{
                "role": "user",
                "content": [
                    {"type": "video", "path": str(clip)},
                    {"type": "text", "text": PROMPT},
                ],
            }]
            inputs = processor.apply_chat_template(
                messages,
                fps=FPS,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to("cuda")
            with torch.inference_mode():
                generated = model.generate(
                    **inputs, max_new_tokens=220, do_sample=False
                )
            reply_tokens = generated[0, inputs["input_ids"].shape[-1]:]
            reply = processor.decode(reply_tokens, skip_special_tokens=True).strip()
            result = {
                "event_id": row["event_id"],
                "human_condition": condition,
                "clip": clip.name,
                "model": MODEL_ID,
                "fps": FPS,
                "raw_response": reply,
            }
            target.write(json.dumps(result) + "\n")
            target.flush()
            print(f"{condition} ({clip.name}): {reply}\n", flush=True)

    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
