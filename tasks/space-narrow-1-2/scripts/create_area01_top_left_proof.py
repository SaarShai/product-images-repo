#!/usr/bin/env python3
"""Create a geometry-masked proof for narrow 1+2 area 01.

This first proof targets the top-left yellow-dashed area. The artwork is
procedural so the SVG cutout zones can be hard-masked before review.
"""

from __future__ import annotations

import json
import math
import random
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


TASK = Path(__file__).resolve().parents[1]
SVG = TASK / "source/narrow-1-plus-2.svg"
GENERATED = TASK / "outputs/generated"
REVIEWS = TASK / "outputs/reviews"

TOKEN_RE = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
CROP = (0, 0, 1668, 1668)
AA = 3
SEED = 1201626


Point = tuple[float, float]


@dataclass
class SvgPath:
    element_index: int
    css_class: str
    data: str


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    return (
        inv**3 * p0[0] + 3 * inv * inv * t * p1[0] + 3 * inv * t * t * p2[0] + t**3 * p3[0],
        inv**3 * p0[1] + 3 * inv * inv * t * p1[1] + 3 * inv * t * t * p2[1] + t**3 * p3[1],
    )


def quad(p0: Point, p1: Point, p2: Point, t: float) -> Point:
    inv = 1.0 - t
    return (
        inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0],
        inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1],
    )


def path_points(data: str, steps: int = 24) -> list[Point]:
    tokens = TOKEN_RE.findall(data.replace(",", " "))
    index = 0
    command = ""
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    last_cubic_control: Point | None = None
    last_quad_control: Point | None = None
    points: list[Point] = []

    def has_number(offset: int = 0) -> bool:
        return index + offset < len(tokens) and not is_command(tokens[index + offset])

    def has_numbers(count: int) -> bool:
        return all(has_number(offset) for offset in range(count))

    def number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    def absolute(point: Point, relative: bool) -> Point:
        if relative:
            return current[0] + point[0], current[1] + point[1]
        return point

    def add_line(point: Point) -> None:
        nonlocal current
        current = point
        points.append(point)

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if not command:
            break

        relative = command.islower()
        cmd = command.upper()

        if cmd == "M":
            first = True
            while has_numbers(2):
                point = absolute((number(), number()), relative)
                add_line(point)
                if first:
                    start = point
                    first = False
                command = "l" if relative else "L"
            last_cubic_control = None
            last_quad_control = None
        elif cmd == "L":
            while has_numbers(2):
                add_line(absolute((number(), number()), relative))
            last_cubic_control = None
            last_quad_control = None
        elif cmd == "H":
            while has_number():
                value = number()
                add_line((current[0] + value, current[1]) if relative else (value, current[1]))
            last_cubic_control = None
            last_quad_control = None
        elif cmd == "V":
            while has_number():
                value = number()
                add_line((current[0], current[1] + value) if relative else (current[0], value))
            last_cubic_control = None
            last_quad_control = None
        elif cmd == "C":
            while has_numbers(6):
                p0 = current
                p1 = absolute((number(), number()), relative)
                p2 = absolute((number(), number()), relative)
                p3 = absolute((number(), number()), relative)
                for step in range(1, steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / steps))
                current = p3
                last_cubic_control = p2
                last_quad_control = None
        elif cmd == "S":
            while has_numbers(4):
                p0 = current
                if last_cubic_control is None:
                    p1 = current
                else:
                    p1 = (2 * current[0] - last_cubic_control[0], 2 * current[1] - last_cubic_control[1])
                p2 = absolute((number(), number()), relative)
                p3 = absolute((number(), number()), relative)
                for step in range(1, steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / steps))
                current = p3
                last_cubic_control = p2
                last_quad_control = None
        elif cmd == "Q":
            while has_numbers(4):
                p0 = current
                p1 = absolute((number(), number()), relative)
                p2 = absolute((number(), number()), relative)
                for step in range(1, steps + 1):
                    points.append(quad(p0, p1, p2, step / steps))
                current = p2
                last_quad_control = p1
                last_cubic_control = None
        elif cmd == "T":
            while has_numbers(2):
                p0 = current
                if last_quad_control is None:
                    p1 = current
                else:
                    p1 = (2 * current[0] - last_quad_control[0], 2 * current[1] - last_quad_control[1])
                p2 = absolute((number(), number()), relative)
                for step in range(1, steps + 1):
                    points.append(quad(p0, p1, p2, step / steps))
                current = p2
                last_quad_control = p1
                last_cubic_control = None
        elif cmd == "A":
            while has_numbers(7):
                _rx = number()
                _ry = number()
                _rot = number()
                _large = number()
                _sweep = number()
                add_line(absolute((number(), number()), relative))
            last_cubic_control = None
            last_quad_control = None
        elif cmd == "Z":
            add_line(start)
            last_cubic_control = None
            last_quad_control = None
            command = ""
        else:
            raise ValueError(f"Unsupported SVG command: {command}")
    return points


def load_paths() -> list[SvgPath]:
    root = ET.parse(SVG).getroot()
    paths: list[SvgPath] = []
    for index, element in enumerate(root.iter()):
        if local_name(element.tag) != "path" or "d" not in element.attrib:
            continue
        paths.append(SvgPath(index, element.attrib.get("class", ""), element.attrib["d"]))
    return paths


def to_px(point: Point) -> tuple[int, int]:
    x0, y0, _, _ = CROP
    return (round((point[0] - x0) * AA), round((point[1] - y0) * AA))


def draw_path_mask(data: str, size: tuple[int, int], blur: float = 0.0) -> Image.Image:
    mask = Image.new("L", (size[0] * AA, size[1] * AA), 0)
    draw = ImageDraw.Draw(mask)
    points = [to_px(point) for point in path_points(data)]
    if len(points) >= 3:
        draw.polygon(points, fill=255)
    if blur:
        mask = mask.filter(ImageFilter.GaussianBlur(blur * AA))
    return mask.resize(size, Image.Resampling.LANCZOS)


def draw_polyline(
    image: Image.Image,
    data: str,
    color: tuple[int, int, int, int],
    width: int,
    dash: int | None = None,
) -> None:
    draw = ImageDraw.Draw(image)
    x0, y0, _, _ = CROP
    points = [(point[0] - x0, point[1] - y0) for point in path_points(data)]
    if len(points) < 2:
        return
    if dash is None:
        draw.line(points, fill=color, width=width, joint="curve")
        return
    for a, b in zip(points, points[1:]):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.hypot(dx, dy)
        if length <= 0:
            continue
        ux, uy = dx / length, dy / length
        pos = 0.0
        while pos < length:
            end = min(length, pos + dash)
            draw.line(
                [(a[0] + ux * pos, a[1] + uy * pos), (a[0] + ux * end, a[1] + uy * end)],
                fill=color,
                width=width,
            )
            pos += dash * 2


def ellipse_mask(size: tuple[int, int], cx: float, cy: float, r: float) -> Image.Image:
    x0, y0, _, _ = CROP
    mask = Image.new("L", (size[0] * AA, size[1] * AA), 0)
    draw = ImageDraw.Draw(mask)
    box = [
        round((cx - r - x0) * AA),
        round((cy - r - y0) * AA),
        round((cx + r - x0) * AA),
        round((cy + r - y0) * AA),
    ]
    draw.ellipse(box, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def rect_mask(size: tuple[int, int], xywh: tuple[float, float, float, float], radius: float = 0) -> Image.Image:
    x, y, w, h = xywh
    x0, y0, _, _ = CROP
    mask = Image.new("L", (size[0] * AA, size[1] * AA), 0)
    draw = ImageDraw.Draw(mask)
    box = [
        round((x - x0) * AA),
        round((y - y0) * AA),
        round((x + w - x0) * AA),
        round((y + h - y0) * AA),
    ]
    if radius:
        draw.rounded_rectangle(box, radius=round(radius * AA), fill=255)
    else:
        draw.rectangle(box, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def composite_mask(*masks: Image.Image) -> Image.Image:
    out = Image.new("L", masks[0].size, 0)
    for mask in masks:
        out = ImageChops.lighter(out, mask)
    return out


def fill_masked(base: Image.Image, overlay: Image.Image, mask: Image.Image) -> None:
    base.alpha_composite(Image.composite(overlay, Image.new("RGBA", base.size, (0, 0, 0, 0)), mask))


def watercolor_texture(size: tuple[int, int], color: tuple[int, int, int], rng: random.Random) -> Image.Image:
    width, height = size
    base = Image.new("RGBA", size, (*color, 255))
    arr = np.asarray(base).astype(np.int16)
    noise = rng_np(width, height, rng)
    arr[:, :, :3] = np.clip(arr[:, :, :3] + noise[:, :, None], 0, 255)
    image = Image.fromarray(arr.astype("uint8"), "RGBA").filter(ImageFilter.GaussianBlur(0.65))
    wash = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(90):
        cx = rng.randint(-100, width + 100)
        cy = rng.randint(-80, height + 80)
        rx = rng.randint(60, 260)
        ry = rng.randint(30, 180)
        tint = rng.choice([(255, 255, 255, 18), (50, 116, 184, 16), (92, 190, 202, 14)])
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=tint)
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    image.alpha_composite(wash)
    return image


def rng_np(width: int, height: int, rng: random.Random) -> np.ndarray:
    seed = rng.randint(0, 2**32 - 1)
    gen = np.random.default_rng(seed)
    low = gen.normal(0, 10, (height, width))
    high = gen.normal(0, 3, (height, width))
    return np.clip(low + high, -28, 26).astype(np.int16)


def draw_rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_control_art(image: Image.Image, element_mask: Image.Image, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    element_draw = ImageDraw.Draw(element_mask)

    navy = (24, 73, 138, 235)
    blue_shadow = (23, 79, 147, 120)
    pale = (223, 244, 255, 185)
    coral = (250, 102, 91, 238)
    yellow = (255, 193, 61, 238)
    teal = (91, 214, 188, 238)
    aqua = (103, 213, 232, 225)

    def mark_rect(box: tuple[int, int, int, int], radius: int = 0) -> None:
        element_draw.rounded_rectangle(box, radius=radius, fill=255)

    def mark_ellipse(box: tuple[int, int, int, int]) -> None:
        element_draw.ellipse(box, fill=255)

    # Soft panel rim, inspired by the blue rounded modules in the references.
    draw_rounded(draw, (48, 58, 620, 1436), 48, (46, 123, 193, 70), navy, 9)
    draw_rounded(draw, (72, 92, 594, 1408), 38, (160, 220, 246, 70), (94, 163, 220, 120), 4)

    # Small planet/radar bubble on the clear upper-left side.
    mark_ellipse((355, 475, 635, 755))
    draw.ellipse((355, 475, 635, 755), fill=(116, 213, 227, 190), outline=navy, width=7)
    draw.arc((390, 510, 600, 720), 195, 332, fill=(31, 109, 175, 185), width=8)
    draw.arc((430, 535, 575, 695), 200, 328, fill=(255, 255, 255, 115), width=13)
    draw.ellipse((408, 525, 458, 575), fill=(255, 255, 255, 150))

    # Slider bank kept left of the internal diagonal cutout and red slot.
    slider_rows = [1084, 1206, 1330]
    for idx, y in enumerate(slider_rows):
        draw_rounded(draw, (145, y, 690, y + 22), 11, (37, 98, 167, 150), (23, 72, 137, 190), 3)
        draw_rounded(draw, (154, y + 3, 680, y + 10), 4, (199, 232, 255, 120))
        mark_rect((145, y, 690, y + 22), 11)
        for x, color in [
            (205 + idx * 78, teal if idx != 1 else coral),
            (462 + idx * 38, yellow),
            (605 - idx * 64, coral if idx == 0 else teal),
        ]:
            box = (x, y - 18, x + 54, y + 34)
            mark_rect(box, 10)
            draw_rounded(draw, (box[0] + 5, box[1] + 6, box[2] + 5, box[3] + 8), 10, (20, 56, 112, 70))
            draw_rounded(draw, box, 9, color, (24, 72, 135, 215), 4)
            draw_rounded(draw, (box[0] + 8, box[1] + 7, box[2] - 8, box[1] + 18), 7, (255, 255, 255, 95))

    # Lower control buttons, placed outside the circular cutout clearance.
    for i, (x, y, color) in enumerate([(1030, 1240, coral), (1168, 1368, yellow), (1312, 1450, teal)]):
        mark_ellipse((x - 46, y - 46, x + 46, y + 46))
        draw.ellipse((x - 56, y - 44, x + 56, y + 68), fill=blue_shadow)
        draw.ellipse((x - 46, y - 46, x + 46, y + 46), fill=color, outline=navy, width=7)
        draw.ellipse((x - 24, y - 30, x + 10, y + 2), fill=(255, 255, 255, 95))
        if i == 2:
            draw.line((x - 16, y + 22, x + 26, y - 20), fill=(16, 96, 126, 120), width=5)

    # Quiet circuit glyphs in the open lower-left field.
    for y in [900, 970, 1448]:
        x_start = 175 + rng.randint(-12, 12)
        x_end = 542 + rng.randint(-20, 30)
        draw.line((x_start, y, x_end, y), fill=pale, width=8)
        element_draw.line((x_start, y, x_end, y), fill=255, width=12)
        for x in [x_start + 70, x_start + 220, x_start + 340]:
            if rng.random() > 0.25:
                mark_ellipse((x - 14, y - 14, x + 14, y + 14))
                draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=aqua, outline=navy, width=3)

    # Highlights and watercolor edge pooling.
    for box in [(82, 105, 368, 145), (95, 175, 180, 235), (430, 70, 542, 100)]:
        draw.rounded_rectangle(box, radius=18, fill=(255, 255, 255, 85))
    for _ in range(50):
        x = rng.randint(70, 600)
        y = rng.randint(105, 1450)
        r = rng.randint(1, 5)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rng.randint(16, 48)))


def add_contour_built_art(image: Image.Image, element_mask: Image.Image, outer_data: str, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    element_draw = ImageDraw.Draw(element_mask)

    navy = (15, 55, 118, 245)
    deep = (19, 76, 152, 230)
    shadow = (8, 35, 88, 120)
    steel = (190, 215, 235, 245)
    steel_dark = (89, 125, 164, 240)
    glow = (95, 225, 255, 235)
    red = (248, 91, 78, 245)
    yellow = (255, 201, 55, 245)
    green = (100, 213, 169, 245)
    cyan = (119, 228, 251, 245)

    def mark_rect(box: tuple[int, int, int, int], radius: int = 0) -> None:
        element_draw.rounded_rectangle(box, radius=radius, fill=255)

    def mark_ellipse(box: tuple[int, int, int, int]) -> None:
        element_draw.ellipse(box, fill=255)

    def rect(box: tuple[int, int, int, int], radius: int, fill, outline=navy, width: int = 4) -> None:
        mark_rect(box, radius)
        draw.rounded_rectangle((box[0] + 8, box[1] + 10, box[2] + 8, box[3] + 12), radius=radius, fill=shadow)
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
        draw.rounded_rectangle((box[0] + 10, box[1] + 10, box[2] - 10, box[1] + 28), radius=12, fill=(255, 255, 255, 68))

    def bolt(cx: int, cy: int, r: int = 11) -> None:
        mark_ellipse((cx - r, cy - r, cx + r, cy + r))
        draw.ellipse((cx - r + 4, cy - r + 6, cx + r + 5, cy + r + 8), fill=(4, 26, 72, 70))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(171, 213, 236, 245), outline=navy, width=3)
        draw.ellipse((cx - r + 4, cy - r + 4, cx - r + 10, cy - r + 10), fill=(255, 255, 255, 140))

    def pipe(points: list[tuple[int, int]], color, width: int = 17, collar_every: int = 0) -> None:
        element_draw.line(points, fill=255, width=width + 10, joint="curve")
        draw.line([(x + 6, y + 8) for x, y in points], fill=(5, 28, 76, 90), width=width + 4, joint="curve")
        draw.line(points, fill=navy, width=width + 7, joint="curve")
        draw.line(points, fill=color, width=width, joint="curve")
        draw.line([(x - 3, y - 3) for x, y in points], fill=(255, 255, 255, 88), width=max(3, width // 4), joint="curve")
        for x, y in points:
            mark_ellipse((x - width // 2, y - width // 2, x + width // 2, y + width // 2))
            draw.ellipse((x - width // 2, y - width // 2, x + width // 2, y + width // 2), fill=color, outline=navy, width=3)
        if collar_every:
            for idx, (x, y) in enumerate(points[1:-1], 1):
                if idx % collar_every == 0:
                    rect((x - 18, y - 12, x + 18, y + 12), 5, (181, 198, 214, 245), navy, 2)

    # Contour-aware metal lip: this follows the SVG outline rather than trimming
    # an unrelated rectangle. It visually makes the silhouette part of the design.
    rim = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw_polyline(rim, outer_data, (8, 45, 104, 215), 66)
    draw_polyline(rim, outer_data, steel, 46)
    draw_polyline(rim, outer_data, (239, 249, 255, 115), 18)
    draw_polyline(rim, outer_data, navy, 8)
    image.alpha_composite(rim)

    # Inset machinery wells, hand-shaped for this contour and its notches.
    left_well = [
        (112, 1418), (112, 1120), (210, 940), (210, 690), (328, 340),
        (480, 178), (630, 150), (694, 205), (694, 1430), (214, 1430),
    ]
    mid_well = [
        (924, 1440), (924, 1020), (966, 994), (1120, 1005), (1288, 1160),
        (1458, 1335), (1502, 1450), (1364, 1450), (1260, 1394), (1136, 1462),
    ]
    for poly in (left_well, mid_well):
        element_draw.polygon(poly, fill=255)
        draw.polygon([(x + 8, y + 9) for x, y in poly], fill=shadow)
        draw.polygon(poly, fill=deep, outline=navy)
        draw.line(poly + [poly[0]], fill=(131, 185, 224, 210), width=6)

    # Bolts are placed on the lip and around pockets, like the reference.
    for point in [
        (470, 170), (610, 190), (324, 356), (226, 688), (156, 1012),
        (150, 1384), (332, 1430), (610, 1420), (724, 1020), (724, 1320),
        (1008, 1034), (1285, 1182), (1450, 1390), (1212, 1488),
    ]:
        bolt(*point)

    # Tall cylinder designed into the top cap and slanted roof.
    rect((480, 250, 626, 580), 48, (43, 151, 208, 245), navy, 5)
    mark_rect((510, 205, 596, 270), 20)
    draw.rounded_rectangle((510, 205, 596, 270), radius=20, fill=(210, 228, 237, 250), outline=navy, width=4)
    rect((516, 318, 592, 510), 34, (160, 238, 255, 248), navy, 3)
    for y in (276, 555):
        rect((472, y, 634, y + 34), 10, (218, 172, 61, 245), navy, 3)

    # Control boxes sit in pockets, never across the SVG cutouts.
    rect((260, 400, 548, 590), 18, steel, navy, 5)
    for i, color in enumerate([red, yellow, green]):
        x = 314 + i * 58
        mark_ellipse((x - 17, 430, x + 17, 464))
        draw.ellipse((x - 17, 430, x + 17, 464), fill=color, outline=navy, width=3)
    for i in range(3):
        x = 310 + i * 62
        rect((x, 492, x + 25, 565), 10, (45, 192, 232, 220), navy, 2)
        draw.rounded_rectangle((x + 7, 502, x + 17, 555), radius=5, fill=(148, 247, 255, 190))

    rect((188, 830, 470, 1035), 20, steel, navy, 5)
    for y in (880, 925, 970):
        draw.rounded_rectangle((262, y, 398, y + 16), radius=8, fill=(16, 65, 126, 220), outline=navy, width=2)
    rect((312, 1120, 572, 1302), 18, steel, navy, 5)
    for i, color in enumerate([red, yellow, green]):
        x = 410
        y = 1172 + i * 46
        mark_ellipse((x - 19, y - 19, x + 19, y + 19))
        draw.ellipse((x - 19, y - 19, x + 19, y + 19), fill=color, outline=navy, width=3)

    rect((1040, 1138, 1248, 1325), 20, steel, navy, 5)
    for i, color in enumerate([red, yellow, green]):
        x = 1110
        y = 1190 + i * 46
        mark_ellipse((x - 18, y - 18, x + 18, y + 18))
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=color, outline=navy, width=3)
    rect((1322, 1246, 1486, 1410), 22, (127, 205, 235, 242), navy, 5)
    for x in (1372, 1436):
        for y in (1300, 1360):
            mark_ellipse((x - 15, y - 15, x + 15, y + 15))
            draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=glow, outline=navy, width=3)

    # Pipe runs are deliberately routed through available lanes and around the
    # diagonal/circular/slot clearances.
    pipe([(352, 590), (350, 720), (310, 790), (310, 830)], red, 15)
    pipe([(408, 590), (408, 708), (380, 790), (380, 830)], yellow, 15)
    pipe([(466, 590), (466, 724), (438, 792), (438, 830)], green, 15)
    pipe([(555, 580), (570, 690), (545, 802), (520, 950), (520, 1118)], cyan, 22, collar_every=2)
    pipe([(398, 1302), (398, 1390), (500, 1480), (606, 1420), (610, 1300)], cyan, 21, collar_every=2)
    pipe([(492, 1300), (565, 1370), (640, 1378), (684, 1290)], red, 15)
    pipe([(1020, 1010), (1038, 1092), (1048, 1138)], cyan, 19)
    pipe([(1246, 1325), (1300, 1390), (1360, 1418), (1410, 1408)], red, 14)
    pipe([(1450, 1246), (1450, 1170), (1378, 1110), (1298, 1062)], yellow, 14)

    # Small edge brackets and sparkle details fill odd contour pockets without
    # pretending to be clipped fragments.
    for box in [(160, 720, 238, 760), (592, 650, 662, 684), (642, 1260, 702, 1294), (1192, 1422, 1270, 1456)]:
        rect(box, 8, (202, 217, 225, 240), navy, 3)
    for _ in range(44):
        x = rng.choice([rng.randint(160, 640), rng.randint(960, 1490)])
        y = rng.randint(220, 1450)
        if 760 < x < 905 and 1000 < y < 1530:
            continue
        r = rng.randint(2, 5)
        fill = rng.choice([(255, 255, 255, 95), (255, 211, 65, 140), (135, 240, 255, 105)])
        mark_ellipse((x - r, y - r, x + r, y + r))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def nonwhite_pixels(image: Image.Image, mask: Image.Image) -> int:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    masked = np.asarray(mask) > 0
    nonwhite = ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > 30
    return int((nonwhite & masked).sum())


def main() -> int:
    rng = random.Random(SEED)
    GENERATED.mkdir(parents=True, exist_ok=True)
    REVIEWS.mkdir(parents=True, exist_ok=True)

    paths = load_paths()
    # In path-only order these are source SVG lines 55 and 57:
    # top-left yellow outer contour and diagonal internal clearance.
    top_left_outer = paths[6].data
    diagonal_cutout = paths[7].data
    circle_cutout_center = (1486.61, 1268.34)
    circle_cutout_radius = 76.0
    red_slot = (770.16, 1054.46, 108.51, 240.12)
    stabilizer_slot = (752.0, 1050.0, 146.0, 502.0)

    size = (CROP[2] - CROP[0], CROP[3] - CROP[1])
    outer = draw_path_mask(top_left_outer, size)
    cutouts = composite_mask(
        draw_path_mask(diagonal_cutout, size),
        ellipse_mask(size, *circle_cutout_center, circle_cutout_radius),
        rect_mask(size, red_slot, radius=12),
        rect_mask(size, stabilizer_slot, radius=12),
    ).filter(ImageFilter.MaxFilter(9))
    hard_outer = outer.point(lambda p: 255 if p > 0 else 0)
    hard_cutouts = cutouts.point(lambda p: 255 if p > 0 else 0)
    paintable = ImageChops.subtract(hard_outer, hard_cutouts)

    art = Image.new("RGBA", size, (255, 255, 255, 255))
    texture = watercolor_texture(size, (54, 126, 198), rng)
    fill_masked(art, texture, paintable)

    element_layer = Image.new("L", size, 0)
    add_contour_built_art(art, element_layer, top_left_outer, rng)

    # Clip everything to the outer area and erase internal cutouts to quiet white.
    transparent = Image.new("RGBA", size, (255, 255, 255, 255))
    art = Image.composite(art, transparent, hard_outer)
    white = Image.new("RGBA", size, (255, 255, 255, 255))
    art = Image.composite(white, art, hard_cutouts)
    element_layer = ImageChops.multiply(element_layer, paintable.point(lambda p: 255 if p > 0 else 0))

    # Add a watercolor blue rim after clipping, then erase cutouts again.
    rim = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_polyline(rim, top_left_outer, (21, 77, 150, 210), 12)
    draw_polyline(rim, top_left_outer, (255, 255, 255, 85), 4)
    art.alpha_composite(rim)
    art = Image.composite(art, transparent, hard_outer)
    art = Image.composite(white, art, hard_cutouts)

    overlay = art.copy()
    overlay_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_polyline(overlay_layer, top_left_outer, (255, 219, 85, 235), 8, dash=24)
    draw_polyline(overlay_layer, diagonal_cutout, (255, 219, 85, 235), 8, dash=24)
    draw = ImageDraw.Draw(overlay_layer, "RGBA")
    cx, cy = circle_cutout_center
    x0, y0, _, _ = CROP
    draw.ellipse(
        (cx - circle_cutout_radius - x0, cy - circle_cutout_radius - y0, cx + circle_cutout_radius - x0, cy + circle_cutout_radius - y0),
        outline=(255, 219, 85, 235),
        width=8,
    )
    rx, ry, rw, rh = red_slot
    draw.rounded_rectangle((rx - x0, ry - y0, rx + rw - x0, ry + rh - y0), radius=12, outline=(237, 28, 36, 230), width=7)
    overlay.alpha_composite(overlay_layer)

    mask_debug = Image.new("RGBA", size, (255, 255, 255, 255))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (88, 169, 226, 170)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_outer))
    mask_debug.alpha_composite(Image.composite(Image.new("RGBA", size, (237, 28, 36, 180)), Image.new("RGBA", size, (0, 0, 0, 0)), hard_cutouts))
    mask_debug.alpha_composite(overlay_layer)

    art_path = GENERATED / "area-01-top-left-contour-designed-artwork.png"
    overlay_path = REVIEWS / "area-01-top-left-contour-designed-template-overlay.png"
    mask_path = REVIEWS / "area-01-top-left-contour-designed-mask-debug.png"
    metadata_path = REVIEWS / "area-01-top-left-contour-designed-metadata.json"
    art.convert("RGB").save(art_path)
    overlay.convert("RGB").save(overlay_path)
    mask_debug.convert("RGB").save(mask_path)

    metrics = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "area": "01 top-left",
        "source_svg": str(SVG.relative_to(TASK.parent.parent)),
        "style_refs": [
            "refs/control-panel-sliders.png",
            "refs/space-planets.png",
            "refs/lever-module.png",
            "refs/dial-toggle-panel.png",
            "refs/radar-screen.png",
        ],
        "crop_svg_units": list(CROP),
        "cutout_zones": {
            "diagonal_yellow_path": "source SVG line 57",
            "circle_yellow_path": {"center": list(circle_cutout_center), "radius_used": circle_cutout_radius},
            "red_slot": list(red_slot),
            "stabilizer_slot_conservative": list(stabilizer_slot),
        },
        "nonwhite_pixels_in_cutout_mask": nonwhite_pixels(art, hard_cutouts),
        "nonwhite_pixels_outside_outer_mask": nonwhite_pixels(art, hard_outer.point(lambda p: 0 if p else 255)),
        "decorative_element_pixels_in_cutout_mask": int(((np.asarray(element_layer) > 0) & (np.asarray(hard_cutouts) > 0)).sum()),
        "artwork": str(art_path.relative_to(TASK)),
        "overlay": str(overlay_path.relative_to(TASK)),
        "mask_debug": str(mask_path.relative_to(TASK)),
    }
    metadata_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
