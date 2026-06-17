#!/usr/bin/env python3
"""Watercolor-first reference fix for narrow 1+2 area 01.

The earlier geometry passed, but the style did not: it looked like crisp vector
UI using sampled reference colors. This pass keeps the SVG-native masks and
rebuilds the rendering language around the supplied references: soft blue
watercolor washes, thick organic navy pooling, simple rounded controls, and
painted white highlights.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_area01_top_left_proof as base  # noqa: E402


OUTPUT_STEM = "area-01-top-left-reference-watercolor-v2"
METHOD = "svg-native-reference-watercolor-v2"
SEED = 2026061605

Color = tuple[int, int, int, int]
Box = tuple[int, int, int, int]

NAVY: Color = (19, 65, 139, 230)
NAVY_DARK: Color = (9, 45, 105, 210)
RIM_BLUE: Color = (42, 109, 190, 190)
PANEL_BLUE: Color = (128, 181, 225, 225)
PALE_BLUE: Color = (190, 224, 242, 220)
GLASS_BLUE: Color = (210, 235, 247, 215)
CORAL: Color = (244, 103, 94, 235)
YELLOW: Color = (248, 194, 67, 235)
TEAL: Color = (89, 202, 181, 235)
WHITE: Color = (255, 255, 255, 255)
REFERENCE_STYLE_PATHS = [
    Path("/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"),
    Path("/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"),
]


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


def mask_rounded(size: tuple[int, int], box: Box, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask


def mask_ellipse(size: tuple[int, int], box: Box) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(box, fill=255)
    return mask


def translated_mask(mask: Image.Image, dx: int, dy: int) -> Image.Image:
    return mask.transform(mask.size, Image.Transform.AFFINE, (1, 0, -dx, 0, 1, -dy))


def clipped(layer: Image.Image, mask: Image.Image) -> Image.Image:
    return Image.composite(layer, Image.new("RGBA", layer.size, (0, 0, 0, 0)), mask)


def color_shift(color: Color, rng: random.Random, amount: int = 18, alpha_delta: int = 0) -> Color:
    return (
        max(0, min(255, color[0] + rng.randint(-amount, amount))),
        max(0, min(255, color[1] + rng.randint(-amount, amount))),
        max(0, min(255, color[2] + rng.randint(-amount, amount))),
        max(0, min(255, color[3] + alpha_delta + rng.randint(-8, 8))),
    )


def watercolor_mask_fill(
    size: tuple[int, int],
    mask: Image.Image,
    color: Color,
    rng: random.Random,
    *,
    blotches: int = 38,
    blur: float = 1.2,
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    base_fill = Image.new("RGBA", size, color)
    layer.alpha_composite(clipped(base_fill, mask.filter(ImageFilter.GaussianBlur(blur))))

    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    width, height = size
    for _ in range(blotches):
        cx = rng.randint(0, width)
        cy = rng.randint(0, height)
        rx = rng.randint(34, 180)
        ry = rng.randint(18, 120)
        fill = rng.choice(
            [
                color_shift(color, rng, 12, -130),
                (255, 255, 255, rng.randint(16, 44)),
                (54, 116, 190, rng.randint(10, 32)),
            ]
        )
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)
    wash = wash.filter(ImageFilter.GaussianBlur(15))
    layer.alpha_composite(clipped(wash, mask))
    return layer


def painted_outline(
    size: tuple[int, int],
    shape: str,
    box: Box,
    rng: random.Random,
    *,
    radius: int = 0,
    color: Color = NAVY,
    width: int = 8,
) -> Image.Image:
    outline = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(outline, "RGBA")
    for offset, alpha in [(-2, 65), (1, 105), (3, 60)]:
        c = (color[0], color[1], color[2], alpha)
        shifted = (box[0] + offset, box[1] + rng.randint(-1, 2), box[2] + offset, box[3] + rng.randint(-2, 1))
        if shape == "ellipse":
            draw.ellipse(shifted, outline=c, width=width)
        else:
            draw.rounded_rectangle(shifted, radius=radius, outline=c, width=width)
    return outline.filter(ImageFilter.GaussianBlur(0.35))


def painted_round_rect(
    size: tuple[int, int],
    box: Box,
    radius: int,
    color: Color,
    rng: random.Random,
    *,
    outline_width: int = 7,
    highlight: bool = True,
) -> tuple[Image.Image, Image.Image]:
    shape = mask_rounded(size, box, radius)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))

    shadow_mask = translated_mask(shape, 7, 10).filter(ImageFilter.GaussianBlur(4))
    layer.alpha_composite(clipped(Image.new("RGBA", size, (5, 34, 95, 54)), shadow_mask))
    layer.alpha_composite(watercolor_mask_fill(size, shape, color, rng, blotches=28, blur=1.4))
    layer.alpha_composite(painted_outline(size, "rect", box, rng, radius=radius, width=outline_width))

    if highlight:
        h = Image.new("RGBA", size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(h, "RGBA")
        x1, y1, x2, y2 = box
        if x2 - x1 > 74:
            hd.rounded_rectangle((x1 + 18, y1 + 12, x2 - 22, y1 + 32), radius=14, fill=(255, 255, 255, 92))
            hd.rounded_rectangle((x1 + 20, y2 - 22, x2 - 26, y2 - 13), radius=7, fill=(255, 255, 255, 36))
        else:
            hd.rounded_rectangle((x1 + 7, y1 + 7, x2 - 8, y1 + 17), radius=5, fill=(255, 255, 255, 92))
        layer.alpha_composite(clipped(h.filter(ImageFilter.GaussianBlur(0.9)), shape))
    return layer, shape


def painted_ellipse(
    size: tuple[int, int],
    box: Box,
    color: Color,
    rng: random.Random,
    *,
    outline_width: int = 8,
    highlight: bool = True,
) -> tuple[Image.Image, Image.Image]:
    shape = mask_ellipse(size, box)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.alpha_composite(clipped(Image.new("RGBA", size, (5, 34, 95, 54)), translated_mask(shape, 8, 12).filter(ImageFilter.GaussianBlur(4))))
    layer.alpha_composite(watercolor_mask_fill(size, shape, color, rng, blotches=32, blur=1.4))
    layer.alpha_composite(painted_outline(size, "ellipse", box, rng, width=outline_width))
    if highlight:
        h = Image.new("RGBA", size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(h, "RGBA")
        x1, y1, x2, y2 = box
        if x2 - x1 > 86 and y2 - y1 > 86:
            hd.ellipse((x1 + 34, y1 + 30, x1 + 112, y1 + 92), fill=(255, 255, 255, 88))
            hd.arc((x1 + 26, y1 + 22, x2 - 26, y2 - 26), 200, 300, fill=(255, 255, 255, 80), width=9)
        else:
            hd.ellipse((x1 + 9, y1 + 8, x1 + 24, y1 + 22), fill=(255, 255, 255, 95))
        layer.alpha_composite(clipped(h.filter(ImageFilter.GaussianBlur(0.9)), shape))
    return layer, shape


def panel_wash(size: tuple[int, int], paintable: Image.Image, rng: random.Random) -> Image.Image:
    width, height = size
    gen = np.random.default_rng(rng.randint(0, 2**32 - 1))
    base_rgb = np.zeros((height, width, 3), dtype=np.float32)
    base_rgb[:, :, :] = np.array([108, 164, 218], dtype=np.float32)
    low_noise = gen.normal(0, 14, (height, width, 1))
    grain = gen.normal(0, 4, (height, width, 1))
    base_rgb += low_noise * np.array([0.42, 0.62, 1.0]) + grain
    image = Image.fromarray(np.clip(base_rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    image = image.filter(ImageFilter.GaussianBlur(0.85))
    ref_texture = reference_texture(size)
    if ref_texture is not None:
        image = Image.blend(image, ref_texture, 0.42)

    washes = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(washes, "RGBA")
    for _ in range(125):
        cx = rng.randint(-160, width + 160)
        cy = rng.randint(-100, height + 100)
        rx = rng.randint(70, 430)
        ry = rng.randint(28, 210)
        fill = rng.choice(
            [
                (255, 255, 255, rng.randint(12, 30)),
                (47, 108, 189, rng.randint(10, 24)),
                (174, 216, 240, rng.randint(18, 38)),
                (100, 160, 217, rng.randint(10, 26)),
            ]
        )
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)
    image.alpha_composite(clipped(washes.filter(ImageFilter.GaussianBlur(23)), paintable))
    return clipped(image, paintable)


def reference_texture(size: tuple[int, int]) -> Image.Image | None:
    refs = [path for path in REFERENCE_STYLE_PATHS if path.exists()]
    if not refs:
        return None
    strips: list[Image.Image] = []
    for path in refs:
        ref = Image.open(path).convert("RGB")
        ref = ref.crop((70, 70, ref.width - 70, ref.height - 70))
        ref = ImageEnhance.Color(ref).enhance(0.82)
        ref = ImageEnhance.Contrast(ref).enhance(1.12)
        target_h = max(1, round(size[0] * ref.height / ref.width))
        ref = ref.resize((size[0], target_h), Image.Resampling.LANCZOS)
        strips.append(ref.filter(ImageFilter.GaussianBlur(17)))
    texture = Image.new("RGB", size, (94, 151, 211))
    y = 0
    index = 0
    while y < size[1]:
        strip = strips[index % len(strips)]
        texture.paste(strip, (0, y))
        y += strip.height
        index += 1
    texture = texture.filter(ImageFilter.GaussianBlur(4))
    return texture.convert("RGBA")


def watercolor_finish(art: Image.Image, paintable: Image.Image, rng: random.Random) -> Image.Image:
    softened = Image.blend(art, art.filter(ImageFilter.GaussianBlur(0.55)), 0.22)
    width, height = art.size
    gen = np.random.default_rng(rng.randint(0, 2**32 - 1))
    paper = gen.normal(0, 7, (height, width, 1))
    fibers = gen.normal(0, 2, (height, width, 1))
    grain = np.clip(247 + paper + fibers, 224, 255).astype(np.uint8)
    grain_rgb = np.repeat(grain, 3, axis=2)
    texture = Image.fromarray(grain_rgb).convert("RGBA")
    texture.putalpha(16)
    softened.alpha_composite(clipped(texture.filter(ImageFilter.GaussianBlur(0.25)), paintable))

    bloom = Image.new("RGBA", art.size, (0, 0, 0, 0))
    bloom.alpha_composite(clipped(Image.new("RGBA", art.size, (255, 255, 255, 8)), paintable.filter(ImageFilter.GaussianBlur(2.4))))
    softened.alpha_composite(clipped(bloom, paintable))
    return softened


def draw_panel_edges(
    art: Image.Image,
    hard_outer: Image.Image,
    paintable: Image.Image,
    top_left_outer: str,
    diagonal_cutout: str,
) -> None:
    size = art.size
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(rim, top_left_outer, (12, 55, 128, 120), 60)
    base.draw_polyline(rim, top_left_outer, (45, 116, 194, 120), 43)
    base.draw_polyline(rim, top_left_outer, (222, 240, 250, 120), 18)
    base.draw_polyline(rim, top_left_outer, NAVY, 7)
    rim = rim.filter(ImageFilter.GaussianBlur(0.45))
    art.alpha_composite(clipped(rim, hard_outer))

    cutout_rims = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(cutout_rims, diagonal_cutout, (18, 74, 150, 150), 42)
    base.draw_polyline(cutout_rims, diagonal_cutout, (198, 226, 242, 88), 18)
    draw = ImageDraw.Draw(cutout_rims, "RGBA")
    x0, y0, _, _ = base.CROP
    circle = (
        round(1486.61 - 95 - x0),
        round(1268.34 - 95 - y0),
        round(1486.61 + 95 - x0),
        round(1268.34 + 95 - y0),
    )
    draw.ellipse(circle, outline=(18, 74, 150, 150), width=24)
    draw.ellipse((circle[0] + 14, circle[1] + 14, circle[2] - 14, circle[3] - 14), outline=(225, 242, 250, 95), width=8)
    red_slot = (
        round(748 - x0),
        round(1035 - y0),
        round(910 - x0),
        round(1565 - y0),
    )
    draw.rounded_rectangle(red_slot, radius=20, outline=(18, 74, 150, 150), width=24)
    draw.rounded_rectangle((red_slot[0] + 14, red_slot[1] + 14, red_slot[2] - 14, red_slot[3] - 14), radius=14, outline=(225, 242, 250, 86), width=8)
    art.alpha_composite(clipped(cutout_rims.filter(ImageFilter.GaussianBlur(0.75)), paintable))


def draw_gauge(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer, shape = painted_ellipse(art.size, (350, 405, 640, 695), GLASS_BLUE, rng, outline_width=8)
    face = Image.new("RGBA", art.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(face, "RGBA")
    fd.pieslice((392, 448, 598, 650), 34, 151, fill=(92, 202, 181, 94))
    fd.pieslice((392, 448, 598, 650), 180, 294, fill=(62, 140, 214, 105))
    fd.arc((395, 450, 600, 653), 30, 150, fill=(255, 255, 255, 115), width=13)
    fd.ellipse((438, 494, 535, 590), fill=(89, 146, 205, 82))
    for angle in [215, 245, 275, 305, 335]:
        x = int(495 + np.cos(np.deg2rad(angle)) * 132)
        y = int(550 + np.sin(np.deg2rad(angle)) * 132)
        tick = mask_rounded(art.size, (x - 7, y - 24, x + 7, y + 24), 7)
        face.alpha_composite(clipped(Image.new("RGBA", art.size, (255, 255, 255, 88)), tick))
        shape = ImageChops.lighter(shape, tick)
    layer.alpha_composite(clipped(face.filter(ImageFilter.GaussianBlur(0.35)), shape))
    return commit(art, element_mask, layer, shape, paintable, "soft watercolor gauge", placements)


def draw_sliders(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    md = ImageDraw.Draw(mask)
    for row, y in enumerate((768, 846, 924, 1002)):
        track_box = (240, y, 686, y + 18)
        track_layer, track_mask = painted_round_rect(art.size, track_box, 10, (154, 205, 235, 150), rng, outline_width=4, highlight=True)
        layer.alpha_composite(track_layer)
        mask = ImageChops.lighter(mask, track_mask)
        for x, color in [
            (275 + row * 38, [CORAL, TEAL, YELLOW, CORAL][row]),
            (420 + row * 20, [YELLOW, CORAL, TEAL, YELLOW][row]),
            (630 - row * 32, [TEAL, YELLOW, CORAL, TEAL][row]),
        ]:
            knob_box = (x - 20, y - 20, x + 22, y + 24)
            knob_layer, knob_mask = painted_round_rect(art.size, knob_box, 9, color, rng, outline_width=4, highlight=True)
            layer.alpha_composite(knob_layer)
            mask = ImageChops.lighter(mask, knob_mask)
    # A few tiny pigment dots echo the references without turning into circuit art.
    for _ in range(8):
        x = rng.randint(250, 670)
        y = rng.randint(750, 1040)
        r = rng.randint(3, 6)
        md.ellipse((x - r, y - r, x + r, y + r), fill=255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rng.randint(35, 70)))
    return commit(art, element_mask, layer, mask, paintable, "soft watercolor slider bank", placements)


def draw_pills(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    for color, y in [(CORAL, 1137), (TEAL, 1228), (YELLOW, 1320)]:
        item, item_mask = painted_round_rect(art.size, (310, y, 660, y + 58), 29, color, rng, outline_width=7, highlight=True)
        layer.alpha_composite(item)
        mask = ImageChops.lighter(mask, item_mask)
    return commit(art, element_mask, layer, mask, paintable, "large soft pill buttons", placements)


def draw_small_button_panel(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer, mask = painted_round_rect(art.size, (1018, 1190, 1308, 1422), 34, PALE_BLUE, rng, outline_width=7, highlight=True)
    for x in (1082, 1180, 1260):
        for y in (1260, 1360):
            dot, dot_mask = painted_ellipse(art.size, (x - 19, y - 19, x + 19, y + 19), GLASS_BLUE, rng, outline_width=3, highlight=True)
            layer.alpha_composite(dot)
            mask = ImageChops.lighter(mask, dot_mask)
    return commit(art, element_mask, layer, mask, paintable, "small rounded button panel", placements)


def draw_reference_marks(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    mask = Image.new("L", art.size, 0)
    draw = ImageDraw.Draw(layer, "RGBA")
    md = ImageDraw.Draw(mask)
    for x, y in [(250, 338), (652, 354), (248, 705), (235, 1382), (645, 1375), (1042, 1150), (1302, 1410)]:
        screw = mask_ellipse(art.size, (x - 14, y - 14, x + 14, y + 14))
        if outside_pixels(screw, paintable):
            continue
        md.bitmap((0, 0), screw, fill=255)
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=(212, 235, 246, 200), outline=NAVY, width=3)
        draw.line((x - 7, y + 6, x + 7, y - 6), fill=(255, 255, 255, 118), width=3)

    placed = 0
    while placed < 42:
        x = rng.choice([rng.randint(215, 690), rng.randint(970, 1360)])
        y = rng.randint(240, 1440)
        r = rng.randint(2, 5)
        dot = mask_ellipse(art.size, (x - r, y - r, x + r, y + r))
        if outside_pixels(dot, paintable):
            continue
        md.bitmap((0, 0), dot, fill=255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=rng.choice([(255, 255, 255, 72), (247, 192, 68, 74), (168, 218, 239, 78)]))
        placed += 1

    # Short pale tick marks near the gauge, shaped like the painted white dashes
    # in the knob/lever reference.
    for x, y in [(382, 360), (465, 350), (553, 362), (612, 430), (348, 468)]:
        tick = mask_rounded(art.size, (x - 6, y - 21, x + 7, y + 21), 7)
        if outside_pixels(tick, paintable):
            continue
        md.bitmap((0, 0), tick, fill=255)
        draw.rounded_rectangle((x - 6, y - 21, x + 7, y + 21), radius=7, fill=(255, 255, 255, 105))
    layer = layer.filter(ImageFilter.GaussianBlur(0.2))
    return commit(art, element_mask, layer, mask, paintable, "reference screws dashes and speckles", placements)


def broad_highlights(size: tuple[int, int], paintable: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    draw.rounded_rectangle((170, 92, 612, 125), radius=18, fill=(255, 255, 255, 72))
    draw.arc((72, 126, 640, 770), 198, 264, fill=(255, 255, 255, 84), width=15)
    draw.rounded_rectangle((1002, 978, 1266, 1005), radius=14, fill=(255, 255, 255, 44))
    draw.arc((955, 1040, 1370, 1435), 210, 288, fill=(255, 255, 255, 45), width=12)
    return clipped(layer.filter(ImageFilter.GaussianBlur(1.0)), paintable)


def overlay_review(
    art: Image.Image,
    top_left_outer: str,
    diagonal_cutout: str,
) -> Image.Image:
    overlay = art.copy()
    overlay_layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    base.draw_polyline(overlay_layer, top_left_outer, (255, 219, 85, 235), 8, dash=24)
    base.draw_polyline(overlay_layer, diagonal_cutout, (255, 219, 85, 235), 8, dash=24)
    odraw = ImageDraw.Draw(overlay_layer, "RGBA")
    x0, y0, _, _ = base.CROP
    odraw.ellipse((1486.61 - 76 - x0, 1268.34 - 76 - y0, 1486.61 + 76 - x0, 1268.34 + 76 - y0), outline=(255, 219, 85, 235), width=8)
    odraw.rounded_rectangle((770.16 - x0, 1054.46 - y0, 878.67 - x0, 1294.58 - y0), radius=12, outline=(237, 28, 36, 230), width=7)
    overlay.alpha_composite(overlay_layer)
    return overlay


def build() -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    rng = random.Random(SEED)
    hard_outer, hard_cutouts, paintable, top_left_outer, diagonal_cutout = masks()
    size = hard_outer.size
    art = Image.new("RGBA", size, WHITE)
    art.alpha_composite(panel_wash(size, paintable, rng))
    draw_panel_edges(art, hard_outer, paintable, top_left_outer, diagonal_cutout)

    element_mask = Image.new("L", size, 0)
    placements: list[dict[str, int | str]] = []
    element_mask = draw_gauge(art, element_mask, paintable, placements, rng)
    element_mask = draw_sliders(art, element_mask, paintable, placements, rng)
    element_mask = draw_pills(art, element_mask, paintable, placements, rng)
    element_mask = draw_small_button_panel(art, element_mask, paintable, placements, rng)
    element_mask = draw_reference_marks(art, element_mask, paintable, placements, rng)
    art.alpha_composite(broad_highlights(size, paintable))
    art = watercolor_finish(art, paintable, rng)

    white = Image.new("RGBA", size, WHITE)
    art = Image.composite(art, white, hard_outer)
    art = Image.composite(white, art, hard_cutouts)

    overlay = overlay_review(art, top_left_outer, diagonal_cutout)

    mask_debug = Image.new("RGBA", size, WHITE)
    mask_debug.alpha_composite(clipped(Image.new("RGBA", size, (88, 169, 226, 170)), hard_outer))
    mask_debug.alpha_composite(clipped(Image.new("RGBA", size, (237, 28, 36, 180)), hard_cutouts))
    mask_debug.alpha_composite(clipped(Image.new("RGBA", size, (38, 230, 150, 145)), element_mask))
    mask_debug = overlay_review(mask_debug, top_left_outer, diagonal_cutout)

    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "area": "01 top-left",
        "method": METHOD,
        "source_svg": str(base.SVG.relative_to(base.TASK.parent.parent)),
        "not_crop_method": True,
        "fix_reason": "Previous restart still substituted palette and motif matching for the references' watercolor rendering language.",
        "style_reference_images": [
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
            "/Users/za/Downloads/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
        ],
        "style_corrections": [
            "soft blue wash constructed as layered pigment rather than flat fill",
            "blurred texture sampled from the actual watercolor control-panel references",
            "blurred organic navy edge pooling instead of clean vector outlines",
            "larger simpler rounded controls with painted highlights",
            "sparser control vocabulary based on the reference panels",
            "explicit style failure note so palette match is not treated as style match",
        ],
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
