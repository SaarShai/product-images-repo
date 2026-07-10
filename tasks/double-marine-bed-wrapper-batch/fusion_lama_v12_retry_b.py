#!/usr/bin/env python3
"""Corrective retry for fusion-lama-v12: reuse LaMa paper, stronger rim kill.

Tag b: raise soft thresholds + kill paper-like FG rim (white halo) using
paper-distance on silhouette band, independent of LaMa delta (which fails when
LaMa ghosts pale washes).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from fusion_lama_v12_mps import (
    PRODUCT,
    REPO,
    Params,
    build_erase_mask,
    composite_preview,
    make_review,
    paper_model,
    save_full,
    luma_chroma,
)

Image.MAX_IMAGE_PIXELS = None


def delta_alpha_b(
    rgb: np.ndarray,
    paper: np.ndarray,
    erase: np.ndarray,
    outer_paper: np.ndarray,
    p: Params,
) -> tuple[np.ndarray, np.ndarray, dict]:
    mean, _ = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    delta = np.abs(rgb.astype(np.float32) - paper.astype(np.float32)).max(axis=2)
    d_paper = np.sqrt(((rgb.astype(np.float32) - mean[None, None, :]) ** 2).sum(2))

    soft = np.clip((delta - p.soft_lo) / max(1e-6, (p.soft_hi - p.soft_lo)), 0.0, 1.0)
    soft[outer_paper] = 0.0
    soft[(~erase) & (delta < p.delta_thr)] = 0.0

    # Stronger: any near-paper pixel (low chroma + high luma + close to mean) → BG
    near_paper = (d_paper < 12.0) & (chroma < 10.0) & (luma > 235.0)
    soft[near_paper] = 0.0

    fg0 = soft >= 0.35
    if fg0.any():
        dist_in = ndi.distance_transform_edt(fg0)
        rim = fg0 & (dist_in <= 4)
        # Kill rim closer to paper than to saturated paint
        soft[rim & (d_paper < 18.0) & (chroma < 18.0)] = 0.0
        soft[rim & (d_paper < 10.0)] = 0.0
        # Soften remaining rim by paper proximity
        soft[rim] = soft[rim] * np.clip((d_paper[rim] - 6.0) / 20.0, 0.0, 1.0)

    fg = soft >= 0.5
    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_noise_area
        keep[0] = False
        fg = keep[labels]
        soft = soft * fg.astype(np.float32)

    alpha = soft.copy()
    rgb_out = rgb.copy().astype(np.float32)
    partial = (alpha > 0.02) & (alpha < 0.98)
    if partial.any():
        a = np.maximum(alpha[partial], 1e-3)[:, None]
        unb = (rgb[partial].astype(np.float32) - (1.0 - a) * mean[None, :]) / a
        rgb_out[partial] = np.clip(unb, 0, 255)
        # After unblend, if still near-white, drop
        still_luma = (
            0.299 * rgb_out[:, :, 0] + 0.587 * rgb_out[:, :, 1] + 0.114 * rgb_out[:, :, 2]
        )
        still_chr = rgb_out.max(2) - rgb_out.min(2)
        kill = partial & (still_luma > 245) & (still_chr < 12)
        alpha[kill] = 0.0

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(rgb_out, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)

    metrics = {
        "delta_mean_erase": float(delta[erase].mean()) if erase.any() else 0.0,
        "delta_p50_erase": float(np.median(delta[erase])) if erase.any() else 0.0,
        "delta_p90_erase": float(np.percentile(delta[erase], 90)) if erase.any() else 0.0,
        "opaque_pct": float(100.0 * (rgba[:, :, 3] == 255).mean()),
        "transparent_pct": float(100.0 * (rgba[:, :, 3] == 0).mean()),
        "semi_pct": float(100.0 * ((rgba[:, :, 3] > 0) & (rgba[:, :, 3] < 255)).mean()),
        "fg_px": int((rgba[:, :, 3] > 0).sum()),
        "near_paper_killed_px": int(near_paper.sum()),
    }
    return rgba, delta, metrics


def main() -> None:
    tag = "b"
    p = Params(
        lama_max_side=2048,
        erase_dilate=3,
        soft_lo=10.0,
        soft_hi=32.0,
        delta_thr=12.0,
        paper_sub_rim=4,
        paper_sub_thr=12.0,
    )

    out_dir = REPO / "Images/candidates/image14-research/fusion-lama-v12"
    paper_path = out_dir / "14-lama-v12-a-x4-paper-estimate.png"
    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    paper = np.asarray(Image.open(paper_path).convert("RGB"), dtype=np.uint8)
    erase, outer_paper, mask_meta = build_erase_mask(rgb, p)

    # Re-lock: paper outside erase = original
    paper = paper.copy()
    paper[~erase] = rgb[~erase]

    rgba, delta, delta_meta = delta_alpha_b(rgb, paper, erase, outer_paper, p)
    metrics = {
        **mask_meta,
        **delta_meta,
        "params": {
            "soft_lo": p.soft_lo,
            "soft_hi": p.soft_hi,
            "delta_thr": p.delta_thr,
            "note": "reuse tag-a LaMa paper; stronger near-paper + rim kill",
        },
        "tag": tag,
        "reused_paper": str(paper_path),
        "lama_seconds": 0.0,
        "device": "reuse",
    }

    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    stem = f"14-lama-v12-{tag}-x4"
    out_png = out_dir / f"{stem}.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    dvis = np.clip(delta / 40.0 * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(dvis, "L").save(out_dir / f"{stem}-delta.png")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    prefix = f"21-lama-v12-{tag}"
    save_full(review / f"{prefix}-full-gray.jpg", rgba, gray, 3600)
    save_full(review / f"{prefix}-full-magenta.jpg", rgba, mag, 3600)
    h = rgba.shape[0]
    save_full(review / f"{prefix}-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], 3600)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int):
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
    ]:
        make_review(review / f"{prefix}-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-lama-v12"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)
    (drive / f"{stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
