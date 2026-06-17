#!/usr/bin/env python3
"""Create a contour-native illustration proof for the attached top-temp SVG.

This is deliberately not a rectangle-first image that gets cropped into the
template. The SVG body is used as the material substrate, and every decorative
component is checked against a margin-safe paintable mask before it is rendered.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[1]
SVG = TASK / "source/top-temp.svg"
GENERATED = TASK / "outputs/generated"
REVIEWS = TASK / "outputs/reviews"
OUTPUT_STEM = "top-temp-contour-native-v1"
METHOD = "contour-native-pocket-planned"
SEED = 2026061603
CROP = (0, 0, 1593, 1571)

sys.path.insert(0, str(REPO / "tasks/space-narrow-1-2/scripts"))
import create_area01_top_left_proof as svgbase  # noqa: E402


Color = tuple[int, int, int, int]
Box = tuple[int, int, int, int]
Point = tuple[int, int]


def configure_svg_helpers() -> None:
    svgbase.SVG = SVG
    svgbase.CROP = CROP


def outside_pixels(mask: Image.Image, allowed: Image.Image) -> int:
    mask_arr = np.asarray(mask) > 0
    allowed_arr = np.asarray(allowed) > 0
    return int((mask_arr & ~allowed_arr).sum())


def nonwhite_pixels(image: Image.Image, mask: Image.Image) -> int:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    masked = np.asarray(mask) > 0
    nonwhite = ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > 30
    return int((nonwhite & masked).sum())


def component(size: tuple[int, int]) -> tuple[Image.Image, Image.Image, ImageDraw.ImageDraw, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    return layer, mask, ImageDraw.Draw(layer, "RGBA"), ImageDraw.Draw(mask)


def commit(
    art: Image.Image,
    element_mask: Image.Image,
    layer: Image.Image,
    mask: Image.Image,
    allowed: Image.Image,
    name: str,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    outside = outside_pixels(mask, allowed)
    placements.append({"name": name, "outside_safe_pocket_pixels": outside})
    if outside:
        raise ValueError(f"{name} crosses the safe SVG pocket by {outside} pixels")
    art.alpha_composite(layer)
    return ImageChops.lighter(element_mask, mask)


def draw_round_box(
    draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw,
    box: Box,
    radius: int,
    fill: Color,
    outline: Color,
    width: int = 5,
) -> None:
    x1, y1, x2, y2 = box
    shadow = (x1 + 8, y1 + 10, x2 + 8, y2 + 12)
    mask_draw.rounded_rectangle(shadow, radius=radius, fill=255)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)
    draw.rounded_rectangle(shadow, radius=radius, fill=(6, 28, 72, 82))
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    draw.rounded_rectangle((x1 + 10, y1 + 10, x2 - 10, y1 + 30), radius=12, fill=(255, 255, 255, 76))


def add_box(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    box: Box,
    radius: int,
    fill: Color,
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    draw_round_box(draw, mask_draw, box, radius, fill, outline)
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_button_bank(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[tuple[int, int, int, Color]],
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    for x, y, r, color in points:
        mask_draw.ellipse((x - r + 5, y - r + 8, x + r + 6, y + r + 10), fill=255)
        mask_draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        draw.ellipse((x - r + 5, y - r + 8, x + r + 6, y + r + 10), fill=(6, 28, 72, 72))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=outline, width=4)
        draw.ellipse((x - r + 9, y - r + 8, x - r + 25, y - r + 24), fill=(255, 255, 255, 105))
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_pipe(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
    color: Color,
    outline: Color,
    width: int,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    shadow = [(x + 5, y + 7) for x, y in points]
    mask_draw.line(shadow, fill=255, width=width + 10, joint="curve")
    mask_draw.line(points, fill=255, width=width + 10, joint="curve")
    draw.line(shadow, fill=(5, 27, 76, 86), width=width + 5, joint="curve")
    draw.line(points, fill=outline, width=width + 7, joint="curve")
    draw.line(points, fill=color, width=width, joint="curve")
    draw.line([(x - 3, y - 3) for x, y in points], fill=(255, 255, 255, 92), width=max(3, width // 4), joint="curve")
    for x, y in points:
        rr = width // 2
        mask_draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color, outline=outline, width=3)
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_poly(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
    fill: Color,
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    shadow = [(x + 8, y + 10) for x, y in points]
    mask_draw.polygon(shadow, fill=255)
    mask_draw.polygon(points, fill=255)
    draw.polygon(shadow, fill=(5, 26, 71, 78))
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=6, joint="curve")
    draw.line([(x + 10, y + 10) for x, y in points[:4]], fill=(178, 225, 245, 135), width=3)
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_louvers(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    box: Box,
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    draw_round_box(draw, mask_draw, box, 20, (190, 218, 235, 246), outline)
    for y in range(box[1] + 48, box[3] - 26, 38):
        strip = (box[0] + 48, y, box[2] - 44, y + 15)
        mask_draw.rounded_rectangle(strip, radius=8, fill=255)
        draw.rounded_rectangle(strip, radius=8, fill=(18, 74, 139, 232))
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_bolts(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    for x, y in points:
        r = 11
        mask_draw.ellipse((x - r + 4, y - r + 6, x + r + 5, y + r + 8), fill=255)
        mask_draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        draw.ellipse((x - r + 4, y - r + 6, x + r + 5, y + r + 8), fill=(5, 25, 72, 75))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(175, 214, 236, 245), outline=outline, width=3)
        draw.ellipse((x - r + 4, y - r + 4, x - r + 10, y - r + 10), fill=(255, 255, 255, 135))
    return commit(art, element_mask, layer, mask, allowed, name, placements)


def add_safe_stars(
    art: Image.Image,
    element_mask: Image.Image,
    allowed: Image.Image,
    placements: list[dict[str, int | str]],
    rng: random.Random,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    count = 0
    for _ in range(520):
        x = rng.choice([rng.randint(105, 660), rng.randint(930, 1365)])
        y = rng.randint(120, 1480)
        r = rng.randint(2, 5)
        dot = Image.new("L", art.size, 0)
        ImageDraw.Draw(dot).ellipse((x - r, y - r, x + r, y + r), fill=255)
        if outside_pixels(dot, allowed):
            continue
        mask_draw.bitmap((0, 0), dot, fill=255)
        fill = rng.choice([(255, 255, 255, 88), (255, 211, 65, 126), (134, 240, 255, 104)])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)
        count += 1
        if count >= 90:
            break
    placements.append({"name": "candidate-checked sparkle details", "outside_safe_pocket_pixels": outside_pixels(mask, allowed)})
    if outside_pixels(mask, allowed):
        raise ValueError("sparkle details crossed safe pocket")
    art.alpha_composite(layer)
    return ImageChops.lighter(element_mask, mask)


def build_art() -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    configure_svg_helpers()
    rng = random.Random(SEED)
    GENERATED.mkdir(parents=True, exist_ok=True)
    REVIEWS.mkdir(parents=True, exist_ok=True)

    paths = svgbase.load_paths()
    if len(paths) < 3:
        raise ValueError(f"Expected at least 3 path elements in {SVG}, found {len(paths)}")

    outer_data = paths[0].data
    diagonal_cutout_data = paths[1].data
    circle_cutout_data = paths[2].data
    size = (CROP[2] - CROP[0], CROP[3] - CROP[1])

    outer = svgbase.draw_path_mask(outer_data, size)
    diagonal_cutout = svgbase.draw_path_mask(diagonal_cutout_data, size)
    circle_cutout = svgbase.draw_path_mask(circle_cutout_data, size)
    hard_outer = outer.point(lambda p: 255 if p > 0 else 0)
    hard_cutouts = svgbase.composite_mask(diagonal_cutout, circle_cutout).filter(ImageFilter.MaxFilter(9)).point(
        lambda p: 255 if p > 0 else 0
    )
    paintable = ImageChops.subtract(hard_outer, hard_cutouts)
    safe_outer = hard_outer.filter(ImageFilter.MinFilter(13))
    safe_cutouts = hard_cutouts.filter(ImageFilter.MaxFilter(25))
    safe_pocket = ImageChops.subtract(safe_outer, safe_cutouts)

    navy: Color = (15, 55, 118, 245)
    deep: Color = (19, 78, 152, 236)
    steel: Color = (190, 218, 235, 246)
    steel_blue: Color = (137, 204, 232, 246)
    red: Color = (248, 92, 78, 246)
    yellow: Color = (255, 201, 54, 246)
    green: Color = (91, 213, 173, 246)
    cyan: Color = (113, 229, 250, 246)
    glow: Color = (122, 232, 252, 246)

    art = Image.new("RGBA", size, (255, 255, 255, 255))
    texture = svgbase.watercolor_texture(size, (54, 126, 198), rng)
    svgbase.fill_masked(art, texture, paintable)

    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    svgbase.draw_polyline(rim, outer_data, (8, 40, 98, 220), 48)
    svgbase.draw_polyline(rim, outer_data, (199, 229, 243, 215), 30)
    svgbase.draw_polyline(rim, outer_data, (255, 255, 255, 100), 10)
    svgbase.draw_polyline(rim, outer_data, navy, 5)
    svgbase.draw_polyline(rim, diagonal_cutout_data, (10, 48, 105, 205), 28)
    svgbase.draw_polyline(rim, diagonal_cutout_data, (216, 237, 247, 205), 18)
    svgbase.draw_polyline(rim, diagonal_cutout_data, navy, 5)
    svgbase.draw_polyline(rim, circle_cutout_data, (10, 48, 105, 205), 26)
    svgbase.draw_polyline(rim, circle_cutout_data, (216, 237, 247, 205), 16)
    svgbase.draw_polyline(rim, circle_cutout_data, navy, 5)
    rim = Image.composite(rim, Image.new("RGBA", size, (0, 0, 0, 0)), paintable)
    art.alpha_composite(rim)

    element_mask = Image.new("L", size, 0)
    placements: list[dict[str, int | str]] = []

    element_mask = add_poly(
        art,
        element_mask,
        safe_pocket,
        placements,
        "left contour machinery well",
        [(138, 1450), (138, 1160), (232, 990), (236, 708), (342, 386), (476, 172), (586, 108), (640, 156), (642, 1448)],
        deep,
        navy,
    )
    element_mask = add_poly(
        art,
        element_mask,
        safe_pocket,
        placements,
        "lower right service bay",
        [(1006, 1448), (1006, 1142), (1074, 1112), (1192, 1138), (1310, 1276), (1352, 1430), (1224, 1448)],
        (26, 83, 160, 235),
        navy,
    )
    element_mask = add_box(art, element_mask, safe_pocket, placements, "top left canister", (486, 176, 616, 480), 42, (57, 174, 221, 246), navy)
    element_mask = add_box(art, element_mask, safe_pocket, placements, "canister cap", (506, 130, 596, 200), 20, (215, 231, 238, 248), navy)
    element_mask = add_box(art, element_mask, safe_pocket, placements, "left switch cluster", (280, 438, 568, 620), 18, steel, navy)
    element_mask = add_louvers(art, element_mask, safe_pocket, placements, "left vent module", (252, 814, 548, 1024), navy)
    element_mask = add_box(art, element_mask, safe_pocket, placements, "lower left button module", (300, 1164, 586, 1360), 20, steel, navy)
    element_mask = add_box(art, element_mask, safe_pocket, placements, "right command module", (1030, 1164, 1254, 1364), 20, steel, navy)

    element_mask = add_button_bank(
        art,
        element_mask,
        safe_pocket,
        placements,
        "left cluster buttons",
        [(334, 488, 18, red), (394, 488, 18, yellow), (454, 488, 18, green), (510, 550, 16, glow)],
        navy,
    )
    element_mask = add_button_bank(
        art,
        element_mask,
        safe_pocket,
        placements,
        "lower left button stack",
        [(402, 1222, 19, red), (402, 1276, 19, yellow), (402, 1330, 19, green), (506, 1268, 18, glow)],
        navy,
    )
    element_mask = add_button_bank(
        art,
        element_mask,
        safe_pocket,
        placements,
        "right command lights",
        [(1106, 1222, 18, red), (1106, 1280, 18, yellow), (1106, 1338, 18, green), (1198, 1258, 17, glow), (1198, 1324, 17, glow)],
        navy,
    )

    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "red left routed pipe", [(350, 620), (350, 720), (316, 782), (316, 814)], red, navy, 15)
    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "yellow left routed pipe", [(410, 620), (410, 716), (382, 782), (382, 814)], yellow, navy, 15)
    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "cyan trunk pipe", [(560, 480), (590, 662), (548, 814), (528, 1164)], cyan, navy, 21)
    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "lower cyan return", [(392, 1360), (392, 1398), (488, 1450), (594, 1398), (598, 1330)], cyan, navy, 20)
    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "right cyan feed", [(986, 1108), (1022, 1164), (1048, 1244)], cyan, navy, 18)
    element_mask = add_pipe(art, element_mask, safe_pocket, placements, "right red return", [(1254, 1352), (1300, 1414), (1350, 1436)], red, navy, 14)

    element_mask = add_bolts(
        art,
        element_mask,
        safe_pocket,
        placements,
        "interior rim bolts",
        [
            (520, 182),
            (586, 194),
            (348, 420),
            (258, 718),
            (214, 1090),
            (176, 1376),
            (348, 1406),
            (612, 1410),
            (1016, 1106),
            (1280, 1240),
            (1360, 1410),
            (1212, 1428),
        ],
        navy,
    )
    element_mask = add_safe_stars(art, element_mask, safe_pocket, placements, rng)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    art = Image.composite(art, white, hard_outer)
    art = Image.composite(white, art, hard_cutouts)

    overlay = art.copy()
    overlay_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    svgbase.draw_polyline(overlay_layer, outer_data, (255, 219, 85, 238), 8, dash=24)
    svgbase.draw_polyline(overlay_layer, diagonal_cutout_data, (255, 219, 85, 238), 8, dash=24)
    svgbase.draw_polyline(overlay_layer, circle_cutout_data, (255, 219, 85, 238), 8, dash=24)
    overlay.alpha_composite(overlay_layer)

    mask_debug = Image.new("RGBA", size, (255, 255, 255, 255))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (74, 154, 220, 160)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (237, 28, 36, 180)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_cutouts))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (38, 230, 150, 145)), Image.new("RGBA", size, (0, 0, 0, 0)), element_mask))
    mask_debug.alpha_composite(overlay_layer)

    outside_mask = hard_outer.point(lambda p: 0 if p else 255)
    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": METHOD,
        "source_svg": str(SVG.relative_to(REPO)),
        "source_attachment": "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/space/top-temp.svg",
        "viewbox_crop": list(CROP),
        "outer_path_index": paths[0].element_index,
        "cutout_path_indices": [paths[1].element_index, paths[2].element_index],
        "not_crop_method": True,
        "boundary_mask_role": "substrate fill and final SVG-edge guard only",
        "decorative_components_checked_before_render": True,
        "safe_outer_margin_pixels": 6,
        "safe_cutout_margin_pixels": 12,
        "component_placements": placements,
        "nonwhite_pixels_outside_outer_mask": nonwhite_pixels(art, outside_mask),
        "nonwhite_pixels_in_cutout_mask": nonwhite_pixels(art, hard_cutouts),
        "decorative_element_pixels_outside_paintable_mask": outside_pixels(element_mask, paintable),
        "decorative_element_pixels_outside_safe_pocket_mask": outside_pixels(element_mask, safe_pocket),
        "artwork": f"outputs/generated/{OUTPUT_STEM}-artwork.png",
        "overlay": f"outputs/reviews/{OUTPUT_STEM}-template-overlay.png",
        "mask_debug": f"outputs/reviews/{OUTPUT_STEM}-mask-debug.png",
    }
    return art, overlay, mask_debug, metadata


def main() -> int:
    art, overlay, mask_debug, metadata = build_art()
    art_path = GENERATED / f"{OUTPUT_STEM}-artwork.png"
    overlay_path = REVIEWS / f"{OUTPUT_STEM}-template-overlay.png"
    mask_path = REVIEWS / f"{OUTPUT_STEM}-mask-debug.png"
    metadata_path = REVIEWS / f"{OUTPUT_STEM}-metadata.json"

    art.convert("RGB").save(art_path)
    overlay.convert("RGB").save(overlay_path)
    mask_debug.convert("RGB").save(mask_path)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
