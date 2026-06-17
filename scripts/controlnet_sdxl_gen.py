#!/usr/bin/env python3
"""SDXL + ControlNet geometry-locked generation (richer style than SD1.5).

SDXL base + an SDXL ControlNet (canny/lineart) locks the contour+openings while
SDXL's stronger prior paints a far better watercolor body (and invents controls)
than SD1.5. Control image = the SVG lineart (inverted to white-on-black for the
canny-class ControlNet). Caller does the exact-opening clear + measurement.
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-map", required=True, type=Path, help="SVG lineart (black-on-white)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--controlnet", default="xinsir/controlnet-canny-sdxl-1.0")
    ap.add_argument("--base-model", default="stabilityai/stable-diffusion-xl-base-1.0")
    ap.add_argument("--prompt", default=("watercolor illustration of a space control panel, cobalt and navy "
                                         "blue washes, granulated paper texture, rounded knobs buttons sliders "
                                         "and toggles, recessed openings with painted bevelled rims, hand-painted "
                                         "ink outlines, soft lighting, white background"))
    ap.add_argument("--negative-prompt", default="photo, 3d render, text, watermark, frame, blurry, flat vector")
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--cond-scale", type=float, default=0.9)
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--invert", action="store_true", help="invert control map to white-on-black (for canny CN)")
    a = ap.parse_args()

    from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    cmap = Image.open(a.control_map if a.control_map.is_absolute() else ROOT / a.control_map).convert("RGB")
    if a.invert:
        cmap = ImageOps.invert(cmap)
    W, H = cmap.size; W -= W % 8; H -= H % 8
    cmap = cmap.resize((W, H), Image.LANCZOS)
    print(f"[sdxl] dev={dev} {W}x{H} cn={a.controlnet} cond={a.cond_scale}", flush=True)
    t0 = time.time()
    cn = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=torch.float32)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(a.base_model, controlnet=cn, torch_dtype=torch.float32)
    pipe.to(dev); pipe.enable_attention_slicing()
    print(f"[sdxl] loaded {time.time()-t0:.0f}s", flush=True)
    g = torch.Generator(device="cpu").manual_seed(a.seed)
    img = pipe(prompt=a.prompt, negative_prompt=a.negative_prompt, image=cmap, num_inference_steps=a.steps,
               guidance_scale=a.guidance, controlnet_conditioning_scale=a.cond_scale, width=W, height=H,
               generator=g).images[0]
    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
    print(f"[sdxl] saved {out} ({time.time()-t0:.0f}s total)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
