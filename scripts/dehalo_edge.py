#!/usr/bin/env python3
"""dehalo_edge.py — deterministic post-key edge-decontamination for RGBA images
produced by scripts/white_key.py (binary alpha + 0.8px feather, bg was pure
#FFFFFF). white_key's feather blends true foreground color with opaque WHITE
in a thin fringe ring; this leaves an opaque white-contaminated halo along the
silhouette edge even where alpha itself looks fine. This tool replaces every
boundary-band pixel's RGB with a SMOOTHED nearest-interior donor color (no
per-pixel accept/reject — coherence across the band beats per-pixel accuracy,
and a per-pixel reconstruction-error gate produces a speckled patchwork of
fixed/unfixed pixels), then re-solves alpha from that donor color and smooths
alpha within the band too, with an alpha-monotonicity floor (rises toward
opaque as distance-into-foreground grows) so the alpha re-solve can't punch
spurious near-transparent speckle holes deep inside the band. Interior pixels
outside the band stay byte-identical.

Adapted from tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py
decontaminate_boundary_rgb (same joint RGB/alpha re-solve idea), simplified
into a standalone CLI keyed to white_key's binary-alpha+feather output.

Usage:
  .venv-gen/bin/python scripts/dehalo_edge.py --image IN.png --out OUT.png \
      [--band 2] [--check]
"""
import argparse
import json
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def dehalo_edge(rgba: np.ndarray, band_px=2, smooth_sigma=1.0, alpha_smooth_sigma=0.8):
    """rgba: HxWx4 uint8. Returns (out_rgba uint8, metrics dict, band, applied_mask)."""
    h, w, _ = rgba.shape
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3].astype(np.float32)

    fg = alpha > 128
    # boundary band: fg pixels within band_px of non-fg (via distance transform on fg)
    fg_dist = ndi.distance_transform_edt(fg)
    band = fg & (fg_dist <= band_px)

    metrics = {
        "band_px": int(band.sum()),
        "applied_px": 0,
        "near_white_donor_px": 0,
    }

    out_rgb = rgb.copy()
    out_alpha = alpha.copy()

    # interior = fg eroded by (band_px+1) — donor source, no color eligibility filter
    interior = ndi.binary_erosion(fg, iterations=band_px + 1)
    if not np.any(band) or not np.any(interior):
        return _assemble(out_rgb, out_alpha), metrics, band, np.zeros_like(band)

    # donor field: nearest-interior color for every pixel, vectorized (no python loop)
    _, indices = ndi.distance_transform_edt(~interior, return_indices=True)
    D_raw = rgb[indices[0], indices[1], :]

    # smooth the donor field (3x3-ish gaussian, sigma=1) so adjacent band pixels get
    # coherent colors instead of a per-pixel patchwork
    D_smooth = np.empty_like(D_raw)
    for c in range(3):
        D_smooth[:, :, c] = ndi.gaussian_filter(D_raw[:, :, c], sigma=smooth_sigma)

    ys, xs = np.where(band)
    D = D_smooth[ys, xs, :]
    O = rgb[ys, xs, :]
    bg_white = 255.0

    valid_channel = D < 252.0
    denom = bg_white - D
    r = np.zeros_like(D)
    np.divide(O - D, denom, out=r, where=valid_channel)
    r = np.clip(r, 0.0, 1.0)

    has_valid = np.any(valid_channel, axis=1)
    r_masked = np.where(valid_channel, r, -np.inf)
    max_r = np.max(r_masked, axis=1)
    alpha_new = np.where(has_valid, 1.0 - max_r, alpha[ys, xs] / 255.0)
    alpha_new = np.clip(alpha_new, 0.0, 1.0)
    metrics["near_white_donor_px"] = int((~has_valid).sum())

    # smooth alpha_new WITHIN the band: extend band values to the whole plane via
    # nearest-band-pixel fill, gaussian-blur, then re-read at band locations —
    # this smooths using only the band's own values (no leakage from outside).
    alpha_new_full = np.zeros((h, w), dtype=np.float32)
    alpha_new_full[ys, xs] = alpha_new
    _, band_indices = ndi.distance_transform_edt(~band, return_indices=True)
    alpha_new_filled = alpha_new_full[band_indices[0], band_indices[1]]
    alpha_new_smooth = ndi.gaussian_filter(alpha_new_filled, sigma=alpha_smooth_sigma)

    # alpha monotonicity floor: the alpha re-solve can punch spurious near-transparent
    # speckle holes deep inside the band (pale observed pixel + more-saturated smoothed
    # donor -> low alpha) even though those pixels are well inside the true silhouette.
    # d = distance (px) from the transparent background; band's outermost ring (d≈1)
    # can go fully soft, but the innermost ring (d≈band_px) floors near-opaque.
    d = fg_dist[ys, xs]
    alpha_floor = np.clip((d - 0.5) / band_px, 0.0, 1.0)
    alpha_new_floored = np.maximum(alpha_new_smooth[ys, xs], alpha_floor)

    # apply: RGB of ALL band pixels := smoothed donor field, no exceptions
    out_rgb[ys, xs, :] = D
    new_alpha_8 = np.round(alpha_new_floored * 255.0)
    out_alpha[ys, xs] = np.minimum(alpha[ys, xs], new_alpha_8)

    applied_mask = np.zeros((h, w), dtype=bool)
    applied_mask[ys, xs] = True
    metrics["applied_px"] = int(band.sum())

    return _assemble(out_rgb, out_alpha), metrics, band, applied_mask


def _assemble(rgb, alpha):
    rgb = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    alpha = np.clip(np.round(alpha), 0, 255).astype(np.uint8)
    return np.dstack([rgb, alpha])


def halo_score(rgba: np.ndarray, band: np.ndarray):
    """Composite over black, then measure min-RGB weighted by alpha in the band —
    a contaminated (whitish) pixel scores high even if alpha itself looks ok."""
    if not np.any(band):
        return {"mean": 0.0, "p95": 0.0}
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    min_rgb = rgb.min(axis=2)
    weighted = min_rgb * alpha
    vals = weighted[band]
    return {"mean": float(vals.mean()), "p95": float(np.percentile(vals, 95))}


def composite(rgba: np.ndarray, bg):
    h, w, _ = rgba.shape
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bg_arr = np.array(bg, dtype=np.float32)
    out = rgb * alpha + bg_arr[None, None, :] * (1.0 - alpha)
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--band", type=int, default=2, help="boundary band width in px")
    ap.add_argument("--smooth-sigma", type=float, default=1.0, help="gaussian sigma for donor-field smoothing")
    ap.add_argument("--alpha-smooth-sigma", type=float, default=0.8, help="gaussian sigma for in-band alpha smoothing")
    ap.add_argument("--check", action="store_true", help="write _magenta.png and _darkcomp.png composites")
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGBA")
    src = np.asarray(im)
    if src.shape[2] != 4:
        print(f"[dehalo_edge] ERROR: {a.image} has no alpha channel", file=sys.stderr)
        sys.exit(1)

    out, metrics, band, applied = dehalo_edge(
        src, band_px=a.band, smooth_sigma=a.smooth_sigma,
        alpha_smooth_sigma=a.alpha_smooth_sigma,
    )

    # interior-untouched check: nothing outside the band may change
    outside_band = ~band
    changed_px = np.any(out != src, axis=2)
    changed_outside = int((changed_px & outside_band).sum())
    assert changed_outside == 0, (
        f"dehalo_edge changed {changed_outside} pixel(s) outside the boundary band"
    )

    before_score = halo_score(src, band)
    after_score = halo_score(out, band)
    metrics["halo_score_before"] = before_score
    metrics["halo_score_after"] = after_score
    metrics["interior_untouched"] = True

    Image.fromarray(out, "RGBA").save(a.out)
    print(json.dumps(metrics, indent=2))

    if a.check:
        magenta = composite(out, (255, 0, 255))
        Image.fromarray(magenta, "RGB").save(a.out.replace(".png", "_magenta.png"))
        darkcomp = composite(out, (0x11, 0x11, 0x11))
        Image.fromarray(darkcomp, "RGB").save(a.out.replace(".png", "_darkcomp.png"))


if __name__ == "__main__":
    main()
