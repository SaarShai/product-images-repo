#!/usr/bin/env python3
"""Pixel-space PUNCH-THROUGH composite: make die-cut holes read as CLEAN cut openings, not
painted discs. Aperture-lock (inpaint body-holes) stops the model painting features ON a hole,
but the hole interior still inherits panel colour. The judge (rubric B) wants: empty cutout =
clean background + a rim/bevel cut edge. This deterministically enforces that AFTER generation.

For each internal_cutout polygon (transform/hidden/clip/circle all handled by svg_classify):
  1) fill the interior with clean background (white, or transparent alpha=0 with --transparent)
  2) draw a bevel: a darker inner ring + lighter outer ring → reads as a cut edge with depth.

Usage:
  punch_holes.py --gen GEN.png --svg TEMPLATE.svg --out OUT.png [--transparent] [--bevel 3]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--svg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--transparent", action="store_true", help="punch holes to alpha=0 instead of white")
    ap.add_argument("--bevel", type=int, default=3, help="bevel ring width in px")
    ap.add_argument("--halo", type=int, default=8, help="px of vignette halo around each hole to "
                                                        "flatten to clean panel colour (0=off)")
    ap.add_argument("--halo-thresh", type=float, default=18.0,
                    help="only flatten halo pixels darker than panel-luma by this much (conditional: "
                         "protects holes the inpaint already kept clean)")
    ap.add_argument("--bg", default="255,255,255", help="clean-background RGB for opaque punch")
    args = ap.parse_args()

    gen = Image.open(args.gen).convert("RGBA")
    W, H = gen.size
    vb, shapes = C.extract_shapes(Path(args.svg))
    cl = C.classify(shapes)
    vx, vy, vw, vh = vb
    sf = W / vw
    cutouts = [s for s in cl if s.role == "internal_cutout"]
    bg = tuple(int(v) for v in args.bg.split(","))

    # masks at gen resolution
    hole = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(hole)
    for s in cutouts:
        pts = [((x - vx) * sf, (y - vy) * sf) for x, y in s.polygon.exterior.coords]
        if len(pts) >= 3:
            hd.polygon(pts, fill=255)

    # 0) flatten the gen's VIGNETTE HALO around each hole: an inpaint shadow ring just OUTSIDE the
    # cut makes a white-punched hole read as a raised button. Replace ONLY the actual vignette
    # (halo-ring pixels DARKER than the panel by --halo-thresh) with median panel colour. This is
    # conditional on purpose: a blind ring-fill DAMAGES a hole the inpaint already kept clean
    # (it paints panel-tan over clean white bleed). Keeps the cut spec-sized; crisp rim only.
    from PIL import ImageChops
    import numpy as np
    halo = max(0, args.halo)
    if halo:
        far = hole.filter(ImageFilter.MaxFilter(2 * (halo + args.bevel) + 1))   # hole+halo+rim zone
        body_clean = np.asarray(ImageChops.subtract(Image.new("L", (W, H), 255), far)) > 128
        rgb = np.asarray(gen.convert("RGB")).astype(np.int16)
        wts = np.array([0.299, 0.587, 0.114])
        panel = (tuple(int(v) for v in np.median(rgb[body_clean], axis=0))
                 if body_clean.any() else (150, 165, 175))
        panel_luma = float(np.dot(panel, wts))
        halo_ring = np.asarray(ImageChops.subtract(hole.filter(ImageFilter.MaxFilter(2 * halo + 1)),
                                                   hole)) > 128
        luma = rgb @ wts
        vignette = halo_ring & (luma < panel_luma - args.halo_thresh)   # ACTUAL shadow only
        out = rgb.copy()
        out[vignette] = panel
        gen = Image.fromarray(out.astype(np.uint8)).convert("RGBA")
        print(f"  halo: panel={panel} flattened {int(vignette.sum())} vignette px "
              f"({int(halo_ring.sum())} ring, thresh={args.halo_thresh})")

    # 1) punch interior to clean background (or transparent)
    if args.transparent:
        a = gen.split()[3]
        a = Image.composite(Image.new("L", (W, H), 0), a, hole)
        gen.putalpha(a)
    else:
        plate = Image.new("RGBA", (W, H), bg + (255,))
        gen = Image.composite(plate, gen, hole)

    # 2) bevel: darker inner ring (shadow just inside the cut) + lighter outer ring (lip)
    b = max(1, args.bevel)
    inner = hole.filter(ImageFilter.MinFilter(2 * b + 1))   # eroded
    outer = hole.filter(ImageFilter.MaxFilter(2 * b + 1))   # dilated
    inner_ring = Image.eval(Image.composite(Image.new("L", (W, H), 0), hole, inner), lambda v: v)  # hole - inner
    # ring masks
    from PIL import ImageChops
    inner_ring = ImageChops.subtract(hole, inner)
    outer_ring = ImageChops.subtract(outer, hole)
    rgb = gen.convert("RGBA")
    shadow = Image.new("RGBA", (W, H), (40, 40, 50, 255))
    lip = Image.new("RGBA", (W, H), (245, 245, 250, 255))
    rgb = Image.composite(shadow, rgb, inner_ring.point(lambda v: int(v * 0.75)))
    rgb = Image.composite(lip, rgb, outer_ring.point(lambda v: int(v * 0.55)))
    gen = rgb

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    if args.transparent:
        gen.save(args.out)
    else:
        gen.convert("RGB").save(args.out, quality=95)
    print(f"punched {len(cutouts)} holes  ({'transparent' if args.transparent else 'white'}+bevel{b})  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
