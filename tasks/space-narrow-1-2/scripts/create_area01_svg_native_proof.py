#!/usr/bin/env python3
"""Create an SVG-native, pocket-planned proof for narrow 1+2 area 01.

This variant is a response to the rejected crop-based method. It fills the
selected SVG contour as a substrate, then places every decorative module into
known safe pockets before rendering. The final masks are verification guards;
they are not used to make a generic full-rectangle picture look correct.
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


OUTPUT_STEM = "area-01-top-left-svg-native-v1"
METHOD = "svg-native-pocket-planned"
SEED = 2026061602


Color = tuple[int, int, int, int]
Box = tuple[int, int, int, int]
Point = tuple[int, int]


def mask_outside_pixels(mask: Image.Image, allowed: Image.Image) -> int:
    mask_arr = np.asarray(mask) > 0
    allowed_arr = np.asarray(allowed) > 0
    return int((mask_arr & ~allowed_arr).sum())


def add_mask(target: Image.Image, mask: Image.Image) -> Image.Image:
    return ImageChops.lighter(target, mask)


def component(size: tuple[int, int]) -> tuple[Image.Image, Image.Image, ImageDraw.ImageDraw, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    return layer, mask, ImageDraw.Draw(layer, "RGBA"), ImageDraw.Draw(mask)


def commit(
    art: Image.Image,
    element_mask: Image.Image,
    layer: Image.Image,
    mask: Image.Image,
    paintable: Image.Image,
    name: str,
    placements: list[dict[str, int | str]],
) -> Image.Image:
    outside = mask_outside_pixels(mask, paintable)
    placements.append({"name": name, "outside_paintable_pixels": outside})
    if outside:
        raise ValueError(f"{name} is not inside the paintable SVG pocket: {outside} pixels outside")
    art.alpha_composite(layer)
    return add_mask(element_mask, mask)


def draw_rounded_box(
    draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw,
    box: Box,
    radius: int,
    fill: Color,
    outline: Color,
    width: int = 4,
) -> None:
    x1, y1, x2, y2 = box
    shadow = (x1 + 8, y1 + 10, x2 + 8, y2 + 12)
    mask_draw.rounded_rectangle(shadow, radius=radius, fill=255)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)
    draw.rounded_rectangle(shadow, radius=radius, fill=(4, 22, 68, 95))
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    draw.rounded_rectangle((x1 + 10, y1 + 10, x2 - 10, y1 + 28), radius=12, fill=(255, 255, 255, 70))


def draw_bolt(draw: ImageDraw.ImageDraw, mask_draw: ImageDraw.ImageDraw, point: Point, r: int = 10) -> None:
    x, y = point
    shadow = (x - r + 4, y - r + 6, x + r + 5, y + r + 8)
    box = (x - r, y - r, x + r, y + r)
    mask_draw.ellipse(shadow, fill=255)
    mask_draw.ellipse(box, fill=255)
    draw.ellipse(shadow, fill=(5, 22, 68, 80))
    draw.ellipse(box, fill=(174, 213, 236, 245), outline=(16, 58, 122, 245), width=3)
    draw.ellipse((x - r + 4, y - r + 4, x - r + 10, y - r + 10), fill=(255, 255, 255, 150))


def draw_pipe(
    draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw,
    points: list[Point],
    color: Color,
    width: int,
    outline: Color,
) -> None:
    shadow_points = [(x + 5, y + 7) for x, y in points]
    mask_draw.line(shadow_points, fill=255, width=width + 9, joint="curve")
    mask_draw.line(points, fill=255, width=width + 9, joint="curve")
    draw.line(shadow_points, fill=(5, 24, 76, 90), width=width + 6, joint="curve")
    draw.line(points, fill=outline, width=width + 7, joint="curve")
    draw.line(points, fill=color, width=width, joint="curve")
    draw.line([(x - 3, y - 3) for x, y in points], fill=(255, 255, 255, 95), width=max(3, width // 4), joint="curve")
    for x, y in points:
        rr = width // 2
        mask_draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color, outline=outline, width=3)


def rounded_box_component(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    box: Box,
    radius: int,
    fill: Color,
    outline: Color,
    buttons: list[tuple[int, int, Color]] | None = None,
    louvers: int = 0,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    draw_rounded_box(draw, mask_draw, box, radius, fill, outline, 5)
    if buttons:
        for x, y, color in buttons:
            mask_draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=255)
            draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=color, outline=outline, width=3)
            draw.ellipse((x - 10, y - 12, x - 1, y - 3), fill=(255, 255, 255, 115))
    for index in range(louvers):
        y = box[1] + 45 + index * 38
        mask_draw.rounded_rectangle((box[0] + 48, y, box[2] - 48, y + 16), radius=8, fill=255)
        draw.rounded_rectangle((box[0] + 48, y, box[2] - 48, y + 16), radius=8, fill=(18, 73, 139, 235))
    return commit(art, element_mask, layer, mask, paintable, name, placements)


def pipe_component(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
    color: Color,
    width: int,
    outline: Color,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    draw_pipe(draw, mask_draw, points, color, width, outline)
    return commit(art, element_mask, layer, mask, paintable, name, placements)


def polygon_component(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
    fill: Color,
    outline: Color,
    width: int = 5,
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    shadow = [(x + 8, y + 9) for x, y in points]
    mask_draw.polygon(shadow, fill=255)
    mask_draw.polygon(points, fill=255)
    draw.polygon(shadow, fill=(4, 22, 68, 82))
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint="curve")
    draw.line([(x + 10, y + 10) for x, y in points[: min(4, len(points))]], fill=(169, 218, 241, 145), width=3)
    return commit(art, element_mask, layer, mask, paintable, name, placements)


def bolt_component(
    art: Image.Image,
    element_mask: Image.Image,
    paintable: Image.Image,
    placements: list[dict[str, int | str]],
    name: str,
    points: list[Point],
) -> Image.Image:
    layer, mask, draw, mask_draw = component(art.size)
    for point in points:
        draw_bolt(draw, mask_draw, point)
    return commit(art, element_mask, layer, mask, paintable, name, placements)


def build_art() -> tuple[Image.Image, Image.Image, Image.Image, dict]:
    rng = random.Random(SEED)
    base.GENERATED.mkdir(parents=True, exist_ok=True)
    base.REVIEWS.mkdir(parents=True, exist_ok=True)

    paths = base.load_paths()
    top_left_outer = paths[6].data
    diagonal_cutout = paths[7].data
    circle_cutout_center = (1486.61, 1268.34)
    circle_cutout_radius = 76.0
    red_slot = (770.16, 1054.46, 108.51, 240.12)
    stabilizer_slot = (752.0, 1050.0, 146.0, 502.0)

    size = (base.CROP[2] - base.CROP[0], base.CROP[3] - base.CROP[1])
    outer = base.draw_path_mask(top_left_outer, size)
    cutouts = base.composite_mask(
        base.draw_path_mask(diagonal_cutout, size),
        base.ellipse_mask(size, *circle_cutout_center, circle_cutout_radius),
        base.rect_mask(size, red_slot, radius=12),
        base.rect_mask(size, stabilizer_slot, radius=12),
    ).filter(ImageFilter.MaxFilter(9))
    hard_outer = outer.point(lambda p: 255 if p > 0 else 0)
    hard_cutouts = cutouts.point(lambda p: 255 if p > 0 else 0)
    paintable = ImageChops.subtract(hard_outer, hard_cutouts)

    navy: Color = (15, 55, 118, 245)
    deep: Color = (17, 70, 145, 240)
    steel: Color = (191, 218, 235, 246)
    steel_blue: Color = (137, 204, 232, 246)
    red: Color = (248, 92, 78, 246)
    yellow: Color = (255, 200, 54, 246)
    green: Color = (91, 213, 173, 246)
    cyan: Color = (113, 229, 250, 246)

    art = Image.new("RGBA", size, (255, 255, 255, 255))

    # Substrate: exact SVG contour fill is allowed. It is not a cropped generic
    # illustration; it is the material surface of this manufactured part.
    texture = base.watercolor_texture(size, (53, 126, 198), rng)
    base.fill_masked(art, texture, paintable)

    # Boundary lip is contour-derived and clipped only to the SVG body so it
    # behaves like an edge treatment, not like cropped decorative content.
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(rim, top_left_outer, (8, 40, 98, 220), 50)
    base.draw_polyline(rim, top_left_outer, (201, 229, 243, 215), 34)
    base.draw_polyline(rim, top_left_outer, (255, 255, 255, 105), 12)
    base.draw_polyline(rim, top_left_outer, navy, 6)
    rim = Image.composite(rim, Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer)
    art.alpha_composite(rim)

    element_mask = Image.new("L", size, 0)
    placements: list[dict[str, int | str]] = []

    element_mask = polygon_component(
        art,
        element_mask,
        paintable,
        placements,
        "left contoured machinery bay",
        [(210, 1360), (210, 1150), (276, 980), (282, 740), (392, 408), (520, 248), (608, 236), (640, 282), (640, 1360), (286, 1360)],
        deep,
        navy,
    )
    element_mask = polygon_component(
        art,
        element_mask,
        paintable,
        placements,
        "right lower safe bay",
        [(958, 1460), (958, 1148), (1030, 1102), (1164, 1128), (1298, 1240), (1368, 1434), (1248, 1470)],
        (27, 83, 160, 235),
        navy,
    )

    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "top left control cluster",
        (338, 438, 608, 620),
        18,
        steel,
        navy,
        buttons=[(392, 478, red), (450, 478, yellow), (508, 478, green)],
    )
    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "left louver module",
        (282, 862, 558, 1038),
        20,
        steel,
        navy,
        louvers=3,
    )
    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "lower button module",
        (302, 1148, 580, 1346),
        20,
        steel,
        navy,
        buttons=[(396, 1208, red), (396, 1264, yellow), (396, 1320, green)],
    )
    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "right safe pocket control module",
        (1042, 1190, 1248, 1364),
        20,
        steel,
        navy,
        buttons=[(1110, 1242, red), (1110, 1296, yellow), (1110, 1350, green)],
    )

    # The tall bottle and all pipe runs are routed through clear lanes around
    # the diagonal cutout, the red slot, and the circular cutout.
    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "top vertical canister",
        (492, 242, 616, 572),
        42,
        (57, 174, 221, 246),
        navy,
    )
    element_mask = rounded_box_component(
        art,
        element_mask,
        paintable,
        placements,
        "canister cap",
        (512, 190, 594, 260),
        20,
        (215, 231, 238, 248),
        navy,
    )

    element_mask = pipe_component(art, element_mask, paintable, placements, "red top pipe", [(370, 620), (370, 725), (318, 812), (318, 854)], red, 15, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "yellow top pipe", [(430, 620), (430, 728), (382, 812), (382, 854)], yellow, 15, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "green top pipe", [(490, 620), (490, 728), (450, 812), (450, 854)], green, 15, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "cyan vertical trunk", [(574, 572), (590, 704), (558, 854), (542, 1148)], cyan, 21, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "lower cyan return", [(395, 1346), (395, 1410), (492, 1484), (610, 1420), (614, 1320)], cyan, 21, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "lower red return", [(496, 1344), (560, 1406), (642, 1416), (704, 1332)], red, 15, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "right cyan feed", [(1016, 1110), (1036, 1190), (1054, 1268)], cyan, 18, navy)
    element_mask = pipe_component(art, element_mask, paintable, placements, "right red exhaust", [(1248, 1362), (1304, 1414), (1360, 1422)], red, 14, navy)

    element_mask = bolt_component(
        art,
        element_mask,
        paintable,
        placements,
        "rim and bay bolts",
        [
            (520, 252),
            (596, 270),
            (392, 420),
            (256, 730),
            (260, 1040),
            (252, 1340),
            (352, 1342),
            (590, 1338),
            (640, 980),
            (640, 1260),
            (1028, 1142),
            (1270, 1260),
            (1336, 1410),
            (1170, 1460),
        ],
    )

    # Small stars and rivet highlights are also checked as decorative content.
    layer, mask, draw, mask_draw = component(size)
    sparkle_count = 0
    for _ in range(180):
        x = rng.choice([rng.randint(190, 650), rng.randint(970, 1360)])
        y = rng.randint(220, 1450)
        r = rng.randint(2, 5)
        dot = Image.new("L", size, 0)
        dot_draw = ImageDraw.Draw(dot)
        dot_draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        if mask_outside_pixels(dot, paintable):
            continue
        fill = rng.choice([(255, 255, 255, 90), (255, 211, 65, 135), (134, 240, 255, 105)])
        mask_draw.bitmap((0, 0), dot, fill=255)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)
        sparkle_count += 1
        if sparkle_count >= 70:
            break
    element_mask = commit(art, element_mask, layer, mask, paintable, "pocket sparkle details", placements)

    overlay = art.copy()
    overlay_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    base.draw_polyline(overlay_layer, top_left_outer, (255, 219, 85, 235), 8, dash=24)
    base.draw_polyline(overlay_layer, diagonal_cutout, (255, 219, 85, 235), 8, dash=24)
    overlay_draw = ImageDraw.Draw(overlay_layer, "RGBA")
    cx, cy = circle_cutout_center
    x0, y0, _, _ = base.CROP
    overlay_draw.ellipse(
        (
            cx - circle_cutout_radius - x0,
            cy - circle_cutout_radius - y0,
            cx + circle_cutout_radius - x0,
            cy + circle_cutout_radius - y0,
        ),
        outline=(255, 219, 85, 235),
        width=8,
    )
    rx, ry, rw, rh = red_slot
    overlay_draw.rounded_rectangle((rx - x0, ry - y0, rx + rw - x0, ry + rh - y0), radius=12, outline=(237, 28, 36, 230), width=7)
    overlay.alpha_composite(overlay_layer)

    mask_debug = Image.new("RGBA", size, (255, 255, 255, 255))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (88, 169, 226, 170)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (237, 28, 36, 180)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_cutouts))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (38, 230, 150, 145)), Image.new("RGBA", size, (0, 0, 0, 0)), element_mask))
    mask_debug.alpha_composite(overlay_layer)

    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "area": "01 top-left",
        "method": METHOD,
        "source_svg": str(base.SVG.relative_to(base.TASK.parent.parent)),
        "style_refs": [
            "refs/control-panel-sliders.png",
            "refs/space-planets.png",
            "refs/lever-module.png",
            "refs/dial-toggle-panel.png",
            "refs/radar-screen.png",
        ],
        "not_crop_method": True,
        "boundary_mask_role": "substrate fill and final SVG-edge guard only",
        "decorative_components_checked_before_render": True,
        "component_placements": placements,
        "crop_svg_units": list(base.CROP),
        "cutout_zones": {
            "diagonal_yellow_path": "source SVG line 57",
            "circle_yellow_path": {"center": list(circle_cutout_center), "radius_used": circle_cutout_radius},
            "red_slot": list(red_slot),
            "stabilizer_slot_conservative": list(stabilizer_slot),
        },
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
    art, overlay, mask_debug, metadata = build_art()

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
