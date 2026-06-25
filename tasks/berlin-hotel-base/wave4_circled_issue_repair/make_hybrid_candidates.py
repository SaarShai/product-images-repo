#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")
EXT = ROOT / "external"
OUT = ROOT / "hybrids"
OUT.mkdir(parents=True, exist_ok=True)

SS_W, SS_H = 2112, 1468
FULL_W, FULL_H = Image.open(BASE).size
Y0 = 439.0
SCALE = FULL_W / SS_W

REGIONS = [
    ("gate_train_wisp_l", (320, 1088, 396, 1205)),
    ("gate_train_wisp_m", (430, 1072, 506, 1198)),
    ("gate_train_wisp_r", (500, 1050, 610, 1212)),
    ("bridge_white_sign", (1000, 1122, 1120, 1192)),
    ("church_base_portal", (1284, 940, 1460, 1124)),
    ("right_mid_haze", (1490, 1055, 1656, 1262)),
    ("hotel_roof_wipe", (1772, 350, 1882, 520)),
    ("hotel_ground_black", (1846, 1210, 1992, 1322)),
    ("far_right_sliver", (2040, 1125, 2112, 1328)),
]


def ss_to_full(box: tuple[int, int, int, int], pad: int = 0) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (
        max(0, int(round(x0 * SCALE)) - pad),
        max(0, int(round(y0 * SCALE + Y0)) - pad),
        min(FULL_W, int(round(x1 * SCALE)) + pad),
        min(FULL_H, int(round(y1 * SCALE + Y0)) + pad),
    )


FULL_REGIONS = [(name, ss_to_full(box, 0)) for name, box in REGIONS]


def mask(names: set[str], pad: int = 0, feather: int = 10, opacity: float = 1.0) -> Image.Image:
    m = Image.new("L", (FULL_W, FULL_H), 0)
    d = ImageDraw.Draw(m)
    for name, (x0, y0, x1, y1) in FULL_REGIONS:
        if name in names:
            d.ellipse((x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=round(255 * opacity))
    return m.filter(ImageFilter.GaussianBlur(feather))


def donor(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != (FULL_W, FULL_H):
        im = im.resize((FULL_W, FULL_H), Image.Resampling.LANCZOS)
    return im


def comp(base: Image.Image, src: Image.Image, m: Image.Image) -> Image.Image:
    return Image.composite(src, base, m)


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    v06 = donor(EXT / "openai_artifact_repair_raw.png")
    v07 = donor(EXT / "openai_watercolor_reconstruct_raw.png")

    all_names = {name for name, _ in FULL_REGIONS}
    non_hotel = all_names - {"hotel_roof_wipe", "hotel_ground_black", "far_right_sliver"}
    hotel = {"hotel_roof_wipe", "hotel_ground_black", "far_right_sliver"}

    comp(base, v07, mask(all_names, pad=-12, feather=9, opacity=1.0)).save(OUT / "v08_openai_watercolor_tight.png")
    comp(base, v07, mask(all_names, pad=0, feather=12, opacity=0.68)).save(OUT / "v09_openai_watercolor_soft_alpha.png")

    mixed = comp(base, v07, mask(non_hotel, pad=-8, feather=10, opacity=0.92))
    mixed = comp(mixed, v06, mask(hotel, pad=-10, feather=9, opacity=0.82))
    mixed.save(OUT / "v10_mixed_openai_nonhotel_artifact_hotel.png")

    very_safe = comp(base, v07, mask(non_hotel, pad=-18, feather=8, opacity=0.72))
    very_safe = comp(very_safe, v06, mask(hotel, pad=-18, feather=7, opacity=0.62))
    very_safe.save(OUT / "v11_mixed_openai_very_safe.png")


if __name__ == "__main__":
    main()
