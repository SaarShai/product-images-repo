#!/usr/bin/env python3
"""hole_bevel.py — complement die-cut holes with an illustrated bevel rim (mask-driven).

Master-template v2 variant of the space re-seat rule: the geometry contract
gives per-panel `<p>-holes.png` (white discs = enclosed cutouts). For each disc
we punch the candidate to a pale paper-white interior and paint the space-proven
hand-illustrated bevel — dark-navy inner shadow on the upper-left arc, pale lit
lip on the lower-right — so the cut reads as a painted recess, not a flat punch.
Reuses build_bevel/sample_* from exact_bevel_composite.py (the SVG-driven
original); this one takes masks, no SVG needed.

CLI: python3 scripts/hole_bevel.py --cand <img> --holes <p>-holes.png \
        --mask <p>-mask.png --out <out.png> [--rim-scale 1.4] [--seed 7]
"""
from __future__ import annotations

import argparse, sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exact_bevel_composite import (  # noqa: E402
    build_bevel, sample_opening_tone, sample_shadow_tone,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--holes", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rim-scale", type=float, default=1.4)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    cand = Image.open(a.cand).convert("RGB")
    arr = np.array(cand).astype(np.float64)
    holes = np.array(Image.open(a.holes).convert("L").resize(cand.size, Image.NEAREST)) > 127
    body = np.array(Image.open(a.mask).convert("L").resize(cand.size, Image.NEAREST)) > 127

    if not holes.any():
        Image.fromarray(arr.astype("uint8")).save(a.out)
        print("no holes; passthrough"); return

    tone_center = sample_opening_tone(arr, body)
    tone_shadow = sample_shadow_tone(arr, body)
    rng = np.random.default_rng(a.seed)

    lab, n = label(holes)
    out = arr.copy()
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() < 40:  # anti-alias sliver
            continue
        ys, xs = np.nonzero(m)
        center = (float(ys.mean()), float(xs.mean()))
        ring_px = max(3.0, float(np.sqrt(m.sum() / np.pi)) * 0.22)
        rgb, alpha = build_bevel(m, center, arr.shape[:2], rng,
                                 tone_center, tone_shadow, ring_px,
                                 rim_scale=a.rim_scale)
        out = out * (1 - alpha[..., None]) + rgb * alpha[..., None]

    Image.fromarray(np.clip(out, 0, 255).astype("uint8")).save(a.out)
    print(f"beveled {n} hole(s) -> {a.out}")


if __name__ == "__main__":
    main()
