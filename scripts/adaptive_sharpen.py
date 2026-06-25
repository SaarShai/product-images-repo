#!/usr/bin/env python3
"""Adaptive local sharpening driven by an auto-computed blur map.

Targets exactly the regions that HAVE structure but are SOFT (depth-of-field /
upscaler blur), while leaving already-sharp regions and flat areas (sky) alone.
No API, no re-gen — one local pass.

blur_weight = structure_presence * edge_softness
  structure_presence = local mean gradient (sky -> ~0, so it never gets boosted)
  edge_softness      = 1 - (local peak gradient / crisp_reference)
                       (crisp facade edges -> ~0 softness, blurry edges -> high)

Then unsharp-mask blended by blur_weight (multi-scale to match broad blur).

Usage:
  adaptive_sharpen.py IN.png OUT.png [--amount 1.6] [--win 41]
                      [--sigmas 1.5,3.5] [--map MAP.png] [--max-weight 1.0]
"""
import argparse, sys
import numpy as np
import cv2


def local_box(x, k):
    return cv2.boxFilter(x, ddepth=-1, ksize=(k, k), normalize=True,
                         borderType=cv2.BORDER_REFLECT)


def build_blur_weight(gray, win, p_presence=90.0, p_crisp=92.0):
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(gx, gy)

    # structure presence: is there edge content in this neighborhood at all?
    presence = local_box(grad, win)
    # local peak edge strength: crisp regions have very strong local peaks
    peak = cv2.dilate(grad, cv2.getStructuringElement(cv2.MORPH_RECT, (win, win)))

    # reference scales from the image's own statistics (robust to exposure)
    pres_ref = np.percentile(presence[presence > 0], p_presence) + 1e-6
    crisp_ref = np.percentile(peak[peak > 0], p_crisp) + 1e-6

    presence_n = np.clip(presence / pres_ref, 0.0, 1.0)
    crispness_n = np.clip(peak / crisp_ref, 0.0, 1.0)
    softness = 1.0 - crispness_n

    weight = presence_n * softness
    # smooth so sharpening doesn't go patchy
    weight = cv2.GaussianBlur(weight, (0, 0), sigmaX=win / 3.0)
    # renormalize to [0,1] using a high percentile (ignore tiny tail)
    w_ref = np.percentile(weight, 99.0) + 1e-6
    weight = np.clip(weight / w_ref, 0.0, 1.0)
    return weight


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--amount", type=float, default=1.6,
                    help="peak unsharp strength where blur_weight==max")
    ap.add_argument("--win", type=int, default=41,
                    help="neighborhood window (px) for the blur map")
    ap.add_argument("--sigmas", default="1.5,3.5",
                    help="comma list of unsharp gaussian sigmas (multi-scale)")
    ap.add_argument("--max-weight", type=float, default=1.0,
                    help="cap on blur_weight (lower = more conservative)")
    ap.add_argument("--map", default=None, help="optional blur-map heatmap PNG")
    args = ap.parse_args()

    bgr = cv2.imread(args.inp, cv2.IMREAD_COLOR)
    if bgr is None:
        sys.exit(f"cannot read {args.inp}")
    img = bgr.astype(np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    weight = build_blur_weight(gray, args.win)
    weight = np.minimum(weight, args.max_weight)
    w3 = weight[..., None]

    sigmas = [float(s) for s in args.sigmas.split(",")]
    out = img.copy()
    for sigma in sigmas:
        blur = cv2.GaussianBlur(img, (0, 0), sigmaX=sigma)
        detail = img - blur
        out += (args.amount / len(sigmas)) * w3 * detail

    out = np.clip(out, 0, 255).astype(np.uint8)
    cv2.imwrite(args.out, out)

    if args.map:
        hm = cv2.applyColorMap((weight * 255).astype(np.uint8), cv2.COLORMAP_JET)
        viz = cv2.addWeighted(bgr, 0.5, hm, 0.5, 0)
        cv2.imwrite(args.map, viz)

    pct = float((weight > 0.15).mean() * 100)
    print(f"sharpened: {args.inp} -> {args.out}")
    print(f"blur_weight>0.15 covers {pct:.1f}% of pixels "
          f"(mean={weight.mean():.3f}, max={weight.max():.3f})")


if __name__ == "__main__":
    main()
