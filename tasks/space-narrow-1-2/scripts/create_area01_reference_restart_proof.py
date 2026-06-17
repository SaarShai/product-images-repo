#!/usr/bin/env python3
"""Reference-first restart for narrow 1+2 area 01.

This is a fresh composition, not a restyle of the machinery sketch. The earlier
geometry method succeeded, so this script keeps the SVG-native component checks.
The style method failed, so the visual vocabulary restarts from the supplied
reference images: simple watercolor control panels, rounded glossy surfaces,
large soft dials/planets, sliders, and sparse colored controls.
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
import create_area01_top_left_proof as base  # noqa: E402


OUTPUT_STEM = "area-01-top-left-reference-restart-v1"
METHOD = "svg-native-reference-first-restart"
SEED = 2026061604

Color = tuple[int, int, int, int]
Box = tuple[int, int, int, int]
Point = tuple[int, int]


NAVY: Color = (24, 69, 142, 235)
DEEP_BLUE: Color = (58, 116, 190, 220)
PANEL_BLUE: Color = (121, 172, 219, 225)
PALE_BLUE: Color = (193, 221, 240, 230)
GLASS_BLUE: Color = (168, 218, 239, 230)
CORAL: Color = (246, 105, 95, 240)
YELLOW: Color = (247, 192, 68, 240)
TEAL: Color = (92, 205, 183, 240)
WHITE: Color = (255, 255, 255, 255)


def masks() -> tuple[Image.Image, Image.Image, Image.Image, str, str]:
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


def component(size: tuple[int, int]) -> tuple[Image.Image, Image.Image, ImageDraw.ImageDraw, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    return layer, mask, ImageDraw.Draw(layer, "RGBA"), ImageDraw.Draw(mask)


def outside_pixels(mask: Image.Image, allowed: Image.Image) -> int:
    arr = np.asarray(mask) > 0
    allowed_arr = np.asarray(allowed) > 0
    return int((arr & ~allowed_arr).sum())


def commit(
    art: Image.Image,
    element_mask: Image.Image,
    layer: Image.Image,
    mask: Image.Image,
    paintable: Image.Image,
    name: str,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    outside = outside_pixels(mask, paintable)
    placements.append({"name": name, "outside_paintable_pixels": outside})
    if outside:
        raise ValueError(f"{name} crosses SVG paintable region by {outside} pixels")
    art.alpha_composite(layer)
    return ImageChops.lighter(element_mask, mask)


def watercolor_fill(size: tuple[int, int], rng: random.Random) -> Image.Image:
    width, height = size
    base_rgb = np.zeros((height, width, 3), dtype=np.float32)
    base_rgb[:, :, :] = np.array([118, 170, 219], dtype=np.float32)
    gen = np.random.default_rng(rng.randint(0, 2**32 - 1))
    noise = gen.normal(0, 9, (height, width, 1)) + gen.normal(0, 4, (height, width, 1))
    base_rgb += noise * np.array([0.55, 0.78, 1.0])
    arr = np.clip(base_rgb, 0, 255).astype(np.uint8)
    image = Image.fromarray(arr).convert("RGBA").filter(ImageFilter.GaussianBlur(0.55))

    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(85):
        cx = rng.randint(-120, width + 120)
        cy = rng.randint(-80, height + 80)
        rx = rng.randint(80, 360)
        ry = rng.randint(30, 180)
        fill = rng.choice([(255, 255, 255, 18), (58, 116, 190, 16), (179, 222, 244, 20)])
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)
    image.alpha_composite(wash.filter(ImageFilter.GaussianBlur(22)))
    return image


def rounded_panel(
    draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw,
    box: Box,
    radius: int,
    fill: Color,
    outline: Color = NAVY,
    width: int = 5,
    shine: bool = True,
) -> None:
    x1, y1, x2, y2 = box
    shadow = (x1 + 8, y1 + 10, x2 + 8, y2 + 12)
    mask_draw.rounded_rectangle(shadow, radius=radius, fill=255)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)
    draw.rounded_rectangle(shadow, radius=radius, fill=(10, 40, 100, 62))
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    if shine:
        draw.rounded_rectangle((x1 + 16, y1 + 14, x2 - 18, y1 + 34), radius=15, fill=(255, 255, 255, 88))
        draw.line((x1 + 22, y2 - 22, x2 - 26, y2 - 22), fill=(255, 255, 255, 48), width=4)


def draw_slider_bank(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    layer, mask, draw, md = component(art.size)
    for row, y in enumerate((775, 848, 921, 994)):
        track = (245, y, 670, y + 17)
        md.rounded_rectangle(track, radius=9, fill=255)
        draw.rounded_rectangle((track[0] + 5, track[1] + 6, track[2] + 5, track[3] + 7), radius=9, fill=(20, 64, 136, 60))
        draw.rounded_rectangle(track, radius=9, fill=(151, 198, 232, 175), outline=NAVY, width=3)
        draw.line((track[0] + 16, y + 4, track[2] - 18, y + 4), fill=(255, 255, 255, 85), width=3)
        for x, color in [
            (280 + row * 42, [CORAL, TEAL, YELLOW, CORAL][row]),
            (430 + row * 18, [YELLOW, CORAL, TEAL, YELLOW][row]),
            (620 - row * 34, [TEAL, YELLOW, CORAL, TEAL][row]),
        ]:
            box = (x - 20, y - 17, x + 20, y + 25)
            md.rounded_rectangle(box, radius=9, fill=255)
            draw.rounded_rectangle((box[0] + 4, box[1] + 6, box[2] + 4, box[3] + 8), radius=9, fill=(16, 52, 118, 65))
            draw.rounded_rectangle(box, radius=9, fill=color, outline=NAVY, width=3)
            draw.rounded_rectangle((box[0] + 7, box[1] + 6, box[2] - 7, box[1] + 16), radius=6, fill=(255, 255, 255, 85))
    return commit(art, element_mask, layer, mask, paintable, "reference slider bank", placements)


def draw_planet_dial(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    layer, mask, draw, md = component(art.size)
    cx, cy, r = 482, 520, 134
    md.ellipse((cx - r - 8, cy - r + 10, cx + r + 8, cy + r + 18), fill=255)
    md.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    draw.ellipse((cx - r - 8, cy - r + 10, cx + r + 8, cy + r + 18), fill=(12, 46, 116, 60))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(188, 222, 241, 230), outline=NAVY, width=6)
    draw.pieslice((cx - 108, cy - 108, cx + 108, cy + 108), 35, 150, fill=(92, 205, 183, 178))
    draw.pieslice((cx - 105, cy - 105, cx + 105, cy + 105), 176, 292, fill=(93, 158, 219, 175))
    draw.arc((cx - 92, cy - 86, cx + 94, cy + 92), 18, 162, fill=(255, 255, 255, 125), width=13)
    draw.ellipse((cx - 72, cy - 72, cx + 40, cy + 44), fill=(255, 255, 255, 36))
    for angle in range(210, 332, 30):
        x = int(cx + np.cos(np.deg2rad(angle)) * 174)
        y = int(cy + np.sin(np.deg2rad(angle)) * 174)
        md.rounded_rectangle((x - 6, y - 22, x + 6, y + 22), radius=6, fill=255)
        draw.rounded_rectangle((x - 6, y - 22, x + 6, y + 22), radius=6, fill=(255, 255, 255, 115))
    return commit(art, element_mask, layer, mask, paintable, "large soft planet dial", placements)


def draw_pill_controls(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    layer, mask, draw, md = component(art.size)
    colors = [CORAL, TEAL, YELLOW]
    for index, y in enumerate((1146, 1238, 1330)):
        box = (315, y, 650, y + 54)
        rounded_panel(draw, md, box, 25, colors[index], NAVY, width=4, shine=True)
        inner = (box[0] + 82, y + 13, box[2] - 28, y + 31)
        md.rounded_rectangle(inner, radius=9, fill=255)
        draw.rounded_rectangle(inner, radius=9, fill=(255, 255, 255, 80))
    return commit(art, element_mask, layer, mask, paintable, "large reference pill buttons", placements)


def draw_right_control_tile(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    layer, mask, draw, md = component(art.size)
    rounded_panel(draw, md, (1015, 1192, 1308, 1422), 34, PALE_BLUE, NAVY, width=5)
    for x in (1080, 1180, 1260):
        for y in (1260, 1360):
            md.ellipse((x - 19, y - 19, x + 19, y + 19), fill=255)
            draw.ellipse((x - 19, y - 19, x + 19, y + 19), fill=GLASS_BLUE, outline=NAVY, width=3)
            draw.ellipse((x - 9, y - 12, x + 4, y + 1), fill=(255, 255, 255, 120))
    return commit(art, element_mask, layer, mask, paintable, "right reference control tile", placements)


def draw_screws_and_sparkles(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    rng = random.Random(SEED)
    layer, mask, draw, md = component(art.size)
    for x, y in [(265, 350), (640, 370), (245, 700), (238, 1382), (640, 1378), (1040, 1150), (1290, 1410)]:
        screw_mask = Image.new("L", art.size, 0)
        smd = ImageDraw.Draw(screw_mask)
        smd.ellipse((x - 13, y - 13, x + 13, y + 13), fill=255)
        if outside_pixels(screw_mask, paintable):
            continue
        md.bitmap((0, 0), screw_mask, fill=255)
        draw.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(205, 228, 242, 230), outline=NAVY, width=3)
        draw.line((x - 6, y + 5, x + 6, y - 5), fill=(255, 255, 255, 120), width=3)
    placed = 0
    while placed < 46:
        x = rng.choice([rng.randint(210, 690), rng.randint(970, 1365)])
        y = rng.randint(245, 1440)
        rr = rng.randint(2, 5)
        dot = Image.new("L", art.size, 0)
        dd = ImageDraw.Draw(dot)
        dd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
        if outside_pixels(dot, paintable):
            continue
        md.bitmap((0, 0), dot, fill=255)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=rng.choice([(255, 255, 255, 85), (247, 192, 68, 95), (168, 218, 239, 95)]))
        placed += 1
    return commit(art, element_mask, layer, mask, paintable, "reference screws and watercolor speckles", placements)


def build() -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    rng = random.Random(SEED)
    hard_outer, hard_cutouts, paintable, top_left_outer, diagonal_cutout = masks()
    size = hard_outer.size
    art = Image.new("RGBA", size, WHITE)
    base_fill = watercolor_fill(size, rng)
    base.fill_masked(art, base_fill, paintable)

    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(rim, top_left_outer, (24, 69, 142, 218), 50)
    base.draw_polyline(rim, top_left_outer, (177, 215, 239, 210), 34)
    base.draw_polyline(rim, top_left_outer, (255, 255, 255, 112), 13)
    base.draw_polyline(rim, top_left_outer, NAVY, 6)
    art.alpha_composite(Image.composite(rim, Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer))

    element_mask = Image.new("L", size, 0)
    placements: list[dict[str, int | str]] = []

    element_mask = draw_planet_dial(art, element_mask, paintable, placements)
    element_mask = draw_slider_bank(art, element_mask, paintable, placements)
    element_mask = draw_pill_controls(art, element_mask, paintable, placements)
    element_mask = draw_right_control_tile(art, element_mask, paintable, placements)
    element_mask = draw_screws_and_sparkles(art, element_mask, paintable, placements)

    # Glass-like broad highlights from the references.
    highlights = Image.new("RGBA", size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlights, "RGBA")
    hdraw.rounded_rectangle((180, 95, 610, 128), radius=18, fill=(255, 255, 255, 78))
    hdraw.arc((80, 130, 620, 760), 198, 264, fill=(255, 255, 255, 95), width=14)
    hdraw.rounded_rectangle((1010, 980, 1260, 1006), radius=13, fill=(255, 255, 255, 50))
    hdraw.arc((960, 1030, 1360, 1435), 208, 288, fill=(255, 255, 255, 54), width=11)
    highlights = Image.composite(highlights, Image.new("RGBA", size, (0, 0, 0, 0)), paintable)
    art.alpha_composite(highlights)

    white = Image.new("RGBA", size, WHITE)
    art = Image.composite(art, white, hard_outer)
    art = Image.composite(white, art, hard_cutouts)

    overlay = art.copy()
    overlay_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(overlay_layer, top_left_outer, (255, 219, 85, 235), 8, dash=24)
    base.draw_polyline(overlay_layer, diagonal_cutout, (255, 219, 85, 235), 8, dash=24)
    odraw = ImageDraw.Draw(overlay_layer, "RGBA")
    x0, y0, _, _ = base.CROP
    odraw.ellipse((1486.61 - 76 - x0, 1268.34 - 76 - y0, 1486.61 + 76 - x0, 1268.34 + 76 - y0), outline=(255, 219, 85, 235), width=8)
    odraw.rounded_rectangle((770.16 - x0, 1054.46 - y0, 878.67 - x0, 1294.58 - y0), radius=12, outline=(237, 28, 36, 230), width=7)
    overlay.alpha_composite(overlay_layer)

    mask_debug = Image.new("RGBA", size, WHITE)
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (88, 169, 226, 170)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (237, 28, 36, 180)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_cutouts))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (38, 230, 150, 145)), Image.new("RGBA", size, (0, 0, 0, 0)), element_mask))
    mask_debug.alpha_composite(overlay_layer)

    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "area": "01 top-left",
        "method": METHOD,
        "source_svg": str(base.SVG.relative_to(base.TASK.parent.parent)),
        "not_crop_method": True,
        "restart_reason": "Geometry succeeded, but prior style failed because palette passes preserved the wrong dark machinery vocabulary.",
        "style_reference_images": [
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_11_51 PM.png",
        ],
        "style_vocabulary": "simple rounded watercolor control-panel objects, glossy rim highlights, sparse sliders, a planet/dial, coral/yellow/teal accents",
        "component_placements": placements,
        "nonwhite_pixels_in_cutout_mask": base.nonwhite_pixels(art, hard_cutouts),
        "nonwhite_pixels_outside_outer_mask": base.nonwhite_pixels(art, hard_outer.point(lambda p: 0 if p else 255)),
        "decorative_element_pixels_in_cutout_mask": int(((np.asarray(element_mask) > 0) & (np.asarray(hard_cutouts) > 0)).sum()),
        "decorative_element_pixels_outside_paintable_mask": int(((np.asarray(element_mask) > 0) & (np.asarray(paintable) == 0)).sum()),
        "artwork": f"outputs/generated/{OUTPUT_STEM}-artwork.png",
        "overlay": f"outputs/reviews/{OUTPUT_STEM}-template-overlay.png",
        "mask_debug": f"outputs/reviews/{OUTPUT_STEM}-mask-debug.png",
    }
    return art, overlay, mask_debug, metadata


def main() -> int:
    base.GENERATED.mkdir(parents=True, exist_ok=True)
    base.REVIEWS.mkdir(parents=True, exist_ok=True)
    art, overlay, mask_debug, metadata = build()
    art.convert("RGB").save(base.GENERATED / f"{OUTPUT_STEM}-artwork.png")
    overlay.convert("RGB").save(base.REVIEWS / f"{OUTPUT_STEM}-template-overlay.png")
    mask_debug.convert("RGB").save(base.REVIEWS / f"{OUTPUT_STEM}-mask-debug.png")
    (base.REVIEWS / f"{OUTPUT_STEM}-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
