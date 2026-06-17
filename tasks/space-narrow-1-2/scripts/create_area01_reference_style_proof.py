#!/usr/bin/env python3
"""Restyle the SVG-native area 01 proof to match the supplied references.

This keeps the contour-first, pocket-planned geometry from
`create_area01_svg_native_proof.py`, then applies a watercolor palette pass
derived from the uploaded control-panel references.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_area01_svg_native_proof as svg_native  # noqa: E402
import create_area01_top_left_proof as base  # noqa: E402


OUTPUT_STEM = "area-01-top-left-reference-style-v2"
METHOD = "svg-native-pocket-planned-reference-style"
SEED = 2026061603


def hard_masks() -> tuple[Image.Image, Image.Image, Image.Image, str, str]:
    paths = base.load_paths()
    top_left_outer = paths[6].data
    diagonal_cutout = paths[7].data
    size = (base.CROP[2] - base.CROP[0], base.CROP[3] - base.CROP[1])

    outer = base.draw_path_mask(top_left_outer, size)
    cutouts = base.composite_mask(
        base.draw_path_mask(diagonal_cutout, size),
        base.ellipse_mask(size, 1486.61, 1268.34, 76.0),
        base.rect_mask(size, (770.16, 1054.46, 108.51, 240.12), radius=12),
        base.rect_mask(size, (752.0, 1050.0, 146.0, 502.0), radius=12),
    ).filter(ImageFilter.MaxFilter(9))

    hard_outer = outer.point(lambda p: 255 if p > 0 else 0)
    hard_cutouts = cutouts.point(lambda p: 255 if p > 0 else 0)
    paintable = ImageChops.subtract(hard_outer, hard_cutouts)
    return hard_outer, hard_cutouts, paintable, top_left_outer, diagonal_cutout


def watercolor_noise(width: int, height: int, rng: random.Random) -> np.ndarray:
    gen = np.random.default_rng(rng.randint(0, 2**32 - 1))
    low = gen.normal(0, 8, (height, width))
    mid = gen.normal(0, 4, (height, width))
    return np.clip(low + mid, -22, 22)


def palette_restyle(art: Image.Image, paintable: Image.Image, hard_cutouts: Image.Image, hard_outer: Image.Image) -> Image.Image:
    rng = random.Random(SEED)
    image = art.convert("RGB")
    arr = np.asarray(image).astype(np.float32)
    h, w, _ = arr.shape
    paint = np.asarray(paintable) > 0

    rgb = arr.copy()
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    saturation = maxc - minc

    blue_like = paint & (rgb[:, :, 2] > rgb[:, :, 0] + 8) & (rgb[:, :, 2] > rgb[:, :, 1] - 12)
    dark_blue = blue_like & (lum < 92)
    mid_blue = blue_like & (lum >= 92)
    neutral_panel = paint & (saturation < 55) & (lum > 95)
    red_like = paint & (rgb[:, :, 0] > rgb[:, :, 1] + 32) & (rgb[:, :, 0] > rgb[:, :, 2] + 20)
    yellow_like = paint & (rgb[:, :, 0] > 155) & (rgb[:, :, 1] > 120) & (rgb[:, :, 2] < 120)
    teal_like = paint & (rgb[:, :, 1] > rgb[:, :, 0] + 20) & (rgb[:, :, 2] > rgb[:, :, 0] + 16)

    targets: list[tuple[np.ndarray, tuple[int, int, int], float]] = [
        (dark_blue, (28, 78, 148), 0.30),
        (mid_blue, (112, 162, 216), 0.30),
        (neutral_panel, (198, 219, 238), 0.28),
        (red_like, (246, 101, 92), 0.28),
        (yellow_like, (248, 192, 66), 0.26),
        (teal_like, (91, 202, 181), 0.24),
    ]
    for mask, target, amount in targets:
        target_arr = np.array(target, dtype=np.float32)
        rgb[mask] = rgb[mask] * (1.0 - amount) + target_arr * amount

    # A light blue wash like the uploaded references, stronger in blank panel
    # areas and weaker over colored controls.
    wash = np.array((132, 178, 224), dtype=np.float32)
    quiet_blue = paint & ~red_like & ~yellow_like & ~teal_like & (lum > 80)
    rgb[quiet_blue] = rgb[quiet_blue] * 0.94 + wash * 0.06

    noise = watercolor_noise(w, h, rng)
    for channel, factor in enumerate((0.62, 0.78, 1.0)):
        rgb[:, :, channel][paint] = rgb[:, :, channel][paint] + noise[paint] * factor

    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    styled = Image.fromarray(rgb).convert("RGBA")

    # Preserve exact white outside and cutout zones.
    white = Image.new("RGBA", styled.size, (255, 255, 255, 255))
    styled = Image.composite(styled, white, hard_outer)
    styled = Image.composite(white, styled, hard_cutouts)
    return styled.filter(ImageFilter.GaussianBlur(0.08))


def add_reference_highlights(
    styled: Image.Image,
    paintable: Image.Image,
    hard_outer: Image.Image,
    hard_cutouts: Image.Image,
    top_left_outer: str,
) -> Image.Image:
    size = styled.size
    highlights = Image.new("RGBA", size, (0, 0, 0, 0))
    hmask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(highlights, "RGBA")
    md = ImageDraw.Draw(hmask)

    def rounded(box: tuple[int, int, int, int], radius: int, alpha: int) -> None:
        md.rounded_rectangle(box, radius=radius, fill=255)
        draw.rounded_rectangle(box, radius=radius, fill=(255, 255, 255, alpha))

    def arc(box: tuple[int, int, int, int], start: int, end: int, width: int, alpha: int) -> None:
        md.arc(box, start, end, fill=255, width=width + 6)
        draw.arc(box, start, end, fill=(255, 255, 255, alpha), width=width)

    # Broad glossy strokes copied from the reference family: pill-panel rim,
    # soft control highlights, and glassy canister shine.
    rounded((250, 95, 565, 128), 22, 82)
    rounded((1020, 1338, 1245, 1362), 12, 62)
    rounded((1080, 1222, 1190, 1242), 10, 92)
    rounded((362, 455, 548, 485), 16, 96)
    rounded((306, 1162, 548, 1192), 16, 78)
    rounded((514, 260, 584, 495), 30, 90)
    arc((258, 226, 650, 650), 198, 275, 13, 68)
    arc((900, 1034, 1370, 1460), 210, 290, 11, 50)

    # A few reference-style short white ticks around controls, not near cutouts.
    for box in [
        (312, 382, 328, 432),
        (632, 392, 646, 442),
        (210, 760, 224, 810),
        (610, 860, 622, 910),
        (1160, 1115, 1172, 1165),
        (1300, 1325, 1312, 1375),
    ]:
        rounded(box, 8, 118)

    hmask = ImageChops.multiply(hmask, paintable)
    hmask = ImageChops.subtract(hmask, hard_cutouts)
    highlights = Image.composite(highlights, Image.new("RGBA", size, (0, 0, 0, 0)), hmask)

    out = styled.copy()
    out.alpha_composite(highlights)

    # Restore a soft navy contour after the wash so the panel still reads
    # Screenery-template accurate.
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(rim, top_left_outer, (23, 70, 145, 210), 10)
    base.draw_polyline(rim, top_left_outer, (255, 255, 255, 70), 4)
    rim = Image.composite(rim, Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer)
    out.alpha_composite(rim)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    out = Image.composite(out, white, hard_outer)
    out = Image.composite(white, out, hard_cutouts)
    return out


def build_reference_style() -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    native_art, _native_overlay, _native_mask_debug, native_metadata = svg_native.build_art()
    hard_outer, hard_cutouts, paintable, top_left_outer, diagonal_cutout = hard_masks()

    styled = palette_restyle(native_art, paintable, hard_cutouts, hard_outer)
    styled = add_reference_highlights(styled, paintable, hard_outer, hard_cutouts, top_left_outer)

    overlay = styled.copy()
    overlay_layer = Image.new("RGBA", styled.size, (0, 0, 0, 0))
    base.draw_polyline(overlay_layer, top_left_outer, (255, 219, 85, 235), 8, dash=24)
    base.draw_polyline(overlay_layer, diagonal_cutout, (255, 219, 85, 235), 8, dash=24)
    draw = ImageDraw.Draw(overlay_layer, "RGBA")
    x0, y0, _, _ = base.CROP
    draw.ellipse((1486.61 - 76 - x0, 1268.34 - 76 - y0, 1486.61 + 76 - x0, 1268.34 + 76 - y0), outline=(255, 219, 85, 235), width=8)
    draw.rounded_rectangle((770.16 - x0, 1054.46 - y0, 878.67 - x0, 1294.58 - y0), radius=12, outline=(237, 28, 36, 230), width=7)
    overlay.alpha_composite(overlay_layer)

    mask_debug = Image.new("RGBA", styled.size, (255, 255, 255, 255))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", styled.size, (88, 169, 226, 170)), Image.new("RGBA", styled.size, (0, 0, 0, 0)), hard_outer))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", styled.size, (237, 28, 36, 180)), Image.new("RGBA", styled.size, (0, 0, 0, 0)), hard_cutouts))
    mask_debug.alpha_composite(overlay_layer)

    metadata = dict(native_metadata)
    metadata.update(
        {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": METHOD,
            "style_reference_images": [
                "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
                "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
                "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_11_51 PM.png",
            ],
            "palette_sample": {
                "panel_blues": ["#78a8d8", "#6090d8", "#c0d8f0"],
                "outline_blue": "#184890",
                "accents": ["#f4675e", "#f6be43", "#5ecbb5"],
            },
            "style_pass": "lighter watercolor wash, glossy white highlights, softened navy outlines, reference accent palette",
            "artwork": f"outputs/generated/{OUTPUT_STEM}-artwork.png",
            "overlay": f"outputs/reviews/{OUTPUT_STEM}-template-overlay.png",
            "mask_debug": f"outputs/reviews/{OUTPUT_STEM}-mask-debug.png",
            "nonwhite_pixels_in_cutout_mask": base.nonwhite_pixels(styled, hard_cutouts),
            "nonwhite_pixels_outside_outer_mask": base.nonwhite_pixels(styled, hard_outer.point(lambda p: 0 if p else 255)),
            "decorative_element_pixels_in_cutout_mask": native_metadata["decorative_element_pixels_in_cutout_mask"],
            "decorative_element_pixels_outside_paintable_mask": native_metadata["decorative_element_pixels_outside_paintable_mask"],
        }
    )
    return styled, overlay, mask_debug, metadata


def main() -> int:
    base.GENERATED.mkdir(parents=True, exist_ok=True)
    base.REVIEWS.mkdir(parents=True, exist_ok=True)
    art, overlay, mask_debug, metadata = build_reference_style()

    art_path = base.GENERATED / f"{OUTPUT_STEM}-artwork.png"
    overlay_path = base.REVIEWS / f"{OUTPUT_STEM}-template-overlay.png"
    mask_path = base.REVIEWS / f"{OUTPUT_STEM}-mask-debug.png"
    metadata_path = base.REVIEWS / f"{OUTPUT_STEM}-metadata.json"

    art.convert("RGB").save(art_path)
    overlay.convert("RGB").save(overlay_path)
    mask_debug.convert("RGB").save(mask_path)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
