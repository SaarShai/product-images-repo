#!/usr/bin/env python3
"""dehalo.py — remove the grey edge-halo / wispy-line artifact that a creative upscaler
(clarity creativity~0.5) leaves around isolated objects on a white page, and flatten the
page to PURE white. Operates on the RGB image (NOT a cutout) so the later bg-removal cut is
also clean.

Method: flood-fill from the image borders through pixels that are BRIGHT and near-NEUTRAL
(R≈G≈B) and set them to white. The flood whitens the white page + the neutral-grey halo ring,
but STOPS at coloured objects (dresses, roofs, wings, butterflies all carry hue) — so figures,
including translucent warm-tinted wings, are preserved.

Usage:
  .venv-gen/bin/python scripts/dehalo.py --image IN.png --out OUT.png [--bright 198] [--neutral 12]
"""
import argparse
import sys
import numpy as np
import cv2
from PIL import Image


def dehalo(img: Image.Image, bright=198, neutral=12, protect=None):
    """protect: list of [x0,y0,x1,y1] boxes the flood must NOT whiten — shields a WHITE/near-neutral
    subject on a white page (e.g. a white dress) that is border-connected and would otherwise be
    flattened by the flood. See [[clarity-grey-edge-halo]] white-on-white DANGER."""
    a = np.asarray(img.convert("RGB")).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    br = np.maximum(np.maximum(R, G), B)
    neu = (np.abs(R - G) < neutral) & (np.abs(G - B) < neutral) & (np.abs(R - B) < neutral + 2)
    cand = ((br >= bright) & neu).astype(np.uint8)
    num, lab = cv2.connectedComponents(cand, connectivity=4)
    border = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    bgmask = np.isin(lab, list(border))
    protected_px = 0
    for x0, y0, x1, y1 in (protect or []):
        if x1 <= x0 or y1 <= y0:   # swapped/empty coords => empty slice => silent no-op shield. warn, don't crash.
            print(f"[dehalo] WARN degenerate protect box {(x0, y0, x1, y1)} skipped (need x0<x1 and y0<y1)", file=sys.stderr)
            continue
        protected_px += int(bgmask[y0:y1, x0:x1].sum())  # count what we actually spare (0 => shield hit nothing)
        bgmask[y0:y1, x0:x1] = False  # shield protected subject from the flood
    out = a.copy(); out[bgmask] = [255, 255, 255]
    return Image.fromarray(out.astype("uint8")), float(bgmask.mean()), protected_px


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bright", type=int, default=198, help="min brightness to treat as page/halo")
    ap.add_argument("--neutral", type=int, default=12, help="max R/G/B spread to treat as neutral grey")
    ap.add_argument("--protect", action="append", default=[],
                    help="x0,y0,x1,y1 box to shield from the flood (repeatable) — for white-on-white subjects")
    a = ap.parse_args()
    protect = [[int(v) for v in p.split(",")] for p in a.protect]
    res, frac, protected_px = dehalo(Image.open(a.image), a.bright, a.neutral, protect)
    res.save(a.out)
    # protected_px=0 with boxes given => the shield hit nothing (swapped coords / wrong box) — a real signal
    print(f"[dehalo] {a.image} -> {a.out}  whitened={frac*100:.1f}% (page+halo)  protected_boxes={len(protect)} protected_px={protected_px}")


if __name__ == "__main__":
    main()
