#!/usr/bin/env python3
"""compose_fairy.py — composite a regenerated fairy back onto the ORIGINAL so that
ONLY the fairy changes; everything else stays byte-identical. Reports change stats.

Mask modes:
  default (rect)  : feathered rectangle from --mask bbox. Simple but for whole-crop
                    instruction edits (Kontext/Flux.2) it lets the model's faint repaint
                    of background INSIDE the box through.
  --diffmask      : GLM #1 fix. Build the mask from where REGEN actually differs from the
                    original (figure = large diff), confined to --mask bbox, hole-closed +
                    dilated + lightly feathered. Keeps surrounding flowers/wall byte-exact
                    and pastes only the figure crisply (no fade, no pose-ghost).

Usage:
  python3 compose_fairy.py --orig O.png --regen R.png --out OUT.png \
      --crop 60,2560,720,3300 --mask 160,2660,480,3110 [--feather 40]
      [--diffmask --diff-thresh 40 --diff-close 4 --diff-dilate 4 --diff-feather 4]
"""
import argparse
import numpy as np
from PIL import Image, ImageFilter, ImageDraw


def box(s):
    return tuple(int(v) for v in s.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True)
    ap.add_argument("--regen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--crop", default=None, help="x0,y0,x1,y1 context-crop box (regen is this crop)")
    ap.add_argument("--mask", required=True, help="x0,y0,x1,y1 fairy mask bbox, full-res coords")
    ap.add_argument("--feather", type=int, default=40)
    ap.add_argument("--diffmask", action="store_true", help="build mask from regen-vs-orig diff (figure only)")
    ap.add_argument("--diff-thresh", type=int, default=40)
    ap.add_argument("--diff-close", type=int, default=4, help="hole-close radius (px)")
    ap.add_argument("--diff-dilate", type=int, default=4, help="dilate radius (px)")
    ap.add_argument("--diff-feather", type=int, default=4)
    a = ap.parse_args()

    orig = Image.open(a.orig).convert("RGB")
    W, H = orig.size
    regen = Image.open(a.regen).convert("RGB")

    layer = orig.copy()
    if a.crop:
        cx0, cy0, cx1, cy1 = box(a.crop)
        regen_r = regen.resize((cx1 - cx0, cy1 - cy0), Image.LANCZOS)
        layer.paste(regen_r, (cx0, cy0))
    else:
        layer = regen.resize((W, H), Image.LANCZOS)

    mx0, my0, mx1, my1 = box(a.mask)
    if a.diffmask:
        o = np.asarray(orig, np.int16); l = np.asarray(layer, np.int16)
        d = np.abs(o - l).max(axis=2)
        bm = np.zeros((H, W), np.uint8)
        bm[(d > a.diff_thresh)] = 255
        reg = np.zeros((H, W), np.uint8); reg[my0:my1, mx0:mx1] = 255
        bm = np.minimum(bm, reg)
        m = Image.fromarray(bm, "L")
        if a.diff_close > 0:
            k = a.diff_close * 2 + 1
            m = m.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))  # close holes
        if a.diff_dilate > 0:
            m = m.filter(ImageFilter.MaxFilter(a.diff_dilate * 2 + 1))
        if a.diff_feather > 0:
            m = m.filter(ImageFilter.GaussianBlur(a.diff_feather))
    else:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rectangle([mx0, my0, mx1, my1], fill=255)
        if a.feather > 0:
            m = m.filter(ImageFilter.GaussianBlur(a.feather))

    out = Image.composite(layer, orig, m)
    out.save(a.out)

    # ---- measurement ----
    o = np.asarray(orig, dtype=np.int16)
    r = np.asarray(out, dtype=np.int16)
    diff = np.abs(o - r).max(axis=2)
    changed = diff > 2
    mk = np.asarray(m, dtype=np.uint8) > 0
    n_out = int((changed & (~mk)).sum())
    out_max = int(diff[~mk].max()) if (~mk).any() else 0
    ys, xs = np.where(changed)
    cb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
    frac = changed.sum() / (W * H)
    print(f"[compose] -> {a.out}  ({'diffmask' if a.diffmask else 'rect'})")
    print(f"  changed_pixels={int(changed.sum())} ({frac*100:.3f}% of image)  changed_bbox={cb}")
    print(f"  OUTSIDE-MASK changed_pixels={n_out}  outside_max_delta={out_max}  (gate: ~0)")


if __name__ == "__main__":
    main()
