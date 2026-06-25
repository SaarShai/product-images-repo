#!/usr/bin/env python3
"""Generate refined, less aggressive wave3 repair variants."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from generate_local_variants import (
    BASELINE,
    FOREGROUND_ZOOM,
    SPHERE_ZOOM,
    blend_with_mask,
    cv_inpaint,
    hard_clip_to_allowed,
    lower_haze_mask,
    sphere_ghost_mask,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "refined_variants"
ZOOM = OUT / "zooms"


def mask_from_rects(size: tuple[int, int], rects: list[tuple[int, int, int, int]], blur: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    for rect in rects:
        d.rounded_rectangle(rect, radius=16, fill=255)
    return hard_clip_to_allowed(mask.filter(ImageFilter.GaussianBlur(blur)))


def paste_donor(base: Image.Image, rect: tuple[int, int, int, int], donor: tuple[int, int, int, int], alpha: int = 210) -> Image.Image:
    patch = base.copy()
    dx0, dy0, dx1, dy1 = donor
    x0, y0, x1, y1 = rect
    donor_crop = base.crop(donor).resize((x1 - x0, y1 - y0), Image.Resampling.BICUBIC)
    donor_crop = donor_crop.filter(ImageFilter.GaussianBlur(1.6))
    local_mask = Image.new("L", base.size, 0)
    d = ImageDraw.Draw(local_mask)
    d.rounded_rectangle(rect, radius=18, fill=alpha)
    local_mask = hard_clip_to_allowed(local_mask.filter(ImageFilter.GaussianBlur(7)))
    patch.paste(donor_crop, (x0, y0))
    return blend_with_mask(base, patch, local_mask)


def soften_poles(base: Image.Image, strength: float = 0.45) -> Image.Image:
    rects = [
        (88, 2160, 130, 2790),
        (218, 2160, 252, 2790),
        (337, 2470, 374, 2790),
        (504, 2380, 540, 2790),
    ]
    mask = mask_from_rects(base.size, rects, blur=9)
    region_blur = base.filter(ImageFilter.GaussianBlur(6))
    arr_base = np.asarray(base.convert("RGB"), dtype=np.float32)
    arr_blur = np.asarray(region_blur.convert("RGB"), dtype=np.float32)
    arr = arr_base * (1 - strength) + arr_blur * strength
    # Lower the chalk-white value slightly and warm it into the surrounding watercolor wash.
    warm = np.array([203, 199, 160], dtype=np.float32)
    arr = arr * 0.86 + warm * 0.14
    patch = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return blend_with_mask(base, patch, mask)


def neighbor_clone_poles(base: Image.Image) -> Image.Image:
    img = base.copy()
    # Narrow donor strokes from neighboring tree/sky, not whole-region repainting.
    for rect, donor, alpha in [
        ((88, 2180, 130, 2780), (36, 2180, 78, 2780), 205),
        ((218, 2180, 252, 2780), (258, 2180, 292, 2780), 190),
        ((337, 2480, 374, 2780), (294, 2480, 331, 2780), 170),
    ]:
        img = paste_donor(img, rect, donor, alpha=alpha)
    return img


def subtle_haze_tint(base: Image.Image, amount: float = 0.22) -> Image.Image:
    mask = lower_haze_mask(base.size, soften=48)
    crop_box = (0, 2260, 620, 2800)
    patch = base.copy()
    crop = base.crop(crop_box)
    crop = ImageEnhance.Contrast(crop).enhance(1.08)
    crop = ImageEnhance.Color(crop).enhance(1.12)
    arr = np.asarray(crop.convert("RGB"), dtype=np.float32)
    olive = np.array([180, 183, 132], dtype=np.float32)
    arr = arr * (1 - amount) + olive * amount
    patch.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), crop_box)
    return blend_with_mask(base, patch, mask)


def sky_patch_sphere_refined(base: Image.Image, alpha_scale: float = 0.72) -> Image.Image:
    patch = base.copy()
    donor = base.crop((62, 1135, 222, 1512)).resize((160, 377), Image.Resampling.BICUBIC)
    donor = donor.filter(ImageFilter.GaussianBlur(2.7))
    patch.paste(donor, (170, 1138))
    mask = sphere_ghost_mask(base.size, soften=15)
    mask = Image.eval(mask, lambda p: int(p * alpha_scale))
    return blend_with_mask(base, patch, mask)


def save(name: str, img: Image.Image, note: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    ZOOM.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.png")
    img.crop(SPHERE_ZOOM).save(ZOOM / f"{name}_sphere.png")
    img.crop(FOREGROUND_ZOOM).save(ZOOM / f"{name}_foreground.png")
    return f"- `{name}.png` — {note}"


def main() -> None:
    base = Image.open(BASELINE).convert("RGB")
    notes: list[str] = []

    sphere_refined = sky_patch_sphere_refined(base, alpha_scale=0.72)
    notes.append(save("r01_sphere_sky_patch_refined", sphere_refined, "Soft sky patch over the sphere crescent; avoids inpainting the orange band."))

    sphere_faint = sky_patch_sphere_refined(base, alpha_scale=0.52)
    notes.append(save("r02_sphere_faint_reduce", sphere_faint, "Lighter version that reduces, not fully removes, the crescent."))

    sphere_inpaint_tight = cv_inpaint(base, sphere_ghost_mask(base.size, soften=0), radius=5, method=cv2.INPAINT_TELEA)
    sphere_inpaint_tight = blend_with_mask(base, sphere_inpaint_tight, Image.eval(sphere_ghost_mask(base.size, soften=10), lambda p: int(p * 0.68)))
    notes.append(save("r03_sphere_tight_inpaint", sphere_inpaint_tight, "Tighter inpaint blend for comparison against the sky-patch method."))

    poles_soft = soften_poles(base, strength=0.38)
    notes.append(save("r04_foreground_soften_white_wipes", poles_soft, "Narrow softening/tinting of hard white vertical foreground wipes."))

    poles_clone = neighbor_clone_poles(base)
    notes.append(save("r05_foreground_neighbor_clone", poles_clone, "Narrow clone strokes from adjacent tree/sky texture over the worst vertical wipes."))

    haze_tint = subtle_haze_tint(base, amount=0.18)
    notes.append(save("r06_foreground_subtle_haze_tint", haze_tint, "Subtle olive/contrast wash in the lower haze without repainting the foreground."))

    combo_soft = soften_poles(sphere_refined, strength=0.34)
    notes.append(save("r07_combo_sphere_poles_soft", combo_soft, "Refined sphere patch plus white-wipe softening."))

    combo_clone = neighbor_clone_poles(sphere_refined)
    notes.append(save("r08_combo_sphere_neighbor_clone", combo_clone, "Refined sphere patch plus narrow neighbor-clone foreground cleanup."))

    combo_haze = subtle_haze_tint(soften_poles(sphere_refined, strength=0.30), amount=0.14)
    notes.append(save("r09_combo_balanced_subtle_haze", combo_haze, "Refined sphere patch, softened vertical wipes, and restrained lower haze tint."))

    combo_inpaint = neighbor_clone_poles(sphere_inpaint_tight)
    combo_inpaint = subtle_haze_tint(combo_inpaint, amount=0.12)
    notes.append(save("r10_combo_tight_inpaint_clone_haze", combo_inpaint, "Tight sphere inpaint plus clone strokes and very light haze tint."))

    (OUT / "notes.md").write_text("# Refined Variants\n\n" + "\n".join(notes) + "\n")
    print(f"wrote {len(notes)} refined variants to {OUT}")


if __name__ == "__main__":
    main()
