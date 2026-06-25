#!/usr/bin/env python3
"""Generate local TV-tower sphere ghost-crescent repair variants.

All outputs stay in this folder. The source image is copied first and only
pixels inside EDIT_BOX are replaced, so unchanged regions remain pixel-identical
to the banked baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
TASK_ROOT = HERE.parents[2]
BASELINE = TASK_ROOT / "wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png"

EDIT_BOX = (190, 1120, 470, 1580)
ZOOM_BOX = (120, 1040, 520, 1660)


@dataclass(frozen=True)
class Variant:
    slug: str
    label: str
    image: np.ndarray


def ellipse_field(xx: np.ndarray, yy: np.ndarray, cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
    return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2


def bbox_for(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def build_masks(base: np.ndarray) -> dict[str, np.ndarray]:
    height, width = base.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]
    x0, y0, x1, y1 = EDIT_BOX
    edit = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)

    # The visible artifact is a duplicate sphere arc: an offset oval crescent to
    # the left of the true tower sphere. Keep the mask left-biased to avoid
    # repainting the tower's band/window detail.
    outer = ellipse_field(xx, yy, 283, 1360, 101, 174)
    inner = ellipse_field(xx, yy, 309, 1360, 82, 145)
    crescent = (outer <= 1.0) & (inner >= 1.0) & (xx < 288)
    outer_rim = (np.abs(outer - 1.0) <= 0.075) & (xx < 252)
    lower_tail = (
        (ellipse_field(xx, yy, 253, 1426, 68, 92) <= 1.0)
        & (xx < 260)
        & (yy > 1330)
        & (yy < 1510)
    )

    rgb = base.astype(np.int16)
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    mean = rgb.mean(axis=2)
    low_sat = (maxc - minc) < 76
    not_orange = ~((rgb[:, :, 0] > 145) & (rgb[:, :, 1] > 75) & (rgb[:, :, 1] < 190) & (rgb[:, :, 2] < 130))
    sky_or_pale_ghost = ((mean > 112) & low_sat & not_orange) | outer_rim

    broad = edit & (crescent | outer_rim | lower_tail) & sky_or_pale_ghost
    narrow = broad & ((xx < 268) | outer_rim)

    search = edit & (crescent | outer_rim | lower_tail) & (xx < 286) & not_orange
    gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 26, 78)
    edge_mask = (edges > 0) & search
    edge_mask = cv2.dilate(edge_mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(bool)
    edge_mask &= edit & (xx < 286) & not_orange

    broad = cv2.dilate(broad.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1).astype(bool) & edit
    narrow = cv2.dilate(narrow.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1).astype(bool) & edit
    return {"broad": broad, "narrow": narrow, "edges": edge_mask, "edit": edit}


def smoothstep(value: np.ndarray, low: float, high: float) -> np.ndarray:
    t = np.clip((value - low) / (high - low), 0.0, 1.0)
    return t * t * (3.0 - (2.0 * t))


def crescent_fade(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    yy, xx = np.mgrid[0:height, 0:width]
    left = smoothstep(xx.astype(np.float32), 198, 220)
    right = 1.0 - smoothstep(xx.astype(np.float32), 283, 303)
    top = smoothstep(yy.astype(np.float32), 1176, 1212)
    bottom = 1.0 - smoothstep(yy.astype(np.float32), 1518, 1552)
    return np.clip(left * right * top * bottom, 0.0, 1.0)


def soft_alpha(mask: np.ndarray, sigma: float, peak: float = 1.0, confine: np.ndarray | None = None) -> np.ndarray:
    blurred = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigmaX=sigma, sigmaY=sigma)
    if blurred.max() > 0:
        blurred /= blurred.max()
    alpha = np.clip(blurred * peak, 0.0, 1.0)
    if confine is not None:
        alpha *= confine.astype(np.float32)
    alpha *= crescent_fade(mask.shape)
    return alpha


def shifted_texture(base: np.ndarray, shift_x: int, shift_y: int = 0) -> np.ndarray:
    height, width = base.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]
    sx = np.clip(xx + shift_x, 0, width - 1)
    sy = np.clip(yy + shift_y, 0, height - 1)
    return base[sy, sx]


def mirror_texture(base: np.ndarray, anchor_x: int = 172) -> np.ndarray:
    height, width = base.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width]
    sx = np.clip((2 * anchor_x) - xx, 0, width - 1)
    return base[yy, sx]


def local_inpaint(base: np.ndarray, mask: np.ndarray, radius: int, method: int) -> np.ndarray:
    bgr = cv2.cvtColor(base, cv2.COLOR_RGB2BGR)
    inpainted = cv2.inpaint(bgr, (mask.astype(np.uint8) * 255), radius, method)
    return cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)


def blend(base: np.ndarray, replacement: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    out = base.copy()
    active = alpha > 0.018
    a = alpha[:, :, None]
    mixed = (base.astype(np.float32) * (1.0 - a)) + (replacement.astype(np.float32) * a)
    out[active] = np.clip(np.rint(mixed[active]), 0, 255).astype(np.uint8)
    return out


def keep_only_edit_box(candidate: np.ndarray, base: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = EDIT_BOX
    out = base.copy()
    out[y0:y1, x0:x1] = candidate[y0:y1, x0:x1]
    return out


def save_mask(mask: np.ndarray, path: Path) -> None:
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def make_contact_sheet(base: np.ndarray, variants: list[Variant]) -> None:
    thumbs: list[tuple[str, Image.Image]] = [
        ("baseline", Image.fromarray(base).crop(ZOOM_BOX)),
        *[(variant.slug, Image.fromarray(variant.image).crop(ZOOM_BOX)) for variant in variants],
    ]
    tile_w, tile_h = 400, 620
    label_h = 36
    sheet = Image.new("RGB", (tile_w * 2, (tile_h + label_h) * 3), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, crop) in enumerate(thumbs):
        x = (idx % 2) * tile_w
        y = (idx // 2) * (tile_h + label_h)
        sheet.paste(crop, (x, y + label_h))
        draw.rectangle((x, y, x + tile_w, y + label_h), fill=(235, 235, 235))
        draw.text((x + 10, y + 10), label, fill=(30, 30, 30))
    sheet.save(HERE / "sphere_clean_contact_sheet.png")


def diff_report(base: np.ndarray, candidate: np.ndarray) -> str:
    changed = np.any(base != candidate, axis=2)
    x0, y0, x1, y1 = EDIT_BOX
    assigned = np.zeros(changed.shape, dtype=bool)
    assigned[y0:y1, x0:x1] = True
    outside = changed & ~assigned
    return (
        f"bbox={bbox_for(changed)} "
        f"changed={int(np.count_nonzero(changed))} "
        f"outside_assigned_changed={int(np.count_nonzero(outside))} "
        f"edit_box={EDIT_BOX}"
    )


def main() -> int:
    base = np.asarray(Image.open(BASELINE).convert("RGB"), dtype=np.uint8)
    masks = build_masks(base)
    save_mask(masks["broad"], HERE / "mask_sphere_ghost_broad.png")
    save_mask(masks["narrow"], HERE / "mask_sphere_ghost_narrow.png")
    save_mask(masks["edges"], HERE / "mask_sphere_ghost_edges.png")

    broad_alpha = soft_alpha(masks["broad"], sigma=3.2, peak=0.68, confine=masks["edit"])
    narrow_alpha = soft_alpha(masks["narrow"], sigma=2.7, peak=0.58, confine=masks["edit"])
    edge_alpha = soft_alpha(masks["edges"], sigma=2.2, peak=0.80, confine=masks["edit"])

    sky_patch = shifted_texture(base, shift_x=-86, shift_y=-5)
    sky_patch = cv2.GaussianBlur(sky_patch, (0, 0), sigmaX=0.55, sigmaY=0.55)

    mirror_patch = mirror_texture(base, anchor_x=176)
    mirror_patch = cv2.GaussianBlur(mirror_patch, (0, 0), sigmaX=0.75, sigmaY=0.75)

    smooth_sky = cv2.GaussianBlur(shifted_texture(base, shift_x=-112), (0, 0), sigmaX=3.8, sigmaY=3.8)
    watercolor_haze = np.clip((0.42 * shifted_texture(base, shift_x=-76) + 0.58 * smooth_sky), 0, 255).astype(np.uint8)

    edge_inpaint = local_inpaint(base, masks["edges"], radius=5, method=cv2.INPAINT_TELEA)
    strong_sky_haze = np.clip((0.72 * sky_patch) + (0.28 * smooth_sky), 0, 255).astype(np.uint8)

    variants = [
        Variant(
            "v01_sky_texture_patch",
            "low-opacity shifted clean sky texture patch",
            keep_only_edit_box(blend(base, sky_patch, broad_alpha), base),
        ),
        Variant(
            "v02_subtle_mirror_sky",
            "subtle crop mirroring from clean left sky",
            keep_only_edit_box(blend(base, mirror_patch, narrow_alpha), base),
        ),
        Variant(
            "v03_watercolor_haze_blend",
            "soft watercolor haze blend over crescent",
            keep_only_edit_box(blend(base, watercolor_haze, soft_alpha(masks["broad"], 4.4, 0.42, masks["edit"])), base),
        ),
        Variant(
            "v04_edge_soft_mask",
            "edge-only inpaint with soft mask",
            keep_only_edit_box(blend(base, edge_inpaint, edge_alpha), base),
        ),
        Variant(
            "v05_strong_sky_haze_patch",
            "stronger clean-sky patch with haze-softened edges",
            keep_only_edit_box(blend(base, strong_sky_haze, soft_alpha(masks["broad"], 3.4, 0.88, masks["edit"])), base),
        ),
    ]

    for variant in variants:
        full_path = HERE / f"sphere_clean_{variant.slug}.png"
        crop_path = HERE / f"sphere_clean_{variant.slug}_zoom_x120-520_y1040-1660.png"
        Image.fromarray(variant.image).save(full_path)
        Image.fromarray(variant.image).crop(ZOOM_BOX).save(crop_path)
        print(f"{variant.slug}: {variant.label}; {diff_report(base, variant.image)}")
        print(f"  full={full_path}")
        print(f"  crop={crop_path}")

    make_contact_sheet(base, variants)
    print(f"contact={HERE / 'sphere_clean_contact_sheet.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
