#!/usr/bin/env python3
"""Fill-agnostic geometry metric: does the output reproduce each SVG opening at
the exact position/size/shape, regardless of how it's filled (white, blue, rim)?

For each SVG opening we flood the connected non-edge region that contains the
opening's mapped centroid (bounded by the model's own drawn outline = strong
gradient edges), then IoU that region against the exact SVG opening polygon.
This measures PLACEMENT+SHAPE, not color — so a blue-filled-but-correctly-placed
opening scores high (unlike white-IoU).
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage  # type: ignore
sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--bbox", help="L,T,R,B; default auto (nonwhite panel)")
    ap.add_argument("--out-overlay", type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--edge-k", type=float, default=1.3, help="edge threshold = mean+k*std of gradient")
    a = ap.parse_args()

    img = Image.open(a.image if a.image.is_absolute() else ROOT / a.image).convert("RGB")
    W, H = img.size
    arr = np.asarray(img).astype(np.float32)
    if a.bbox:
        L, T, R, B = (int(v) for v in a.bbox.split(","))
    else:
        nonwhite = np.any(arr < 240, axis=2)
        ys, xs = np.where(nonwhite)
        L, T, R, B = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1) if len(xs) else (0, 0, W, H)

    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    _, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)
    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
    cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
    sx = (R - L) / (cx1 - cx0); sy = (B - T) / (cy1 - cy0)
    f = lambda x, y: (L + (x - cx0) * sx, T + (y - cy0) * sy)

    gray = arr.mean(axis=2)
    gx, gy = np.gradient(gray)
    mag = np.hypot(gx, gy)
    edge = mag > (mag.mean() + a.edge_k * mag.std())
    labels, _ = ndimage.label(~edge)

    def poly_mask(poly) -> np.ndarray:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([f(x, y) for x, y in poly.exterior.coords], fill=255)
        return np.asarray(m) > 127

    rows, ious = [], []
    ov = img.copy(); d = ImageDraw.Draw(ov)
    for i, s in enumerate(cuts, 1):
        pm = poly_mask(s.polygon)
        cxp, cyp = f(*s.polygon.representative_point().coords[0])
        cxi, cyi = int(min(W - 1, max(0, cxp))), int(min(H - 1, max(0, cyp)))
        comp = labels[cyi, cxi]
        region = (labels == comp) & (~edge)
        # reject body-leak: if region is huge vs opening, the outline was broken -> 0
        if region.sum() > pm.sum() * 4:
            region = np.zeros_like(region)
        inter = int((region & pm).sum()); union = int((region | pm).sum())
        iou = inter / union if union else 0.0
        ious.append(iou); rows.append({"i": i, "kind": s.kind, "region_iou": round(iou, 3)})
        d.line([f(x, y) for x, y in s.polygon.exterior.coords] + [f(*s.polygon.exterior.coords[0])],
               fill=(0, 230, 0) if iou >= 0.7 else (235, 40, 40), width=2)
    for s in body:
        d.line([f(x, y) for x, y in s.polygon.exterior.coords] + [f(*s.polygon.exterior.coords[0])], fill=(0, 200, 255), width=2)

    mean_iou = sum(ious) / len(ious) if ious else 0.0
    print(f"mean region-IoU (fill-agnostic placement) = {mean_iou:.3f}")
    for r in rows:
        print(f"  opening {r['i']} ({r['kind']}): {r['region_iou']}")
    if a.out_overlay:
        p = a.out_overlay if a.out_overlay.is_absolute() else ROOT / a.out_overlay
        p.parent.mkdir(parents=True, exist_ok=True); ov.save(p); print(f"overlay -> {p}")
    if a.json_out:
        p = a.json_out if a.json_out.is_absolute() else ROOT / a.json_out
        p.write_text(json.dumps({"image": str(a.image), "bbox": [L, T, R, B], "mean_region_iou": round(mean_iou, 4), "openings": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
