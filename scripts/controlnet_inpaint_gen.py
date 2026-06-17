#!/usr/bin/env python3
"""GEOMETRY-EXACT generation: ControlNet (locks the outer contour) + inpaint mask
(pins every opening to its exact SVG coordinates by construction).

The openings are NOT generated — they are masked-out (kept = white) from the SVG
geometry, so they land at literally the SVG coordinates (region-IoU -> ~1.0). The
model only paints the panel BODY, bounded by the contour via the lineart ControlNet.
This is the research-recommended exact-geometry route the pure models can't do.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import torch
from diffusers import StableDiffusionControlNetInpaintPipeline, ControlNetModel
sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--control-map", required=True, type=Path, help="lineart map (contour+openings), sets W/H")
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--base-model", default="stable-diffusion-v1-5/stable-diffusion-v1-5")
    ap.add_argument("--controlnet", default="lllyasviel/control_v11p_sd15_lineart")
    ap.add_argument("--prompt", default="space control panel, simple flat shapes on white background")
    ap.add_argument("--negative-prompt", default="text, watermark, frame, border, clutter")
    ap.add_argument("--steps", type=int, default=24)
    ap.add_argument("--cond-scale", type=float, default=1.2)
    ap.add_argument("--guidance", type=float, default=7.0)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    cmap = Image.open(a.control_map if a.control_map.is_absolute() else ROOT / a.control_map).convert("RGB")
    W, H = cmap.size
    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    vb, shapes = C.extract_shapes(svg); shapes = C.classify(shapes)
    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
    cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
    f = lambda x, y: ((x - cx0) * W / (cx1 - cx0), (y - cy0) * H / (cy1 - cy0))

    def fill(roles):
        m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
        for s in shapes:
            if s.polygon is not None and s.role in roles:
                d.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
        return np.asarray(m) > 127

    body_m = fill(("outer_contour", "paintable_region"))
    hole_m = fill(("internal_cutout",))
    paint = body_m & ~hole_m                      # inpaint region = body minus openings
    mask = Image.fromarray((paint * 255).astype(np.uint8))   # white = generate, black = keep
    init = Image.new("RGB", (W, H), (255, 255, 255))         # kept areas (openings+outside) stay white

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    cn = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=torch.float32)
    pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(a.base_model, controlnet=cn, torch_dtype=torch.float32, safety_checker=None)
    pipe.to(device)
    g = torch.Generator(device="cpu").manual_seed(a.seed)
    print(f"[inpaint] {device} {W}x{H} cond={a.cond_scale}")
    img = pipe(prompt=a.prompt, negative_prompt=a.negative_prompt, image=init, mask_image=mask,
               control_image=cmap, num_inference_steps=a.steps, guidance_scale=a.guidance,
               controlnet_conditioning_scale=a.cond_scale, generator=g).images[0]
    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
