#!/usr/bin/env python3
"""Generate local lower-left foreground repair variants for the Berlin banked image."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png"
OUT_DIR = Path(__file__).resolve().parent

EDIT_BOX = (0, 2050, 620, 2920)
ZOOM_BOX = (0, 1960, 760, 3040)


@dataclass(frozen=True)
class Variant:
    stem: str
    label: str
    method: str
    caveat: str
    image: np.ndarray


def rect_mask(size: tuple[int, int], boxes: list[tuple[int, int, int, int, float]], blur: float) -> np.ndarray:
    width, height = size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for x0, y0, x1, y1, strength in boxes:
        draw.rectangle((x0, y0, x1, y1), fill=int(round(255 * strength)))
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return np.clip(np.asarray(mask, dtype=np.float32) / 255.0, 0.0, 1.0)


def ellipse_mask(size: tuple[int, int], ellipses: list[tuple[int, int, int, int, float]], blur: float) -> np.ndarray:
    width, height = size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for x0, y0, x1, y1, strength in ellipses:
        draw.ellipse((x0, y0, x1, y1), fill=int(round(255 * strength)))
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return np.clip(np.asarray(mask, dtype=np.float32) / 255.0, 0.0, 1.0)


def line_mask(size: tuple[int, int], lines: list[tuple[tuple[int, int], tuple[int, int], int, float]], blur: float) -> np.ndarray:
    width, height = size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for start, end, thickness, strength in lines:
        draw.line((start, end), fill=int(round(255 * strength)), width=thickness)
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return np.clip(np.asarray(mask, dtype=np.float32) / 255.0, 0.0, 1.0)


def blend(base: np.ndarray, repaired: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = alpha[..., None].astype(np.float32)
    out = base.astype(np.float32) * (1.0 - a) + repaired.astype(np.float32) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def enforce_edit_box(base_full: np.ndarray, region_rgb: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = EDIT_BOX
    full = base_full.copy()
    full[y0:y1, x0:x1] = region_rgb
    return full


def make_inpaint(region: np.ndarray, mask: np.ndarray, radius: int = 5, telea: bool = True) -> np.ndarray:
    binary = np.where(mask > 0.08, 255, 0).astype(np.uint8)
    bgr = cv2.cvtColor(region, cv2.COLOR_RGB2BGR)
    method = cv2.INPAINT_TELEA if telea else cv2.INPAINT_NS
    out = cv2.inpaint(bgr, binary, radius, method)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def horizontal_texture_patch(region: np.ndarray) -> np.ndarray:
    """Replace narrow vertical wipes with same-row samples from their edges."""
    patch_boxes = [
        (162, 124, 202, 555, 0.95),
        (224, 76, 256, 426, 0.86),
        (278, 132, 308, 448, 0.82),
        (404, 330, 466, 650, 0.56),
    ]
    height, width = region.shape[:2]
    out = region.astype(np.float32).copy()
    for x0, y0, x1, y1, strength in patch_boxes:
        x0 = max(0, min(width - 1, x0))
        x1 = max(x0 + 1, min(width, x1))
        y0 = max(0, min(height - 1, y0))
        y1 = max(y0 + 1, min(height, y1))
        left0 = max(0, x0 - 34)
        left1 = max(left0 + 1, x0 - 5)
        right0 = min(width - 1, x1 + 5)
        right1 = min(width, x1 + 38)
        left = np.median(region[y0:y1, left0:left1], axis=1).astype(np.float32)
        right = np.median(region[y0:y1, right0:right1], axis=1).astype(np.float32)
        t = np.linspace(0.0, 1.0, x1 - x0, dtype=np.float32)[None, :, None]
        fill = left[:, None, :] * (1.0 - t) + right[:, None, :] * t
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1.0 - strength) + fill * strength

    out = np.clip(out, 0, 255).astype(np.uint8)
    return watercolor_soften(out)


def hsv_tone(region: np.ndarray, value_scale: float, saturation_scale: float, value_shift: float = 0.0) -> np.ndarray:
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation_scale, 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * value_scale + value_shift, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def watercolor_soften(region: np.ndarray) -> np.ndarray:
    softened = cv2.bilateralFilter(region, 9, 35, 35)
    blur = cv2.GaussianBlur(softened, (0, 0), 1.0)
    return np.clip(softened.astype(np.float32) * 0.72 + blur.astype(np.float32) * 0.28, 0, 255).astype(np.uint8)


def luminance_whiteness_mask(region: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1].astype(np.float32)
    val = hsv[..., 2].astype(np.float32)
    white = ((val - 184.0) / 58.0) * ((90.0 - sat) / 90.0)
    white = np.clip(white, 0.0, 1.0)
    y = np.arange(region.shape[0])[:, None]
    x = np.arange(region.shape[1])[None, :]
    lower_foreground = (y > 70) & (y < 675) & (x < 618)
    return cv2.GaussianBlur((white * lower_foreground).astype(np.float32), (0, 0), 2.5)


def edge_feather(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    y = np.arange(height, dtype=np.float32)[:, None]
    x = np.arange(width, dtype=np.float32)[None, :]
    right = np.clip((width - 1 - x) / 88.0, 0.0, 1.0)
    top = np.clip(y / 58.0, 0.0, 1.0)
    lower = np.clip((760.0 - y) / 128.0, 0.0, 1.0)
    return right * top * lower


def build_masks(region: np.ndarray) -> dict[str, np.ndarray]:
    height, width = region.shape[:2]
    size = (width, height)
    feather = edge_feather((height, width))

    hard_wipes = rect_mask(
        size,
        [
            (162, 124, 202, 555, 0.92),
            (224, 76, 256, 426, 0.72),
            (278, 132, 308, 448, 0.68),
            (404, 330, 466, 650, 0.34),
            (540, 340, 594, 642, 0.18),
        ],
        blur=8,
    )
    fog_band = rect_mask(
        size,
        [
            (0, 370, 545, 610, 0.34),
            (88, 438, 520, 692, 0.25),
            (0, 555, 388, 686, 0.16),
        ],
        blur=24,
    )
    column_wash = rect_mask(
        size,
        [
            (365, 220, 560, 640, 0.20),
            (500, 285, 590, 675, 0.12),
        ],
        blur=20,
    )
    tree_pockets = ellipse_mask(
        size,
        [
            (18, 170, 210, 575, 0.24),
            (130, 138, 342, 455, 0.18),
            (208, 325, 474, 620, 0.14),
        ],
        blur=22,
    )
    white_auto = luminance_whiteness_mask(region)
    hard_wipes *= feather
    fog_band *= feather
    column_wash *= feather
    tree_pockets *= feather
    white_auto *= feather
    target = np.clip(hard_wipes + fog_band * 0.48 + column_wash * 0.42 + white_auto * 0.34, 0, 1)
    return {
        "hard_wipes": hard_wipes,
        "fog_band": fog_band,
        "column_wash": column_wash,
        "tree_pockets": tree_pockets,
        "white_auto": white_auto,
        "target": target,
    }


def variant_sampled_texture(region: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    sampled = horizontal_texture_patch(region)
    toned = hsv_tone(sampled, value_scale=0.94, saturation_scale=1.08, value_shift=-2)
    sampled = blend(sampled, toned, np.clip(masks["fog_band"] * 0.22 + masks["column_wash"] * 0.16, 0, 0.24))
    alpha = np.clip(masks["hard_wipes"] * 0.88 + masks["fog_band"] * 0.20 + masks["white_auto"] * 0.16, 0, 0.88)
    return blend(region, sampled, alpha)


def variant_haze_thinning(region: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    toned = hsv_tone(region, value_scale=0.88, saturation_scale=1.18, value_shift=-5)
    local_contrast = cv2.addWeighted(region, 1.22, cv2.GaussianBlur(region, (0, 0), 12), -0.22, 0)
    repaired = np.clip(toned.astype(np.float32) * 0.62 + local_contrast.astype(np.float32) * 0.38, 0, 255).astype(np.uint8)
    alpha = np.clip(masks["fog_band"] * 0.50 + masks["white_auto"] * 0.34 + masks["column_wash"] * 0.28, 0, 0.52)
    return blend(region, watercolor_soften(repaired), alpha)


def variant_soft_wash(region: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    patched = horizontal_texture_patch(region)
    softened = watercolor_soften(cv2.bilateralFilter(patched, 11, 42, 42))
    wash = hsv_tone(softened, value_scale=0.97, saturation_scale=1.03, value_shift=-1)
    alpha = np.clip(masks["hard_wipes"] * 0.44 + masks["fog_band"] * 0.23 + masks["column_wash"] * 0.16, 0, 0.44)
    return blend(region, wash, alpha)


def variant_tree_silhouette(region: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    base = variant_sampled_texture(region, masks)
    layer = Image.fromarray(base.copy()).convert("RGBA")
    draw = ImageDraw.Draw(layer, "RGBA")

    trunk = (66, 83, 77, 42)
    branch = (70, 86, 78, 34)
    leaf_dark = (110, 125, 88, 18)
    leaf_gold = (177, 170, 103, 18)

    for line in [((170, 210), (153, 550), 4), ((198, 180), (198, 455), 3), ((246, 125), (234, 410), 2), ((288, 180), (298, 440), 2)]:
        draw.line((line[0], line[1]), fill=trunk, width=line[2])
    for line in [((170, 360), (102, 250), 2), ((184, 334), (240, 240), 2), ((205, 430), (274, 316), 2), ((148, 510), (58, 454), 2), ((247, 420), (338, 360), 2)]:
        draw.line((line[0], line[1]), fill=branch, width=line[2])

    rng = np.random.default_rng(12)
    centers = [(150, 260), (228, 230), (110, 430), (282, 360), (344, 510)]
    for cx, cy in centers:
        for _ in range(12):
            rx = int(rng.normal(cx, 44))
            ry = int(rng.normal(cy, 38))
            rad = int(rng.integers(2, 7))
            color = leaf_gold if rng.random() > 0.45 else leaf_dark
            draw.ellipse((rx - rad, ry - rad, rx + rad, ry + rad), fill=color)

    painted = np.asarray(layer.filter(ImageFilter.GaussianBlur(1.25)).convert("RGB")).astype(np.uint8)
    alpha = np.clip(masks["hard_wipes"] * 0.36 + masks["fog_band"] * 0.08 + masks["tree_pockets"] * 0.06, 0, 0.36)
    return blend(base, painted, alpha)


def variant_conservative(region: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    sampled = variant_sampled_texture(region, masks)
    thinned = variant_haze_thinning(region, masks)
    combined = np.clip(sampled.astype(np.float32) * 0.48 + thinned.astype(np.float32) * 0.52, 0, 255).astype(np.uint8)
    alpha = np.clip(masks["hard_wipes"] * 0.28 + masks["fog_band"] * 0.18 + masks["white_auto"] * 0.16, 0, 0.30)
    return blend(region, combined, alpha)


def save_outputs(base_full: np.ndarray, variants: list[Variant]) -> None:
    crop_manifest = []
    for variant in variants:
        full = enforce_edit_box(base_full, variant.image)
        candidate_path = OUT_DIR / f"{variant.stem}.png"
        crop_path = OUT_DIR / f"{variant.stem}_zoom_x0-760_y1960-3040.png"
        Image.fromarray(full).save(candidate_path)
        Image.fromarray(full).crop(ZOOM_BOX).save(crop_path)
        crop_manifest.append((variant, crop_path))

    crops = [Image.open(OUT_DIR / "baseline_zoom_reference.png")] if (OUT_DIR / "baseline_zoom_reference.png").exists() else []
    labels = ["baseline"] if crops else []
    for variant, crop_path in crop_manifest:
        crops.append(Image.open(crop_path))
        labels.append(variant.stem)
    if crops:
        thumb_w, thumb_h = 304, 432
        board = Image.new("RGB", (thumb_w * len(crops), thumb_h + 34), (244, 242, 234))
        draw = ImageDraw.Draw(board)
        for idx, (label, crop) in enumerate(zip(labels, crops)):
            thumb = crop.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            board.paste(thumb, (idx * thumb_w, 34))
            draw.text((idx * thumb_w + 8, 10), label, fill=(39, 46, 50))
        board.save(OUT_DIR / "candidate_crops_contact_sheet.png")


def main() -> None:
    base = np.asarray(Image.open(BASELINE).convert("RGB"))
    x0, y0, x1, y1 = EDIT_BOX
    region = base[y0:y1, x0:x1].copy()
    masks = build_masks(region)

    variants = [
        Variant(
            "foreground_clean_01_sampled_texture_patch",
            "Sampled tree/sky/column texture patch",
            "Inpainted the hard white vertical wipes and fog band, then blended nearby tree and column texture with watercolor softening.",
            "Most assertive local cleanup; can slightly invent midground foliage texture in the masked wipe zones.",
            variant_sampled_texture(region, masks),
        ),
        Variant(
            "foreground_clean_02_haze_thinning",
            "Haze thinning",
            "Reduced the low-saturation white fog band with local value reduction, saturation recovery, and gentle contrast while avoiding heavy replacement.",
            "Keeps more original paint, so the thinnest white pole traces remain visible.",
            variant_haze_thinning(region, masks),
        ),
        Variant(
            "foreground_clean_03_soft_watercolor_wash",
            "Soft watercolor wash",
            "Used a broad, soft inpaint and muted blue/olive/column wash to make the erased band read as intentional atmospheric paint.",
            "Softest result; less structural recovery in trees.",
            variant_soft_wash(region, masks),
        ),
        Variant(
            "foreground_clean_04_tree_silhouette_restoration",
            "Tree-silhouette restoration",
            "Started from sampled texture cleanup, then restored soft trunk, branch, and foliage silhouettes through the wiped tree area.",
            "Adds the most new silhouette information and should be judged for whether the restored trees feel natural.",
            variant_tree_silhouette(region, masks),
        ),
        Variant(
            "foreground_clean_05_conservative_blend",
            "Conservative blend",
            "Low-alpha blend of sampled texture repair and haze thinning for the least invasive artifact reduction.",
            "Safest preservation, but leaves more of the original fog artifact than the stronger variants.",
            variant_conservative(region, masks),
        ),
    ]

    save_outputs(base, variants)
    manifest = OUT_DIR / "generated_manifest.txt"
    manifest.write_text(
        "\n".join(
            [
                f"{v.stem}.png\t{v.label}\t{v.method}\t{v.caveat}"
                for v in variants
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
