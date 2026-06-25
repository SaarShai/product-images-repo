#!/usr/bin/env python3
"""OpenAI p1/p2/p3 registration experiments for the Berlin hotel base."""

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
PLATE_PATH = TASK / "work/building_recreate/cand_openai_p1.png"

VERIFY_BOX = (3162, 2582, 4082, 2845)
ZOOM_BOX = (3050, 2480, 4120, 2900)
CONTEXT_BOX = (3000, 1150, 4140, 2900)
FACADE_REF_BOX = (3162, 2240, 4082, 2582)

SOURCE_PERIOD = 90.0
PLATE_PERIOD = 66.0
RHYTHM_SCALE = SOURCE_PERIOD / PLATE_PERIOD


@dataclass(frozen=True)
class Experiment:
    name: str
    crop: tuple[int, int, int, int]
    bottom_y: int
    left_x: int
    edit_box: tuple[int, int, int, int]
    top_inset: int
    color_strength: float
    alpha_scale: float
    top_start: float
    top_feather: int
    bottom_end: float
    bottom_feather: int
    blur_radius: float
    preserve_right: bool = False
    occlusion: bool = False
    notes: str = ""


EXPERIMENTS = [
    Experiment(
        name="p123_rhythm_fullmask",
        crop=(77, 19, 828, 1600),
        bottom_y=2845,
        left_x=3050,
        edit_box=VERIFY_BOX,
        top_inset=18,
        color_strength=0.62,
        alpha_scale=0.92,
        top_start=0.38,
        top_feather=52,
        bottom_end=0.42,
        bottom_feather=28,
        blur_radius=0.35,
        notes="actual building bbox, rhythm scale, full allowed box",
    ),
    Experiment(
        name="p123_rhythm_right_preserve",
        crop=(77, 19, 828, 1600),
        bottom_y=2845,
        left_x=3050,
        edit_box=VERIFY_BOX,
        top_inset=18,
        color_strength=0.64,
        alpha_scale=0.92,
        top_start=0.34,
        top_feather=58,
        bottom_end=0.42,
        bottom_feather=30,
        blur_radius=0.35,
        preserve_right=True,
        notes="same rhythm registration, right face fades back to original artwork",
    ),
    Experiment(
        name="p123_expanded_crop_occlusion_soft",
        crop=(68, 19, 842, 1600),
        bottom_y=2862,
        left_x=3038,
        edit_box=VERIFY_BOX,
        top_inset=28,
        color_strength=0.68,
        alpha_scale=0.84,
        top_start=0.22,
        top_feather=74,
        bottom_end=0.30,
        bottom_feather=42,
        blur_radius=0.55,
        preserve_right=True,
        occlusion=True,
        notes="expanded crop/lower anchor, longer feather, preserves tree/foreground occlusions",
    ),
]


def rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def mild_color_match(patch: np.ndarray, reference: np.ndarray, strength: float) -> np.ndarray:
    patch_f = patch.astype(np.float32)
    ref_f = reference.astype(np.float32)
    p_luma = patch_f.mean(axis=2)
    r_luma = ref_f.mean(axis=2)
    p_sel = patch_f[(p_luma > 35) & (p_luma < 245)]
    r_sel = ref_f[(r_luma > 35) & (r_luma < 235)]
    if len(p_sel) < 100 or len(r_sel) < 100:
        return patch
    p_mean, p_std = p_sel.mean(axis=0), p_sel.std(axis=0) + 1e-3
    r_mean, r_std = r_sel.mean(axis=0), r_sel.std(axis=0) + 1e-3
    matched = (patch_f - p_mean) * (r_std / p_std) + r_mean
    return np.clip(patch_f * (1.0 - strength) + matched * strength, 0, 255).astype(np.uint8)


def warp_plate(src_shape: tuple[int, int, int], plate: np.ndarray, exp: Experiment) -> tuple[np.ndarray, np.ndarray, tuple[tuple[float, float], ...]]:
    x0, y0, x1, y1 = exp.crop
    crop = plate[y0:y1, x0:x1]
    h, w = crop.shape[:2]
    dest_w = w * RHYTHM_SCALE
    dest_h = h * RHYTHM_SCALE
    left = float(exp.left_x)
    right = left + dest_w
    bottom = float(exp.bottom_y)
    top = bottom - dest_h
    dst_quad = (
        (left + exp.top_inset, top),
        (right - exp.top_inset, top + 16),
        (right, bottom),
        (left, bottom),
    )
    src_quad = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    matrix = cv2.getPerspectiveTransform(src_quad, np.float32(dst_quad))
    out_h, out_w = src_shape[:2]
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
    return warped, mask, dst_quad


def alpha_for(src_patch: np.ndarray, exp: Experiment) -> np.ndarray:
    h, w = src_patch.shape[:2]
    alpha = np.ones((h, w), dtype=np.float32) * exp.alpha_scale
    top = min(exp.top_feather, h)
    bottom = min(exp.bottom_feather, h)
    alpha[:top, :] *= np.linspace(exp.top_start, 1.0, top, dtype=np.float32)[:, None]
    alpha[-bottom:, :] *= np.linspace(1.0, exp.bottom_end, bottom, dtype=np.float32)[:, None]
    side = min(10, w)
    alpha[:, :side] *= np.linspace(0.58, 1.0, side, dtype=np.float32)[None, :]
    alpha[:, -side:] *= np.linspace(1.0, 0.58, side, dtype=np.float32)[None, :]

    if exp.preserve_right:
        start = max(0, min(w, 700))
        ramp = np.ones(w, dtype=np.float32)
        if start < w:
            ramp[start:] = np.linspace(1.0, 0.10, w - start, dtype=np.float32)
        alpha *= ramp[None, :]

    if exp.occlusion:
        yy, xx = np.mgrid[0:h, 0:w]
        r, g, b = src_patch[..., 0], src_patch[..., 1], src_patch[..., 2]
        luma = src_patch.mean(axis=2)
        left_zone = xx < 180
        vegetation = left_zone & (g > r * 0.90) & (g > b * 1.03) & (luma < 215)
        dark_branches = left_zone & (luma < 118)
        foreground = yy > h - 45
        alpha[vegetation | dark_branches] *= 0.18
        alpha[foreground] *= 0.58

    return alpha[..., None]


def save_context(src: np.ndarray, warped: np.ndarray, mask: np.ndarray, exp: Experiment, dst_quad: tuple[tuple[float, float], ...]) -> None:
    overlay = np.where((mask > 0)[..., None], (0.62 * src + 0.38 * warped).astype(np.uint8), src)
    im = Image.fromarray(overlay).crop(CONTEXT_BOX)
    draw = ImageDraw.Draw(im)
    cx0, cy0 = CONTEXT_BOX[:2]
    vx0, vy0, vx1, vy1 = VERIFY_BOX
    ex0, ey0, ex1, ey1 = exp.edit_box
    draw.rectangle((vx0 - cx0, vy0 - cy0, vx1 - cx0, vy1 - cy0), outline=(255, 0, 0), width=4)
    draw.rectangle((ex0 - cx0, ey0 - cy0, ex1 - cx0, ey1 - cy0), outline=(0, 90, 255), width=3)
    draw.line([(x - cx0, y - cy0) for x, y in dst_quad] + [(dst_quad[0][0] - cx0, dst_quad[0][1] - cy0)], fill=(0, 180, 90), width=3)
    im.save(OUT / f"{exp.name}_registered_context.png")


def build(exp: Experiment, src: np.ndarray, plate: np.ndarray) -> Path:
    warped, plate_mask, dst_quad = warp_plate(src.shape, plate, exp)
    save_context(src, warped, plate_mask, exp, dst_quad)

    x0, y0, x1, y1 = exp.edit_box
    ref = src[FACADE_REF_BOX[1] : FACADE_REF_BOX[3], FACADE_REF_BOX[0] : FACADE_REF_BOX[2]]
    patch = mild_color_match(warped[y0:y1, x0:x1], ref, exp.color_strength)
    if exp.blur_radius:
        patch = np.asarray(Image.fromarray(patch).filter(ImageFilter.GaussianBlur(exp.blur_radius)))
    src_patch = src[y0:y1, x0:x1]
    alpha = alpha_for(src_patch, exp)
    merged = np.clip(src_patch.astype(np.float32) * (1 - alpha) + patch.astype(np.float32) * alpha, 0, 255).astype(np.uint8)

    out = src.copy()
    out[y0:y1, x0:x1] = merged
    im = Image.fromarray(out)
    cand = OUT / f"w2_whole_tower_{exp.name}_composited.png"
    im.save(cand)
    zoom = im.crop(ZOOM_BOX)
    zoom.save(OUT / f"w2_whole_tower_{exp.name}_zoom.png")
    zoom.resize((zoom.width * 2, zoom.height * 2), Image.Resampling.LANCZOS).save(
        OUT / f"w2_whole_tower_{exp.name}_zoom_2x.png"
    )
    Image.fromarray(patch).save(OUT / f"{exp.name}_registered_patch.png")
    return cand


def save_contact(paths: list[Path]) -> None:
    images = [Image.open(SRC_PATH).convert("RGB")] + [Image.open(p).convert("RGB") for p in paths]
    labels = ["source"] + [p.name.replace("w2_whole_tower_", "").replace("_composited.png", "") for p in paths]
    crops = [im.crop(ZOOM_BOX) for im in images]
    thumb_w, thumb_h = 455, 179
    pad, label_h = 18, 28
    sheet = Image.new("RGB", (thumb_w + 2 * pad, len(crops) * (thumb_h + label_h + pad) + pad), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (label, crop) in enumerate(zip(labels, crops)):
        crop.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad
        y = pad + i * (thumb_h + label_h + pad)
        sheet.paste(crop, (x, y))
        draw.text((x, y + crop.height + 6), label, fill=(20, 20, 20))
    sheet.save(OUT / "p123_candidate_zoom_contact_sheet.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    src = rgb(SRC_PATH)
    plate = rgb(PLATE_PATH)
    outputs = [build(exp, src, plate) for exp in EXPERIMENTS]
    save_contact(outputs)
    print(f"source_period={SOURCE_PERIOD} plate_period={PLATE_PERIOD} rhythm_scale={RHYTHM_SCALE:.4f}")
    for out in outputs:
        print(out)


if __name__ == "__main__":
    main()
