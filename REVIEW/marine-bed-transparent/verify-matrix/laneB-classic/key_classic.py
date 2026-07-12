#!/usr/bin/env python3
"""
Lane B: classic green-screen keyer (industry chroma-key formula family).

  alpha = 1 - clamp((G - max(R,B) - t0) / (t1 - t0), 0, 1)

  - diff = G - max(R,B) is the standard "greenness" signal.
  - t0/t1 tuned on this image's histogram (see analysis below).
  - Despill: G = min(G, max(R,B) + k), applied ONLY where the pixel was
    partially/fully keyed (keyed-ness = 1-alpha > 0), so unaffected
    foreground pixels keep their original color.
  - Light edge feather: small gaussian blur confined to the alpha
    transition band (does not touch flat 0/1 regions).

Histogram of diff on raw_green_P1.png showed a clean bimodal split:
foreground mass concentrated below ~40, background mass concentrated
above ~210 (66% of pixels), with a small sparse tail in between
(edge/fine-detail pixels near the green screen). t0=60 / t1=200 puts
the ramp squarely in that sparse gap.
"""
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

RAW = "/Users/za/Documents/product images repo/REVIEW/marine-bed-transparent/chroma-lane/raws/raw_green_P1.png"
OUTDIR = "/Users/za/Documents/product images repo/REVIEW/marine-bed-transparent/verify-matrix/laneB-classic"

T0 = 60.0
T1 = 200.0
DESPILL_K = 10.0  # G capped to max(R,B)+k where keyed
FEATHER_SIGMA = 1.2  # px, applied only in the alpha transition band


def load_rgb():
    im = Image.open(RAW).convert("RGB")
    return np.array(im).astype(np.float32)


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def key(rgb):
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxrb = np.maximum(R, B)
    diff = G - maxrb

    keyness = clamp01((diff - T0) / (T1 - T0))  # 0=foreground .. 1=background
    alpha = 1.0 - keyness

    # Despill: only where the pixel carries some green-key signal (keyness>0)
    mask = keyness > 0
    G_despilled = G.copy()
    G_despilled[mask] = np.minimum(G[mask], maxrb[mask] + DESPILL_K)

    out_rgb = rgb.copy()
    out_rgb[..., 1] = G_despilled

    return out_rgb, alpha, diff


def feather_alpha(alpha):
    """Gaussian-blur alpha only within its own transition band, so flat
    0/1 interior/exterior regions stay crisp (no whole-image softening)."""
    transition = (alpha > 0.01) & (alpha < 0.99)
    band = ndimage.binary_dilation(transition, iterations=3)
    blurred = ndimage.gaussian_filter(alpha, sigma=FEATHER_SIGMA)
    out = alpha.copy()
    out[band] = blurred[band]
    return out


def enclosed_green_pockets(alpha, min_px=4):
    """Count connected components of background (alpha==0) NOT touching
    the image border, with area > min_px pixels (leaked/enclosed holes)."""
    bg = alpha <= 0.001
    labeled, n = ndimage.label(bg)
    h, w = bg.shape
    border_labels = set(labeled[0, :]) | set(labeled[-1, :]) | set(labeled[:, 0]) | set(labeled[:, -1])
    border_labels.discard(0)
    count = 0
    for lbl in range(1, n + 1):
        if lbl in border_labels:
            continue
        size = int((labeled == lbl).sum())
        if size > min_px:
            count += 1
    return count


def rim_vs_interior_greenness(alpha, diff, band_px=6):
    """boundary band = pixels within band_px of the alpha edge (subject side);
    interior = subject pixels farther than band_px from the edge."""
    subject = alpha > 0.5
    subject_dil = ndimage.binary_erosion(subject, iterations=band_px)
    boundary_band = subject & ~subject_dil
    interior = subject_dil
    rim_mean = float(diff[boundary_band].mean()) if boundary_band.any() else None
    interior_mean = float(diff[interior].mean()) if interior.any() else None
    return rim_mean, interior_mean


def border_occupancy(alpha, strip_px=3):
    h, w = alpha.shape
    strip = np.zeros_like(alpha, dtype=bool)
    strip[:strip_px, :] = True
    strip[-strip_px:, :] = True
    strip[:, :strip_px] = True
    strip[:, -strip_px:] = True
    occupied = (alpha[strip] > 0.5).mean()
    return float(occupied * 100.0)


def save_crop(rgba_img, box, name):
    crop = rgba_img.crop(box)
    crop.save(f"{OUTDIR}/crop_{name}.png")


def composite_over(rgba_img, color):
    bg = Image.new("RGBA", rgba_img.size, color + (255,))
    return Image.alpha_composite(bg, rgba_img).convert("RGB")


def main():
    rgb = load_rgb()
    out_rgb, alpha, diff = key(rgb)
    alpha = feather_alpha(alpha)

    alpha_u8 = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    rgba = np.dstack([np.clip(out_rgb, 0, 255).astype(np.uint8), alpha_u8])
    rgba_img = Image.fromarray(rgba, mode="RGBA")
    rgba_img.save(f"{OUTDIR}/keyed_classic.png")

    composite_over(rgba_img, (255, 0, 255)).save(f"{OUTDIR}/composite_magenta.png")
    composite_over(rgba_img, (255, 255, 255)).save(f"{OUTDIR}/composite_white.png")

    h, w = alpha.shape
    # crops: bubble (upper/mid area, translucent bluish object), coral tip,
    # seahorse, sand edge (lower band). Coordinates are generic quadrant
    # boxes sized to catch each region on a 1024x1536 canvas; adjusted by
    # inspecting composite_white.png if a crop lands off-subject.
    crops = {
        "bubble": (int(w * 0.30), int(h * 0.02), int(w * 0.55), int(h * 0.20)),
        "coral_tip": (int(w * 0.35), int(h * 0.00), int(w * 0.75), int(h * 0.18)),
        "seahorse": (int(w * 0.18), int(h * 0.62), int(w * 0.45), int(h * 0.82)),
        "sand_edge": (int(w * 0.00), int(h * 0.85), int(w * 1.00), int(h * 1.00)),
    }
    for name, box in crops.items():
        save_crop(rgba_img, box, name)

    pockets = enclosed_green_pockets(alpha, min_px=4)
    rim_mean, interior_mean = rim_vs_interior_greenness(alpha, diff, band_px=6)
    occ = border_occupancy(alpha, strip_px=3)
    pct_a0 = float((alpha <= 0.001).mean() * 100.0)
    pct_a1 = float((alpha >= 0.999).mean() * 100.0)

    metrics = {
        "t0": T0,
        "t1": T1,
        "despill_k": DESPILL_K,
        "feather_sigma": FEATHER_SIGMA,
        "enclosed_green_pockets_gt4px": pockets,
        "rim_greenness_mean_boundary_band": rim_mean,
        "rim_greenness_mean_interior": interior_mean,
        "border_occupancy_pct": occ,
        "pct_alpha_0": pct_a0,
        "pct_alpha_1": pct_a1,
    }
    with open(f"{OUTDIR}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
