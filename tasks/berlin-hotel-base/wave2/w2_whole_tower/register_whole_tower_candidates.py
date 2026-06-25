#!/usr/bin/env python3
"""Register existing complete Ritz/Beisheim tower plates into the Berlin artwork."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path("/Users/za/Documents/product images repo")
TASK = ROOT / "tasks/berlin-hotel-base"
OUT = TASK / "wave2/w2_whole_tower"
SRC_PATH = TASK / "work/src.png"

VERIFY_BOX = (3162, 2582, 4082, 2845)
EDIT_BOX = (3162, 2582, 4082, 2828)
ZOOM_BOX = (3050, 2480, 4120, 2900)
CONTEXT_BOX = (3000, 1150, 4140, 2900)
FACADE_REF_BOX = (3162, 2350, 4082, 2582)


@dataclass(frozen=True)
class PlateSpec:
    name: str
    source: Path
    crop: tuple[int, int, int, int]
    dst_quad: tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]
    color_strength: float
    verdict: str
    alpha_scale: float = 1.0
    top_start: float = 0.84
    top_feather: int = 18
    bottom_end: float = 0.72
    blur_radius: float = 0.0


PLATES = [
    PlateSpec(
        name="openai_v2_generated_plate",
        source=OUT / "generated_plate_openai_v2.png",
        crop=(42, 31, 936, 1577),
        dst_quad=((3048, 1150), (4078, 1166), (4090, 2828), (3042, 2828)),
        color_strength=0.50,
        verdict="fresh full-tower plate with lower floors continuing the same pier/window rhythm",
    ),
    PlateSpec(
        name="openai_v2_generated_plate_softblend",
        source=OUT / "generated_plate_openai_v2.png",
        crop=(42, 31, 936, 1577),
        dst_quad=((3048, 1150), (4078, 1166), (4090, 2828), (3042, 2828)),
        color_strength=0.58,
        verdict="same fresh plate with softer watercolor integration and longer seam feather",
        alpha_scale=0.86,
        top_start=0.28,
        top_feather=58,
        bottom_end=0.46,
        blur_radius=0.45,
    ),
    PlateSpec(
        name="openai_p2_clean_masonry",
        source=TASK / "work/building_recreate/cand_openai_p2.png",
        crop=(77, 19, 828, 1600),
        dst_quad=((3065, 1168), (4052, 1192), (4087, 2828), (3052, 2828)),
        color_strength=0.58,
        verdict="cleanest continuous masonry base; flatter than source but no canopy/glass hall",
    ),
    PlateSpec(
        name="flux2_p1_perspective",
        source=TASK / "work/building_recreate/cand_flux2_p1.png",
        crop=(58, 0, 1038, 1694),
        dst_quad=((3055, 1152), (4078, 1166), (4090, 2828), (3044, 2828)),
        color_strength=0.28,
        verdict="best perspective/style continuity; base is darker and more storefront-like",
    ),
    PlateSpec(
        name="openai_p2_lower_shaft_sample",
        source=TASK / "work/building_recreate/cand_openai_p2.png",
        crop=(77, 19, 828, 1600),
        dst_quad=((3065, 1342), (4052, 1366), (4087, 3002), (3052, 3002)),
        color_strength=0.62,
        verdict="samples the complete plate's lower-shaft rhythm to avoid its generated storefront block",
    ),
]


def as_rgb_array(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def warp_plate(spec: PlateSpec, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    plate = as_rgb_array(spec.source)
    x0, y0, x1, y1 = spec.crop
    crop = plate[y0:y1, x0:x1]
    h, w = crop.shape[:2]
    src_quad = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    dst_quad = np.float32(spec.dst_quad)
    matrix = cv2.getPerspectiveTransform(src_quad, dst_quad)
    out_h, out_w = shape[:2]
    warped = cv2.warpPerspective(
        crop,
        matrix,
        (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    mask_src = np.full((h, w), 255, dtype=np.uint8)
    mask = cv2.warpPerspective(
        mask_src,
        matrix,
        (out_w, out_h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return warped, mask


def mild_color_match(patch: np.ndarray, reference: np.ndarray, strength: float) -> np.ndarray:
    patch_f = patch.astype(np.float32)
    ref_f = reference.astype(np.float32)
    # Ignore near-white paper/background and very dark ink specks when estimating tone.
    p_luma = patch_f.mean(axis=2)
    r_luma = ref_f.mean(axis=2)
    p_sel = patch_f[(p_luma > 35) & (p_luma < 245)]
    r_sel = ref_f[(r_luma > 35) & (r_luma < 235)]
    if len(p_sel) < 100 or len(r_sel) < 100:
        return patch
    p_mean, p_std = p_sel.mean(axis=0), p_sel.std(axis=0) + 1e-3
    r_mean, r_std = r_sel.mean(axis=0), r_sel.std(axis=0) + 1e-3
    matched = (patch_f - p_mean) * (r_std / p_std) + r_mean
    blended = patch_f * (1.0 - strength) + matched * strength
    return np.clip(blended, 0, 255).astype(np.uint8)


def edit_alpha(width: int, height: int, spec: PlateSpec) -> np.ndarray:
    alpha = np.ones((height, width), dtype=np.float32)
    top = min(spec.top_feather, height)
    bottom = min(12, height)
    left = min(8, width)
    right = min(8, width)
    alpha[:top, :] *= np.linspace(spec.top_start, 1.0, top, dtype=np.float32)[:, None]
    alpha[-bottom:, :] *= np.linspace(1.0, spec.bottom_end, bottom, dtype=np.float32)[:, None]
    alpha[:, :left] *= np.linspace(0.75, 1.0, left, dtype=np.float32)[None, :]
    alpha[:, -right:] *= np.linspace(1.0, 0.78, right, dtype=np.float32)[None, :]
    alpha *= spec.alpha_scale
    return alpha[..., None]


def save_zoom(candidate: Image.Image, path: Path) -> None:
    zoom = candidate.crop(ZOOM_BOX)
    zoom.save(path)
    zoom.resize((zoom.width * 2, zoom.height * 2), Image.Resampling.LANCZOS).save(
        path.with_name(path.stem + "_2x.png")
    )


def save_registered_context(src: np.ndarray, warped: np.ndarray, mask: np.ndarray, spec: PlateSpec) -> None:
    overlay = src.copy()
    m = (mask > 0)[..., None]
    overlay = np.where(m, (0.58 * overlay + 0.42 * warped).astype(np.uint8), overlay)
    im = Image.fromarray(overlay).crop(CONTEXT_BOX)
    draw = ImageDraw.Draw(im)
    vx0, vy0, vx1, vy1 = VERIFY_BOX
    ex0, ey0, ex1, ey1 = EDIT_BOX
    cx0, cy0 = CONTEXT_BOX[:2]
    draw.rectangle((vx0 - cx0, vy0 - cy0, vx1 - cx0, vy1 - cy0), outline=(255, 0, 0), width=4)
    draw.rectangle((ex0 - cx0, ey0 - cy0, ex1 - cx0, ey1 - cy0), outline=(0, 90, 255), width=3)
    im.save(OUT / f"{spec.name}_registered_context.png")


def build_candidate(spec: PlateSpec, src: np.ndarray) -> Path:
    warped, plate_mask = warp_plate(spec, src.shape)
    save_registered_context(src, warped, plate_mask, spec)

    x0, y0, x1, y1 = EDIT_BOX
    ref = src[FACADE_REF_BOX[1] : FACADE_REF_BOX[3], FACADE_REF_BOX[0] : FACADE_REF_BOX[2]]
    patch = mild_color_match(warped[y0:y1, x0:x1], ref, spec.color_strength)
    if spec.blur_radius:
        patch = np.asarray(Image.fromarray(patch).filter(ImageFilter.GaussianBlur(spec.blur_radius)))
    base = src[y0:y1, x0:x1].astype(np.float32)
    alpha = edit_alpha(x1 - x0, y1 - y0, spec)
    merged = np.clip(base * (1.0 - alpha) + patch.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    out = src.copy()
    out[y0:y1, x0:x1] = merged
    image = Image.fromarray(out)
    cand_path = OUT / f"w2_whole_tower_{spec.name}_composited.png"
    image.save(cand_path)
    save_zoom(image, OUT / f"w2_whole_tower_{spec.name}_zoom.png")
    Image.fromarray(patch).save(OUT / f"{spec.name}_registered_base_patch.png")
    return cand_path


def save_contact_sheet(paths: list[Path]) -> None:
    labels = ["source"] + [p.name.replace("w2_whole_tower_", "").replace("_composited.png", "") for p in paths]
    images = [Image.open(SRC_PATH).convert("RGB")] + [Image.open(p).convert("RGB") for p in paths]
    crops = [im.crop(ZOOM_BOX) for im in images]
    thumb_w, thumb_h = 420, 165
    pad, label_h = 18, 26
    sheet = Image.new("RGB", (thumb_w + 2 * pad, len(crops) * (thumb_h + label_h + pad) + pad), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (label, crop) in enumerate(zip(labels, crops)):
        crop.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad
        y = pad + i * (thumb_h + label_h + pad)
        sheet.paste(crop, (x, y))
        draw.text((x, y + crop.height + 6), label, fill=(20, 20, 20))
    sheet.save(OUT / "candidate_zoom_contact_sheet.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    src = as_rgb_array(SRC_PATH)
    outputs = [build_candidate(spec, src) for spec in PLATES]
    save_contact_sheet(outputs)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
