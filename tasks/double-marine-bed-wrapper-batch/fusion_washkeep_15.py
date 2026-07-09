#!/usr/bin/env python3
"""Variant B wash-pocket restoration for double Marine Bed Wrapper image 15."""

from __future__ import annotations

import gc
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


REPO_ROOT = Path(__file__).resolve().parents[2]
VARIANT_A_PATH = REPO_ROOT / (
    "Images/candidates/batch-fusion/15-fusion-Tw250-erode1-defringe.png"
)
SOURCE_RGB_PATH = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/finals/"
    "15-ChatGPT_Image_Jul_7_2026_11_34_15_AM@x8-bg-removed.png"
)
OUT_DIR = REPO_ROOT / "Images/candidates/batch-fusion"
REVIEW_DIR = REPO_ROOT / "REVIEW/batch-fusion"
THRESHOLDS = (130, 150, 170)
RING_KERNEL = np.ones((11, 11), dtype=np.uint8)
ROI_SIZE = 720
COL_W = 720
FULL_H = 480
HEADER_H = 104
LABEL_H = 36
FOOTER_H = 28


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


def load_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with Image.open(VARIANT_A_PATH) as variant_im:
        variant_rgba = np.array(variant_im.convert("RGBA"), dtype=np.uint8)
    with Image.open(SOURCE_RGB_PATH) as source_im:
        source_rgb = np.array(source_im.convert("RGB"), dtype=np.uint8)
    if variant_rgba.shape[:2] != source_rgb.shape[:2]:
        raise RuntimeError(
            f"dimension mismatch: variant={variant_rgba.shape[:2]} source={source_rgb.shape[:2]}"
        )
    source_luma = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    return variant_rgba, source_rgb, source_luma


def label_transparent_components(alpha: np.ndarray) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    transparent = (alpha == 0).astype(np.uint8)
    labels_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        transparent, 8
    )
    del transparent
    return labels_count, labels, stats, centroids


def border_touch_labels(labels: np.ndarray, labels_count: int) -> np.ndarray:
    touches = np.zeros(labels_count, dtype=bool)
    border_ids = np.concatenate(
        (labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1])
    )
    touches[np.unique(border_ids)] = True
    touches[0] = False
    return touches


def component_p10_luma(
    *,
    label_id: int,
    labels: np.ndarray,
    stats: np.ndarray,
    alpha: np.ndarray,
    source_luma: np.ndarray,
) -> float:
    x = int(stats[label_id, cv2.CC_STAT_LEFT])
    y = int(stats[label_id, cv2.CC_STAT_TOP])
    w = int(stats[label_id, cv2.CC_STAT_WIDTH])
    h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
    height, width = alpha.shape
    x0 = max(0, x - 5)
    y0 = max(0, y - 5)
    x1 = min(width, x + w + 5)
    y1 = min(height, y + h + 5)

    label_crop = labels[y0:y1, x0:x1]
    comp = (label_crop == label_id).astype(np.uint8)
    dilated = cv2.dilate(comp, RING_KERNEL, iterations=1).astype(bool)
    ring = dilated & (alpha[y0:y1, x0:x1] != 0)
    if not bool(ring.any()):
        return 255.0
    return float(np.percentile(source_luma[y0:y1, x0:x1][ring], 10))


def classify_holes(
    labels_count: int,
    labels: np.ndarray,
    stats: np.ndarray,
    centroids: np.ndarray,
    alpha: np.ndarray,
    source_luma: np.ndarray,
) -> list[Hole]:
    touches_border = border_touch_labels(labels, labels_count)
    holes: list[Hole] = []
    for label_id in range(1, labels_count):
        if touches_border[label_id]:
            continue
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        x = int(stats[label_id, cv2.CC_STAT_LEFT])
        y = int(stats[label_id, cv2.CC_STAT_TOP])
        w = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        p10_luma = component_p10_luma(
            label_id=label_id,
            labels=labels,
            stats=stats,
            alpha=alpha,
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
    return holes


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


def paint_components(mask: np.ndarray, labels: np.ndarray, holes: list[Hole]) -> None:
    for hole in holes:
        x, y, w, h = hole.bbox_xywh
        crop = mask[y : y + h, x : x + w]
        crop[labels[y : y + h, x : x + w] == hole.label_id] = True


def composite_on_bg(rgba: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", rgba.size, (*bg, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def full_composite_tile(rgba: np.ndarray, bg: tuple[int, int, int]) -> Image.Image:
    work = Image.fromarray(rgba).resize((COL_W, FULL_H), Image.Resampling.LANCZOS)
    return composite_on_bg(work, bg)


def roi_tile(rgba: np.ndarray, box: tuple[int, int, int, int], bg: tuple[int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    crop = Image.fromarray(rgba[y0:y1, x0:x1])
    return composite_on_bg(crop, bg)


def roi_rows(
    restored_holes: list[Hole],
    kept_holes: list[Hole],
    image_size: tuple[int, int],
) -> list[tuple[str, tuple[int, int, int, int], Hole | None]]:
    rows: list[tuple[str, tuple[int, int, int, int], Hole | None]] = []
    for idx, hole in enumerate(sorted(restored_holes, key=lambda h: h.area, reverse=True)[:3], 1):
        rows.append((f"RESTORED wash pocket {idx}", crop_box(hole.center_xy, image_size), hole))
    if kept_holes:
        kept = sorted(kept_holes, key=lambda h: h.area, reverse=True)[0]
        rows.append(("KEPT true ink-bounded hole", crop_box(kept.center_xy, image_size), kept))

    center = (image_size[0] / 2, image_size[1] / 2)
    while len(rows) < 4:
        rows.append(("NO COMPONENT AVAILABLE", crop_box(center, image_size), None))
    return rows[:4]


def make_review_sheet(
    *,
    threshold: int,
    output_rgba: np.ndarray,
    restored_holes: list[Hole],
    kept_holes: list[Hole],
    out_path: Path,
) -> tuple[int, int]:
    font = get_font(22)
    small = get_font(16)
    image_size = (output_rgba.shape[1], output_rgba.shape[0])
    rows = roi_rows(restored_holes, kept_holes, image_size)
    width = COL_W * 2
    height = HEADER_H + FULL_H + len(rows) * (LABEL_H + ROI_SIZE) + FOOTER_H
    sheet = Image.new("RGB", (width, height), (232, 232, 232))
    draw = ImageDraw.Draw(sheet)

    draw.rectangle((0, 0, width, HEADER_H), fill=(255, 255, 255))
    draw.text((12, 10), f"image 15 washkeep ink{threshold}", fill=(0, 0, 0), font=font)
    draw.text(
        (12, 48),
        (
            f"kept true holes={len(kept_holes)}  restored wash pockets={len(restored_holes)}  "
            f"restored_px={sum(h.area for h in restored_holes)}"
        ),
        fill=(0, 0, 0),
        font=small,
    )
    draw.text(
        (12, 74),
        "columns: mid grey composite | black composite",
        fill=(0, 0, 0),
        font=small,
    )

    y = HEADER_H
    for x, label, bg in (
        (0, "full over mid grey", (128, 128, 128)),
        (COL_W, "full over black", (0, 0, 0)),
    ):
        sheet.paste(full_composite_tile(output_rgba, bg), (x, y))
        draw.rectangle((x, y, x + COL_W, y + 28), fill=(255, 255, 255))
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0), font=small)
    y += FULL_H

    for label, box, hole in rows:
        x0, y0, x1, y1 = box
        if hole is None:
            info = f"{label}: crop=({x0},{y0},{x1},{y1})"
        else:
            info = (
                f"{label}: component={hole.label_id} area={hole.area} "
                f"p10_luma={hole.p10_luma:.1f} crop=({x0},{y0},{x1},{y1})"
            )
        draw.rectangle((0, y, width, y + LABEL_H), fill=(250, 250, 250))
        draw.text((8, y + 9), info, fill=(0, 0, 0), font=small)
        y += LABEL_H
        sheet.paste(roi_tile(output_rgba, box, (128, 128, 128)), (0, y))
        sheet.paste(roi_tile(output_rgba, box, (0, 0, 0)), (COL_W, y))
        y += ROI_SIZE

    draw.rectangle((0, height - FOOTER_H, width, height), fill=(255, 255, 255))
    draw.text(
        (8, height - 22),
        f"source: {SOURCE_RGB_PATH.name}; variant A alpha holes classified by 5px luma ring",
        fill=(0, 0, 0),
        font=small,
    )
    sheet.save(out_path, quality=92)
    return sheet.size


def output_path(threshold: int) -> Path:
    return OUT_DIR / f"15-fusion-washkeep-ink{threshold}.png"


def review_path(threshold: int) -> Path:
    return REVIEW_DIR / f"15-washkeep-ink{threshold}-review-sheet.jpg"


def write_png(path: Path, rgba: np.ndarray) -> None:
    Image.fromarray(rgba).save(path, compress_level=6)


def process_threshold(
    *,
    threshold: int,
    variant_rgba: np.ndarray,
    source_rgb: np.ndarray,
    labels: np.ndarray,
    holes: list[Hole],
) -> dict[str, object]:
    restored_holes = [h for h in holes if h.p10_luma >= threshold]
    kept_holes = [h for h in holes if h.p10_luma < threshold]

    restore_mask = np.zeros(labels.shape, dtype=bool)
    paint_components(restore_mask, labels, restored_holes)

    output_rgba = variant_rgba.copy()
    output_rgba[restore_mask, :3] = source_rgb[restore_mask]
    alpha = ((variant_rgba[:, :, 3] != 0) | restore_mask).astype(np.uint8) * 255
    output_rgba[:, :, 3] = alpha

    png_path = output_path(threshold)
    jpg_path = review_path(threshold)
    write_png(png_path, output_rgba)
    sheet_size = make_review_sheet(
        threshold=threshold,
        output_rgba=output_rgba,
        restored_holes=restored_holes,
        kept_holes=kept_holes,
        out_path=jpg_path,
    )
    vals = [int(v) for v in np.unique(output_rgba[:, :, 3])]
    metrics: dict[str, object] = {
        "threshold": threshold,
        "holes_kept_true": len(kept_holes),
        "holes_restored_wash": len(restored_holes),
        "pixels_restored": int(restore_mask.sum()),
        "alpha_values": vals,
        "output_png": str(png_path),
        "review_sheet": str(jpg_path),
        "review_sheet_size": sheet_size,
    }
    print(
        (
            f"ink{threshold}: holes_kept_true={metrics['holes_kept_true']} "
            f"holes_restored_wash={metrics['holes_restored_wash']} "
            f"pixels_restored={metrics['pixels_restored']} "
            f"alpha_values={vals} png={png_path} review={jpg_path} "
            f"review_size={sheet_size[0]}x{sheet_size[1]}"
        ),
        flush=True,
    )
    del restore_mask, output_rgba, alpha
    gc.collect()
    return metrics


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    variant_rgba, source_rgb, source_luma = load_inputs()
    alpha = variant_rgba[:, :, 3]
    labels_count, labels, stats, centroids = label_transparent_components(alpha)
    holes = classify_holes(labels_count, labels, stats, centroids, alpha, source_luma)

    border_touching = labels_count - 1 - len(holes)
    print(f"variant_a: {VARIANT_A_PATH}", flush=True)
    print(f"source_rgb: {SOURCE_RGB_PATH}", flush=True)
    print(
        (
            f"transparent_components_total={labels_count - 1} "
            f"border_touching={border_touching} enclosed_holes={len(holes)}"
        ),
        flush=True,
    )
    for threshold in THRESHOLDS:
        process_threshold(
            threshold=threshold,
            variant_rgba=variant_rgba,
            source_rgb=source_rgb,
            labels=labels,
            holes=holes,
        )


if __name__ == "__main__":
    main()
