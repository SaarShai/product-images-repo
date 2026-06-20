#!/usr/bin/env python3
"""Register a FREE-FORM panel illustration (a subscription gen: the painted panel sits on a white
background, roughly the right shape but not pixel-exact) onto the EXACT die-cut geometry of an SVG,
then enforce that geometry: clip everything outside the true contour to white and punch the cutouts
to clean voids. The painted controls (interior) are preserved; only the outer edge is trimmed to the
exact contour and the holes are made exact. This is the geometry-recovery step that lets a rich
subscription style become a production-exact die-cut panel.

Pipeline: detect gen body (non-white) -> best-fit scale+translate onto the SVG body mask by IoU
(bbox seed + local refine) -> compose on a viewBox canvas -> clip outside-contour to white ->
punch holes (white void + crisp bevel rim).

  register_to_svg.py --gen GEN.png --svg PANEL.svg --out OUT.png [--width 1024] [--bevel 2]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402


def svg_masks(svg, W):
    vb, shapes = C.extract_shapes(Path(svg)); cl = C.classify(shapes)
    vx, vy, vw, vh = vb
    H = int(round(W * vh / vw)); sf = W / vw
    body = Image.new("L", (W, H), 0); hole = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(body); hd = ImageDraw.Draw(hole)
    def S(p): return [((x - vx) * sf, (y - vy) * sf) for x, y in p.exterior.coords]
    for s in cl:
        if s.role in ("outer_contour", "paintable_region"):
            bd.polygon(S(s.polygon), fill=255)
    for s in cl:
        if s.role == "internal_cutout":
            hd.polygon(S(s.polygon), fill=255)
    return (np.asarray(body) > 128), (np.asarray(hole) > 128), (W, H)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True, type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--bevel", type=int, default=2)
    ap.add_argument("--white", type=int, default=244, help="bg threshold: sum(rgb)>3*white => white")
    a = ap.parse_args()

    svg_body, svg_hole, (W, H) = svg_masks(a.svg, a.width)
    paint_target = svg_body & ~svg_hole

    gen = Image.open(a.gen).convert("RGB")
    g = np.asarray(gen)
    gbody = g.sum(2) < (3 * a.white)
    gbody = cv2.morphologyEx(gbody.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(gbody, 8)
    if n <= 1:
        print("no gen body", file=sys.stderr); return 2
    gid = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.where(lbl == gid)
    gx0, gy0, gx1, gy1 = xs.min(), ys.min(), xs.max(), ys.max()
    gcrop = gen.crop((gx0, gy0, gx1 + 1, gy1 + 1))
    gw, gh = gcrop.size

    # SVG body bbox on the canvas
    sy, sx = np.where(svg_body)
    sx0, sy0, sx1, sy1 = sx.min(), sy.min(), sx.max(), sy.max()
    sw, sh = sx1 - sx0 + 1, sy1 - sy0 + 1

    best = None
    for sc in [s / 100 for s in range(88, 113, 3)]:
        tw, th = max(1, int(gw * (sw / gw) * sc)), max(1, int(gh * (sh / gh) * sc))
        rg = gcrop.resize((tw, th))
        # center the resized gen on the svg body bbox center
        cxs, cys = (sx0 + sx1) // 2, (sy0 + sy1) // 2
        ox, oy = cxs - tw // 2, cys - th // 2
        for dx in (-6, 0, 6):
            for dy in (-6, 0, 6):
                canvas = Image.new("RGB", (W, H), (255, 255, 255))
                canvas.paste(rg, (ox + dx, oy + dy))
                cb = np.asarray(canvas).sum(2) < (3 * a.white)
                inter = (cb & svg_body).sum(); union = (cb | svg_body).sum()
                iou = inter / union if union else 0
                if best is None or iou > best[0]:
                    best = (iou, canvas)
    iou, canvas = best

    # enforce exact geometry: outside contour -> white; holes -> white void + bevel rim
    arr = np.asarray(canvas).copy()
    arr[~paint_target] = 255
    out = Image.fromarray(arr)
    if a.bevel > 0:
        hole_img = Image.fromarray((svg_hole * 255).astype(np.uint8))
        inner = hole_img.filter(ImageFilter.MinFilter(2 * a.bevel + 1))
        rim = np.asarray(ImageChops.subtract(hole_img, inner)) > 128
        o = np.asarray(out).copy(); o[rim] = (60, 60, 70); out = Image.fromarray(o)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=95)
    print(f"registered iou={iou:.3f} canvas={W}x{H} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
