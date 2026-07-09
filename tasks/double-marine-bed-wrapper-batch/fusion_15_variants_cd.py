#!/usr/bin/env python3
"""Build image 15 fusion variants C/D for the ragged cream-haze boundary."""

from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fusion_bg_removal import count_holes, defringe_rgb, erode_bool, luma_chroma, remove_small_fg

Image.MAX_IMAGE_PIXELS = None


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_RGB_PATH = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/finals/"
    "15-ChatGPT_Image_Jul_7_2026_11_34_15_AM@x8-bg-removed.png"
)
VARIANT_A_PATH = REPO_ROOT / "Images/candidates/batch-fusion/15-fusion-Tw250-erode1-defringe.png"
OUT_DIR = REPO_ROOT / "Images/candidates/batch-fusion"
REVIEW_DIR = REPO_ROOT / "REVIEW/batch-fusion"

C_OUT = OUT_DIR / "15-fusion-C-washfull.png"
D_OUT = OUT_DIR / "15-fusion-D-smooth.png"
C_REVIEW = REVIEW_DIR / "15-C-washfull-review-sheet.jpg"
D_REVIEW = REVIEW_DIR / "15-D-smooth-review-sheet.jpg"

ROI_SIZE = 720
FULL_W = 720
FULL_H = 480
HEADER_H = 132
LABEL_H = 38
FOOTER_H = 30
RING_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))


@dataclass(frozen=True)
class Hole:
    label_id: int
    area: int
    bbox_xywh: tuple[int, int, int, int]
    center_xy: tuple[float, float]
    p10_luma: float


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


def load_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not SOURCE_RGB_PATH.exists():
        raise FileNotFoundError(SOURCE_RGB_PATH)
    if not VARIANT_A_PATH.exists():
        raise FileNotFoundError(VARIANT_A_PATH)

    with Image.open(SOURCE_RGB_PATH) as source_im:
        source_rgba = np.array(source_im.convert("RGBA"), dtype=np.uint8)
    with Image.open(VARIANT_A_PATH) as variant_im:
        variant_a_rgba = np.array(variant_im.convert("RGBA"), dtype=np.uint8)

    if source_rgba.shape[:2] != variant_a_rgba.shape[:2]:
        raise RuntimeError(
            f"dimension mismatch: source={source_rgba.shape[:2]} variant_a={variant_a_rgba.shape[:2]}"
        )

    source_rgb = np.ascontiguousarray(source_rgba[:, :, :3])
    bria_fg = source_rgba[:, :, 3] >= 128
    variant_a_fg = variant_a_rgba[:, :, 3] != 0
    source_luma, source_chroma = luma_chroma(source_rgb)
    return source_rgb, source_luma, source_chroma, bria_fg, variant_a_fg


def disk_kernel(radius: int) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def morph_close(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, disk_kernel(radius)).astype(bool)


def morph_open(mask: np.ndarray, radius: int) -> np.ndarray:
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, disk_kernel(radius)).astype(bool)


def flood_outer_bg(luma: np.ndarray, chroma: np.ndarray) -> np.ndarray:
    near_white = ((luma >= 252) & (chroma <= 6)).astype(np.uint8)
    h, w = near_white.shape
    padded = np.empty((h + 2, w + 2), dtype=np.uint8)
    padded.fill(1)
    padded[1:-1, 1:-1] = near_white
    cv2.floodFill(padded, None, (0, 0), 2, flags=8)
    outer_bg = padded[1:-1, 1:-1] == 2
    del near_white, padded
    return outer_bg


def border_touch_labels(labels: np.ndarray, labels_count: int) -> np.ndarray:
    touches = np.zeros(labels_count, dtype=bool)
    border_ids = np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
    touches[np.unique(border_ids)] = True
    touches[0] = False
    return touches


def component_p10_luma(
    *,
    label_id: int,
    labels: np.ndarray,
    stats: np.ndarray,
    fg_for_ring: np.ndarray,
    source_luma: np.ndarray,
) -> float:
    x = int(stats[label_id, cv2.CC_STAT_LEFT])
    y = int(stats[label_id, cv2.CC_STAT_TOP])
    w = int(stats[label_id, cv2.CC_STAT_WIDTH])
    h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
    height, width = source_luma.shape
    x0 = max(0, x - 5)
    y0 = max(0, y - 5)
    x1 = min(width, x + w + 5)
    y1 = min(height, y + h + 5)

    comp = (labels[y0:y1, x0:x1] == label_id).astype(np.uint8)
    ring = cv2.dilate(comp, RING_KERNEL, iterations=1).astype(bool) & fg_for_ring[y0:y1, x0:x1]
    if not bool(ring.any()):
        return 255.0
    return float(np.percentile(source_luma[y0:y1, x0:x1][ring], 10))


def enclosed_components(
    transparent_mask: np.ndarray,
    *,
    fg_for_ring: np.ndarray,
    source_luma: np.ndarray,
    min_area: int = 1,
) -> tuple[list[Hole], np.ndarray, np.ndarray]:
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        transparent_mask.astype(np.uint8), 8
    )
    touches_border = border_touch_labels(labels, labels_count)
    holes: list[Hole] = []
    for label_id in range(1, labels_count):
        if touches_border[label_id]:
            continue
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[label_id, cv2.CC_STAT_LEFT])
        y = int(stats[label_id, cv2.CC_STAT_TOP])
        w = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        p10_luma = component_p10_luma(
            label_id=label_id,
            labels=labels,
            stats=stats,
            fg_for_ring=fg_for_ring,
            source_luma=source_luma,
        )
        holes.append(
            Hole(
                label_id=label_id,
                area=area,
                bbox_xywh=(x, y, w, h),
                center_xy=(float(centroids[label_id][0]), float(centroids[label_id][1])),
                p10_luma=p10_luma,
            )
        )
    return holes, labels, stats


def paint_component_ids(mask: np.ndarray, labels: np.ndarray, holes: list[Hole], value: bool) -> int:
    px = 0
    for hole in holes:
        x, y, w, h = hole.bbox_xywh
        comp = labels[y : y + h, x : x + w] == hole.label_id
        mask[y : y + h, x : x + w][comp] = value
        px += hole.area
    return px


def fill_transparent_specks(
    mask: np.ndarray,
    *,
    source_luma: np.ndarray,
) -> tuple[np.ndarray, int, int]:
    holes, labels, _stats = enclosed_components(
        ~mask,
        fg_for_ring=mask,
        source_luma=source_luma,
        min_area=1,
    )
    fill = [hole for hole in holes if hole.area < 64 and hole.p10_luma >= 150.0]
    out = mask.copy()
    filled_px = paint_component_ids(out, labels, fill, True)
    filled_count = len(fill)
    del labels, holes
    return out, filled_count, filled_px


def finish_rgba(
    source_rgb: np.ndarray,
    source_luma: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    eroded = erode_bool(mask, 1)
    rgb_defringed, defringe_px = defringe_rgb(source_rgb, eroded, source_luma)
    rgba = np.empty((source_rgb.shape[0], source_rgb.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_defringed
    rgba[:, :, 3] = eroded.astype(np.uint8) * 255
    del rgb_defringed
    return rgba, eroded, defringe_px


def write_png(path: Path, rgba: np.ndarray) -> None:
    Image.fromarray(rgba).save(path, compress_level=6)


def crop_box(center_xy: tuple[float, float], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    crop_w = min(ROI_SIZE, width)
    crop_h = min(ROI_SIZE, height)
    cx, cy = center_xy
    x0 = int(round(cx - crop_w / 2))
    y0 = int(round(cy - crop_h / 2))
    x0 = max(0, min(x0, width - crop_w))
    y0 = max(0, min(y0, height - crop_h))
    return x0, y0, x0 + crop_w, y0 + crop_h


def composite_on_bg(rgba: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", rgba.size, (*bg, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def full_tile(rgba: np.ndarray, bg: tuple[int, int, int]) -> Image.Image:
    work = Image.fromarray(rgba).resize((FULL_W, FULL_H), Image.Resampling.LANCZOS)
    return composite_on_bg(work, bg)


def roi_tile(rgba: np.ndarray, box: tuple[int, int, int, int], bg: tuple[int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    crop = Image.fromarray(rgba[y0:y1, x0:x1])
    return composite_on_bg(crop, bg)


def choose_ink_hole_crop(final_mask: np.ndarray, source_luma: np.ndarray) -> tuple[str, tuple[int, int, int, int]]:
    holes, labels, _stats = enclosed_components(
        ~final_mask,
        fg_for_ring=final_mask,
        source_luma=source_luma,
        min_area=64,
    )
    ink_holes = [hole for hole in holes if hole.p10_luma < 150.0]
    image_size = (final_mask.shape[1], final_mask.shape[0])
    if ink_holes:
        hole = max(ink_holes, key=lambda h: h.area)
        label = (
            f"kept ink hole: component={hole.label_id} area={hole.area} "
            f"p10_luma={hole.p10_luma:.1f}"
        )
        box = crop_box(hole.center_xy, image_size)
    else:
        label = "kept ink hole: none found; fallback seaweed crop"
        box = crop_box((7573, 3959), image_size)
    del holes, labels
    return label, box


def choose_top_haze_crop(final_mask: np.ndarray) -> tuple[str, tuple[int, int, int, int]]:
    region_xyxy = (4500, 0, 6500, 2500)
    x0, y0, x1, y1 = region_xyxy
    region = final_mask[y0:y1, x0:x1]
    kernel = np.ones((3, 3), dtype=np.uint8)
    edge = cv2.dilate(region.astype(np.uint8), kernel, iterations=1) != cv2.erode(
        region.astype(np.uint8), kernel, iterations=1
    )
    if bool(edge.any()):
        ys, xs = np.nonzero(edge)
        cx = float(np.median(xs) + x0)
        cy = float(np.median(ys) + y0)
        label = f"top-center haze edge: center=({cx:.0f},{cy:.0f}), size=720"
        return label, crop_box((cx, cy), (final_mask.shape[1], final_mask.shape[0]))
    label = "top-center haze edge: no edge found; fallback center=(5500,1250), size=720"
    return label, crop_box((5500, 1250), (final_mask.shape[1], final_mask.shape[0]))


def make_review_sheet(
    *,
    variant_name: str,
    rgba: np.ndarray,
    final_mask: np.ndarray,
    source_luma: np.ndarray,
    metrics: dict[str, int | float | str | list[int]],
    out_path: Path,
) -> tuple[int, int]:
    font = get_font(22)
    small = get_font(16)
    width = FULL_W * 2
    rows: list[tuple[str, tuple[int, int, int, int]]] = [
        choose_top_haze_crop(final_mask),
        ("seaweed zone: center=(7573,3959), size=720", crop_box((7573, 3959), (rgba.shape[1], rgba.shape[0]))),
        choose_ink_hole_crop(final_mask, source_luma),
    ]
    height = HEADER_H + FULL_H + len(rows) * (LABEL_H + ROI_SIZE) + FOOTER_H
    sheet = Image.new("RGB", (width, height), (232, 232, 232))
    draw = ImageDraw.Draw(sheet)

    draw.rectangle((0, 0, width, HEADER_H), fill=(255, 255, 255))
    draw.text((12, 10), f"image 15 fusion {variant_name}", fill=(0, 0, 0), font=font)
    draw.text(
        (12, 46),
        (
            f"fg_px={metrics['fg_px']}  delta_vs_A={metrics['fg_delta_vs_A']}  "
            f"holes_open={metrics['holes_open_count']}  holes_px={metrics['holes_open_px']}"
        ),
        fill=(0, 0, 0),
        font=small,
    )
    draw.text(
        (12, 72),
        (
            f"alpha_values={metrics['alpha_values']}  defringe_px={metrics['defringe_px']}  "
            f"{metrics['extra']}"
        ),
        fill=(0, 0, 0),
        font=small,
    )
    draw.text((12, 100), "columns: mid grey composite | black composite", fill=(0, 0, 0), font=small)

    y = HEADER_H
    for x, label, bg in (
        (0, "full over mid grey", (128, 128, 128)),
        (FULL_W, "full over black", (0, 0, 0)),
    ):
        sheet.paste(full_tile(rgba, bg), (x, y))
        draw.rectangle((x, y, x + FULL_W, y + 28), fill=(255, 255, 255))
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0), font=small)
    y += FULL_H

    for label, box in rows:
        x0, y0, x1, y1 = box
        draw.rectangle((0, y, width, y + LABEL_H), fill=(250, 250, 250))
        draw.text(
            (8, y + 10),
            f"{label}; crop=({x0},{y0},{x1},{y1})",
            fill=(0, 0, 0),
            font=small,
        )
        y += LABEL_H
        sheet.paste(roi_tile(rgba, box, (128, 128, 128)), (0, y))
        sheet.paste(roi_tile(rgba, box, (0, 0, 0)), (FULL_W, y))
        y += ROI_SIZE

    draw.rectangle((0, height - FOOTER_H, width, height), fill=(255, 255, 255))
    draw.text(
        (8, height - 23),
        f"source RGB payload: {SOURCE_RGB_PATH.name}; variant A alpha reference: {VARIANT_A_PATH.name}",
        fill=(0, 0, 0),
        font=small,
    )
    sheet.save(out_path, quality=92)
    return sheet.size


def metrics_for(
    *,
    name: str,
    rgba: np.ndarray,
    final_mask: np.ndarray,
    variant_a_fg_px: int,
    defringe_px: int,
    extra: str,
) -> dict[str, int | float | str | list[int]]:
    fg_px = int(final_mask.sum())
    holes_open_count, holes_open_px = count_holes(final_mask)
    alpha_values = [int(v) for v in np.unique(rgba[:, :, 3])]
    return {
        "name": name,
        "fg_px": fg_px,
        "variant_A_fg_px": variant_a_fg_px,
        "fg_delta_vs_A": fg_px - variant_a_fg_px,
        "holes_open_count": holes_open_count,
        "holes_open_px": holes_open_px,
        "alpha_values": alpha_values,
        "defringe_px": int(defringe_px),
        "extra": extra,
    }


def build_variant_c(
    *,
    source_rgb: np.ndarray,
    source_luma: np.ndarray,
    source_chroma: np.ndarray,
    bria_fg: np.ndarray,
    variant_a_fg_px: int,
) -> dict[str, int | float | str | list[int]]:
    outer_bg = flood_outer_bg(source_luma, source_chroma)
    fg0 = ~outer_bg
    closed_fg = morph_close(fg0, 24)
    del outer_bg, fg0
    gc.collect()

    bria_holes, labels, _stats = enclosed_components(
        ~bria_fg,
        fg_for_ring=bria_fg,
        source_luma=source_luma,
        min_area=1000,
    )
    punched_holes = [hole for hole in bria_holes if hole.p10_luma < 150.0]
    punched_px = paint_component_ids(closed_fg, labels, punched_holes, False)
    del bria_holes, labels
    gc.collect()

    rgba, final_mask, defringe_px = finish_rgba(source_rgb, source_luma, closed_fg)
    del closed_fg
    write_png(C_OUT, rgba)
    metrics = metrics_for(
        name="C-washfull",
        rgba=rgba,
        final_mask=final_mask,
        variant_a_fg_px=variant_a_fg_px,
        defringe_px=defringe_px,
        extra=f"punched_ink_holes={len(punched_holes)} punched_px={punched_px}",
    )
    sheet_size = make_review_sheet(
        variant_name="C-washfull",
        rgba=rgba,
        final_mask=final_mask,
        source_luma=source_luma,
        metrics=metrics,
        out_path=C_REVIEW,
    )
    metrics["png"] = str(C_OUT)
    metrics["review_sheet"] = str(C_REVIEW)
    metrics["review_sheet_size"] = f"{sheet_size[0]}x{sheet_size[1]}"
    del rgba, final_mask, punched_holes
    gc.collect()
    return metrics


def build_variant_d(
    *,
    source_rgb: np.ndarray,
    source_luma: np.ndarray,
    variant_a_fg: np.ndarray,
    variant_a_fg_px: int,
) -> dict[str, int | float | str | list[int]]:
    editable = source_luma >= 243
    regularized = morph_open(morph_close(variant_a_fg, 16), 16)
    final_fg = (regularized & editable) | (variant_a_fg & ~editable)
    del regularized, editable
    cleaned_fg, removed_summary = remove_small_fg(final_fg, 64)
    del final_fg
    filled_fg, filled_count, filled_px = fill_transparent_specks(cleaned_fg, source_luma=source_luma)
    del cleaned_fg
    gc.collect()

    rgba, final_mask, defringe_px = finish_rgba(source_rgb, source_luma, filled_fg)
    del filled_fg
    write_png(D_OUT, rgba)
    metrics = metrics_for(
        name="D-smooth",
        rgba=rgba,
        final_mask=final_mask,
        variant_a_fg_px=variant_a_fg_px,
        defringe_px=defringe_px,
        extra=(
            f"removed_fg_specks={removed_summary['small_fg_removed_components']}/"
            f"{removed_summary['small_fg_removed_px']}px "
            f"filled_transparent_specks={filled_count}/{filled_px}px"
        ),
    )
    sheet_size = make_review_sheet(
        variant_name="D-smooth",
        rgba=rgba,
        final_mask=final_mask,
        source_luma=source_luma,
        metrics=metrics,
        out_path=D_REVIEW,
    )
    metrics["png"] = str(D_OUT)
    metrics["review_sheet"] = str(D_REVIEW)
    metrics["review_sheet_size"] = f"{sheet_size[0]}x{sheet_size[1]}"
    del rgba, final_mask
    gc.collect()
    return metrics


def print_metric(metric: dict[str, int | float | str | list[int]]) -> None:
    print(
        (
            f"{metric['name']}: png={metric['png']} review={metric['review_sheet']} "
            f"review_size={metric['review_sheet_size']} fg_px={metric['fg_px']} "
            f"variant_A_fg_px={metric['variant_A_fg_px']} "
            f"fg_delta_vs_A={metric['fg_delta_vs_A']} "
            f"holes_open_count={metric['holes_open_count']} "
            f"holes_open_px={metric['holes_open_px']} "
            f"alpha_values={metric['alpha_values']} "
            f"defringe_px={metric['defringe_px']} {metric['extra']}"
        ),
        flush=True,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    source_rgb, source_luma, source_chroma, bria_fg, variant_a_fg = load_inputs()
    variant_a_fg_px = int(variant_a_fg.sum())
    print(f"source_rgb: {SOURCE_RGB_PATH}", flush=True)
    print(f"variant_a: {VARIANT_A_PATH}", flush=True)
    print(f"image_size: {source_rgb.shape[1]}x{source_rgb.shape[0]}", flush=True)
    print(f"variant_A_fg_px={variant_a_fg_px}", flush=True)

    metric_c = build_variant_c(
        source_rgb=source_rgb,
        source_luma=source_luma,
        source_chroma=source_chroma,
        bria_fg=bria_fg,
        variant_a_fg_px=variant_a_fg_px,
    )
    print_metric(metric_c)

    metric_d = build_variant_d(
        source_rgb=source_rgb,
        source_luma=source_luma,
        variant_a_fg=variant_a_fg,
        variant_a_fg_px=variant_a_fg_px,
    )
    print_metric(metric_d)


if __name__ == "__main__":
    main()
