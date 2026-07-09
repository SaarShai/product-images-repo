#!/usr/bin/env python3
"""Fusion background-removal prototype for double Marine Bed Wrapper image14."""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
MANIFEST_PATH = PRODUCT_DIR / "Images/finals/batch-manifest.json"
RESEARCH_MANIFEST = PRODUCT_DIR / "Images/candidates/image14-research/manifest.json"
BRIA_RAW = PRODUCT_DIR / (
    "Images/candidates/image14-research/raw/"
    "01-bria-rmbg-alpha-matting-hard180.png"
)
REQUESTED_FUSION_DIR = PRODUCT_DIR / "Images/candidates/image14-research/fusion"
FALLBACK_FUSION_DIR = REPO_ROOT / "Images/candidates/image14-research/fusion"
FUSION_DIR = REQUESTED_FUSION_DIR
REVIEW_DIR = REPO_ROOT / "REVIEW/image14-bg"

TW_VALUES = (243, 247, 250)
VARIANTS = ("erode1", "erode2", "erode1-defringe")
KERNEL3 = np.ones((3, 3), np.uint8)


def get_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_manifest_entry() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in data["entries"]:
        if str(entry.get("index")) == "14" or str(entry.get("slug", "")).startswith("14-"):
            return entry
    raise RuntimeError(f"image14 entry not found in {MANIFEST_PATH}")


def choose_x8_white_source(entry: dict[str, Any]) -> tuple[Path, str]:
    """Prefer a saved x8 RGB/white intermediate; otherwise use final RGB payload."""
    final = Path(entry["final_path"])
    slug = entry["slug"]
    size = (int(entry["final_width"]), int(entry["final_height"]))
    search_roots = []
    if entry.get("candidate_dir"):
        search_roots.append(Path(entry["candidate_dir"]))
    search_roots.extend(
        [
        PRODUCT_DIR / "Images/candidates/batch-x8-hard180",
        ]
    )
    patterns = (
        f"**/{slug}*@x8-rgb*.png",
        f"**/{slug}*@x8-white-bg*.png",
        f"**/{slug}*@x8-source-rgb*.png",
    )
    seen: set[Path] = set()
    for root in search_roots:
        if not root or not root.exists():
            continue
        for pattern in patterns:
            for candidate in root.glob(pattern):
                if candidate in seen or candidate == final:
                    continue
                name = candidate.name.lower()
                if "dewhite" in name or "bg-removed" in name or "repair" in str(candidate.parent).lower():
                    continue
                seen.add(candidate)
                try:
                    with Image.open(candidate) as im:
                        if im.size != size:
                            continue
                        if "A" in im.getbands():
                            alpha = im.getchannel("A")
                            if alpha.getextrema() != (255, 255):
                                continue
                            return candidate, "found saved x8 white/RGB intermediate"
                except Exception:
                    continue
    return final, (
        "used manifest final RGBA path as the x8 white-bg source; "
        "run_batch_x8_hard180.py writes the x8 RGB first, then transfers binary alpha, "
        "so the RGB payload is the white-background intermediate"
    )


def load_rois() -> tuple[list[tuple[int, int, int, int]], str]:
    if RESEARCH_MANIFEST.exists():
        data = json.loads(RESEARCH_MANIFEST.read_text(encoding="utf-8"))
        rois = [tuple(map(int, r)) for r in data.get("rois_xyxy", [])]
        if rois:
            return rois[:8], f"loaded from {RESEARCH_MANIFEST}"
    return [], "none found"


def ensure_output_dirs() -> str:
    global FUSION_DIR
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        REQUESTED_FUSION_DIR.mkdir(parents=True, exist_ok=True)
        FUSION_DIR = REQUESTED_FUSION_DIR
        return "using requested production fusion directory"
    except PermissionError as exc:
        FALLBACK_FUSION_DIR.mkdir(parents=True, exist_ok=True)
        FUSION_DIR = FALLBACK_FUSION_DIR
        return (
            f"requested production fusion directory is not writable in this sandbox "
            f"({type(exc).__name__}: {exc}); wrote candidate PNGs to repo-local fallback"
        )


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r = rgb[:, :, 0].astype(np.uint16)
    g = rgb[:, :, 1].astype(np.uint16)
    b = rgb[:, :, 2].astype(np.uint16)
    luma = ((77 * r + 150 * g + 29 * b) >> 8).astype(np.uint8)
    del r, g, b
    mx = np.maximum(np.maximum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    mn = np.minimum(np.minimum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2])
    chroma = (mx - mn).astype(np.uint8)
    return luma, chroma


def mean_luma_for_mask(rgb: np.ndarray, mask: np.ndarray) -> float | None:
    if not bool(mask.any()):
        return None
    r = rgb[:, :, 0][mask].astype(np.float32)
    g = rgb[:, :, 1][mask].astype(np.float32)
    b = rgb[:, :, 2][mask].astype(np.float32)
    out = float((0.299 * r + 0.587 * g + 0.114 * b).mean())
    del r, g, b
    return out


def flood_bg_mask(luma: np.ndarray, chroma: np.ndarray, tw: int) -> tuple[np.ndarray, dict[str, Any]]:
    near = ((luma >= tw) & (chroma <= 12)).astype(np.uint8)
    h, w = near.shape
    padded = np.empty((h + 2, w + 2), dtype=np.uint8)
    padded.fill(1)
    padded[1:-1, 1:-1] = near
    cv2.floodFill(padded, None, (0, 0), 2, flags=8)
    flood_bg = padded[1:-1, 1:-1] == 2
    stats = {
        "near_white_px": int(near.sum()),
        "flood_bg_px": int(flood_bg.sum()),
    }
    del near, padded
    return flood_bg, stats


def bg_color_model(rgb: np.ndarray, flood_bg: np.ndarray) -> dict[str, Any]:
    n = int(flood_bg.sum())
    if n == 0:
        return {"count": 0, "mean_rgb": None, "std_rgb": None}
    means: list[float] = []
    stds: list[float] = []
    for channel in range(3):
        vals = rgb[:, :, channel][flood_bg]
        means.append(float(vals.mean()))
        stds.append(float(vals.std()))
        del vals
    return {"count": n, "mean_rgb": means, "std_rgb": stds}


def component_decisions(
    r_mask: np.ndarray,
    bria_fg: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    labels_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        r_mask.astype(np.uint8), 8
    )
    restored = np.zeros_like(r_mask, dtype=bool)
    decisions: list[dict[str, Any]] = []
    restored_components = 0
    restored_px = 0
    kept_components = 0
    kept_px = 0

    for component_id in range(1, labels_count):
        x = int(stats[component_id, cv2.CC_STAT_LEFT])
        y = int(stats[component_id, cv2.CC_STAT_TOP])
        w = int(stats[component_id, cv2.CC_STAT_WIDTH])
        h = int(stats[component_id, cv2.CC_STAT_HEIGHT])
        area = int(stats[component_id, cv2.CC_STAT_AREA])
        comp = labels[y : y + h, x : x + w] == component_id
        med_chroma = float(np.median(chroma[y : y + h, x : x + w][comp]))
        med_luma = float(np.median(luma[y : y + h, x : x + w][comp]))

        y0 = max(0, y - 1)
        x0 = max(0, x - 1)
        y1 = min(labels.shape[0], y + h + 1)
        x1 = min(labels.shape[1], x + w + 1)
        comp_pad = (labels[y0:y1, x0:x1] == component_id).astype(np.uint8)
        touches_bria = bool((cv2.dilate(comp_pad, KERNEL3, iterations=1).astype(bool) & bria_fg[y0:y1, x0:x1]).any())
        paint_like = med_chroma > 10.0 or med_luma < 235.0
        restore = area >= 64 and touches_bria and paint_like

        if restore:
            restored_crop = restored[y : y + h, x : x + w]
            restored_crop[comp] = True
            restored_components += 1
            restored_px += area
            verdict = "restore"
            reason = "area>=64_touches_bria_paint_like"
        else:
            kept_components += 1
            kept_px += area
            verdict = "keep_transparent"
            if area < 64:
                reason = "area_lt_64"
            elif not touches_bria:
                reason = "not_touching_bria"
            else:
                reason = "paper_like_hole_or_fringe"

        decisions.append(
            {
                "component_id": component_id,
                "area": area,
                "bbox_xywh": [x, y, w, h],
                "touches_bria": touches_bria,
                "median_chroma": med_chroma,
                "median_luma": med_luma,
                "verdict": verdict,
                "reason": reason,
            }
        )

    summary = {
        "candidate_components": labels_count - 1,
        "restored_components": restored_components,
        "restored_px": restored_px,
        "kept_transparent_components": kept_components,
        "kept_transparent_px": kept_px,
    }
    del labels, stats
    return restored, decisions, summary


def remove_small_fg(mask: np.ndarray, min_area: int = 32) -> tuple[np.ndarray, dict[str, int]]:
    labels_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8
    )
    out = mask.copy()
    removed_components = 0
    removed_px = 0
    for component_id in range(1, labels_count):
        area = int(stats[component_id, cv2.CC_STAT_AREA])
        if area >= min_area:
            continue
        x = int(stats[component_id, cv2.CC_STAT_LEFT])
        y = int(stats[component_id, cv2.CC_STAT_TOP])
        w = int(stats[component_id, cv2.CC_STAT_WIDTH])
        h = int(stats[component_id, cv2.CC_STAT_HEIGHT])
        comp = labels[y : y + h, x : x + w] == component_id
        out_crop = out[y : y + h, x : x + w]
        out_crop[comp] = False
        removed_components += 1
        removed_px += area
    del labels, stats
    return out, {"small_fg_removed_components": removed_components, "small_fg_removed_px": removed_px}


def erode_bool(mask: np.ndarray, iterations: int) -> np.ndarray:
    return cv2.erode(mask.astype(np.uint8), KERNEL3, iterations=iterations).astype(bool)


def defringe_rgb(rgb: np.ndarray, mask: np.ndarray, luma: np.ndarray) -> tuple[np.ndarray, int]:
    out = rgb.copy()
    inner_band = mask & ~erode_bool(mask, 3)
    count = int(inner_band.sum())
    if count == 0:
        return out, 0
    alpha = np.clip((255.0 - luma[inner_band].astype(np.float32)) / 75.0, 0.15, 1.0)
    colors = out[inner_band].astype(np.float32)
    colors = (colors - (1.0 - alpha[:, None]) * 255.0) / alpha[:, None]
    out[inner_band] = np.clip(colors, 0, 255).astype(np.uint8)
    del alpha, colors
    return out, count


def count_holes(mask: np.ndarray) -> tuple[int, int]:
    transparent = (~mask).astype(np.uint8)
    h, w = transparent.shape
    padded = np.empty((h + 2, w + 2), dtype=np.uint8)
    padded.fill(1)
    padded[1:-1, 1:-1] = transparent
    cv2.floodFill(padded, None, (0, 0), 2, flags=8)
    border_connected = padded[1:-1, 1:-1] == 2
    holes = transparent.astype(bool) & ~border_connected
    del transparent, padded, border_connected
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        holes.astype(np.uint8), 8
    )
    count = 0
    px = 0
    for component_id in range(1, labels_count):
        area = int(stats[component_id, cv2.CC_STAT_AREA])
        if area >= 64:
            count += 1
            px += area
    del holes, labels, stats, centroids
    return count, px


def edge_metrics(
    rgb_variant: np.ndarray,
    mask: np.ndarray,
    chroma: np.ndarray,
    source_luma: np.ndarray,
) -> dict[str, Any]:
    edge_band = mask & ~erode_bool(mask, 2)
    interior = erode_bool(mask, 8)
    if not bool(interior.any()):
        interior = mask
    edge_luma = mean_luma_for_mask(rgb_variant, edge_band)
    interior_luma = float(source_luma[interior].mean()) if bool(interior.any()) else None
    fringe_score = (
        None
        if edge_luma is None or interior_luma is None
        else float(edge_luma - interior_luma)
    )

    adjacent_bg = cv2.dilate(mask.astype(np.uint8), KERNEL3, iterations=1).astype(bool) & ~mask
    overcut_score = int((adjacent_bg & (chroma > 15)).sum())
    holes_count, holes_px = count_holes(mask)
    return {
        "holes_kept_open": holes_count,
        "holes_kept_open_px": holes_px,
        "fringe_score": fringe_score,
        "edge_luma_mean": edge_luma,
        "interior_luma_mean": interior_luma,
        "overcut_score": overcut_score,
    }


def flood_intrusion_report(
    flood_bg: np.ndarray,
    bria_fg: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
) -> dict[str, Any]:
    adjacent_bria_bg = cv2.dilate(bria_fg.astype(np.uint8), KERNEL3, iterations=1).astype(bool) & ~bria_fg
    suspicious = flood_bg & adjacent_bria_bg & ((chroma > 10) | (luma < 235))
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        suspicious.astype(np.uint8), 8
    )
    components = []
    px = 0
    for component_id in range(1, labels_count):
        area = int(stats[component_id, cv2.CC_STAT_AREA])
        if area < 64:
            continue
        x = int(stats[component_id, cv2.CC_STAT_LEFT])
        y = int(stats[component_id, cv2.CC_STAT_TOP])
        w = int(stats[component_id, cv2.CC_STAT_WIDTH])
        h = int(stats[component_id, cv2.CC_STAT_HEIGHT])
        components.append({"area": area, "bbox_xywh": [x, y, w, h]})
        px += area
    del suspicious, labels, stats, centroids
    return {
        "recall_broken": bool(components),
        "flooded_paint_like_components": len(components),
        "flooded_paint_like_px": px,
        "components": components[:50],
    }


def write_rgba(rgb: np.ndarray, mask: np.ndarray, out_path: Path) -> None:
    rgba = np.empty((rgb.shape[0], rgb.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = mask.astype(np.uint8) * 255
    Image.fromarray(rgba, "RGBA").save(out_path, compress_level=6)
    del rgba


def fit_tile(im: Image.Image, size: tuple[int, int], bg: tuple[int, int, int]) -> Image.Image:
    tile = Image.new("RGB", size, bg)
    work = im.copy()
    work.thumbnail((size[0] - 12, size[1] - 12), Image.Resampling.LANCZOS)
    tile.paste(work.convert("RGB"), ((size[0] - work.width) // 2, (size[1] - work.height) // 2))
    return tile


def composite_on_bg(rgba: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", rgba.size, (*bg, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def rgba_thumbnail_tile(path: str, bg: tuple[int, int, int], size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as im:
        work = im.convert("RGBA")
    work.thumbnail((size[0] - 12, size[1] - 12), Image.Resampling.LANCZOS)
    comp = composite_on_bg(work, bg)
    tile = Image.new("RGB", size, bg)
    tile.paste(comp, ((size[0] - comp.width) // 2, (size[1] - comp.height) // 2))
    return tile


def full_overlay_tile(
    rgb: np.ndarray,
    restored: np.ndarray,
    kept: np.ndarray,
    removed: np.ndarray,
    size: tuple[int, int],
) -> Image.Image:
    h, w = rgb.shape[:2]
    scale = min((size[0] - 12) / w, (size[1] - 12) / h)
    thumb_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    base = Image.fromarray(rgb, "RGB").resize(thumb_size, Image.Resampling.LANCZOS).convert("RGBA")
    overlay = np.zeros((thumb_size[1], thumb_size[0], 4), dtype=np.uint8)
    masks = (
        (restored, (0, 210, 70, 130)),
        (kept, (0, 95, 255, 130)),
        (removed, (255, 40, 20, 150)),
    )
    for mask, color in masks:
        small = Image.fromarray(mask.astype(np.uint8) * 255, "L").resize(thumb_size, Image.Resampling.NEAREST)
        overlay[np.asarray(small) > 0] = color
    base.alpha_composite(Image.fromarray(overlay, "RGBA"))
    tile = Image.new("RGB", size, (245, 245, 245))
    out = base.convert("RGB")
    tile.paste(out, ((size[0] - out.width) // 2, (size[1] - out.height) // 2))
    del overlay
    return tile


def overlay_image(
    rgb_crop: np.ndarray,
    restored: np.ndarray,
    kept: np.ndarray,
    removed: np.ndarray,
) -> Image.Image:
    base = Image.fromarray(rgb_crop, "RGB").convert("RGBA")
    overlay = np.zeros((rgb_crop.shape[0], rgb_crop.shape[1], 4), dtype=np.uint8)
    overlay[restored] = (0, 210, 70, 130)
    overlay[kept] = (0, 95, 255, 130)
    overlay[removed] = (255, 40, 20, 150)
    base.alpha_composite(Image.fromarray(overlay, "RGBA"))
    del overlay
    return base.convert("RGB")


def make_review_sheet(
    metric: dict[str, Any],
    rgb: np.ndarray,
    bria_fg: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
    rois: list[tuple[int, int, int, int]],
    out_path: Path,
) -> None:
    tw = int(metric["tw"])
    variant = metric["variant"]
    flood_bg, _stats = flood_bg_mask(luma, chroma, tw)
    r_mask = (~flood_bg) & ~bria_fg
    restored, _decisions, _summary = component_decisions(r_mask, bria_fg, luma, chroma)
    final_mask, _removed_small = remove_small_fg(bria_fg | restored, 32)
    if variant == "erode2":
        variant_mask = erode_bool(final_mask, 2)
    else:
        variant_mask = erode_bool(final_mask, 1)
    kept = r_mask & ~restored
    removed = final_mask & ~variant_mask

    font = get_font(18)
    small = get_font(14)
    tile = (360, 430)
    row_h = 300
    label_h = 28
    width = tile[0] * 3
    height = 70 + tile[1] + len(rois) * (label_h + row_h) + 26
    sheet = Image.new("RGB", (width, height), (232, 232, 232))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, width, 70), fill=(255, 255, 255))
    draw.text((12, 10), f"{metric['name']}  Tw={tw}  {variant}", fill=(0, 0, 0), font=font)
    draw.text(
        (12, 38),
        (
            f"restored {metric['restored_components']} comps/{metric['restored_px']} px; "
            f"holes {metric['holes_kept_open']}; fringe {metric['fringe_score']:.2f}; "
            f"overcut {metric['overcut_score']}"
        ),
        fill=(0, 0, 0),
        font=small,
    )

    grey = rgba_thumbnail_tile(metric["path"], (128, 128, 128), tile)
    black = rgba_thumbnail_tile(metric["path"], (0, 0, 0), tile)
    overlay_tile = full_overlay_tile(rgb, restored, kept, removed, tile)
    for col, (label, im) in enumerate((("mid grey", grey), ("black", black), ("decision overlay", overlay_tile))):
        x = col * tile[0]
        sheet.paste(im, (x, 70))
        draw.rectangle((x, 70, x + tile[0], 96), fill=(255, 255, 255))
        draw.text((x + 8, 75), label, fill=(0, 0, 0), font=small)

    y = 70 + tile[1]
    candidate = Image.open(metric["path"]).convert("RGBA")
    for idx, roi in enumerate(rois, start=1):
        x0, y0, x1, y1 = roi
        draw.rectangle((0, y, width, y + label_h), fill=(250, 250, 250))
        draw.text((8, y + 6), f"ROI {idx}: x={x0} y={y0} w={x1 - x0} h={y1 - y0}", fill=(0, 0, 0), font=small)
        y += label_h
        crop = candidate.crop(roi)
        roi_grey = fit_tile(composite_on_bg(crop, (128, 128, 128)), (tile[0], row_h), (128, 128, 128))
        roi_black = fit_tile(composite_on_bg(crop, (0, 0, 0)), (tile[0], row_h), (0, 0, 0))
        roi_overlay = fit_tile(
            overlay_image(
                rgb[y0:y1, x0:x1],
                restored[y0:y1, x0:x1],
                kept[y0:y1, x0:x1],
                removed[y0:y1, x0:x1],
            ),
            (tile[0], row_h),
            (245, 245, 245),
        )
        sheet.paste(roi_grey, (0, y))
        sheet.paste(roi_black, (tile[0], y))
        sheet.paste(roi_overlay, (tile[0] * 2, y))
        y += row_h

    draw.rectangle((0, height - 26, width, height), fill=(255, 255, 255))
    draw.text((8, height - 22), "overlay: restored=green, kept-hole/paper=blue, removed-fringe=red", fill=(0, 0, 0), font=small)
    sheet.save(out_path, quality=92)
    candidate.close()
    del flood_bg, r_mask, restored, final_mask, variant_mask, kept, removed, sheet
    gc.collect()


def ranking_key(metric: dict[str, Any]) -> tuple[int, float, int]:
    fringe = metric["fringe_score"]
    if fringe is None:
        fringe = 9999.0
    return (int(metric["overcut_score"]), float(fringe), -int(metric["restored_px"]))


def process_tw(
    tw: int,
    rgb: np.ndarray,
    bria_fg: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    print(f"\n== Tw {tw} ==", flush=True)
    flood_bg, flood_stats = flood_bg_mask(luma, chroma, tw)
    flood_stats["bg_color_model"] = bg_color_model(rgb, flood_bg)
    intrusion = flood_intrusion_report(flood_bg, bria_fg, luma, chroma)
    r_mask = (~flood_bg) & ~bria_fg
    restored, decisions, summary = component_decisions(r_mask, bria_fg, luma, chroma)
    final_mask, small_summary = remove_small_fg(bria_fg | restored, 32)
    kept_transparent = r_mask & ~restored
    print(
        f"components={summary['candidate_components']} restored={summary['restored_components']} "
        f"restored_px={summary['restored_px']} kept_transparent={summary['kept_transparent_components']} "
        f"flood_intrusion_components={intrusion['flooded_paint_like_components']}",
        flush=True,
    )

    metrics: list[dict[str, Any]] = []
    for variant in VARIANTS:
        if variant == "erode2":
            mask = erode_bool(final_mask, 2)
            rgb_variant = rgb
            defringe_px = 0
        elif variant == "erode1-defringe":
            mask = erode_bool(final_mask, 1)
            rgb_variant, defringe_px = defringe_rgb(rgb, mask, luma)
        else:
            mask = erode_bool(final_mask, 1)
            rgb_variant = rgb
            defringe_px = 0

        out_path = FUSION_DIR / f"14-fusion-Tw{tw}-{variant}.png"
        write_rgba(rgb_variant, mask, out_path)
        edge = edge_metrics(rgb_variant, mask, chroma, luma)
        metric = {
            "name": f"14-fusion-Tw{tw}-{variant}",
            "tw": tw,
            "variant": variant,
            "path": str(out_path),
            "restored_components": summary["restored_components"],
            "restored_px": summary["restored_px"],
            "holes_kept_open": edge["holes_kept_open"],
            "holes_kept_open_px": edge["holes_kept_open_px"],
            "fringe_score": edge["fringe_score"],
            "overcut_score": edge["overcut_score"],
            "edge_luma_mean": edge["edge_luma_mean"],
            "interior_luma_mean": edge["interior_luma_mean"],
            "defringe_px": defringe_px,
            **small_summary,
        }
        metrics.append(metric)
        print(
            f"{metric['name']} restored={metric['restored_components']}/{metric['restored_px']} "
            f"holes={metric['holes_kept_open']} fringe={metric['fringe_score']:.3f} "
            f"overcut={metric['overcut_score']}",
            flush=True,
        )
        if variant == "erode1-defringe":
            del rgb_variant
        del mask
        gc.collect()

    flood_report = {
        "tw": tw,
        **flood_stats,
        "candidate_summary": summary,
        "small_fg_cleanup": small_summary,
        "flood_intrusion": intrusion,
        "kept_transparent_px": int(kept_transparent.sum()),
    }
    del flood_bg, r_mask, restored, final_mask, kept_transparent
    gc.collect()
    return metrics, flood_report, decisions


def main() -> None:
    output_dir_note = ensure_output_dirs()
    entry = load_manifest_entry()
    x8_source, source_note = choose_x8_white_source(entry)
    if not x8_source.exists():
        raise FileNotFoundError(x8_source)
    if not BRIA_RAW.exists():
        raise FileNotFoundError(BRIA_RAW)

    print(f"x8_white_source: {x8_source}", flush=True)
    print(f"x8_source_note: {source_note}", flush=True)
    print(f"bria_raw: {BRIA_RAW}", flush=True)
    print(f"fusion_output_dir: {FUSION_DIR}", flush=True)
    print(f"fusion_output_note: {output_dir_note}", flush=True)

    with Image.open(x8_source) as im:
        src_rgba = im.convert("RGBA")
        rgb = np.asarray(src_rgba.convert("RGB")).copy()
        size = src_rgba.size
    with Image.open(BRIA_RAW) as im:
        alpha = im.convert("RGBA").getchannel("A")
        if alpha.size != size:
            alpha = alpha.resize(size, Image.Resampling.NEAREST)
        bria_fg = np.asarray(alpha) >= 128

    luma, chroma = luma_chroma(rgb)
    rois, roi_source = load_rois()
    if not rois:
        raise RuntimeError("No ROI coordinates found; expected image14 research manifest rois_xyxy.")
    print(f"roi_source: {roi_source}", flush=True)

    all_metrics: list[dict[str, Any]] = []
    flood_reports: list[dict[str, Any]] = []
    decisions_by_tw: dict[str, list[dict[str, Any]]] = {}
    for tw in TW_VALUES:
        metrics, flood_report, decisions = process_tw(tw, rgb, bria_fg, luma, chroma)
        all_metrics.extend(metrics)
        flood_reports.append(flood_report)
        decisions_by_tw[str(tw)] = decisions

    best_three = sorted(all_metrics, key=ranking_key)[:3]
    review_sheets: list[str] = []
    for metric in best_three:
        out = REVIEW_DIR / f"{metric['name']}-review-sheet.jpg"
        make_review_sheet(metric, rgb, bria_fg, luma, chroma, rois, out)
        metric["review_sheet"] = str(out)
        review_sheets.append(str(out))
        print(f"review_sheet: {out}", flush=True)

    metrics_doc = {
        "source_x8_white_bg": str(x8_source),
        "source_selection_note": source_note,
        "manifest": str(MANIFEST_PATH),
        "bria_raw": str(BRIA_RAW),
        "fusion_dir": str(FUSION_DIR),
        "requested_fusion_dir": str(REQUESTED_FUSION_DIR),
        "fusion_output_note": output_dir_note,
        "review_dir": str(REVIEW_DIR),
        "roi_source": roi_source,
        "rois_xyxy": [list(r) for r in rois],
        "metrics": all_metrics,
        "flood_reports": flood_reports,
        "component_decisions_by_tw": decisions_by_tw,
        "best_three": [
            {"name": m["name"], "path": m["path"], "review_sheet": m.get("review_sheet")}
            for m in best_three
        ],
        "flood_fill_recall_broken_tw": [
            report["tw"]
            for report in flood_reports
            if report["flood_intrusion"]["recall_broken"]
        ],
    }
    metrics_path = FUSION_DIR / "fusion-metrics.json"
    metrics_path.write_text(json.dumps(metrics_doc, indent=2), encoding="utf-8")
    print(f"metrics_json: {metrics_path}", flush=True)

    print("\nMETRICS TABLE", flush=True)
    print("Tw\tvariant\trestored_components\trestored_px\tholes_kept_open\tfringe_score\tovercut_score", flush=True)
    for metric in all_metrics:
        print(
            f"{metric['tw']}\t{metric['variant']}\t{metric['restored_components']}\t"
            f"{metric['restored_px']}\t{metric['holes_kept_open']}\t"
            f"{metric['fringe_score']:.3f}\t{metric['overcut_score']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
