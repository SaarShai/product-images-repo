#!/usr/bin/env python3
"""upscale.py — best-effort high-res upscale for gen output (gpt-image caps ~896x1792).

cv2 Lanczos resize + a mild unsharp mask to restore crispness. This is an UPSCALE, not
native high-res — the generator's resolution is the real ceiling; flag that to the user.

Usage: python3 scripts/upscale.py IN OUT [--factor 2.5] [--sharp 0.6]
"""
import argparse
import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--factor", type=float, default=2.5)
    ap.add_argument("--sharp", type=float, default=0.6, help="unsharp amount (0=off)")
    a = ap.parse_args()
    img = cv2.imread(a.inp, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"cannot read {a.inp}")
    h, w = img.shape[:2]
    nw, nh = int(round(w * a.factor)), int(round(h * a.factor))
    up = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    if a.sharp > 0:
        blur = cv2.GaussianBlur(up, (0, 0), 1.2)
        up = cv2.addWeighted(up, 1 + a.sharp, blur, -a.sharp, 0)
    cv2.imwrite(a.out, up, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    print(f"upscaled {w}x{h} -> {nw}x{nh} (factor {a.factor}, sharp {a.sharp}) -> {a.out}")


if __name__ == "__main__":
    main()
