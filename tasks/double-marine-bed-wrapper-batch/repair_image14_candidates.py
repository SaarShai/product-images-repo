#!/usr/bin/env python3
"""Generate one-image mask repair candidates for double Marine image 14.

The script never overwrites source or final files. It writes reviewable
candidates under the product folder's Images/candidates/image14-repair/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

IMAGE_ROOT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
SLUG = "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM"
SOURCE = IMAGE_ROOT / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
FINAL = IMAGE_ROOT / "Images/finals" / f"{SLUG}@x8-bg-removed.png"
BATCH_CANDIDATES = IMAGE_ROOT / "Images/candidates/batch-x8-hard180"
X4_RGB = BATCH_CANDIDATES / "x4-rgb" / f"{SLUG}@x4-rgb.png"
X4_CUTOUT = BATCH_CANDIDATES / "x4-hard180" / f"{SLUG}@x4-hard180-colorrestore.png"
OUT_DIR = IMAGE_ROOT / "Images/candidates/image14-repair"
REVIEW_DIR = OUT_DIR / "review"


@dataclass
class Candidate:
    name: str
    label: str
    build: Callable[[np.ndarray], tuple[np.ndarray, dict]]
    dewhite: bool = False
    dewhite_strength: float = 0.0


def rgb_to_sv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    arr = rgb.astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    delta = mx - mn
    sat = np.zeros_like(mx)
    nz = mx > 0
    sat[nz] = delta[nz] / mx[nz]
    return (sat * 255.0).astype(np.uint8), (mx * 255.0).astype(np.uint8)


def remove_tiny_foreground(mask: np.ndarray, min_area: int = 4) -> tuple[np.ndarray, int, int]:
    labels, count = ndi.label(mask)
    if count == 0:
        return mask, 0, 0
    areas = np.bincount(labels.ravel())
    remove_labels = np.where((areas > 0) & (areas < min_area))[0]
    remove_labels = remove_labels[remove_labels != 0]
    if len(remove_labels) == 0:
        return mask, 0, 0
    remove = np.isin(labels, remove_labels)
    out = mask.copy()
    out[remove] = False
    return out, int(remove.sum()), int(len(remove_labels))


def colored_margin_restore(
    rgb: np.ndarray,
    mask: np.ndarray,
    saturation_threshold: int = 18,
    value_max: int = 214,
    dilate_px: int = 6,
    min_component_px: int = 256,
    max_pct: float = 0.55,
    max_components: int = 260,
) -> tuple[np.ndarray, dict, np.ndarray]:
    sat, val = rgb_to_sv(rgb)
    colored = (sat >= saturation_threshold) | (
        (val <= value_max) & (sat >= max(7, saturation_threshold // 2))
    )
    near_foreground = ndi.binary_dilation(mask, iterations=dilate_px)
    candidates = (~mask) & near_foreground & colored
    labels, raw_count = ndi.label(candidates)
    areas = np.bincount(labels.ravel()) if raw_count else np.array([], dtype=np.int64)
    if raw_count:
        keep_labels = np.where(areas >= min_component_px)[0]
        keep_labels = keep_labels[keep_labels != 0]
        restore = np.isin(labels, keep_labels)
        count = int(len(keep_labels))
    else:
        restore = candidates
        count = 0
    restore_px = int(restore.sum())
    restore_pct = restore_px / mask.size * 100.0
    applied = restore_px > 0 and restore_pct <= max_pct and count <= max_components
    out = mask.copy()
    if applied:
        out[restore] = True
    else:
        restore = np.zeros_like(mask, dtype=bool)
    return out, {
        "applied": bool(applied),
        "restored_px": int(restore.sum()),
        "candidate_pct": restore_pct,
        "candidate_components": count,
        "raw_candidate_components": int(raw_count),
    }, restore


def halo_trim(
    rgb: np.ndarray,
    raw_alpha: np.ndarray,
    mask: np.ndarray,
    val_min: int,
    sat_max: int,
    raw_max: int,
    boundary_px: int,
    min_component_px: int = 12,
) -> tuple[np.ndarray, dict, np.ndarray]:
    sat, val = rgb_to_sv(rgb)
    bg = ~mask
    boundary = mask & ndi.binary_dilation(bg, iterations=boundary_px)
    candidates = boundary & (val >= val_min) & (sat <= sat_max) & (raw_alpha <= raw_max)
    labels, count = ndi.label(candidates)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)
    if count:
        keep = np.where(areas >= min_component_px)[0]
        keep = keep[keep != 0]
        trim = np.isin(labels, keep)
    else:
        trim = candidates
    out = mask.copy()
    out[trim] = False
    return out, {
        "trimmed_px": int(trim.sum()),
        "raw_candidate_components": int(count),
        "kept_components": int(ndi.label(trim)[1]) if trim.any() else 0,
        "val_min": val_min,
        "sat_max": sat_max,
        "raw_max": raw_max,
        "boundary_px": boundary_px,
    }, trim


def confidence_restore(
    rgb: np.ndarray,
    raw_alpha: np.ndarray,
    base: np.ndarray,
    raw_min: int,
    sat_min: int,
    val_max: int,
    near_px: int,
    min_component_px: int,
    max_pct: float,
) -> tuple[np.ndarray, dict, np.ndarray]:
    sat, val = rgb_to_sv(rgb)
    near = ndi.binary_dilation(base, iterations=near_px)
    candidates = (~base) & near & (raw_alpha >= raw_min) & ((sat >= sat_min) | (val <= val_max))
    labels, count = ndi.label(candidates)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)
    if count:
        keep = np.where(areas >= min_component_px)[0]
        keep = keep[keep != 0]
        restore = np.isin(labels, keep)
    else:
        restore = candidates
    restore_pct = int(restore.sum()) / base.size * 100.0
    if restore_pct > max_pct:
        restore = np.zeros_like(base, dtype=bool)
    out = base.copy()
    out[restore] = True
    return out, {
        "restored_px": int(restore.sum()),
        "candidate_components": int(ndi.label(restore)[1]) if restore.any() else 0,
        "raw_candidate_components": int(count),
        "restore_pct": restore_pct,
        "raw_min": raw_min,
        "sat_min": sat_min,
        "val_max": val_max,
        "near_px": near_px,
    }, restore


def internal_component_restore(
    rgb: np.ndarray,
    raw_alpha: np.ndarray,
    mask: np.ndarray,
    raw_mean_min: float = 65.0,
    raw_frac_min: float = 0.18,
    min_area: int = 48,
    max_area: int = 42000,
) -> tuple[np.ndarray, dict, np.ndarray]:
    sat, val = rgb_to_sv(rgb)
    bg = ~mask
    labels, count = ndi.label(bg)
    if count == 0:
        return mask.copy(), {"restored_px": 0, "components": 0}, np.zeros_like(mask, dtype=bool)
    border = set(np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])).tolist())
    areas = np.bincount(labels.ravel())
    restore = np.zeros_like(mask, dtype=bool)
    kept = 0
    for lab in range(1, count + 1):
        if lab in border:
            continue
        area = int(areas[lab])
        if area < min_area or area > max_area:
            continue
        region = labels == lab
        raw_vals = raw_alpha[region]
        sat_vals = sat[region]
        val_vals = val[region]
        raw_mean = float(raw_vals.mean())
        raw_frac = float((raw_vals >= 64).mean())
        color_hint = float(sat_vals.mean()) >= 7.0 or float(val_vals.mean()) <= 250.0
        if color_hint and (raw_mean >= raw_mean_min or raw_frac >= raw_frac_min):
            restore[region] = True
            kept += 1
    out = mask.copy()
    out[restore] = True
    return out, {
        "restored_px": int(restore.sum()),
        "components": kept,
        "raw_mean_min": raw_mean_min,
        "raw_frac_min": raw_frac_min,
        "min_area": min_area,
        "max_area": max_area,
    }, restore


def alpha_metrics(mask: np.ndarray) -> dict:
    labels, components = ndi.label(mask)
    areas = np.bincount(labels.ravel()) if components else np.array([], dtype=np.int64)
    return {
        "opaque_px": int(mask.sum()),
        "transparent_px": int(mask.size - mask.sum()),
        "opaque_pct": float(mask.sum() / mask.size * 100.0),
        "transparent_pct": float((mask.size - mask.sum()) / mask.size * 100.0),
        "semi_px": 0,
        "semi_pct": 0.0,
        "foreground_components": int(components),
        "small_foreground_components_lt64": int(((areas[1:] < 64) & (areas[1:] > 0)).sum()) if areas.size else 0,
    }


def x4_halo_score(rgb: np.ndarray, raw_alpha: np.ndarray, mask: np.ndarray) -> int:
    sat, val = rgb_to_sv(rgb)
    boundary = mask & ndi.binary_dilation(~mask, iterations=3)
    return int((boundary & (val >= 245) & (sat <= 30) & (raw_alpha <= 235)).sum())


def load_raw_alpha(x4_rgb: Path, cache: Path) -> np.ndarray:
    if cache.exists():
        return np.asarray(Image.open(cache).convert("L"))
    from rembg import new_session, remove

    session = new_session("bria-rmbg")
    rgb_img = Image.open(x4_rgb).convert("RGB")
    raw = remove(rgb_img.convert("RGBA"), session=session)
    alpha = raw.getchannel("A")
    cache.parent.mkdir(parents=True, exist_ok=True)
    alpha.save(cache)
    return np.asarray(alpha)


def save_x8_candidate(final_rgb: Image.Image, x4_mask: np.ndarray, out_path: Path) -> None:
    alpha_x4 = Image.fromarray(np.where(x4_mask, 255, 0).astype(np.uint8), "L")
    alpha_x8 = alpha_x4.resize(final_rgb.size, Image.Resampling.NEAREST)
    out = final_rgb.convert("RGBA")
    out.putalpha(alpha_x8)
    out.save(out_path, compress_level=3)


def dewhite_rgb_for_mask(
    final_rgb: Image.Image,
    rgb_x4: np.ndarray,
    raw_alpha: np.ndarray,
    mask_x4: np.ndarray,
    strength: float,
    boundary_px: int = 4,
    val_min: int = 242,
    sat_max: int = 34,
    raw_max: int = 244,
) -> tuple[Image.Image, dict]:
    """Recolor likely matte contamination without changing the alpha mask."""
    sat, val = rgb_to_sv(rgb_x4)
    halo_x4 = (
        mask_x4
        & ndi.binary_dilation(~mask_x4, iterations=boundary_px)
        & (val >= val_min)
        & (sat <= sat_max)
        & (raw_alpha <= raw_max)
    )
    good = mask_x4 & ~halo_x4 & ((sat >= 12) | (val <= 248))
    if not good.any() or not halo_x4.any():
        return final_rgb, {
            "applied": False,
            "dewhite_px_x4": int(halo_x4.sum()),
            "reason": "missing halo or donor pixels",
        }

    indices = ndi.distance_transform_edt(~good, return_distances=False, return_indices=True)
    repaired_x4 = rgb_x4.copy()
    donor = rgb_x4[indices[0], indices[1]]
    old = repaired_x4[halo_x4].astype(np.float32)
    new = donor[halo_x4].astype(np.float32)
    repaired_x4[halo_x4] = np.clip(old * (1.0 - strength) + new * strength, 0, 255).astype(np.uint8)

    repaired_x8 = Image.fromarray(repaired_x4, "RGB").resize(final_rgb.size, Image.Resampling.BICUBIC)
    halo_img = Image.fromarray(halo_x4.astype(np.uint8) * 255, "L").resize(final_rgb.size, Image.Resampling.NEAREST)
    base = np.asarray(final_rgb.convert("RGB")).copy()
    rep = np.asarray(repaired_x8)
    halo = np.asarray(halo_img) > 0
    base[halo] = rep[halo]
    return Image.fromarray(base, "RGB"), {
        "applied": True,
        "dewhite_px_x4": int(halo_x4.sum()),
        "dewhite_px_x8": int(halo.sum()),
        "strength": strength,
        "boundary_px": boundary_px,
        "val_min": val_min,
        "sat_max": sat_max,
        "raw_max": raw_max,
    }


def composite_on_gray(path: Path, max_side: int = 1600) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    scale = min(1.0, max_side / max(im.size))
    if scale < 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", im.size, (96, 96, 96, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def make_contact(candidates: list[dict], out_path: Path) -> None:
    thumbs = []
    for item in candidates:
        img = composite_on_gray(Path(item["path"]), max_side=900)
        tile = Image.new("RGB", (520, 840), (226, 226, 226))
        img.thumbnail((500, 760), Image.Resampling.LANCZOS)
        tile.paste(img, ((520 - img.width) // 2, 48 + (760 - img.height) // 2))
        thumbs.append((item["label"], tile))
    sheet = Image.new("RGB", (520 * len(thumbs), 840), (236, 236, 236))
    draw = ImageDraw.Draw(sheet)
    font = get_font(18)
    for idx, (label, tile) in enumerate(thumbs):
        x = idx * 520
        sheet.paste(tile, (x, 0))
        draw.rectangle((x, 0, x + 520, 42), fill=(255, 255, 255))
        draw.text((x + 10, 12), label[:54], fill=(0, 0, 0), font=font)
    sheet.save(out_path, quality=92)


def get_font(size: int):
    for p in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def pick_regions(rgb: np.ndarray, raw_alpha: np.ndarray, base: np.ndarray, candidate_masks: dict[str, np.ndarray]) -> list[tuple[int, int, int, int, str]]:
    regions: list[tuple[int, int, int, int, str, int]] = []
    union_restore = np.zeros_like(base, dtype=bool)
    union_trim = np.zeros_like(base, dtype=bool)
    for mask in candidate_masks.values():
        union_restore |= mask & ~base
        union_trim |= base & ~mask

    for label_name, change in (("restore", union_restore), ("trim", union_trim)):
        labels, count = ndi.label(change)
        areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)
        for lab in range(1, count + 1):
            area = int(areas[lab])
            if area < 100:
                continue
            ys, xs = np.where(labels == lab)
            x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
            regions.append((x0, y0, x1, y1, label_name, area))

    sat, val = rgb_to_sv(rgb)
    halo = base & ndi.binary_dilation(~base, iterations=3) & (val >= 245) & (sat <= 30) & (raw_alpha <= 235)
    labels, count = ndi.label(halo)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)
    for lab in range(1, count + 1):
        area = int(areas[lab])
        if area < 180:
            continue
        ys, xs = np.where(labels == lab)
        regions.append((int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1), "halo", area))

    regions.sort(key=lambda r: r[5], reverse=True)
    selected: list[tuple[int, int, int, int, str]] = []
    centers: list[tuple[float, float]] = []
    for x0, y0, x1, y1, kind, _area in regions:
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        if any((cx - ox) ** 2 + (cy - oy) ** 2 < 180**2 for ox, oy in centers):
            continue
        selected.append((x0, y0, x1, y1, kind))
        centers.append((cx, cy))
        if len(selected) >= 10:
            break
    return selected


def crop_rgba_on_gray(path: Path, box_x8: tuple[int, int, int, int], tile_size: int = 460) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    crop = im.crop(box_x8)
    bg = Image.new("RGBA", crop.size, (96, 96, 96, 255))
    bg.alpha_composite(crop)
    rgb = bg.convert("RGB")
    rgb.thumbnail((tile_size, tile_size), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (tile_size, tile_size), (218, 218, 218))
    tile.paste(rgb, ((tile_size - rgb.width) // 2, (tile_size - rgb.height) // 2))
    return tile


def make_crop_board(items: list[dict], regions_x4: list[tuple[int, int, int, int, str]], out_path: Path) -> None:
    tile = 460
    label_h = 44
    cols = len(items)
    rows = len(regions_x4)
    board = Image.new("RGB", (cols * tile, rows * (tile + label_h) + label_h), (235, 235, 235))
    draw = ImageDraw.Draw(board)
    font = get_font(18)
    small = get_font(15)
    for c, item in enumerate(items):
        x = c * tile
        draw.rectangle((x, 0, x + tile, label_h), fill=(255, 255, 255))
        draw.text((x + 8, 12), item["label"][:44], fill=(0, 0, 0), font=font)
    for r, (x0, y0, x1, y1, kind) in enumerate(regions_x4):
        pad = 80
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        size = max(300, min(760, max(x1 - x0, y1 - y0) + 2 * pad))
        bx0 = max(0, cx - size // 2)
        by0 = max(0, cy - size // 2)
        bx1 = bx0 + size
        by1 = by0 + size
        box_x8 = (bx0 * 2, by0 * 2, bx1 * 2, by1 * 2)
        y = label_h + r * (tile + label_h)
        for c, item in enumerate(items):
            img = crop_rgba_on_gray(Path(item["path"]), box_x8, tile)
            x = c * tile
            board.paste(img, (x, y + label_h))
            draw.rectangle((x, y, x + tile, y + label_h), fill=(255, 255, 255))
            draw.text((x + 8, y + 12), f"{kind} x4=({x0},{y0})", fill=(0, 0, 0), font=small)
    board.save(out_path, quality=94)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    rgb = np.asarray(Image.open(X4_RGB).convert("RGB"))
    base_mask = np.asarray(Image.open(X4_CUTOUT).convert("RGBA").getchannel("A")) > 0
    raw_alpha = load_raw_alpha(X4_RGB, OUT_DIR / "raw" / f"{SLUG}@x4-bria-raw-alpha.png")
    final_rgb = Image.open(FINAL).convert("RGB")

    def build_halo_trim(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask, trim_metrics, trim = halo_trim(rgb, _raw, base_mask, val_min=243, sat_max=32, raw_max=232, boundary_px=4)
        return mask, {"trim": trim_metrics, "trimmed_px": int(trim.sum())}

    def build_lower150(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask = _raw >= 150
        mask, tiny_px, tiny_components = remove_tiny_foreground(mask, 4)
        mask, restore_metrics, restore = colored_margin_restore(rgb, mask, saturation_threshold=18, value_max=214, dilate_px=6)
        mask, trim_metrics, trim = halo_trim(rgb, _raw, mask, val_min=246, sat_max=30, raw_max=232, boundary_px=3)
        return mask, {
            "threshold": 150,
            "tiny_removed_px": tiny_px,
            "tiny_removed_components": tiny_components,
            "restore": restore_metrics,
            "trim": trim_metrics,
            "restored_px": int(restore.sum()),
            "trimmed_px": int(trim.sum()),
        }

    def build_confidence(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask, conf_metrics, conf_restore = confidence_restore(
            rgb, _raw, base_mask, raw_min=85, sat_min=9, val_max=248, near_px=11, min_component_px=80, max_pct=0.72
        )
        mask, internal_metrics, internal_restore = internal_component_restore(rgb, _raw, mask)
        mask, trim_metrics, trim = halo_trim(rgb, _raw, mask, val_min=246, sat_max=30, raw_max=232, boundary_px=3)
        return mask, {
            "confidence_restore": conf_metrics,
            "internal_restore": internal_metrics,
            "trim": trim_metrics,
            "restored_px": int((conf_restore | internal_restore).sum()),
            "trimmed_px": int(trim.sum()),
        }

    def build_restore_only(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask, conf_metrics, conf_restore = confidence_restore(
            rgb, _raw, base_mask, raw_min=75, sat_min=7, val_max=249, near_px=12, min_component_px=80, max_pct=0.9
        )
        mask, internal_metrics, internal_restore = internal_component_restore(rgb, _raw, mask, raw_mean_min=54.0, raw_frac_min=0.12)
        return mask, {
            "confidence_restore": conf_metrics,
            "internal_restore": internal_metrics,
            "restored_px": int((conf_restore | internal_restore).sum()),
            "trimmed_px": 0,
        }

    def build_lower150_restore_no_trim(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask = _raw >= 150
        mask, tiny_px, tiny_components = remove_tiny_foreground(mask, 4)
        mask, restore_metrics, restore = colored_margin_restore(
            rgb, mask, saturation_threshold=18, value_max=214, dilate_px=6
        )
        return mask, {
            "threshold": 150,
            "tiny_removed_px": tiny_px,
            "tiny_removed_components": tiny_components,
            "restore": restore_metrics,
            "restored_px": int(restore.sum()),
            "trimmed_px": 0,
        }

    def build_confidence_no_trim(_raw: np.ndarray) -> tuple[np.ndarray, dict]:
        mask, conf_metrics, conf_restore = confidence_restore(
            rgb, _raw, base_mask, raw_min=85, sat_min=9, val_max=248, near_px=11, min_component_px=80, max_pct=0.72
        )
        mask, internal_metrics, internal_restore = internal_component_restore(rgb, _raw, mask)
        return mask, {
            "confidence_restore": conf_metrics,
            "internal_restore": internal_metrics,
            "restored_px": int((conf_restore | internal_restore).sum()),
            "trimmed_px": 0,
        }

    candidates = [
        Candidate("01-hard180-halo-trim", "hard180 halo trim", build_halo_trim),
        Candidate("02-lower150-guarded-trim", "lower150 guarded trim", build_lower150),
        Candidate("03-confidence-restore-trim", "confidence restore+trim", build_confidence),
        Candidate("04-restore-only", "restore only", build_restore_only),
        Candidate("05-hard180-dewhite", "hard180 dewhite RGB", lambda _raw: (base_mask.copy(), {"restored_px": 0, "trimmed_px": 0}), True, 0.88),
        Candidate("06-lower150-restore-dewhite", "lower150 restore+dewhite", build_lower150_restore_no_trim, True, 0.88),
        Candidate("07-confidence-restore-dewhite", "confidence restore+dewhite", build_confidence_no_trim, True, 0.78),
    ]

    baseline_item = {
        "name": "00-current-final",
        "label": "current final",
        "path": str(FINAL),
        "x4_metrics": alpha_metrics(base_mask) | {"halo_score_px": x4_halo_score(rgb, raw_alpha, base_mask)},
        "method": "existing batch final",
    }
    items = [baseline_item]
    masks: dict[str, np.ndarray] = {}
    for cand in candidates:
        mask, details = cand.build(raw_alpha)
        mask, tiny_px, tiny_components = remove_tiny_foreground(mask, 4)
        out = OUT_DIR / f"{SLUG}@x8-{cand.name}.png"
        out_rgb = final_rgb
        if cand.dewhite:
            out_rgb, dewhite_metrics = dewhite_rgb_for_mask(
                final_rgb, rgb, raw_alpha, mask, strength=cand.dewhite_strength
            )
            details["dewhite_rgb"] = dewhite_metrics
        save_x8_candidate(out_rgb, mask, out)
        metrics = alpha_metrics(mask)
        metrics["halo_score_px"] = x4_halo_score(rgb, raw_alpha, mask)
        metrics["tiny_removed_after_px"] = tiny_px
        metrics["tiny_removed_after_components"] = tiny_components
        item = {
            "name": cand.name,
            "label": cand.label,
            "path": str(out),
            "method": cand.name,
            "x4_metrics": metrics,
            "details": details,
            "delta_vs_current_x4": {
                "restored_alpha_px": int((mask & ~base_mask).sum()),
                "removed_alpha_px": int((base_mask & ~mask).sum()),
            },
        }
        items.append(item)
        masks[cand.name] = mask

    make_contact(items, REVIEW_DIR / f"{SLUG}-candidate-contact-gray.jpg")
    regions = pick_regions(rgb, raw_alpha, base_mask, masks)
    make_crop_board(items, regions, REVIEW_DIR / f"{SLUG}-defect-crop-board.jpg")

    manifest = {
        "source": str(SOURCE),
        "current_final": str(FINAL),
        "x4_rgb": str(X4_RGB),
        "x4_cutout": str(X4_CUTOUT),
        "raw_alpha": str(OUT_DIR / "raw" / f"{SLUG}@x4-bria-raw-alpha.png"),
        "output_dir": str(OUT_DIR),
        "review": {
            "contact_gray": str(REVIEW_DIR / f"{SLUG}-candidate-contact-gray.jpg"),
            "defect_crop_board": str(REVIEW_DIR / f"{SLUG}-defect-crop-board.jpg"),
        },
        "candidate_count": len(items) - 1,
        "items": items,
        "regions_x4": [
            {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "kind": kind}
            for x0, y0, x1, y1, kind in regions
        ],
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "manifest": str(manifest_path),
        "contact_gray": manifest["review"]["contact_gray"],
        "defect_crop_board": manifest["review"]["defect_crop_board"],
        "candidates": [item["path"] for item in items[1:]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
