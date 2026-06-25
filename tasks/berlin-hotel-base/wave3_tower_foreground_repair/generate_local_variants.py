#!/usr/bin/env python3
"""Generate local repair candidates for wave3 TV tower / foreground defects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent
BASELINE = (ROOT / "../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png").resolve()
OUT = ROOT / "local_variants"
ZOOM = OUT / "zooms"

ALLOWED_BOX = (0, 900, 860, 3050)
SPHERE_ZOOM = (120, 1040, 520, 1660)
FOREGROUND_ZOOM = (0, 1960, 760, 3040)


@dataclass
class Variant:
    name: str
    image: Image.Image
    note: str


def blank_mask(size: tuple[int, int]) -> Image.Image:
    return Image.new("L", size, 0)


def gaussian(mask: Image.Image, radius: float) -> Image.Image:
    return mask.filter(ImageFilter.GaussianBlur(radius))


def hard_clip_to_allowed(mask: Image.Image) -> Image.Image:
    allowed = blank_mask(mask.size)
    ImageDraw.Draw(allowed).rectangle(ALLOWED_BOX, fill=255)
    return ImageChops_multiply(mask, allowed)


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    return Image.fromarray((np.asarray(a, dtype=np.uint16) * np.asarray(b, dtype=np.uint16) // 255).astype(np.uint8), "L")


def sphere_ghost_mask(size: tuple[int, int], soften: float = 0) -> Image.Image:
    mask = blank_mask(size)
    d = ImageDraw.Draw(mask)
    # Covers the translucent crescent to the left of the sphere, avoiding most of the real ball edge.
    d.ellipse((170, 1138, 330, 1515), fill=255)
    d.ellipse((247, 1168, 410, 1495), fill=0)
    d.rectangle((300, 1120, 470, 1585), fill=0)
    d.rectangle((0, 0, 185, size[1]), fill=0)
    if soften:
        mask = gaussian(mask, soften)
    return hard_clip_to_allowed(mask)


def foreground_vertical_mask(size: tuple[int, int], soften: float = 0) -> Image.Image:
    mask = blank_mask(size)
    d = ImageDraw.Draw(mask)
    # Hard white wipes/poles visible in the circled foreground.
    d.rounded_rectangle((84, 2140, 132, 2850), radius=20, fill=255)
    d.rounded_rectangle((215, 2135, 255, 2860), radius=18, fill=255)
    d.rounded_rectangle((486, 2190, 525, 2860), radius=16, fill=180)
    # Low fog columns near the tower/gate bases.
    d.rounded_rectangle((324, 2480, 396, 2915), radius=26, fill=130)
    d.rounded_rectangle((550, 2525, 620, 2920), radius=24, fill=100)
    if soften:
        mask = gaussian(mask, soften)
    return hard_clip_to_allowed(mask)


def lower_haze_mask(size: tuple[int, int], soften: float = 0) -> Image.Image:
    mask = blank_mask(size)
    d = ImageDraw.Draw(mask)
    d.ellipse((-70, 2460, 710, 3035), fill=210)
    d.rectangle((0, 2860, 860, 3050), fill=0)
    # Leave most of the train intact.
    d.rectangle((0, 2875, 860, 3050), fill=0)
    if soften:
        mask = gaussian(mask, soften)
    return hard_clip_to_allowed(mask)


def hsv_bright_low_sat_mask(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGB"))
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    bright = (hsv[:, :, 2] > 212) & (hsv[:, :, 1] < 45)
    y = np.arange(arr.shape[0])[:, None]
    x = np.arange(arr.shape[1])[None, :]
    region = (x >= 0) & (x <= 650) & (y >= 2050) & (y <= 2860)
    mask = (bright & region).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.dilate(mask, np.ones((11, 11), np.uint8), iterations=1)
    return hard_clip_to_allowed(Image.fromarray(mask, "L"))


def cv_inpaint(img: Image.Image, mask: Image.Image, radius: int = 7, method: int = cv2.INPAINT_TELEA) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    repaired = cv2.inpaint(bgr, np.asarray(mask), radius, method)
    return Image.fromarray(cv2.cvtColor(repaired, cv2.COLOR_BGR2RGB))


def blend_with_mask(base: Image.Image, patch: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(patch, base, mask)


def sky_patch_sphere(base: Image.Image) -> Image.Image:
    patch = base.copy()
    # Nearby sky from left of the tower, shifted into the ghost crescent and blurred to watercolor softness.
    donor = base.crop((70, 1140, 230, 1517)).resize((160, 377), Image.Resampling.BICUBIC)
    donor = donor.filter(ImageFilter.GaussianBlur(3.2))
    patch.paste(donor, (170, 1138))
    return blend_with_mask(base, patch, sphere_ghost_mask(base.size, soften=13))


def contrast_haze_region(base: Image.Image, amount: float = 0.34) -> Image.Image:
    crop_box = (0, 2100, 650, 2875)
    crop = base.crop(crop_box)
    arr = np.asarray(crop.convert("RGB"))
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.25, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    lab2 = cv2.merge((l2, a, b))
    enhanced = Image.fromarray(cv2.cvtColor(lab2, cv2.COLOR_LAB2RGB))
    # Keep the watercolor low contrast by mixing the enhanced crop gently.
    mixed = Image.blend(crop, enhanced, amount)
    patch = base.copy()
    patch.paste(mixed, crop_box)
    return blend_with_mask(base, patch, lower_haze_mask(base.size, soften=35))


def tree_wash(base: Image.Image) -> Image.Image:
    patch = base.copy()
    donor = base.crop((0, 2210, 235, 2830)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    donor = donor.resize((420, 620), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2.2))
    # Muted olive wash to replace blank fog, but not a literal duplicate.
    arr = np.asarray(donor.convert("RGB"), dtype=np.float32)
    tint = np.array([196, 196, 148], dtype=np.float32)
    arr = arr * 0.72 + tint * 0.28
    donor = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    patch.paste(donor, (150, 2240))
    return blend_with_mask(base, patch, lower_haze_mask(base.size, soften=42))


def soften_watercolor(base: Image.Image, region_mask: Image.Image, strength: float = 0.22) -> Image.Image:
    soft = base.filter(ImageFilter.GaussianBlur(1.1))
    grain = Image.effect_noise(base.size, 7).convert("L").filter(ImageFilter.GaussianBlur(0.8))
    arr = np.asarray(soft.convert("RGB"), dtype=np.int16)
    noise = np.asarray(grain, dtype=np.int16)[:, :, None] - 128
    arr = np.clip(arr + noise * 0.09, 0, 255).astype(np.uint8)
    textured = Image.fromarray(arr, "RGB")
    mask = gaussian(region_mask, 6)
    weakened = Image.eval(mask, lambda p: int(p * strength))
    return Image.composite(textured, base, weakened)


def save_variant(variant: Variant) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ZOOM.mkdir(parents=True, exist_ok=True)
    full = OUT / f"{variant.name}.png"
    variant.image.save(full)
    variant.image.crop(SPHERE_ZOOM).save(ZOOM / f"{variant.name}_sphere.png")
    variant.image.crop(FOREGROUND_ZOOM).save(ZOOM / f"{variant.name}_foreground.png")


def main() -> None:
    base = Image.open(BASELINE).convert("RGB")
    variants: list[Variant] = []

    sphere_mask = sphere_ghost_mask(base.size, soften=0)
    fg_mask = foreground_vertical_mask(base.size, soften=0)
    auto_white = hsv_bright_low_sat_mask(base)
    pole_mask_arr = np.maximum(np.asarray(fg_mask), np.asarray(auto_white)).astype(np.uint8)
    pole_mask = hard_clip_to_allowed(Image.fromarray(pole_mask_arr, "L"))

    sphere_telea = cv_inpaint(base, sphere_mask, radius=9, method=cv2.INPAINT_TELEA)
    variants.append(Variant("v01_sphere_inpaint_telea", sphere_telea, "Telea inpaint over the left sphere ghost crescent only."))

    sphere_ns = cv_inpaint(base, sphere_mask, radius=7, method=cv2.INPAINT_NS)
    sphere_ns = soften_watercolor(sphere_ns, sphere_ghost_mask(base.size, soften=9), strength=0.35)
    variants.append(Variant("v02_sphere_inpaint_ns_soft", sphere_ns, "Navier-Stokes inpaint plus light watercolor re-softening."))

    variants.append(Variant("v03_sphere_sky_patch_soft", sky_patch_sphere(base), "Nearby sky donor patch blended into the sphere crescent."))

    fg_inpaint = cv_inpaint(base, pole_mask, radius=11, method=cv2.INPAINT_TELEA)
    variants.append(Variant("v04_foreground_pole_inpaint", fg_inpaint, "Inpaint hard white foreground wipes and low fog columns."))

    fg_haze = contrast_haze_region(base, amount=0.34)
    fg_haze = cv_inpaint(fg_haze, pole_mask, radius=9, method=cv2.INPAINT_TELEA)
    variants.append(Variant("v05_foreground_haze_thin", fg_haze, "Gently thin fog and inpaint obvious vertical wipes."))

    fg_tree = tree_wash(base)
    fg_tree = cv_inpaint(fg_tree, pole_mask, radius=9, method=cv2.INPAINT_NS)
    variants.append(Variant("v06_foreground_tree_wash", fg_tree, "Muted tree-texture wash through lower fog plus wipe removal."))

    combo_subtle = cv_inpaint(sphere_telea, pole_mask, radius=8, method=cv2.INPAINT_TELEA)
    variants.append(Variant("v07_combo_subtle_clean", combo_subtle, "Sphere Telea plus conservative foreground wipe cleanup."))

    combo_balanced = cv_inpaint(sphere_telea, pole_mask, radius=10, method=cv2.INPAINT_TELEA)
    combo_balanced = contrast_haze_region(combo_balanced, amount=0.26)
    variants.append(Variant("v08_combo_balanced_haze", combo_balanced, "Sphere cleanup plus mild foreground haze thinning."))

    combo_tree = tree_wash(sky_patch_sphere(base))
    combo_tree = cv_inpaint(combo_tree, pole_mask, radius=10, method=cv2.INPAINT_TELEA)
    variants.append(Variant("v09_combo_tree_sky_patch", combo_tree, "Sky-patched sphere plus tree wash foreground repair."))

    strong_mask = Image.fromarray(np.maximum(np.asarray(sphere_ghost_mask(base.size, 0)), np.asarray(lower_haze_mask(base.size, 0))).astype(np.uint8), "L")
    combo_strong = contrast_haze_region(sphere_telea, amount=0.45)
    combo_strong = cv_inpaint(combo_strong, pole_mask, radius=13, method=cv2.INPAINT_TELEA)
    combo_strong = soften_watercolor(combo_strong, strong_mask, strength=0.18)
    variants.append(Variant("v10_combo_stronger_reveal", combo_strong, "More assertive reveal: sphere cleanup, stronger fog thinning, wipe removal."))

    notes = []
    for variant in variants:
        save_variant(variant)
        notes.append(f"- `{variant.name}.png` — {variant.note}")
    (OUT / "notes.md").write_text("# Local Variants\n\n" + "\n".join(notes) + "\n")
    print(f"wrote {len(variants)} variants to {OUT}")


if __name__ == "__main__":
    main()
