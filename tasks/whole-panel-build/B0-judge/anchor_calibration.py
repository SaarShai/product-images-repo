#!/usr/bin/env python3
"""B0.1 — L1 geometry-layer calibration on the labeled anchors.

For each combined anchor: render the registered candidate (artwork pasted at the exact SVG
<image> transform onto a viewBox-sized canvas, via make_anchor_overlay --artwork-only), then
measure geometry-adherence signals that need NO model:
  - contour_coverage : fraction of the outer-contour interior that carries artwork (alpha>0).
                       Under-fill (art not reaching the panel) drops this.
  - bottom_fill / top_fill : coverage in the bottom/top 8% band of the contour (localizes
                       under-fill — the FAIL anchor's "doesn't reach the bottom" mode).
Pair each with the user's ground-truth label and print a table. This MEASURES what the
deterministic layer separates (and therefore what must fall to L2/L3), instead of assuming it.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("/Users/za/Documents/product images repo")
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402

ANCHORS = ROOT / "tasks/whole-panel-build/anchors"
B0 = ROOT / "tasks/whole-panel-build/B0-judge"
# combined source SVGs (lines+art) live outside the repo (too big for git)
SRC = {
    "princess-narrow-01": "<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/princess/princess narrow panel template and illustration.svg",
    "space-stabilizer-01": "<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/space/space stabilizer example.svg",
    "space-narrow-panels-01": "<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/space/space narrow panels example.svg",
    "princess-panels-FAIL-01": "<DRIVE_ROOT>/Wanderland Folder/Files/Products/Screenery/production files/princess/princess panels template FAIL.svg",
    "window-fit-01": "/Users/za/Downloads/example - window fit.svg",
}
WIDTH = 900


def contour_mask(template_svg: Path, W: int, H: int):
    """Rasterize the in-viewBox outer-contour interior as a boolean mask at canvas size."""
    vb, shapes = C.extract_shapes(template_svg)
    cl = C.classify(shapes)
    vx, vy, vw, vh = vb
    sf = W / vw
    # active-panel contour = largest outer_contour whose bbox sits within the viewBox
    cands = [s for s in cl if s.role == "outer_contour" and s.polygon is not None
             and s.bounds[0] >= vx - vw * 0.1 and s.bounds[2] <= vx + vw * 1.1]
    if not cands:
        cands = [s for s in cl if s.role == "outer_contour" and s.polygon is not None]
    contour = max(cands, key=lambda s: s.area)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    xs = [(x - vx) * sf for x, y in contour.polygon.exterior.coords]
    ys = [(y - vy) * sf for x, y in contour.polygon.exterior.coords]
    d.polygon(list(zip(xs, ys)), fill=255)
    return np.array(img) > 127, (min(ys), max(ys))


def main() -> int:
    labels = json.loads((B0 / "labels.json").read_text())["anchors"]
    rows = []
    for name, src in SRC.items():
        cand = B0 / f"reg_{name}.png"
        subprocess.run([sys.executable, str(ROOT / "scripts/make_anchor_overlay.py"), src,
                        "--out", str(cand), "--width", str(WIDTH), "--artwork-only"],
                       check=True, capture_output=True)
        im = Image.open(cand).convert("RGBA")
        W, H = im.size
        alpha = np.array(im)[:, :, 3] > 16
        mask, (ytop, ybot) = contour_mask(ANCHORS / name / "source/template.svg", W, H)
        area = mask.sum()
        coverage = (alpha & mask).sum() / area if area else 0.0
        band = max(1, int((ybot - ytop) * 0.08))
        botm = mask.copy(); botm[: int(ybot) - band] = False
        topm = mask.copy(); topm[int(ytop) + band:] = False
        bottom_fill = (alpha & botm).sum() / botm.sum() if botm.sum() else 0.0
        top_fill = (alpha & topm).sum() / topm.sum() if topm.sum() else 0.0
        rows.append((name, labels[name]["label"], coverage, bottom_fill, top_fill))

    print(f"{'anchor':26s} {'label':5s} {'coverage':>9s} {'bottom':>7s} {'top':>6s}")
    print("-" * 62)
    out = {}
    for name, lab, cov, bf, tf in rows:
        flag = "  <-- under-fill?" if (cov < 0.95 or bf < 0.9) else ""
        print(f"{name:26s} {lab:5s} {cov:9.3f} {bf:7.3f} {tf:6.3f}{flag}")
        out[name] = {"label": lab, "coverage": round(cov, 4), "bottom_fill": round(bf, 4), "top_fill": round(tf, 4)}
    (B0 / "calibration_L1.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {B0/'calibration_L1.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
