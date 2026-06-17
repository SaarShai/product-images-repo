#!/usr/bin/env python3
"""Route A — aperture/rim-split inpaint: EXACT openings by construction + a
model-PAINTED bevel rim.

The combination nothing else achieves: model-painted openings always drift
(the model invents the hole), and code-placement (clear_to_svg) is exact but
FLAT (no bevel). This splits the difference:

  - aperture_mask  = the EXACT SVG cutout interiors -> KEPT white by construction
                     (inpaint never touches them => the opening EDGE is exact).
  - rim_annulus    = dilate each aperture by D px, minus the aperture -> GENERATE
                     (the model paints the bevel/rim right up to the kept edge).
  - body           = inside the outer contour, minus apertures -> GENERATE.

So the inpaint mask (white = generate) = body u rim_annulus; aperture interiors
stay black (= kept from the white init image). The model paints a bevel that
butts exactly against the kept-white aperture, giving exact-aperture + painted-rim.

Registration: masks are built in the SAME SVG->canvas mapping that
scripts/svg_classify.render_map uses to draw the lineart control map (viewBox
mapped by scale = max_w / box_w). The generated panel therefore fills the same
pixels the control map drew, so the downstream contour-bbox -> auto-nonwhite-bbox
registration used by geom_iou.py / svg_geometry_check.py lands on the exact
openings.

Pipeline: StableDiffusionControlNetInpaintPipeline with a REAL inpainting
checkpoint (vanilla SD1.5 gives rainbow garbage) + lineart ControlNet for the
contour. torch MPS, fp32.

This is a NEW file. It deliberately reuses scripts/svg_classify.py (extract +
classify) and does NOT edit geom_adherence_test.py / controlnet_style_gen.py /
results_db.py or anything other routes depend on.

Usage:
  rimsplit_inpaint_gen.py --control-map <png> --svg <svg> --outdir <dir> \
      --rim-dilate 14 --seed 12345 [--style-refs a.png b.png] [--steps 28]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROMPT = (
    "cobalt and indigo granulated watercolor space control panel, "
    "recessed openings with hand-painted bevelled rims, "
    "dark navy inner shadow on the upper-left of each rim, "
    "pale lit lip on the lower-right, clean empty pale aperture centers, "
    "soft hardware in open areas, white background"
)
DEFAULT_NEGATIVE = (
    "blurry, low quality, text, watermark, signature, frame, border, "
    "extra openings, deformed holes, filled openings, photo, 3d render, photorealistic"
)


def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def render_map_mapper(viewbox, canvas_w: int, canvas_h: int):
    """Replicate svg_classify.render_map's SVG->canvas mapping exactly, so the
    masks we build align pixel-for-pixel with the lineart control map."""
    min_x, min_y, box_w, box_h = viewbox
    scale = canvas_w / box_w
    # render_map computes H = round(box_h * scale); sy == sx == scale.
    def f(x, y):
        return ((x - min_x) * scale, (y - min_y) * scale)
    return f


def polys_to_mask(polys, f, size) -> np.ndarray:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([f(x, y) for x, y in p.exterior.coords], fill=255)
    return np.asarray(m) > 127


def build_masks(svg: Path, canvas_w: int, canvas_h: int, rim_dilate: int):
    """Return (aperture_bool, rim_bool, body_bool) at canvas resolution.

    aperture = exact cutout interiors (KEEP white).
    rim      = dilate(aperture, rim_dilate) - aperture (GENERATE the bevel).
    body     = inside outer contour, minus apertures (GENERATE).
    """
    viewbox, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)
    body_shapes = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cut_shapes = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    if not body_shapes:
        raise SystemExit("no outer contour found in SVG")
    f = render_map_mapper(viewbox, canvas_w, canvas_h)
    size = (canvas_w, canvas_h)

    contour = polys_to_mask([s.polygon for s in body_shapes], f, size)
    aperture = polys_to_mask([s.polygon for s in cut_shapes], f, size)

    # dilate apertures by rim_dilate px (square structuring element ~ disk)
    if rim_dilate > 0 and aperture.any():
        struct = ndimage.generate_binary_structure(2, 1)
        dil = ndimage.binary_dilation(aperture, structure=struct, iterations=rim_dilate)
    else:
        dil = aperture.copy()
    rim = dil & ~aperture
    # rim must stay inside the body (don't paint a rim outside the contour)
    rim = rim & contour

    body = contour & ~aperture & ~rim
    return aperture, rim, body, len(cut_shapes)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--control-map", required=True, type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path, help="writes raw.png + mask_debug.png + init.png")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    ap.add_argument("--base-model", default="Lykon/dreamshaper-8-inpainting",
                    help="REAL inpainting checkpoint; fallbacks tried if unavailable")
    ap.add_argument("--controlnet", default="lllyasviel/control_v11p_sd15_lineart")
    ap.add_argument("--style-refs", nargs="*", type=Path, default=[],
                    help="watercolor style crops passed as ip_adapter_image")
    ap.add_argument("--ip-scale", type=float, default=0.55)
    ap.add_argument("--no-ip", action="store_true")
    ap.add_argument("--rim-dilate", type=int, default=14, help="rim annulus width in px")
    ap.add_argument("--cond-scale", type=float, default=1.1, help="controlnet_conditioning_scale (geometry lock)")
    ap.add_argument("--guidance", type=float, default=7.0)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--strength", type=float, default=1.0, help="inpaint strength on the generate region")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--device", default="auto", choices=["auto", "mps", "cpu", "cuda"])
    ap.add_argument("--downscale", type=float, default=1.0,
                    help="<1.0 shrinks the canvas for speed (e.g. 0.66); masks scale with it")
    a = ap.parse_args()

    from diffusers import (ControlNetModel, StableDiffusionControlNetInpaintPipeline,
                           UniPCMultistepScheduler)

    device = pick_device(a.device)
    dtype = torch.float32  # fp16 buggy on MPS
    outdir = a.outdir if a.outdir.is_absolute() else ROOT / a.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    cmap = Image.open(a.control_map if a.control_map.is_absolute() else ROOT / a.control_map).convert("RGB")
    W, H = cmap.size
    if a.downscale != 1.0:
        W = int(W * a.downscale)
        H = int(H * a.downscale)
        cmap = cmap.resize((W, H), Image.LANCZOS)
    W -= W % 8
    H -= H % 8
    if (W, H) != cmap.size:
        cmap = cmap.resize((W, H), Image.LANCZOS)

    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    aperture, rim, body, n_cut = build_masks(svg, W, H, max(1, round(a.rim_dilate * a.downscale)))
    generate = body | rim          # white = generate
    keep = ~generate               # black = keep (apertures + outside-contour)

    # init image: white everywhere. Aperture interiors are kept => stay exact white.
    init = Image.new("RGB", (W, H), (255, 255, 255))
    mask_img = Image.fromarray((generate.astype(np.uint8) * 255), mode="L")

    # debug viz: aperture=red(kept), rim=green(painted), body=blue(painted)
    dbg = np.full((H, W, 3), 255, np.uint8)
    dbg[body] = (120, 140, 200)
    dbg[rim] = (40, 200, 90)
    dbg[aperture] = (230, 60, 60)
    Image.fromarray(dbg).save(outdir / "mask_debug.png")
    mask_img.save(outdir / "inpaint_mask.png")
    init.save(outdir / "init.png")
    print(f"[rimsplit] canvas={W}x{H} cutouts={n_cut} rim_dilate={a.rim_dilate} "
          f"aperture_px={int(aperture.sum())} rim_px={int(rim.sum())} body_px={int(body.sum())}")

    # ---- load pipeline (real inpainting checkpoint + lineart CN) ----
    t0 = time.time()
    controlnet = ControlNetModel.from_pretrained(a.controlnet, torch_dtype=dtype)
    base_candidates = [a.base_model, "stabilityai/stable-diffusion-2-inpainting",
                       "runwayml/stable-diffusion-inpainting"]
    seen = set()
    base_candidates = [b for b in base_candidates if not (b in seen or seen.add(b))]
    pipe = None
    used_base = None
    last_err = None
    for base in base_candidates:
        try:
            pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
                base, controlnet=controlnet, torch_dtype=dtype, safety_checker=None)
            used_base = base
            break
        except Exception as e:  # noqa: BLE001
            print(f"[rimsplit] base {base} unavailable: {repr(e)[:160]}")
            last_err = e
    if pipe is None:
        raise SystemExit(f"no inpainting checkpoint loadable: {last_err!r}")
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
            print(f"[rimsplit] IP-Adapter loaded; {len(ip_images)} style refs")
        except Exception as e:  # noqa: BLE001
            print(f"[rimsplit] IP-Adapter load FAILED ({repr(e)[:120]}); style from base+prompt")
            ip_images = None
    print(f"[rimsplit] base={used_base} models loaded in {time.time()-t0:.1f}s (ip={used_ip})")

    gen = torch.Generator(device="cpu").manual_seed(a.seed)
    kwargs = dict(
        prompt=a.prompt,
        negative_prompt=a.negative_prompt,
        image=init,
        mask_image=mask_img,
        control_image=cmap,
        num_inference_steps=a.steps,
        guidance_scale=a.guidance,
        controlnet_conditioning_scale=a.cond_scale,
        strength=a.strength,
        width=W,
        height=H,
        generator=gen,
    )
    if ip_images is not None:
        kwargs["ip_adapter_image"] = [ip_images]

    t1 = time.time()
    image = pipe(**kwargs).images[0]
    print(f"[rimsplit] inference {time.time()-t1:.1f}s")

    # Enforce exact apertures post-hoc too (belt-and-braces): the pipeline KEEPS
    # masked-out pixels, but VAE round-trips can bleed a few px at the boundary.
    # Re-stamp the kept regions (apertures + outside-contour) to white so the
    # aperture edge is provably exact. The rim+body the model painted stays.
    arr = np.asarray(image.convert("RGB")).copy()
    arr[keep] = 255
    out = Image.fromarray(arr)

    raw_path = outdir / "raw.png"
    out.save(raw_path)
    print(f"[rimsplit] saved {raw_path} (apertures re-stamped exact white; rim+body kept)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
