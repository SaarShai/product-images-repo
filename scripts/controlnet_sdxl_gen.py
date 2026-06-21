#!/usr/bin/env python3
"""GEOMETRY-EXACT generation, SDXL edition: SDXL-inpaint + xinsir canny SDXL
ControlNet, fed the authoritative SVG geometry as the control image and an
opening/hole mask that is NEVER generated (kept = white) by construction.

Upgrade of scripts/controlnet_inpaint_gen.py (SD1.5 -> SDXL). Identical exact-
geometry contract:
  * control image  = SVG canny map (outer contour + every cutout, white-on-black)
  * inpaint mask   = body(outer_contour + paintable_region) MINUS holes
  * init image     = white  -> kept regions (holes + outside) stay white
The openings land at the literal SVG coordinates (region-IoU -> ~1.0) because they
are masked out, not generated. The model only paints the panel BODY, bounded by
the contour via the canny ControlNet.

Reuses, does NOT duplicate: scripts/svg_classify.py for the parser, and the SAME
body/hole-mask construction as controlnet_inpaint_gen.py. Geometry must be MEASURED
afterwards with scripts/svg_geometry_check.py — this script only sets it up.

Models (apache-2.0, must be in the HF cache or will download):
  base       : diffusers/stable-diffusion-xl-1.0-inpainting-0.1
  controlnet : xinsir/controlnet-canny-sdxl-1.0

Prompt-template style: NO geometry/production strokes in the prompt. Geometry comes
ONLY from the control image + mask. Keep the prompt about content+style.

Usage (control map can be precomputed OR rendered from the SVG here):
  controlnet_sdxl_gen.py --svg SVG --out OUT.png \
      [--control-map MAP.png | --width 1024] [--prompt "..."] \
      [--bbox L,T,R,B] [--steps 30] [--cond-scale 0.8] [--guidance 6.0] \
      [--strength 1.0] [--seed 7] [--smoke] [--save-debug]

If --bbox is given (SVG user units L,T,R,B) only that sub-region of the viewBox is
mapped, isolating a SINGLE panel of a multi-panel template. The control map AND
masks are rendered for exactly that crop, so svg_geometry_check.py (run with the
SAME --bbox in candidate px = whole output image) measures what was generated.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch
from diffusers import StableDiffusionXLControlNetInpaintPipeline, ControlNetModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402  (reuse the authoritative parser)

ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
CN_MODEL = "xinsir/controlnet-canny-sdxl-1.0"


def round8(v) -> int:
    v = int(round(v))
    return max(8, v - (v % 8))


# A cutout whose height spans more than this fraction of the panel is a STRUCTURAL
# saloon-flap / splay piece, NOT an enclosed opening. On a full-bleed facade panel
# (the door) it must be PAINTED, not carved out — carving it leaves white trapezoid
# corners (the taper bug). Mirrors skyline_panel.cmd_guide's hfrac>0.45 skip so the
# gen mask and the gen guide agree on which holes are "real". See repo memory
# "guide-no-flap-outlines-trapezoid".
FLAP_HFRAC = 0.45


def render_control_and_masks(svg_path, src_rect, W, H, stroke, crop_filter=False,
                             full_bleed=False, flap_hfrac=FLAP_HFRAC):
    """Render the canny control image (white lines on black) + inpaint mask
    (white = generate body-minus-holes, black = keep) + hole mask, all mapped from
    src_rect (min_x,min_y,box_w,box_h in SVG units) onto the WxH output.

    Mirrors svg_to_controlmap.mapper and controlnet_inpaint_gen.fill exactly so the
    same geometry is enforced as the SD1.5 route.

    crop_filter: when isolating ONE panel via --bbox, keep only shapes whose
    centroid falls inside src_rect, so side-panel cutouts of a multi-panel template
    are not mapped into this crop (they would wrongly punch holes in the body /
    invite paint outside it). measure_sdxl_cn.py applies the identical filter so
    generation and measurement see the same geometry.

    full_bleed: door-style FACADE panel — the artwork must fill the rectangular
    contour edge-to-edge. The large saloon-flap / splay cutouts (height fraction of
    the panel > flap_hfrac) are NOT subtracted from the paint mask (so the bottom
    corners get facade, not white) and are drawn only as FAINT central hints in the
    control map (so the model doesn't trace them as the silhouette → trapezoid).
    Genuinely enclosed small openings (knobs, vents) are still carved + bold so they
    stay clean. Returns the same tuple; `drawn` gains a "flaps_skipped" count.
    """
    min_x, min_y, box_w, box_h = src_rect
    sx = W / box_w
    sy = H / box_h
    panel_h = box_h  # SVG-unit panel height, for the flap height-fraction test

    def f(x, y):
        return ((x - min_x) * sx, (y - min_y) * sy)

    _, shapes = C.extract_shapes(svg_path)
    shapes = C.classify(shapes)

    def in_crop(s):
        x0, y0, x1, y1 = s.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return (min_x <= cx <= min_x + box_w) and (min_y <= cy <= min_y + box_h)

    sel = [s for s in shapes if s.polygon is not None and (in_crop(s) if crop_filter else True)]

    def is_flap(s):
        """Large structural flap/splay cutout (tall enough to read as the silhouette)."""
        x0, y0, x1, y1 = s.bounds
        return s.role == "internal_cutout" and (y1 - y0) / panel_h > flap_hfrac

    # control image: canny style (black bg, white lines) — like svg_to_controlmap --style canny
    ctrl = Image.new("L", (W, H), 0)
    dc = ImageDraw.Draw(ctrl)
    drawn = {"outer_contour": 0, "paintable_region": 0, "internal_cutout": 0, "flaps_skipped": 0}
    faint = max(1, stroke // 3)
    for s in sel:
        if s.role not in ("outer_contour", "paintable_region", "internal_cutout"):
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        if full_bleed and is_flap(s):
            # FAINT hint only (interior detail), never a bold silhouette edge.
            dc.line(pts + [pts[0]], fill=90, width=faint, joint="curve")
            drawn["flaps_skipped"] += 1
            continue
        dc.line(pts + [pts[0]], fill=255, width=stroke, joint="curve")
        drawn[s.role] += 1

    # masks: SAME construction as controlnet_inpaint_gen.fill
    def fill(roles, predicate=None):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for s in sel:
            if s.role in roles and (predicate is None or predicate(s)):
                d.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
        return np.asarray(m) > 127

    body_m = fill(("outer_contour", "paintable_region"))
    if full_bleed:
        # carve ONLY the genuinely-enclosed small openings; keep flaps painted.
        hole_m = fill(("internal_cutout",), predicate=lambda s: not is_flap(s))
    else:
        hole_m = fill(("internal_cutout",))
    paint = body_m & ~hole_m  # inpaint region = body minus (real) openings
    return ctrl.convert("RGB"), paint, hole_m, drawn


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--control-map", type=Path, help="precomputed canny map (white-on-black); sets W/H. If omitted, rendered from SVG.")
    ap.add_argument("--width", type=int, default=1024, help="output width when rendering the control map (height from src aspect)")
    ap.add_argument("--bbox", help="L,T,R,B in SVG user units to isolate one panel (default = body bounds)")
    ap.add_argument("--no-composite", action="store_true", help="skip the hard white-out of kept regions (measure raw pipeline leakage)")
    ap.add_argument("--full-bleed", action="store_true",
                    help="door-style FACADE panel: paint the artwork edge-to-edge inside the "
                         "outer contour. Large saloon-flap/splay cutouts are NOT carved from the "
                         "paint mask and are drawn faint (not bold) in the control map, so the "
                         "facade fills the bottom corners instead of tapering to a trapezoid. "
                         "Small enclosed openings (knobs) stay carved + bold.")
    ap.add_argument("--flap-hfrac", type=float, default=0.45,
                    help="under --full-bleed, a cutout taller than this fraction of the panel is "
                         "treated as a structural flap (painted, not carved). Default 0.45.")
    ap.add_argument("--base-model", default=BASE_MODEL)
    ap.add_argument("--controlnet", default=CN_MODEL)
    ap.add_argument("--prompt", default="a clean flat-color cityscape illustration, simple stylized buildings, soft colors, children's book style")
    ap.add_argument("--negative-prompt", default="text, words, signage, watermark, frame, border, photo, realistic, clutter, people")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cond-scale", type=float, default=0.8)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--stroke", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="fp16", help="weight variant to load (fp16 = use cached fp16 weights, upcast to dtype). 'none' = no variant")
    ap.add_argument("--dtype", default="float32", choices=["float32", "float16"], help="compute dtype (float32 = MPS-safe)")
    ap.add_argument("--smoke", action="store_true", help="memory smoke test: tiny res + 2 steps")
    ap.add_argument("--save-debug", action="store_true", help="also write *_control.png and *_mask.png next to --out")
    a = ap.parse_args()

    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)

    # source rect: a panel bbox if given, else the body bounds (matches svg_geometry_check)
    vb, shapes0 = C.extract_shapes(svg)
    shapes0 = C.classify(shapes0)
    if a.bbox:
        L, T, R, Bm = (float(v) for v in a.bbox.split(","))
        src_rect = (L, T, R - L, Bm - T)
    else:
        body = [s for s in shapes0 if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
        cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
        cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
        src_rect = (cx0, cy0, cx1 - cx0, cy1 - cy0)
    _, _, box_w, box_h = src_rect

    # output W/H
    if a.control_map is not None:
        cmap_path = a.control_map if a.control_map.is_absolute() else ROOT / a.control_map
        precomputed = Image.open(cmap_path).convert("RGB")
        W, H = precomputed.size
    else:
        precomputed = None
        W = a.width
        H = round8(W * box_h / box_w)

    if a.smoke:
        scale = 384.0 / max(W, H)
        W = round8(W * scale); H = round8(H * scale)
        a.steps = 2
        precomputed = None  # re-render at smoke res

    ctrl, paint, hole_m, drawn = render_control_and_masks(
        svg, src_rect, W, H, a.stroke, crop_filter=bool(a.bbox),
        full_bleed=a.full_bleed, flap_hfrac=a.flap_hfrac)
    if precomputed is not None:
        ctrl = precomputed if precomputed.size == (W, H) else precomputed.resize((W, H))

    mask_img = Image.fromarray((paint * 255).astype(np.uint8))  # white = generate
    init = Image.new("RGB", (W, H), (255, 255, 255))            # kept areas stay white

    if a.save_debug:
        ctrl.save(out.with_name(out.stem + "_control.png"))
        mask_img.save(out.with_name(out.stem + "_mask.png"))

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[sdxl-cn] device={device} {W}x{H} aspect={W/H:.3f} steps={a.steps} "
          f"cond={a.cond_scale} guid={a.guidance} strength={a.strength} "
          f"contours={drawn['outer_contour']} paintable={drawn['paintable_region']} cutouts={drawn['internal_cutout']} "
          f"full_bleed={a.full_bleed} flaps_skipped={drawn.get('flaps_skipped', 0)}",
          flush=True)

    t0 = time.time()
    dtype = torch.float16 if a.dtype == "float16" else torch.float32
    base_variant = None if a.variant in ("", "none") else a.variant

    def from_pretrained(loader, repo, **kw):
        """Load preferring the requested variant; if those weights aren't cached
        (e.g. xinsir CN ships only plain .safetensors), fall back to variant=None
        rather than triggering a multi-GB download of the missing variant."""
        want = kw.pop("variant", None)
        try:
            return loader.from_pretrained(repo, variant=want, **kw)
        except Exception as e:
            if want is None:
                raise
            print(f"[sdxl-cn] {repo} variant={want!r} unavailable ({type(e).__name__}); using variant=None", flush=True)
            return loader.from_pretrained(repo, variant=None, **kw)

    # base inpaint UNet is cached ONLY as fp16 (no plain .safetensors) -> load the
    # fp16 variant and upcast to dtype; xinsir CN ships ONLY plain weights -> the
    # helper falls back to variant=None for it. Neither path hits the network.
    cn = from_pretrained(ControlNetModel, a.controlnet, torch_dtype=dtype, variant=base_variant)
    pipe = from_pretrained(
        StableDiffusionXLControlNetInpaintPipeline, a.base_model,
        controlnet=cn, torch_dtype=dtype, variant=base_variant,
    )
    pipe.to(device)
    try:
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
    except Exception:
        pass
    print(f"[sdxl-cn] pipeline loaded {time.time()-t0:.0f}s, generating...", flush=True)

    g = torch.Generator(device="cpu").manual_seed(a.seed)
    img = pipe(
        prompt=a.prompt,
        negative_prompt=a.negative_prompt,
        image=init,
        mask_image=mask_img,
        control_image=ctrl,
        width=W, height=H,
        num_inference_steps=a.steps,
        guidance_scale=a.guidance,
        strength=a.strength,
        controlnet_conditioning_scale=a.cond_scale,
        generator=g,
    ).images[0]

    # Hard exact-geometry composite: pin every KEPT region (holes + outside the
    # paint mask) to pure white. On MPS the SDXL inpaint VAE decode tints the whole
    # canvas grey (it does not keep masked latents byte-exact), so the holes-clear
    # guarantee must be enforced here rather than trusted from the pipeline. This is
    # what makes region-IoU -> ~1.0 "by construction"; the model still only INVENTS
    # content in the paint region (bounded by the canny ControlNet contour).
    if not a.no_composite:
        out_arr = np.asarray(img.convert("RGB")).copy()
        keep = ~paint                      # holes + outside contour
        out_arr[keep] = 255                # force pure white
        img = Image.fromarray(out_arr)

    img.save(out)
    print(f"[sdxl-cn] saved {out} ({time.time()-t0:.0f}s total)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
