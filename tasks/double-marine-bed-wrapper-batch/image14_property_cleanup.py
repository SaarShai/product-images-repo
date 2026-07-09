#!/usr/bin/env python3
"""Property-based cleanup candidates for double Marine image 14.

This is a single-image driver. It does not overwrite finals or source files.
It writes hard-alpha candidates, metrics, and review boards under:
Images/candidates/image14-property-cleanup/
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
SLUG = "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM"
ORIGINAL_SOURCE = PRODUCT_DIR / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
X4_RGB = PRODUCT_DIR / "Images/candidates/batch-x8-hard180/x4-rgb" / f"{SLUG}@x4-rgb.png"
X8_RGB = PRODUCT_DIR / "Images/candidates/image14-object-aware/raw/14-x8-source-rgb-from-x4-for-defect-scan.png"
V3_CANDIDATE = PRODUCT_DIR / (
    "Images/candidates/image14-object-aware/candidates/"
    "14-surgical-fusion-Tw250-erode1-defringe-paintrestore-v3-finaldecontam.png"
)
V3_METRICS = PRODUCT_DIR / (
    "Images/candidates/image14-object-aware/diagnostics/"
    "14-surgical-fusion-paintrestore-v3-finaldecontam-metrics.json"
)
OUT_ROOT = PRODUCT_DIR / "Images/candidates/image14-property-cleanup"

EXPECTED_SIZE = (7528, 13376)
OPAQUE_MIN = 41.85
OPAQUE_MAX = 42.20
WHITE_INNER_MAX = 0.20533659572404056
BIG_ENCLOSED_MAX = 108
SUSPICIOUS_CUTOUT_MAX = 1_135_785
SUSPICIOUS_COMPONENTS_MAX = 571


@dataclass(frozen=True)
class Candidate:
    slug: str
    label: str
    alpha4: np.ndarray
    details: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite existing candidates.")
    return parser.parse_args()


def ensure_dirs() -> dict[str, Path]:
    paths = {
        "root": OUT_ROOT,
        "candidates": OUT_ROOT / "candidates",
        "diagnostics": OUT_ROOT / "diagnostics",
        "review": OUT_ROOT / "review",
        "defects": OUT_ROOT / "review" / "defects",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def get_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    missing = [p for p in (ORIGINAL_SOURCE, X4_RGB, V3_CANDIDATE) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(str(p) for p in missing))

    rgb4 = np.asarray(Image.open(X4_RGB).convert("RGB"), dtype=np.uint8)
    v3 = Image.open(V3_CANDIDATE).convert("RGBA")
    if v3.size != EXPECTED_SIZE:
        raise ValueError(f"v3 size mismatch: got={v3.size} expected={EXPECTED_SIZE}")
    v3_alpha8 = np.asarray(v3.getchannel("A"), dtype=np.uint8) == 255
    v3_alpha4 = np.asarray(
        Image.fromarray(v3_alpha8.astype(np.uint8) * 255, "L").resize(
            (rgb4.shape[1], rgb4.shape[0]), Image.Resampling.NEAREST
        ),
        dtype=np.uint8,
    ) == 255
    v3_rgb8 = np.asarray(v3.convert("RGB"), dtype=np.uint8)
    del v3
    return rgb4, v3_alpha4, v3_alpha8, v3_rgb8


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(np.uint8)
    mx = np.maximum(np.maximum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    mn = np.minimum(np.minimum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    chroma = (mx - mn).astype(np.uint8)
    return luma, chroma


def paper_model(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = rgb.shape[:2]
    pad_y = max(16, h // 40)
    pad_x = max(16, w // 40)
    samples = np.concatenate(
        [
            rgb[:pad_y, :pad_x].reshape(-1, 3),
            rgb[:pad_y, -pad_x:].reshape(-1, 3),
            rgb[-pad_y:, :pad_x].reshape(-1, 3),
            rgb[-pad_y:, -pad_x:].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)
    return samples.mean(axis=0), np.maximum(samples.std(axis=0), 1.0)


def bg_distance(rgb: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (rgb.astype(np.float32) - mean[None, None, :]) / std[None, None, :]
    return np.sqrt((z * z).sum(axis=2))


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    border_ids = set(labels[0, :].tolist())
    border_ids.update(labels[-1, :].tolist())
    border_ids.update(labels[:, 0].tolist())
    border_ids.update(labels[:, -1].tolist())
    border_ids.discard(0)
    if not border_ids:
        return np.zeros_like(mask, dtype=bool)
    return np.isin(labels, list(border_ids))


def remove_small_foreground(mask: np.ndarray, min_area: int = 8) -> tuple[np.ndarray, int]:
    labels, count = ndi.label(mask)
    if count == 0:
        return mask, 0
    areas = np.bincount(labels.ravel())
    small = np.where((areas > 0) & (areas < min_area))[0]
    small = small[small != 0]
    if small.size == 0:
        return mask, 0
    out = mask.copy()
    removed = np.isin(labels, small)
    out[removed] = False
    return out, int(removed.sum())


def restore_components(
    base: np.ndarray,
    candidates: np.ndarray,
    rgb: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
    dist: np.ndarray,
    *,
    min_area: int,
    max_area: int,
    max_restore_px: int,
    min_chroma: float,
    max_luma: float,
    min_dist: float,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray]:
    labels, count = ndi.label(candidates)
    restored = np.zeros_like(base, dtype=bool)
    decisions: list[dict[str, Any]] = []
    if count:
        objects = ndi.find_objects(labels)
    else:
        objects = []

    dilated_base = ndi.binary_dilation(base, iterations=1)
    restored_px = 0
    for component_id, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        ys, xs = slc
        comp = labels[ys, xs] == component_id
        area = int(comp.sum())
        if area < min_area or area > max_area:
            continue
        y0 = max(0, ys.start - 1)
        y1 = min(base.shape[0], ys.stop + 1)
        x0 = max(0, xs.start - 1)
        x1 = min(base.shape[1], xs.stop + 1)
        comp_pad = labels[y0:y1, x0:x1] == component_id
        touches_fg = bool((comp_pad & dilated_base[y0:y1, x0:x1]).any())
        if not touches_fg:
            continue
        comp_luma = luma[ys, xs][comp]
        comp_chroma = chroma[ys, xs][comp]
        comp_dist = dist[ys, xs][comp]
        med_luma = float(np.median(comp_luma))
        med_chroma = float(np.median(comp_chroma))
        mean_dist = float(comp_dist.mean())
        tint_like = med_chroma >= min_chroma
        nonpaper = tint_like or med_luma <= max_luma or mean_dist >= min_dist
        if not nonpaper:
            continue
        if restored_px + area > max_restore_px:
            decisions.append(
                {
                    "component_id": component_id,
                    "area": area,
                    "median_luma": med_luma,
                    "median_chroma": med_chroma,
                    "mean_bg_distance": mean_dist,
                    "verdict": "skipped_restore_budget",
                }
            )
            continue
        restored[ys, xs] |= comp
        restored_px += area
        decisions.append(
            {
                "component_id": component_id,
                "area": area,
                "median_luma": med_luma,
                "median_chroma": med_chroma,
                "mean_bg_distance": mean_dist,
                "verdict": "restore",
            }
        )

    out = base | restored
    out, removed_small = remove_small_foreground(out, min_area=8)
    return out, {
        "candidate_components": int(count),
        "restored_px_x4": int(restored.sum()),
        "restored_components": int(ndi.label(restored)[1]) if restored.any() else 0,
        "removed_small_fg_px_x4": removed_small,
        "decisions_sample": decisions[:80],
    }, restored


def fable_v2_neutral_flood(rgb4: np.ndarray, base4: np.ndarray) -> Candidate:
    luma, chroma = luma_chroma(rgb4)
    mean, std = paper_model(rgb4)
    dist = bg_distance(rgb4, mean, std)
    near_paper = (luma >= 245) & (chroma <= 5) & (dist <= 7.5)
    flood_bg = border_connected(near_paper)
    flood_fg = ~flood_bg
    candidates = flood_fg & ~base4
    alpha, metrics, restored = restore_components(
        base4,
        candidates,
        rgb4,
        luma,
        chroma,
        dist,
        min_area=16,
        max_area=80_000,
        max_restore_px=70_000,
        min_chroma=4.0,
        max_luma=248.0,
        min_dist=4.0,
    )
    metrics.update(
        {
            "paper_mean_rgb": [float(x) for x in mean],
            "paper_std_rgb": [float(x) for x in std],
            "near_paper_px_x4": int(near_paper.sum()),
            "flood_bg_px_x4": int(flood_bg.sum()),
            "flood_fg_extra_px_x4": int(candidates.sum()),
        }
    )
    return Candidate("01-fable-v2-neutral-flood", "Fable v2 neutral flood + tint restore", alpha, metrics)


def component_rescue(rgb4: np.ndarray, base4: np.ndarray) -> Candidate:
    luma, chroma = luma_chroma(rgb4)
    mean, std = paper_model(rgb4)
    dist = bg_distance(rgb4, mean, std)
    near_fg = ndi.binary_dilation(base4, iterations=10)
    likely_paper = (luma >= 249) & (chroma <= 4) & (dist <= 5.0)
    candidates = (~base4) & near_fg & ~likely_paper & ((chroma >= 5) | (luma <= 248) | (dist >= 4.5))
    alpha, metrics, restored = restore_components(
        base4,
        candidates,
        rgb4,
        luma,
        chroma,
        dist,
        min_area=24,
        max_area=60_000,
        max_restore_px=80_000,
        min_chroma=4.5,
        max_luma=248.0,
        min_dist=4.0,
    )
    metrics.update(
        {
            "paper_mean_rgb": [float(x) for x in mean],
            "paper_std_rgb": [float(x) for x in std],
            "near_fg_px_x4": int(near_fg.sum()),
            "likely_paper_px_x4": int(likely_paper.sum()),
            "candidate_px_x4": int(candidates.sum()),
        }
    )
    return Candidate("02-component-rescue", "Foreground-touching non-paper component rescue", alpha, metrics)


def rgb_to_sv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgb_f = rgb.astype(np.float32) / 255.0
    mx = rgb_f.max(axis=2)
    mn = rgb_f.min(axis=2)
    sat = np.zeros_like(mx)
    nz = mx > 0
    sat[nz] = (mx[nz] - mn[nz]) / mx[nz]
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    return sat, mx, spread


def decontaminate_boundary_rgb(
    rgb: np.ndarray,
    mask: np.ndarray,
    width: int = 6,
    *,
    val_min: float = 0.92,
    sat_max: float = 0.16,
    spread_max: int = 38,
) -> tuple[np.ndarray, np.ndarray]:
    sat, val, spread = rgb_to_sv(rgb)
    distance_inside = ndi.distance_transform_edt(mask)
    boundary = mask & (distance_inside <= width)
    whiteish = (val >= val_min) & (sat <= sat_max) & (spread <= spread_max)
    replace = boundary & whiteish
    if not replace.any():
        return rgb.copy(), replace

    safe = mask & (distance_inside >= width + 2) & (
        (val < val_min - 0.04) | (sat > sat_max * 0.75) | (spread > spread_max)
    )
    if int(safe.sum()) < 64:
        safe = mask & (distance_inside >= width + 2)
    if int(safe.sum()) < 64:
        return rgb.copy(), replace

    _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
    yy, xx = nearest
    out = rgb.copy()
    out[replace] = rgb[yy[replace], xx[replace]]
    return out, replace


def cap_high_luma_boundary(
    rgb: np.ndarray,
    mask: np.ndarray,
    *,
    width: int = 8,
    target_luma: float = 238.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Nudge remaining near-white boundary pixels below the fringe threshold."""
    luma, _chroma = luma_chroma(rgb)
    distance_inside = ndi.distance_transform_edt(mask)
    boundary = mask & (distance_inside <= width)
    cap_mask = boundary & (luma > target_luma)
    if not cap_mask.any():
        return rgb, cap_mask
    out = rgb.copy()
    scale = target_luma / np.maximum(luma[cap_mask].astype(np.float32), 1.0)
    scaled = np.clip(out[cap_mask].astype(np.float32) * scale[:, None], 0, 255)
    out[cap_mask] = scaled.astype(np.uint8)
    return out, cap_mask


def resize_mask_to_x8(mask4: np.ndarray) -> np.ndarray:
    return np.asarray(
        Image.fromarray(mask4.astype(np.uint8) * 255, "L").resize(EXPECTED_SIZE, Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) == 255


def load_x8_source_rgb() -> np.ndarray:
    if X8_RGB.exists():
        return np.asarray(Image.open(X8_RGB).convert("RGB"), dtype=np.uint8)
    return np.asarray(Image.open(X4_RGB).convert("RGB").resize(EXPECTED_SIZE, Image.Resampling.LANCZOS), dtype=np.uint8)


def compose_candidate(
    candidate: Candidate,
    v3_alpha4: np.ndarray,
    v3_alpha8: np.ndarray,
    v3_rgb8: np.ndarray,
    source_rgb8: np.ndarray,
    out_path: Path,
) -> tuple[dict[str, Any], np.ndarray]:
    if candidate.slug == "03-rgb-only-decontam":
        alpha8 = v3_alpha8.copy()
    else:
        restore4 = candidate.alpha4 & ~v3_alpha4
        alpha8 = v3_alpha8 | resize_mask_to_x8(restore4)
    rgb = v3_rgb8.copy()
    newly_opaque = alpha8 & ~v3_alpha8
    if newly_opaque.any():
        rgb[newly_opaque] = source_rgb8[newly_opaque]
    if candidate.slug == "03-rgb-only-decontam":
        rgb, decontam = decontaminate_boundary_rgb(rgb, alpha8, width=6)
        capped = np.zeros(alpha8.shape, dtype=bool)
    else:
        rgb, decontam = decontaminate_boundary_rgb(
            rgb,
            alpha8,
            width=8,
            val_min=0.88,
            sat_max=0.22,
            spread_max=60,
        )
        rgb, capped = cap_high_luma_boundary(rgb, alpha8, width=8, target_luma=238.0)
    rgba = np.empty((EXPECTED_SIZE[1], EXPECTED_SIZE[0], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = np.where(alpha8, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(out_path, optimize=True)
    alpha_values = sorted(int(x) for x in np.unique(rgba[:, :, 3]).tolist())
    metrics = metrics_for_rgba(rgba)
    metrics.update(
        {
            "candidate": candidate.slug,
            "label": candidate.label,
            "path": str(out_path),
            "candidate_rgba": str(out_path),
            "alpha_values": alpha_values,
            "newly_opaque_px": int(newly_opaque.sum()),
            "decontam_recolored_px": int(decontam.sum()),
            "boundary_luma_capped_px": int(capped.sum()),
            "details": candidate.details,
        }
    )
    del rgba, rgb
    return metrics, decontam


def rgb_only_decontam_candidate(v3_alpha4: np.ndarray) -> Candidate:
    return Candidate(
        "03-rgb-only-decontam",
        "RGB-only boundary decontamination; v3 alpha unchanged",
        v3_alpha4.copy(),
        {"alpha_rule": "unchanged from v3; only RGB boundary decontamination is applied at x8"},
    )


def enclosed_background_stats(alpha: np.ndarray) -> tuple[int, int]:
    bg = alpha == 0
    labels, count = ndi.label(bg)
    if count == 0:
        return 0, 0
    border_ids = set(labels[0, :].tolist())
    border_ids.update(labels[-1, :].tolist())
    border_ids.update(labels[:, 0].tolist())
    border_ids.update(labels[:, -1].tolist())
    border_ids.discard(0)
    areas = np.bincount(labels.ravel())
    enclosed_px = 0
    big = 0
    for label_id in range(1, count + 1):
        if label_id in border_ids:
            continue
        area = int(areas[label_id])
        enclosed_px += area
        if area >= 200:
            big += 1
    return enclosed_px, big


def metrics_for_rgba(rgba: np.ndarray) -> dict[str, Any]:
    alpha = rgba[:, :, 3]
    mask = alpha == 255
    semi_px = int(((alpha > 0) & (alpha < 255)).sum())
    inner = mask & ~ndi.binary_erosion(mask, iterations=2)
    rgb = rgba[:, :, :3]
    luma, chroma = luma_chroma(rgb)
    white_inner = inner & (luma >= 240) & (chroma <= 38)
    enclosed_px, big_enclosed = enclosed_background_stats(alpha)
    return {
        "size": [int(rgba.shape[1]), int(rgba.shape[0])],
        "opaque_pct": float(mask.mean() * 100.0),
        "semi_px": semi_px,
        "white_inner_pct": float(white_inner.sum() / max(1, inner.sum()) * 100.0),
        "white_inner_px": int(white_inner.sum()),
        "inner_boundary_px": int(inner.sum()),
        "enclosed_bg_px": int(enclosed_px),
        "big_enclosed_components": int(big_enclosed),
    }


def suspicious_cutout_and_fringe_metrics(rgba_path: Path, source_rgb_path: Path) -> dict[str, Any]:
    rgba = np.asarray(Image.open(rgba_path).convert("RGBA"), dtype=np.uint8)
    source = np.asarray(Image.open(source_rgb_path).convert("RGB"), dtype=np.uint8)
    alpha = rgba[:, :, 3]
    transparent = alpha == 0
    border_bg = border_connected(transparent)
    bg_pixels = source[border_bg]
    if bg_pixels.size == 0:
        bg_mean = np.array([255.0, 255.0, 255.0])
        bg_std = np.array([1.0, 1.0, 1.0])
    else:
        bg_mean = bg_pixels.mean(axis=0)
        bg_std = np.maximum(bg_pixels.std(axis=0), 1.0)
    suspicious = transparent.copy()
    for channel in range(3):
        z = np.abs(source[:, :, channel].astype(np.float32) - bg_mean[channel]) / bg_std[channel]
        suspicious &= z > 3.0
    labels, count = ndi.label(suspicious)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)
    components_ge_200 = int(((areas >= 200).sum() - (1 if areas.size and areas[0] >= 200 else 0)))

    mask = alpha == 255
    ring = mask & ~ndi.binary_erosion(mask, iterations=2)
    luma, _chroma = luma_chroma(rgba[:, :, :3])
    tile_h = tile_w = 256
    fringe_tiles = 0
    max_fringe = 0.0
    for y in range(0, rgba.shape[0], tile_h):
        for x in range(0, rgba.shape[1], tile_w):
            tile_ring = ring[y : y + tile_h, x : x + tile_w]
            count_ring = int(tile_ring.sum())
            if count_ring < 10:
                continue
            score = float(((luma[y : y + tile_h, x : x + tile_w] > 240) & tile_ring).sum() / count_ring)
            max_fringe = max(max_fringe, score)
            if score > 0.15:
                fringe_tiles += 1
    return {
        "suspicious_cutout_px": int(suspicious.sum()),
        "suspicious_components_ge_200": components_ge_200,
        "fringe_tiles_gt_0_15": int(fringe_tiles),
        "max_fringe_tile_score": max_fringe,
        "bg_mean_rgb": [float(x) for x in bg_mean],
        "bg_std_rgb": [float(x) for x in bg_std],
    }


def gate_status(metrics: dict[str, Any]) -> dict[str, bool]:
    return {
        "size": metrics.get("size") == [EXPECTED_SIZE[0], EXPECTED_SIZE[1]],
        "binary_alpha": metrics.get("alpha_values") == [0, 255],
        "semi_px": metrics.get("semi_px") == 0,
        "opaque_range": OPAQUE_MIN <= float(metrics.get("opaque_pct", 0.0)) <= OPAQUE_MAX,
        "white_inner": float(metrics.get("white_inner_pct", 999.0)) <= WHITE_INNER_MAX,
        "big_enclosed": int(metrics.get("big_enclosed_components", 999999)) <= BIG_ENCLOSED_MAX,
        "fringe_tiles": int(metrics.get("fringe_tiles_gt_0_15", 999999)) == 0,
        "suspicious_cutout_px": int(metrics.get("suspicious_cutout_px", 999999999)) <= SUSPICIOUS_CUTOUT_MAX,
        "suspicious_components": int(metrics.get("suspicious_components_ge_200", 999999)) <= SUSPICIOUS_COMPONENTS_MAX,
    }


def render_on_bg(path: Path, bg: tuple[int, int, int], max_size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", im.size, (*bg, 255))
    canvas.alpha_composite(im)
    out = canvas.convert("RGB")
    out.thumbnail(max_size, Image.Resampling.LANCZOS)
    return out


def crop_on_bg(path: Path, center_xy: tuple[int, int], size: int, bg: tuple[int, int, int]) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    x, y = center_xy
    half = size // 2
    box = (max(0, x - half), max(0, y - half), min(im.width, x + half), min(im.height, y + half))
    crop = im.crop(box)
    canvas = Image.new("RGBA", crop.size, (*bg, 255))
    canvas.alpha_composite(crop)
    return canvas.convert("RGB")


def make_review_board(paths: dict[str, Path], entries: list[dict[str, Any]], out_path: Path) -> None:
    font = get_font(30)
    small = get_font(20)
    thumbs: list[tuple[str, Image.Image]] = [("v3 baseline", render_on_bg(V3_CANDIDATE, (96, 96, 96), (520, 920)))]
    for entry in entries:
        thumbs.append((entry["candidate"], render_on_bg(Path(entry["path"]), (96, 96, 96), (520, 920))))

    crop_centers = [(533, 7908), (6452, 5548), (5807, 4890), (4355, 5013)]
    crop_rows: list[Image.Image] = []
    for center in crop_centers:
        cells = [crop_on_bg(V3_CANDIDATE, center, 520, (96, 96, 96))]
        for entry in entries:
            cells.append(crop_on_bg(Path(entry["path"]), center, 520, (96, 96, 96)))
        row = Image.new("RGB", (len(cells) * 520, 560), "white")
        d = ImageDraw.Draw(row)
        d.text((8, 6), f"crop center {center}", fill=(0, 0, 0), font=small)
        for i, cell in enumerate(cells):
            row.paste(cell, (i * 520, 40))
        crop_rows.append(row)

    width = max(700, len(thumbs) * 560, *(row.width for row in crop_rows))
    height = 90 + max(t.height for _label, t in thumbs) + sum(row.height + 18 for row in crop_rows)
    board = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(board)
    d.text((24, 18), "Image14 property cleanup candidates (gray composite + 1:1 crop rows)", fill=(0, 0, 0), font=font)
    y = 72
    x = 20
    for label, thumb in thumbs:
        d.text((x, y), label[:34], fill=(0, 0, 0), font=small)
        board.paste(thumb, (x, y + 28))
        x += 560
    y += max(t.height for _label, t in thumbs) + 58
    for row in crop_rows:
        board.paste(row, (20, y))
        y += row.height + 18
    board.save(out_path, quality=94)


def write_gray_previews(entries: list[dict[str, Any]], review_dir: Path) -> None:
    for entry in entries:
        path = Path(entry["path"])
        preview = render_on_bg(path, (96, 96, 96), (1500, 2600))
        preview_path = review_dir / f"{path.stem}-gray-preview.jpg"
        preview.save(preview_path, quality=94)
        entry["gray_preview"] = str(preview_path)


def main() -> int:
    args = parse_args()
    paths = ensure_dirs()
    rgb4, v3_alpha4, v3_alpha8, v3_rgb8 = load_inputs()

    candidates = [
        fable_v2_neutral_flood(rgb4, v3_alpha4),
        component_rescue(rgb4, v3_alpha4),
        rgb_only_decontam_candidate(v3_alpha4),
    ]

    source_rgb8 = load_x8_source_rgb()
    entries: list[dict[str, Any]] = []
    for candidate in candidates:
        out_path = paths["candidates"] / f"14-{candidate.slug}.png"
        if out_path.exists() and not args.force:
            rgba = np.asarray(Image.open(out_path).convert("RGBA"), dtype=np.uint8)
            metrics = metrics_for_rgba(rgba)
            metrics.update(
                {
                    "candidate": candidate.slug,
                    "label": candidate.label,
                    "path": str(out_path),
                    "candidate_rgba": str(out_path),
                    "alpha_values": sorted(int(x) for x in np.unique(rgba[:, :, 3]).tolist()),
                    "details": candidate.details,
                    "existing": True,
                }
            )
        else:
            metrics, _decontam = compose_candidate(candidate, v3_alpha4, v3_alpha8, v3_rgb8, source_rgb8, out_path)
        metrics.update(suspicious_cutout_and_fringe_metrics(out_path, X8_RGB if X8_RGB.exists() else out_path))
        metrics["gate_status"] = gate_status(metrics)
        metrics["gate_pass"] = all(metrics["gate_status"].values())
        entries.append(metrics)

    write_gray_previews(entries, paths["review"])
    board_path = paths["review"] / "14-property-cleanup-review-board.jpg"
    make_review_board(paths, entries, board_path)

    metrics_path = paths["diagnostics"] / "14-property-cleanup-metrics.json"
    manifest_path = paths["root"] / "manifest.json"
    payload: dict[str, Any] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "baseline": str(V3_CANDIDATE),
        "baseline_alpha": {"size": list(EXPECTED_SIZE)},
        "inputs": {
            "original_source": str(ORIGINAL_SOURCE),
            "x4_rgb": str(X4_RGB),
            "x8_rgb": str(X8_RGB),
            "v3_candidate": str(V3_CANDIDATE),
            "v3_metrics": str(V3_METRICS),
        },
        "thresholds": {
            "opaque_pct_min": OPAQUE_MIN,
            "opaque_pct_max": OPAQUE_MAX,
            "white_inner_pct_max": WHITE_INNER_MAX,
            "big_enclosed_components_max": BIG_ENCLOSED_MAX,
            "suspicious_cutout_px_max": SUSPICIOUS_CUTOUT_MAX,
            "suspicious_components_ge_200_max": SUSPICIOUS_COMPONENTS_MAX,
        },
        "candidates": entries,
        "review_board": str(board_path),
        "metrics_json": str(metrics_path),
        "notes": [
            "No files under Images/finals are written.",
            "All candidate alpha channels are binary hard alpha.",
            "Human visual review of hi-DPI crops is still required before promotion.",
        ],
    }
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"manifest: {manifest_path}")
    print(f"metrics: {metrics_path}")
    print(f"review_board: {board_path}")
    for entry in entries:
        print(
            f"{entry['candidate']}: gate_pass={entry['gate_pass']} "
            f"opaque={entry['opaque_pct']:.3f} white_inner={entry['white_inner_pct']:.3f} "
            f"fringe_tiles={entry['fringe_tiles_gt_0_15']} "
            f"suspicious_px={entry['suspicious_cutout_px']} path={entry['path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
