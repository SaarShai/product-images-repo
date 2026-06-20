#!/usr/bin/env python3
"""Code-based duplicate-element detector to back the VLM count gate.

Problem: a VLM count gate missed a stacked DOUBLE wooden window/door in a
generated die-cut panel. This script independently counts how many times a
known element (template PNG) appears in a candidate PNG, using multi-scale
template matching + non-max suppression. It is meant as a cheap, deterministic
second opinion behind the VLM count.

Method
------
* The template PNG is auto-cropped to its non-white bounding box, so white
  page margins around the element do not dilute the correlation.
* Matching is done in COLOR (3-channel TM_CCOEFF_NORMED). The wooden element
  is tan/brown and sits in a cream/stone scene; color matching rejects the
  many same-shaped-but-stone turrets/arches that fool a grayscale match.
* The element in a full-panel candidate is almost always SMALLER than the
  standalone template and its size varies, so we DOWNSCALE the template across
  a range of scales (scan scales) and run cv2.matchTemplate at each. This is
  equivalent to scanning the candidate at multiple scales while keeping the
  candidate (the thing we report coordinates in) at native resolution.
* For every scale we keep every location whose normalized correlation exceeds
  --thresh, recording (score, box).
* All hits from all scales are pooled and run through one greedy IoU-based
  non-max suppression, so a single physical element matched at several
  neighbouring scales/positions collapses to ONE detection.
* The number of surviving detections is the duplicate count.

Tuned acceptance (template = window-cut.png, this repo's princess panels):
  thresh=0.43, scales=0.13,0.24,12, nms=0.30
    EW-B1-edit-guided.png   -> count 1  (single wooden door)
    EW-B2-edit-noguide.png  -> count 2  (two stacked wooden doors)
  B1's real door scores ~0.44; B2's two doors score ~0.53 / ~0.51; every
  spurious stone turret scores <0.43 -- so 0.43 sits in the gap.

CLI
---
python3 scripts/dup_detect.py --cand PNG --template PNG [--expected 1]
        [--thresh 0.x] [--scales lo,hi,n] [--nms 0.x]
        [--no-crop] [--gray] [--debug OUT.png]

Exit code: 0 if (no --expected) or (count == expected), else 1 -- so it can
gate a pipeline. Always prints `count=<N>` on its own line for easy parsing.

Deps: cv2, numpy, PIL (PIL only for robust PNG read).
"""
import argparse
import sys

import cv2
import numpy as np
from PIL import Image


def load_bgr(path):
    """Robust read (PIL handles odd PNGs) -> uint8 BGR ndarray."""
    arr = np.array(Image.open(path).convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def crop_to_element(bgr, white=245):
    """Crop a flat template to the bounding box of its non-white content.

    Falls back to the full image if (almost) everything is white.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(gray < white)
    if ys.size == 0:
        return bgr
    return bgr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def iou(a, b):
    """IoU of two boxes (x0, y0, x1, y1)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / float(area_a + area_b - inter)


def nms(dets, iou_thresh):
    """Greedy non-max suppression. dets = list of (score, (x0,y0,x1,y1))."""
    dets = sorted(dets, key=lambda d: d[0], reverse=True)
    kept = []
    for score, box in dets:
        if all(iou(box, k[1]) < iou_thresh for k in kept):
            kept.append((score, box))
    return kept


def detect(cand_path, tmpl_path, thresh, scales, nms_iou, do_crop=True, gray=False):
    cand = load_bgr(cand_path)
    tmpl0 = load_bgr(tmpl_path)
    if do_crop:
        tmpl0 = crop_to_element(tmpl0)
    if gray:
        cand = cv2.cvtColor(cand, cv2.COLOR_BGR2GRAY)
        tmpl0 = cv2.cvtColor(tmpl0, cv2.COLOR_BGR2GRAY)

    H, W = cand.shape[:2]
    th0, tw0 = tmpl0.shape[:2]

    lo, hi, n = scales
    scale_list = np.linspace(lo, hi, int(n))

    raw = []  # (score, box) pre-NMS
    for s in scale_list:
        tw, th = int(round(tw0 * s)), int(round(th0 * s))
        if tw < 8 or th < 8 or tw > W or th > H:
            continue
        tmpl = cv2.resize(tmpl0, (tw, th), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(cand, tmpl, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= thresh)
        for x, y in zip(xs, ys):
            raw.append((float(res[y, x]), (int(x), int(y), int(x + tw), int(y + th))))

    kept = nms(raw, nms_iou)
    return kept, (W, H)


def main():
    ap = argparse.ArgumentParser(description="Multi-scale duplicate-element detector.")
    ap.add_argument("--cand", required=True, help="candidate PNG to scan")
    ap.add_argument("--template", required=True, help="known element PNG to find")
    ap.add_argument("--expected", type=int, default=None,
                    help="expected count; if set, exit 1 on mismatch")
    ap.add_argument("--thresh", type=float, default=0.43,
                    help="min TM_CCOEFF_NORMED correlation for a hit (tuned default 0.43)")
    ap.add_argument("--scales", default="0.13,0.24,12",
                    help="template scan scales as lo,hi,n relative to (cropped) template size")
    ap.add_argument("--nms", type=float, default=0.30,
                    help="IoU above which two detections are merged")
    ap.add_argument("--no-crop", action="store_true",
                    help="do NOT auto-crop the template to its non-white bbox")
    ap.add_argument("--gray", action="store_true",
                    help="match in grayscale instead of color (color is the default/tuned mode)")
    ap.add_argument("--debug", default=None,
                    help="optional path to write candidate with detection boxes drawn")
    a = ap.parse_args()

    lo, hi, n = a.scales.split(",")
    scales = (float(lo), float(hi), float(n))

    kept, (W, H) = detect(a.cand, a.template, a.thresh, scales, a.nms,
                          do_crop=not a.no_crop, gray=a.gray)
    count = len(kept)

    print(f"count={count}")
    print(f"thresh={a.thresh} scales={a.scales} nms={a.nms} "
          f"mode={'gray' if a.gray else 'color'} crop={not a.no_crop} cand={W}x{H}")
    for i, (score, box) in enumerate(sorted(kept, key=lambda d: d[1][1])):
        x0, y0, x1, y1 = box
        print(f"  det{i+1}: score={score:.3f} box=({x0},{y0})-({x1},{y1}) "
              f"center=({(x0+x1)//2},{(y0+y1)//2})")

    if a.debug:
        cand = load_bgr(a.cand)
        for score, (x0, y0, x1, y1) in kept:
            cv2.rectangle(cand, (x0, y0), (x1, y1), (0, 0, 255), max(2, W // 300))
            cv2.putText(cand, f"{score:.2f}", (x0, max(12, y0 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, max(0.5, W / 1400.0),
                        (0, 0, 255), max(1, W // 600))
        cv2.imwrite(a.debug, cand)
        print(f"debug -> {a.debug}")

    if a.expected is not None and count != a.expected:
        print(f"FAIL: expected {a.expected}, got {count}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
