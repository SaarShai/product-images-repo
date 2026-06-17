#!/usr/bin/env python3
"""STYLED geometry-locked generation: lineart ControlNet (locks the contour +
openings) + IP-Adapter (paints the real reference STYLE on), then an exact SVG
clear of openings + outside-contour.

This answers the open question: once you paint the *real* style on (vs the grey
geometry-locked baseline), does the contour/openings drift?

Pipeline
--------
1. Generate with StableDiffusionControlNetPipeline (the WORKING recipe:
   lineart CN `control_v11p_sd15_lineart` + base SD1.5, control map = the 480x1624
   lineart). Style is injected via IP-Adapter (load_ip_adapter + ip_adapter_image
   = watercolor crops). Output canvas == control-map size so the panel lands
   exactly on the SVG lines the metrics measure against.  -> raw.png  (pre-clear;
   measure THIS to see real style-induced drift).
2. Clear the EXACT SVG openings + outside-contour to white, replicating CN-exact:
   map SVG -> panel via svg_classify.extract_shapes+classify, mapping the outer
   contour bbox onto the auto-detected non-white panel bbox; openings+outside -> white.
   -> exact.png
3. (caller measures both with geom_iou.py + svg_geometry_check.py)

Fallback: if IP-Adapter fails to load on MPS, pass --no-ip and a watercolor-leaning
base (e.g. Lykon/dreamshaper-8) so style comes from the checkpoint+prompt instead.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def auto_bbox(arr: np.ndarray, white: int = 240) -> tuple[int, int, int, int]:
    nonwhite = np.any(arr < white, axis=2)
    ys, xs = np.where(nonwhite)
    if len(xs) == 0:
        h, w = arr.shape[:2]
        return (0, 0, w, h)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def clear_to_svg(img: Image.Image, svg: Path) -> Image.Image:
    """Replicate CN-exact clearing: set openings + outside-contour to white.

    Registers the SVG by the outer-contour bbox mapped onto the auto-detected
    non-white panel bbox (same registration geom_iou / svg_geometry_check use),
    so the cleared openings land on the exact SVG coordinates.
    """
    W, H = img.size
    arr = np.asarray(img.convert("RGB"))
    L, T, R, B = auto_bbox(arr)

    _, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)
    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    cx0 = min(s.bounds[0] for s in body)
    cy0 = min(s.bounds[1] for s in body)
    cx1 = max(s.bounds[2] for s in body)
    cy1 = max(s.bounds[3] for s in body)
    sx = (R - L) / (cx1 - cx0)
    sy = (B - T) / (cy1 - cy0)
    f = lambda x, y: (L + (x - cx0) * sx, T + (y - cy0) * sy)

    def fill(polys) -> np.ndarray:
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for p in polys:
            d.polygon([f(x, y) for x, y in p.exterior.coords], fill=255)
        return np.asarray(m) > 127

    contour_m = fill([s.polygon for s in body])
    holes_m = fill([s.polygon for s in cuts])
    keep_body = contour_m & ~holes_m  # only the painted panel body survives

    out = arr.copy()
    out[~keep_body] = 255  # openings + everything outside the contour -> white
    return Image.fromarray(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--control-map", required=True, type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path, help="STYLE1 dir; writes raw.png + exact.png")
    ap.add_argument("--prompt", default=(
        "watercolor painting of a space control panel, soft blue watercolor wash, "
        "painterly hand-painted edges, gouache, muted palette, knobs and switches, "
        "white background, illustration"))
    ap.add_argument("--negative-prompt", default=(
        "blurry, low quality, text, watermark, signature, frame, border, "
        "extra openings, deformed holes, photo, 3d render, photorealistic"))
    ap.add_argument("--base-model", default="stable-diffusion-v1-5/stable-diffusion-v1-5")
    ap.add_argument("--controlnet", default="lllyasviel/control_v11p_sd15_lineart")
    ap.add_argument("--style-refs", nargs="*", type=Path, default=[],
                    help="watercolor style crops passed as ip_adapter_image")
    ap.add_argument("--ip-scale", type=float, default=0.6, help="ip_adapter_scale (style strength)")
    ap.add_argument("--cond-scale", type=float, default=1.4, help="controlnet_conditioning_scale (geometry lock)")
    ap.add_argument("--guidance", type=float, default=7.0)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--device", default="auto", choices=["auto", "mps", "cpu", "cuda"])
    ap.add_argument("--no-ip", action="store_true", help="skip IP-Adapter (fallback: style from base+prompt)")
    a = ap.parse_args()

    from diffusers import (ControlNetModel, StableDiffusionControlNetPipeline,
                           UniPCMultistepScheduler)

    device = pick_device(a.device)
    dtype = torch.float32  # fp16 buggy on MPS
    outdir = a.outdir if a.outdir.is_absolute() else ROOT / a.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    cmap = Image.open(a.control_map if a.control_map.is_absolute() else ROOT / a.control_map).convert("RGB")
    W, H = cmap.size
    W -= W % 8
    H -= H % 8
    if (W, H) != cmap.size:
        cmap = cmap.resize((W, H), Image.LANCZOS)
    print(f"[style_gen] device={device} canvas={W}x{H} cond={a.cond_scale} ip_scale={a.ip_scale} no_ip={a.no_ip}")

    t0 = time.time()
    controlnet = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=dtype)
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        a.base_model, controlnet=controlnet, torch_dtype=dtype, safety_checker=None)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()

    ip_images = None
    used_ip = False
    if not a.no_ip and a.style_refs:
        try:
            pipe.load_ip_adapter("h94/IP-Adapter", subfolder="models", weight_name="ip-adapter_sd15.bin")
            pipe.set_ip_adapter_scale(a.ip_scale)
            ip_images = [Image.open(r if r.is_absolute() else ROOT / r).convert("RGB") for r in a.style_refs]
            used_ip = True
            print(f"[style_gen] IP-Adapter loaded; {len(ip_images)} style refs")
        except Exception as e:  # noqa: BLE001
            print(f"[style_gen] IP-Adapter load FAILED ({e!r}); falling back to base+prompt style")
            ip_images = None
            used_ip = False
    print(f"[style_gen] models loaded in {time.time()-t0:.1f}s (ip={used_ip})")

    gen = torch.Generator(device="cpu").manual_seed(a.seed)
    kwargs = dict(
        prompt=a.prompt,
        negative_prompt=a.negative_prompt,
        image=cmap,
        num_inference_steps=a.steps,
        guidance_scale=a.guidance,
        controlnet_conditioning_scale=a.cond_scale,
        width=W,
        height=H,
        generator=gen,
    )
    if ip_images is not None:
        # ONE IP-Adapter is loaded; its (possibly multiple) reference images must be
        # grouped as a single nested entry so diffusers maps N images -> 1 adapter
        # (a flat list of N is misread as N adapters -> ValueError).
        kwargs["ip_adapter_image"] = [ip_images]

    t1 = time.time()
    image = pipe(**kwargs).images[0]
    print(f"[style_gen] inference {time.time()-t1:.1f}s -> raw")

    raw_path = outdir / "raw.png"
    image.save(raw_path)
    print(f"[style_gen] saved {raw_path}")

    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    exact = clear_to_svg(image, svg)
    exact_path = outdir / "exact.png"
    exact.save(exact_path)
    print(f"[style_gen] saved {exact_path}  (openings+outside cleared to white)")
    print(f"[style_gen] used_ip={used_ip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
