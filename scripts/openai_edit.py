#!/usr/bin/env python3
"""openai_edit.py — TRUE masked inpaint via the OpenAI images/edits endpoint (gpt-image-1).

Unlike the no-key subgen path, this regenerates ONLY the masked (transparent) region and
preserves the rest — native "change nothing else". Reads OPENAI_API_KEY from .secrets/openai.env
or the env. Builds the alpha mask internally from --mask-box (transparent = edit area).

Usage:
  python3 scripts/openai_edit.py --image CROP.png --out OUT.png --prompt-file P.md \
      --mask-box x0,y0,x1,y1 [--feather 24] [--size 1024x1024] [--fidelity high] [--quality high]

The mask-box is in the SENT image's pixel space (after --size resize). OUT is the edited crop
at --size; resize it back to the original crop dims and composite with compose_fairy.py.
"""
import argparse
import base64
import io
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_openai_key as load_key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--mask-box", required=True, help="x0,y0,x1,y1 transparent(edit) region in SENT-image coords")
    ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--fidelity", default="high", choices=["high", "low"])
    ap.add_argument("--quality", default="high", choices=["high", "medium", "low", "auto"])
    ap.add_argument("--model", default="gpt-image-1")
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else None)
    if not prompt:
        raise SystemExit("need --prompt or --prompt-file")

    W, H = (int(x) for x in a.size.split("x"))
    img = Image.open(a.image).convert("RGB").resize((W, H), Image.LANCZOS)

    # alpha mask: transparent (0) where to EDIT, opaque (255) where to PRESERVE
    x0, y0, x1, y1 = (int(v) for v in a.mask_box.split(","))
    edit = Image.new("L", (W, H), 0)
    ImageDraw.Draw(edit).rectangle([x0, y0, x1, y1], fill=255)  # 255 inside = edit
    if a.feather > 0:
        edit = edit.filter(ImageFilter.GaussianBlur(a.feather))
    alpha = Image.eval(edit, lambda v: 255 - v)  # invert: inside->0 (transparent=edit)
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)

    img_buf = io.BytesIO(); img.save(img_buf, format="PNG"); img_buf.seek(0)
    mask_buf = io.BytesIO(); rgba.save(mask_buf, format="PNG"); mask_buf.seek(0)

    key = load_key()
    files = {
        "image": ("image.png", img_buf, "image/png"),
        "mask": ("mask.png", mask_buf, "image/png"),
    }
    data = {
        "model": a.model, "prompt": prompt, "n": "1", "size": a.size,
        "input_fidelity": a.fidelity, "quality": a.quality,
    }
    r = requests.post("https://api.openai.com/v1/images/edits",
                      headers={"Authorization": f"Bearer {key}"},
                      files=files, data=data, timeout=300)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:800]}", file=sys.stderr)
        raise SystemExit(1)
    j = r.json()
    b64 = j["data"][0]["b64_json"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(base64.b64decode(b64))
    usage = j.get("usage", {})
    print(f"[openai_edit] OK -> {a.out}  size={a.size} fidelity={a.fidelity} quality={a.quality} usage={usage}")


if __name__ == "__main__":
    main()
