#!/usr/bin/env python3
"""Generic local inpaint: repaint ONLY the white area of a mask on a base image, leaving the rest
(esp. a locked exact element) untouched. Used to blend a composited fixed window/door into the wall
— paint a stone ring + vines right up to the locked door edge so it sits IN the building, no seam.

  inpaint_region.py --base BASE.png --mask MASK.png --out OUT.png --prompt "..." [--steps 32]

MASK: white (255) = repaint, black = keep. Runs Lykon/dreamshaper-8-inpainting on MPS/CPU.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import torch
from PIL import Image
from diffusers import StableDiffusionInpaintPipeline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--mask", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative-prompt", default="photo, realistic, harsh, text, watermark, frame, seam, cutout")
    ap.add_argument("--model", default="Lykon/dreamshaper-8-inpainting")
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    base = Image.open(a.base).convert("RGB")
    mask = Image.open(a.mask).convert("L")
    # SD wants multiples of 8; work at a capped width then resize back
    W0, H0 = base.size
    W = min(1024, W0 - W0 % 8); H = int(H0 * W / W0); H -= H % 8
    b = base.resize((W, H)); m = mask.resize((W, H))

    pipe = StableDiffusionInpaintPipeline.from_pretrained(a.model, torch_dtype=torch.float32,
                                                          safety_checker=None)
    pipe = pipe.to(device)
    g = torch.Generator(device="cpu").manual_seed(a.seed)
    print(f"[inpaint_region] {device} {W}x{H} steps={a.steps} strength={a.strength}", file=sys.stderr)
    out = pipe(prompt=a.prompt, negative_prompt=a.negative_prompt, image=b, mask_image=m,
               num_inference_steps=a.steps, guidance_scale=a.guidance, strength=a.strength,
               generator=g).images[0]
    out = out.resize((W0, H0))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=95)
    print(f"saved {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
