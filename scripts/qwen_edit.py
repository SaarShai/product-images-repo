#!/usr/bin/env python3
"""qwen_edit.py — text-aware image edit via fal.ai Qwen-Image-Edit.

The TEXT specialist: Qwen-Image-Edit is SOTA at rendering/replacing specific
glyphs inside an image (e.g. change the word "TAXI" on a car door to "CAB",
preserving the lettering style) — the case where Flux Kontext / Flux Fill /
nano / OpenAI tend to mangle or hallucinate the text. Use it when the edit is
about the *words in the picture*, not the picture's content.

Reads FAL_KEY from .secrets/fal.env (same as falgen.py). Auth scheme is
`Key <id:secret>` (NOT Bearer). The local image (and optional mask) are sent
as base64 PNG data URIs. The result URL is downloaded to --out.

Endpoints (verified against fal OpenAPI 2026-06):
  edit (default)  : fal-ai/qwen-image-edit          — instruction edit, whole image.
  inpaint (--mask): fal-ai/qwen-image-edit/inpaint  — masked edit (mask white=repaint).

Input schema (both): prompt (req), image_url (req), [inpaint: mask_url (req)],
  output_format(png), num_images(1), seed, guidance_scale(0-20, default 4),
  num_inference_steps(2-50, default 30), negative_prompt, acceleration.
Output: {images:[{url,width,height,content_type}], seed, ...}.

Usage:
  # whole-image instruction edit (text replace):
  python3 scripts/qwen_edit.py --image CAR.png --out OUT.png \
      --prompt 'replace the word "TAXI" on the car door with "CAB", same lettering style'

  # masked inpaint (constrain the edit to a region; mask white = repaint):
  python3 scripts/qwen_edit.py --image CAR.png --out OUT.png --mask MASK.png \
      --prompt 'the door reads "CAB" in the same yellow block lettering'
"""
import argparse
import base64
import io
import os
import sys
from pathlib import Path

import requests
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_fal_key as load_key, data_uri

ENDPOINTS = {
    "edit": "fal-ai/qwen-image-edit",
    "inpaint": "fal-ai/qwen-image-edit/inpaint",
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--image", required=True, help="path to image to edit")
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--prompt", help="edit instruction")
    ap.add_argument("--prompt-file", help="read the prompt from this file")
    ap.add_argument("--mask", help="mask PNG (white=repaint); switches to the inpaint endpoint")
    ap.add_argument("--maxside", type=int, default=1536,
                    help="resize longer side to this before sending (default 1536)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--guidance", type=float, default=None, help="guidance_scale (0-20, default 4)")
    ap.add_argument("--steps", type=int, default=None, help="num_inference_steps (2-50, default 30)")
    ap.add_argument("--negative", default=None, help="negative_prompt")
    ap.add_argument("--acceleration", default="regular", choices=["none", "regular", "high"])
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    if not prompt.strip():
        raise SystemExit("a --prompt (or --prompt-file) is required")

    img = Image.open(a.image).convert("RGB")
    if a.maxside:
        w, h = img.size
        s = a.maxside / max(w, h)
        if s < 1:
            img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    W, H = img.size

    mode = "inpaint" if a.mask else "edit"
    body = {
        "prompt": prompt,
        "image_url": data_uri(img),
        "output_format": "png",
        "num_images": 1,
        "acceleration": a.acceleration,
    }
    if a.seed is not None:
        body["seed"] = a.seed
    if a.guidance is not None:
        body["guidance_scale"] = a.guidance
    if a.steps is not None:
        body["num_inference_steps"] = a.steps
    if a.negative is not None:
        body["negative_prompt"] = a.negative

    if mode == "inpaint":
        m = Image.open(a.mask).convert("L").resize((W, H))
        body["mask_url"] = data_uri(m.convert("RGB"))

    key = load_key()
    url = f"https://fal.run/{ENDPOINTS[mode]}"
    r = requests.post(
        url,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        json=body,
        timeout=300,
    )
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:600]}", file=sys.stderr)
        raise SystemExit(1)
    j = r.json()
    imgs = j.get("images") or ([j["image"]] if j.get("image") else [])
    if not imgs:
        print(f"no images in response: {str(j)[:400]}", file=sys.stderr)
        raise SystemExit(1)
    out_url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    data = requests.get(out_url, timeout=120).content
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(data)
    print(f"[qwen_edit] OK mode={mode} -> {a.out}  sent={W}x{H} seed={j.get('seed')}")


if __name__ == "__main__":
    main()
