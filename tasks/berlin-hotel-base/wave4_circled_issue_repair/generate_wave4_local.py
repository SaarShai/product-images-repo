#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")
SRC = Path("tasks/berlin-hotel-base/work/src.png")
BANKED = Path("tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png")
SCREENSHOT = Path("/Users/za/Desktop/Screenshot 2026-06-23 at 02.08.24.png")

OUT = ROOT / "local_variants"
RESULTS = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)


# Screenshot-to-fullres mapping measured by width-fit match:
# screenshot is full image scaled to 2112px width, cropped from full y ~= 439.
SS_W, SS_H = Image.open(SCREENSHOT).size
FULL_W, FULL_H = Image.open(BASE).size
SCALE = FULL_W / SS_W
Y0 = 439.0


REGIONS = [
    # name, screenshot bbox (x0, y0, x1, y1), notes
    ("gate_train_wisp_l", (320, 1088, 396, 1205), "white vertical wipe near train/gate trees"),
    ("gate_train_wisp_m", (430, 1072, 506, 1198), "white vertical wipe between train cars"),
    ("gate_train_wisp_r", (500, 1050, 610, 1212), "broad pale tree/steam block"),
    ("bridge_white_sign", (1000, 1122, 1120, 1192), "blank white bridge rectangle"),
    ("church_base_portal", (1284, 940, 1460, 1124), "overdrawn ghost portal at church base"),
    ("right_mid_haze", (1490, 1055, 1656, 1262), "rectangular haze/tree block beside small hotel"),
    ("hotel_roof_wipe", (1772, 350, 1882, 520), "right tower roof/facade vertical wipe"),
    ("hotel_ground_black", (1846, 1210, 1992, 1322), "black vertical ground-floor artifacts"),
    ("far_right_sliver", (2040, 1125, 2112, 1328), "far-right sliver/vertical artifact"),
]


def ss_to_full(box: tuple[int, int, int, int], pad: int = 0) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    fx0 = int(round(x0 * SCALE)) - pad
    fx1 = int(round(x1 * SCALE)) + pad
    fy0 = int(round(y0 * SCALE + Y0)) - pad
    fy1 = int(round(y1 * SCALE + Y0)) + pad
    return max(0, fx0), max(0, fy0), min(FULL_W, fx1), min(FULL_H, fy1)


FULL_REGIONS = [(name, ss_to_full(box, 12), note) for name, box, note in REGIONS]


def ellipse_mask(size: tuple[int, int], regions=FULL_REGIONS, extra_pad: int = 0, feather: int = 18) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for _, (x0, y0, x1, y1), _ in regions:
        d.ellipse((x0 - extra_pad, y0 - extra_pad, x1 + extra_pad, y1 + extra_pad), fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def rect_mask(size: tuple[int, int], names: set[str], pad: int = 0, feather: int = 12) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for name, (x0, y0, x1, y1), _ in FULL_REGIONS:
        if name in names:
            d.rounded_rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), radius=24, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def composite_donor(base: Image.Image, donor: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(donor, base, mask)


def local_color_wash(base: Image.Image, names: set[str], alpha: float = 0.55) -> Image.Image:
    arr = np.array(base).astype(np.float32)
    out = arr.copy()
    for name, (x0, y0, x1, y1), _ in FULL_REGIONS:
        if name not in names:
            continue
        pad = 70
        sx0, sy0 = max(0, x0 - pad), max(0, y0 - pad)
        sx1, sy1 = min(FULL_W, x1 + pad), min(FULL_H, y1 + pad)
        region = arr[sy0:sy1, sx0:sx1]
        # Use nearby pixels but exclude the defect bbox to get a local watercolor average.
        keep = np.ones(region.shape[:2], dtype=bool)
        keep[y0 - sy0:y1 - sy0, x0 - sx0:x1 - sx0] = False
        sample = region[keep]
        if sample.size == 0:
            continue
        med = np.median(sample.reshape(-1, 3), axis=0)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        ry, rx = max(1, (y1 - y0) / 2), max(1, (x1 - x0) / 2)
        e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        w = np.clip(1 - e, 0, 1)[..., None] * alpha
        out[y0:y1, x0:x1] = arr[y0:y1, x0:x1] * (1 - w) + med * w
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def inpaint_variant(base: Image.Image, names: set[str], radius: int = 9) -> Image.Image:
    bgr = cv2.cvtColor(np.array(base), cv2.COLOR_RGB2BGR)
    m = np.zeros((FULL_H, FULL_W), dtype=np.uint8)
    for name, (x0, y0, x1, y1), _ in FULL_REGIONS:
        if name not in names:
            continue
        cv2.ellipse(
            m,
            ((x0 + x1) // 2, (y0 + y1) // 2),
            ((x1 - x0) // 2, (y1 - y0) // 2),
            0,
            0,
            360,
            255,
            -1,
        )
    # Inpaint a contracted mask first; then feather it back onto the original.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    hard = cv2.erode(m, kernel, iterations=1)
    repaired = cv2.inpaint(bgr, hard, radius, cv2.INPAINT_TELEA)
    rep = Image.fromarray(cv2.cvtColor(repaired, cv2.COLOR_BGR2RGB))
    mask = Image.fromarray(m).filter(ImageFilter.GaussianBlur(18))
    return composite_donor(base, rep, mask)


def make_mask_debug(base: Image.Image) -> None:
    dbg = base.copy()
    d = ImageDraw.Draw(dbg, "RGBA")
    for name, box, _ in FULL_REGIONS:
        d.ellipse(box, outline=(80, 210, 40, 255), width=8)
        d.text((box[0], box[1] - 22), name, fill=(160, 0, 0, 255))
    dbg.save(RESULTS / "wave4_issue_regions_fullres.png")
    m = ellipse_mask(base.size, feather=3)
    m.save(RESULTS / "wave4_issue_mask_hardish.png")
    ellipse_mask(base.size, feather=28).save(RESULTS / "wave4_issue_mask_feathered.png")


def build_crop_board(paths: list[tuple[str, Path]], out: Path) -> None:
    # Crop the nine issue regions, grouped by candidate.
    tile_w, tile_h = 260, 180
    label_h = 34
    gap = 10
    cols = len(FULL_REGIONS)
    rows = len(paths)
    board = Image.new("RGB", (cols * tile_w + (cols + 1) * gap, rows * (tile_h + label_h) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(board)
    for r, (label, p) in enumerate(paths):
        im = Image.open(p).convert("RGB")
        ybase = gap + r * (tile_h + label_h + gap)
        draw.text((gap, ybase), label, fill=(140, 0, 0))
        for c, (name, (x0, y0, x1, y1), _) in enumerate(FULL_REGIONS):
            crop = im.crop((x0, y0, x1, y1))
            crop.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            x = gap + c * (tile_w + gap)
            y = ybase + label_h
            board.paste(crop, (x, y))
            draw.rectangle((x, y, x + tile_w - 1, y + tile_h - 1), outline=(210, 210, 210))
            if r == 0:
                draw.text((x + 3, y + 3), name, fill=(0, 70, 120))
    board.save(out)


def build_context_board(paths: list[tuple[str, Path]], out: Path) -> None:
    cols = 2
    thumb_w = 860
    label_h = 40
    gap = 20
    rows = (len(paths) + cols - 1) // cols
    thumb_h = round(thumb_w * 1468 / 2112)
    board = Image.new("RGB", (cols * thumb_w + (cols + 1) * gap, rows * (thumb_h + label_h) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(board)
    crop_y0 = int(round(Y0))
    crop_y1 = int(round(Y0 + SS_H * SCALE))
    for i, (label, p) in enumerate(paths):
        im = Image.open(p).convert("RGB")
        visible = im.crop((0, crop_y0, FULL_W, crop_y1))
        visible = visible.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        col = i % cols
        row = i // cols
        x = gap + col * (thumb_w + gap)
        y = gap + row * (thumb_h + label_h + gap)
        draw.text((x, y), label, fill=(140, 0, 0))
        board.paste(visible, (x, y + label_h))
    board.save(out)


def verify(paths: list[tuple[str, Path]], protected: list[tuple[int, int, int, int]] = []) -> None:
    base = np.array(Image.open(BASE).convert("RGB"))
    allowed = np.array(ellipse_mask((FULL_W, FULL_H), extra_pad=18, feather=0)) > 0
    lines = []
    for label, p in paths:
        if label == "base":
            continue
        im = np.array(Image.open(p).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        outside = int((diff & ~allowed).sum())
        inside = int((diff & allowed).sum())
        lines.append(f"{label}\\tinside_changed={inside}\\toutside_changed={outside}\\tpath={p}")
    (RESULTS / "wave4_local_verification.txt").write_text("\\n".join(lines) + "\\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    src = Image.open(SRC).convert("RGB")
    banked = Image.open(BANKED).convert("RGB")

    make_mask_debug(base)

    all_names = {name for name, _, _ in FULL_REGIONS}
    non_hotel = all_names - {"hotel_roof_wipe", "hotel_ground_black", "far_right_sliver"}
    hotel = {"hotel_roof_wipe", "hotel_ground_black", "far_right_sliver"}
    haze_names = {"gate_train_wisp_l", "gate_train_wisp_m", "gate_train_wisp_r", "bridge_white_sign", "right_mid_haze"}

    variants: list[tuple[str, Path]] = [("base", BASE)]

    mask_all = ellipse_mask(base.size, extra_pad=10, feather=22)
    v01 = composite_donor(base, src, mask_all)
    p01 = OUT / "v01_source_donor_all_circled.png"
    v01.save(p01)
    variants.append(("v01 source donor all circled", p01))

    mask_non_hotel = rect_mask(base.size, non_hotel, pad=12, feather=20)
    mask_hotel = rect_mask(base.size, hotel, pad=10, feather=18)
    v02 = composite_donor(base, src, mask_non_hotel)
    v02 = composite_donor(v02, banked, mask_hotel)
    p02 = OUT / "v02_source_nonhotel_banked_hotel.png"
    v02.save(p02)
    variants.append(("v02 source nonhotel + banked hotel", p02))

    v03 = inpaint_variant(base, all_names, radius=11)
    p03 = OUT / "v03_telea_inpaint_all_circled.png"
    v03.save(p03)
    variants.append(("v03 local inpaint all circled", p03))

    v04 = local_color_wash(base, haze_names | {"hotel_roof_wipe"}, alpha=0.42)
    v04 = composite_donor(v04, src, rect_mask(base.size, {"church_base_portal", "bridge_white_sign"}, pad=4, feather=12))
    p04 = OUT / "v04_soft_wash_plus_source_detail.png"
    v04.save(p04)
    variants.append(("v04 soft wash + source details", p04))

    v05 = composite_donor(base, src, rect_mask(base.size, {"bridge_white_sign", "church_base_portal", "right_mid_haze"}, pad=16, feather=22))
    v05 = inpaint_variant(v05, {"gate_train_wisp_l", "gate_train_wisp_m", "gate_train_wisp_r", "hotel_roof_wipe", "hotel_ground_black", "far_right_sliver"}, radius=7)
    p05 = OUT / "v05_hybrid_source_detail_inpaint_wisps_hotel.png"
    v05.save(p05)
    variants.append(("v05 hybrid source + targeted inpaint", p05))

    build_crop_board(variants, RESULTS / "wave4_local_detail_board.png")
    build_context_board(variants, RESULTS / "wave4_local_context_board.png")
    verify(variants)


if __name__ == "__main__":
    main()
