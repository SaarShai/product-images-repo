#!/usr/bin/env python3
"""mask_check.py — PRE-SPEND mask guardrail. Verify a mask actually covers the
intended target BEFORE wasting an edit/erase API call.

Catches the recurring failure where a hand-authored mask is ~100px off the target
(e.g. masked empty building above a roof sign) so the eraser/inpaint "does nothing".

It detects the TARGET pixels (the thing you mean to edit) inside an expected REGION,
then measures:
  containment = (target ∩ mask) / target      (how much of the target the mask covers)
  leak        = mask pixels that are NOT on/near target / mask area  (mask too big/misplaced)
PASS iff containment >= --min-contain AND leak <= --max-leak.

Usage:
  python3 scripts/mask_check.py --image CTX.png --mask MASK.png \
     --target dark --region 400,492,728,592 --out work/_mc.png
  # or a box instead of a mask file:
  python3 scripts/mask_check.py --image CTX.png --mask-box 348,196,512,300 --target white ...

Targets: dark | white | yellow | nonwhite | edges
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def box(s):
    return tuple(int(v) for v in s.split(","))


def detect(a, target):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = np.maximum(np.maximum(R, G), B)
    if target == "dark":
        return mx < 95
    if target == "white":
        return (R > 205) & (G > 205) & (B > 195)
    if target == "yellow":
        return (R > 180) & (G > 150) & (B < 155) & ((G - B) > 45)
    if target == "nonwhite":
        return mx < 235
    if target == "edges":
        g = np.asarray(Image.fromarray(a.astype("uint8")).convert("L").filter(ImageFilter.FIND_EDGES))
        return g > 40
    raise SystemExit(f"unknown target {target}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--mask")
    ap.add_argument("--mask-box")
    ap.add_argument("--target", default="nonwhite")
    ap.add_argument("--region", help="x0,y0,x1,y1 where the target is expected (default whole image)")
    ap.add_argument("--min-contain", type=float, default=0.85)
    ap.add_argument("--max-leak", type=float, default=0.65)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    W, H = img.size
    arr = np.asarray(img).astype(int)

    if a.mask:
        m = np.asarray(Image.open(a.mask).convert("L").resize((W, H))) > 128
    else:
        x0, y0, x1, y1 = box(a.mask_box)
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = True

    tgt = detect(arr, a.target)
    if a.region:
        rx0, ry0, rx1, ry1 = box(a.region)
        reg = np.zeros((H, W), bool)
        reg[ry0:ry1, rx0:rx1] = True
        tgt = tgt & reg

    tgt_n = int(tgt.sum())
    if tgt_n == 0:
        print(f"[mask_check] target={a.target} found 0 pixels in region — nothing to cover (suspicious).")
        contain = 0.0
    else:
        contain = float((tgt & m).sum()) / tgt_n

    # leak: mask pixels not on/near the target (target dilated by ~12px)
    from scipy import ndimage
    tgt_d = ndimage.binary_dilation(tgt, iterations=12)
    m_n = int(m.sum())
    leak = float((m & ~tgt_d).sum()) / m_n if m_n else 1.0

    ok = (contain >= a.min_contain) and (leak <= a.max_leak)
    print(f"[mask_check] target={a.target} target_px={tgt_n} mask_px={m_n}")
    print(f"  containment={contain:.3f} (need >= {a.min_contain})   leak={leak:.3f} (need <= {a.max_leak})")
    print(f"  -> {'PASS' if ok else 'FAIL'}")

    if a.out:
        ov = img.copy()
        o = np.asarray(ov).copy()
        o[m & ~tgt] = (o[m & ~tgt] * 0.5 + np.array([255, 0, 0]) * 0.5).astype("uint8")   # mask-only = red
        o[tgt & ~m] = (o[tgt & ~m] * 0.4 + np.array([0, 150, 255]) * 0.6).astype("uint8")  # missed target = blue
        o[tgt & m] = (o[tgt & m] * 0.3 + np.array([0, 255, 0]) * 0.7).astype("uint8")       # covered = green
        Image.fromarray(o).save(a.out)
        print(f"  overlay -> {a.out}  (green=covered target, blue=MISSED target, red=mask-on-empty)")

    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
