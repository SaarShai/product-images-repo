#!/usr/bin/env python3
"""Create the first two space SVG checkpoint illustrations.

This is a geometry-native checkpoint generator. It classifies large SVG
contours as paintable regions, smaller contained contours as cutouts, and then
draws a watercolor-style control-panel illustration inside the allowed mask.
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/space-svg-exports-batch"
sys.path.insert(0, str(ROOT / "scripts"))

import export_svg_template_fit as fit_export  # noqa: E402
from export_svg_template_fit import sha256  # noqa: E402


Color = tuple[int, int, int, int]
Point = tuple[float, float]


COMMAND_RE = re.compile(r"[MmLlHhVvCcSsZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def read_number(tokens: list[str], index: int) -> tuple[float, int]:
    if index >= len(tokens) or is_command(tokens[index]):
        raise ValueError("Expected numeric SVG path token")
    return float(tokens[index]), index + 1


def read_pair(tokens: list[str], index: int) -> tuple[Point, int]:
    x, index = read_number(tokens, index)
    y, index = read_number(tokens, index)
    return (x, y), index


def apply_relative(point: Point, current: Point, relative: bool) -> Point:
    return (current[0] + point[0], current[1] + point[1]) if relative else point


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    return (
        (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0]),
        (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1]),
    )


def parse_path_d_with_smooth_curves(data: str, curve_steps: int = 28) -> list[list[Point]]:
    tokens = COMMAND_RE.findall(data.replace(",", " "))
    index = 0
    command: str | None = None
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    previous_cubic_control: Point | None = None
    current_poly: list[Point] = []
    subpaths: list[list[Point]] = []

    def finish_poly() -> None:
        nonlocal current_poly
        if len(current_poly) >= 3:
            subpaths.append(current_poly)
        current_poly = []

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if command is None:
            raise ValueError(f"SVG path starts without a command: {data[:40]}")

        relative = command.islower()
        upper = command.upper()

        if upper == "M":
            point, index = read_pair(tokens, index)
            current = apply_relative(point, current, relative)
            finish_poly()
            current_poly = [current]
            start = current
            previous_cubic_control = None
            implicit = "l" if relative else "L"
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
            command = implicit
        elif upper == "L":
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
            previous_cubic_control = None
        elif upper == "H":
            while index < len(tokens) and not is_command(tokens[index]):
                x, index = read_number(tokens, index)
                current = (current[0] + x, current[1]) if relative else (x, current[1])
                current_poly.append(current)
            previous_cubic_control = None
        elif upper == "V":
            while index < len(tokens) and not is_command(tokens[index]):
                y, index = read_number(tokens, index)
                current = (current[0], current[1] + y) if relative else (current[0], y)
                current_poly.append(current)
            previous_cubic_control = None
        elif upper == "C":
            while index < len(tokens) and not is_command(tokens[index]):
                control_1, index = read_pair(tokens, index)
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                p0 = current
                p1 = apply_relative(control_1, current, relative)
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    current_poly.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                previous_cubic_control = p2
        elif upper == "S":
            while index < len(tokens) and not is_command(tokens[index]):
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                p0 = current
                if previous_cubic_control is None:
                    p1 = current
                else:
                    p1 = ((2 * current[0]) - previous_cubic_control[0], (2 * current[1]) - previous_cubic_control[1])
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    current_poly.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                previous_cubic_control = p2
        elif upper == "Z":
            if current_poly and current_poly[-1] != start:
                current_poly.append(start)
            current = start
            finish_poly()
            previous_cubic_control = None
            command = None
        else:
            raise ValueError(f"Unsupported SVG path command {command!r}")

    finish_poly()
    return subpaths


fit_export.parse_path_d = parse_path_d_with_smooth_curves


@dataclass
class ShapeRecord:
    source_type: str
    index: int
    polygon: Polygon
    area: float
    bounds: tuple[float, float, float, float]
    role: str = "unknown"


PALETTE = {
    "rim": (13, 66, 132, 255),
    "rim_dark": (6, 42, 96, 255),
    "rim_soft": (13, 66, 132, 86),
    "blue": (103, 162, 224, 255),
    "blue_light": (156, 202, 239, 255),
    "blue_wash": (88, 146, 211, 255),
    "screen": (164, 224, 225, 255),
    "screen_dark": (24, 87, 130, 255),
    "cream": (226, 240, 247, 255),
    "red": (237, 82, 77, 255),
    "red_light": (255, 154, 145, 255),
    "yellow": (246, 178, 50, 255),
    "yellow_light": (255, 218, 112, 255),
    "mint": (91, 197, 176, 255),
    "mint_light": (169, 234, 219, 255),
}


def svg_path(name: str) -> Path:
    return TASK / "source" / name


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def parse_points(value: str) -> list[Point]:
    numbers = [float(item) for item in NUMBER_RE.findall(value)]
    if len(numbers) % 2:
        raise ValueError(f"Odd number of SVG point coordinates: {value}")
    return list(zip(numbers[0::2], numbers[1::2]))


def read_svg_polylines(svg: Path) -> list[list[Point]]:
    root = ET.parse(svg).getroot()
    return [
        parse_points(element.attrib["points"])
        for element in root.iter()
        if tag_name(element) == "polyline" and element.attrib.get("points")
    ]


def close_open_path_with_polyline(points: list[Point], polylines: list[list[Point]]) -> list[Point]:
    """Use separate SVG polyline closure segments before falling back to diagonal closure.

    Some Screenery exports split a paintable contour between an open path and a
    polyline. If the polyline is ignored, Shapely closes the open path with a
    diagonal and removes legitimate bottom/right panel area.
    """
    if len(points) < 3 or points[0] == points[-1]:
        return points
    start = points[0]
    end = points[-1]
    for polyline in polylines:
        if len(polyline) < 2:
            continue
        # Match the common export pattern: path ends on a vertical side, while
        # a polyline supplies the bottom edge and lower part of that side.
        candidates = [polyline, list(reversed(polyline))]
        for candidate in candidates:
            first = candidate[0]
            last = candidate[-1]
            start_near_first = math.hypot(start[0] - first[0], start[1] - first[1]) < 8
            start_near_last = math.hypot(start[0] - last[0], start[1] - last[1]) < 8
            end_aligned = abs(end[0] - last[0]) < 8 or abs(end[0] - first[0]) < 8
            if start_near_first and end_aligned:
                return points + list(reversed(candidate))
            if start_near_last and end_aligned:
                return points + candidate
    return points


def poly_from_points(points: list[Point]) -> Polygon | None:
    pts = points[:]
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    polygon = Polygon(pts)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty or polygon.area <= 1:
        return None
    if isinstance(polygon, MultiPolygon):
        polygon = max(polygon.geoms, key=lambda part: part.area)
    return polygon


def classify_svg(svg: Path) -> tuple[object, list[ShapeRecord], object, object]:
    geometry = fit_export.read_template(svg)
    polylines = read_svg_polylines(svg)
    records: list[ShapeRecord] = []
    for idx, points in enumerate(geometry.paths):
        points = close_open_path_with_polyline(points, polylines)
        polygon = poly_from_points(points)
        if polygon is None:
            continue
        records.append(ShapeRecord("path", idx, polygon, float(polygon.area), polygon.bounds))
    for idx, points in enumerate(geometry.polygons):
        polygon = poly_from_points(points)
        if polygon is None:
            continue
        records.append(ShapeRecord("polygon", idx, polygon, float(polygon.area), polygon.bounds))

    if not records:
        raise ValueError(f"No usable contours in {svg}")

    max_area = max(record.area for record in records)
    for record in records:
        contained_by = [
            other
            for other in records
            if other is not record
            and other.area > record.area * 1.8
            and other.polygon.buffer(0.05).contains(record.polygon.representative_point())
        ]
        bitten_by = [
            other
            for other in records
            if other is not record
            and record.area < max_area * 0.25
            and other.area > record.area * 1.8
            and (record.polygon.intersection(other.polygon).area / max(1.0, record.area)) > 0.10
        ]
        if contained_by:
            record.role = "cutout"
        elif bitten_by:
            record.role = "cutout"
        elif record.area >= max_area * 0.10:
            record.role = "paintable"
        else:
            record.role = "cutout"

    paintable = [record.polygon for record in records if record.role == "paintable"]
    cutouts = [record.polygon for record in records if record.role == "cutout"]
    allowed = unary_union(paintable)
    holes = unary_union(cutouts) if cutouts else Polygon()
    allowed = allowed.difference(holes)
    return geometry, records, allowed, holes


def image_size(viewbox: tuple[float, float, float, float], target_width: int) -> tuple[int, int]:
    _, _, box_w, box_h = viewbox
    return target_width, max(1, round(target_width * box_h / box_w))


def tx(point: Point, viewbox: tuple[float, float, float, float], size: tuple[int, int], aa: int = 1) -> tuple[int, int]:
    min_x, min_y, box_w, box_h = viewbox
    width, height = size
    return (
        round((point[0] - min_x) * width / box_w * aa),
        round((point[1] - min_y) * height / box_h * aa),
    )


def geom_parts(geom: object) -> list[Polygon]:
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if getattr(geom, "geoms", None):
        return [part for part in geom.geoms if isinstance(part, Polygon)]
    return []


def draw_geom_mask(
    geom: object,
    viewbox: tuple[float, float, float, float],
    size: tuple[int, int],
    aa: int = 4,
) -> Image.Image:
    width, height = size
    mask = Image.new("L", (width * aa, height * aa), 0)
    draw = ImageDraw.Draw(mask)
    for part in geom_parts(geom):
        exterior = [tx(point, viewbox, size, aa) for point in part.exterior.coords]
        draw.polygon(exterior, fill=255)
        for interior in part.interiors:
            draw.polygon([tx(point, viewbox, size, aa) for point in interior.coords], fill=0)
    return mask.resize(size, Image.Resampling.LANCZOS)


def draw_records_lines(
    image: Image.Image,
    records: list[ShapeRecord],
    viewbox: tuple[float, float, float, float],
    size: tuple[int, int],
    width: int,
    fill: Color,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for record in records:
        coords = [tx(point, viewbox, size) for point in record.polygon.exterior.coords]
        if len(coords) > 1:
            draw.line(coords, fill=fill, width=width, joint="curve")


def watercolor_body(mask: Image.Image, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    width, height = mask.size
    base = np.zeros((height, width, 4), dtype=np.uint8)
    base[:, :, 0] = 105
    base[:, :, 1] = 164
    base[:, :, 2] = 224
    base[:, :, 3] = 255

    coarse = rng.normal(0, 22, (max(8, height // 12), max(8, width // 12))).astype(np.float32)
    noise = Image.fromarray(np.clip(coarse + 128, 0, 255).astype(np.uint8), "L")
    noise = noise.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1.8))
    noise_np = np.asarray(noise).astype(np.int16) - 128
    base[:, :, 0] = np.clip(base[:, :, 0].astype(np.int16) + noise_np * 0.55, 0, 255)
    base[:, :, 1] = np.clip(base[:, :, 1].astype(np.int16) + noise_np * 0.45, 0, 255)
    base[:, :, 2] = np.clip(base[:, :, 2].astype(np.int16) + noise_np * 0.25, 0, 255)

    body = Image.fromarray(base, "RGBA")
    washes = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(washes, "RGBA")
    random.seed(seed)
    for _ in range(46):
        x = random.randint(-width // 6, width)
        y = random.randint(-height // 6, height)
        rx = random.randint(max(24, width // 12), max(40, width // 3))
        ry = random.randint(max(24, height // 16), max(40, height // 5))
        color = random.choice(
            [
                (54, 126, 204, 18),
                (169, 211, 241, 28),
                (42, 99, 178, 14),
                (230, 243, 251, 22),
            ]
        )
        draw.ellipse((x, y, x + rx, y + ry), fill=color)
    washes = washes.filter(ImageFilter.GaussianBlur(14))
    body.alpha_composite(washes)
    return Image.composite(body, Image.new("RGBA", (width, height), (255, 255, 255, 255)), mask)


def add_beveled_edges(
    image: Image.Image,
    allowed_mask: Image.Image,
    hole_mask: Image.Image,
    records: list[ShapeRecord],
    viewbox: tuple[float, float, float, float],
    size: tuple[int, int],
) -> None:
    safe_erode = allowed_mask.filter(ImageFilter.MinFilter(27))
    edge_band = ImageChops.subtract(allowed_mask, safe_erode).filter(ImageFilter.GaussianBlur(1.1))
    dark = Image.new("RGBA", size, (5, 47, 110, 82))
    image.alpha_composite(Image.composite(dark, Image.new("RGBA", size, (255, 255, 255, 0)), edge_band))

    hole_edge = hole_mask.filter(ImageFilter.GaussianBlur(1.4))
    image.alpha_composite(Image.composite(Image.new("RGBA", size, (8, 53, 120, 70)), Image.new("RGBA", size, (0, 0, 0, 0)), hole_edge))

    draw_records_lines(image, records, viewbox, size, 13, (9, 61, 132, 150))
    draw_records_lines(image, records, viewbox, size, 5, PALETTE["rim"])
    highlight = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(highlight, "RGBA")
    for record in records:
        x0, y0, x1, y1 = [int(v) for v in record.bounds]
        p0 = tx((x0 + 28, y0 + 36), viewbox, size)
        p1 = tx((x0 + (x1 - x0) * 0.44, y0 + 24), viewbox, size)
        draw.line((p0, p1), fill=(245, 252, 255, 130), width=4)
    highlight = Image.composite(highlight, Image.new("RGBA", size, (0, 0, 0, 0)), allowed_mask)
    image.alpha_composite(highlight)


def safe_region(mask: Image.Image, margin: int) -> Image.Image:
    size = max(3, margin * 2 + 1)
    if size % 2 == 0:
        size += 1
    return mask.filter(ImageFilter.MinFilter(size))


def fits(mask_np: np.ndarray, box: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 >= mask_np.shape[1] or y1 >= mask_np.shape[0]:
        return False
    region = mask_np[y0:y1, x0:x1]
    return bool(region.size and region.min() > 0)


def shadowed_layer(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    layer = Image.new("RGBA", size, (255, 255, 255, 0))
    return layer, ImageDraw.Draw(layer, "RGBA")


def rounded_button(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: Color, light: Color, radius: int | None = None) -> None:
    x0, y0, x1, y1 = box
    r = radius or max(8, (y1 - y0) // 2)
    draw.rounded_rectangle((x0 + 5, y0 + 7, x1 + 5, y1 + 7), radius=r, fill=(3, 44, 105, 80))
    draw.rounded_rectangle((x0 - 4, y0 - 4, x1 + 4, y1 + 4), radius=r + 5, fill=PALETTE["rim_dark"])
    draw.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=fill, outline=PALETTE["rim"], width=2)
    draw.rounded_rectangle((x0 + 8, y0 + 6, x1 - 8, y0 + max(10, (y1 - y0) // 2)), radius=max(4, r - 4), fill=light)
    draw.arc((x0 + 7, y0 + 5, x0 + 46, y0 + 34), 190, 265, fill=(255, 255, 255, 150), width=3)


def draw_screen(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], seed: int) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 7, y0 + 8, x1 + 7, y1 + 8), radius=12, fill=(3, 44, 105, 82))
    draw.rounded_rectangle((x0 - 5, y0 - 5, x1 + 5, y1 + 5), radius=15, fill=PALETTE["rim_dark"])
    draw.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=PALETTE["screen"], outline=PALETTE["rim"], width=3)
    draw.rounded_rectangle((x0 + 10, y0 + 9, x1 - 10, y1 - 9), radius=7, fill=(174, 229, 229, 255), outline=(35, 115, 155, 150), width=2)
    for i in range(1, 4):
        gx = x0 + 10 + i * (x1 - x0 - 20) // 4
        draw.line((gx, y0 + 13, gx, y1 - 13), fill=(53, 137, 167, 75), width=1)
    for i in range(1, 3):
        gy = y0 + 10 + i * (y1 - y0 - 20) // 3
        draw.line((x0 + 14, gy, x1 - 14, gy), fill=(53, 137, 167, 70), width=1)
    random.seed(seed)
    for _ in range(5):
        cx = random.randint(x0 + 20, x1 - 20)
        cy = random.randint(y0 + 18, y1 - 18)
        color = random.choice([PALETTE["red"], PALETTE["yellow"], PALETTE["mint"], PALETTE["cream"]])
        draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=color, outline=PALETTE["rim"], width=1)
    draw.arc((x0 + 14, y0 + 10, x0 + 62, y0 + 40), 185, 255, fill=(255, 255, 255, 150), width=3)


def draw_dial(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, angle: float = -0.78) -> None:
    cx, cy = center
    draw.ellipse((cx - radius + 7, cy - radius + 9, cx + radius + 7, cy + radius + 9), fill=(3, 44, 105, 82))
    draw.ellipse((cx - radius - 7, cy - radius - 7, cx + radius + 7, cy + radius + 7), fill=PALETTE["rim_dark"])
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(205, 231, 245, 255), outline=PALETTE["rim"], width=4)
    draw.ellipse((cx - radius + 13, cy - radius + 13, cx + radius - 13, cy + radius - 13), outline=(54, 113, 173, 180), width=3)
    for i in range(9):
        a = -math.pi * 0.9 + i * math.pi * 1.8 / 8
        r0 = radius - 17
        r1 = radius - 7
        p0 = (cx + int(math.cos(a) * r0), cy + int(math.sin(a) * r0))
        p1 = (cx + int(math.cos(a) * r1), cy + int(math.sin(a) * r1))
        draw.line((p0, p1), fill=PALETTE["rim"], width=3)
    needle = (cx + int(math.cos(angle) * (radius - 24)), cy + int(math.sin(angle) * (radius - 24)))
    draw.line((cx, cy, needle[0], needle[1]), fill=PALETTE["rim_dark"], width=6)
    draw.line((cx, cy, needle[0], needle[1]), fill=(60, 128, 200, 255), width=3)
    draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=PALETTE["cream"], outline=PALETTE["rim"], width=2)
    draw.arc((cx - radius + 15, cy - radius + 10, cx - radius + 74, cy - radius + 54), 190, 260, fill=(255, 255, 255, 160), width=5)


def draw_toggle(draw: ImageDraw.ImageDraw, base: tuple[int, int], scale: float, color: Color, light: Color) -> None:
    cx, cy = base
    r = round(25 * scale)
    h = round(75 * scale)
    w = round(24 * scale)
    draw.ellipse((cx - r + 5, cy - r + 10, cx + r + 5, cy + r + 10), fill=(3, 44, 105, 85))
    draw.ellipse((cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5), fill=PALETTE["rim_dark"])
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(31, 100, 176, 255), outline=PALETTE["rim"], width=3)
    draw.rounded_rectangle((cx - w, cy - h, cx + w, cy + 8), radius=w, fill=color, outline=PALETTE["rim"], width=2)
    draw.ellipse((cx - w, cy - h - 5, cx + w, cy - h + round(18 * scale)), fill=light)
    draw.line((cx - w // 2, cy - h + 10, cx - w // 2, cy - 8), fill=(255, 255, 255, 115), width=max(2, round(4 * scale)))


def draw_socket(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int) -> None:
    cx, cy = center
    draw.ellipse((cx - radius + 4, cy - radius + 7, cx + radius + 4, cy + radius + 7), fill=(3, 44, 105, 85))
    draw.ellipse((cx - radius - 4, cy - radius - 4, cx + radius + 4, cy + radius + 4), fill=PALETTE["rim_dark"])
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(207, 230, 244, 255), outline=PALETTE["rim"], width=3)
    draw.line((cx - radius // 2, cy + radius // 2, cx + radius // 2, cy - radius // 2), fill=(78, 137, 195, 180), width=max(3, radius // 5))
    draw.arc((cx - radius + 8, cy - radius + 8, cx + radius - 8, cy + radius - 8), 200, 250, fill=(255, 255, 255, 160), width=3)


def draw_slider(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], knobs: list[tuple[float, Color, Color]]) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) // 2, fill=PALETTE["rim_dark"])
    draw.rounded_rectangle((x0 + 7, y0 + 6, x1 - 7, y1 - 6), radius=max(2, (y1 - y0) // 4), fill=(121, 183, 231, 190))
    draw.line((x0 + 14, y0 + 8, x1 - 14, y0 + 8), fill=(224, 245, 255, 130), width=2)
    for fraction, color, light in knobs:
        cx = round(x0 + fraction * (x1 - x0))
        size = max(18, (y1 - y0) + 6)
        rounded_button(draw, (cx - size // 2, y0 - size // 4, cx + size // 2, y1 + size // 4), color, light, radius=6)


def draw_circuit(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], colors: list[Color]) -> None:
    for a, b in zip(points, points[1:]):
        draw.line((a, b), fill=PALETTE["rim_dark"], width=7)
        draw.line((a, b), fill=(150, 208, 239, 195), width=3)
    for idx, point in enumerate(points):
        color = colors[idx % len(colors)]
        cx, cy = point
        rounded_button(draw, (cx - 13, cy - 13, cx + 13, cy + 13), color, tuple(min(255, c + 50) for c in color[:3]) + (255,), radius=6)


def place_layer(canvas: Image.Image, layer: Image.Image, allowed_mask: Image.Image) -> None:
    clipped = Image.composite(layer, Image.new("RGBA", canvas.size, (0, 0, 0, 0)), allowed_mask)
    canvas.alpha_composite(clipped)


def vb_box(viewbox: tuple[float, float, float, float], size: tuple[int, int], box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x0, y0 = tx((box[0], box[1]), viewbox, size)
    x1, y1 = tx((box[2], box[3]), viewbox, size)
    return x0, y0, x1, y1


def draw_np01_back_top(canvas: Image.Image, allowed_mask: Image.Image, viewbox: tuple[float, float, float, float]) -> None:
    size = canvas.size
    safe = np.asarray(safe_region(allowed_mask, 24)) > 0
    layer, draw = shadowed_layer(size)
    placements: list[tuple[str, tuple[int, int, int, int]]] = [
        ("screen", vb_box(viewbox, size, (160, 730, 560, 990))),
        ("buttons", vb_box(viewbox, size, (145, 1090, 530, 1378))),
        ("dial", vb_box(viewbox, size, (560, 1115, 850, 1405))),
        ("circuit", vb_box(viewbox, size, (180, 520, 740, 650))),
        ("toggles", vb_box(viewbox, size, (600, 255, 910, 520))),
        ("sockets", vb_box(viewbox, size, (1435, 1230, 1580, 1455))),
    ]
    for kind, box in placements:
        if kind != "circuit" and not fits(safe, box):
            continue
        x0, y0, x1, y1 = box
        if kind == "screen":
            draw_screen(draw, box, 31)
        elif kind == "buttons":
            gap = max(8, (y1 - y0) // 12)
            h = (y1 - y0 - gap * 2) // 3
            for i, (fill, light) in enumerate([(PALETTE["red"], PALETTE["red_light"]), (PALETTE["yellow"], PALETTE["yellow_light"]), (PALETTE["mint"], PALETTE["mint_light"])]):
                yy = y0 + i * (h + gap)
                rounded_button(draw, (x0, yy, x1, yy + h), fill, light)
        elif kind == "dial":
            draw_dial(draw, ((x0 + x1) // 2, (y0 + y1) // 2), min(x1 - x0, y1 - y0) // 2)
        elif kind == "circuit":
            points = [
                tx((190, 590), viewbox, size),
                tx((335, 590), viewbox, size),
                tx((335, 545), viewbox, size),
                tx((510, 545), viewbox, size),
                tx((510, 620), viewbox, size),
                tx((720, 620), viewbox, size),
            ]
            draw_circuit(draw, points, [PALETTE["mint"], PALETTE["yellow"], PALETTE["red"]])
        elif kind == "toggles":
            for n, (color, light) in enumerate([(PALETTE["red"], PALETTE["red_light"]), (PALETTE["yellow"], PALETTE["yellow_light"]), (PALETTE["mint"], PALETTE["mint_light"])]):
                draw_toggle(draw, (x0 + (n + 1) * (x1 - x0) // 4, y1 - 15), 0.72, color, light)
        elif kind == "sockets":
            draw_socket(draw, (x0 + 50, y0 + 50), 25)
            draw_socket(draw, (x1 - 36, y1 - 40), 23)
    place_layer(canvas, layer, allowed_mask)


def draw_np01_front_bottom(canvas: Image.Image, allowed_mask: Image.Image, viewbox: tuple[float, float, float, float]) -> None:
    size = canvas.size
    safe = np.asarray(safe_region(allowed_mask, 22)) > 0
    layer, draw = shadowed_layer(size)
    checks = [
        ("left_screen", vb_box(viewbox, size, (76, 1715, 468, 2032))),
        ("left_buttons", vb_box(viewbox, size, (82, 2132, 470, 2442))),
        ("left_circuit", vb_box(viewbox, size, (58, 530, 218, 1010))),
        ("left_slider", vb_box(viewbox, size, (415, 620, 690, 670))),
        ("right_bars", vb_box(viewbox, size, (935, 258, 1155, 570))),
        ("right_sockets", vb_box(viewbox, size, (1460, 250, 1570, 1180))),
        ("right_lower_left", vb_box(viewbox, size, (940, 1650, 1190, 2300))),
        ("right_lower_right", vb_box(viewbox, size, (1415, 1660, 1582, 2310))),
        ("center_dial", vb_box(viewbox, size, (468, 900, 720, 1152))),
    ]
    for kind, box in checks:
        if kind not in {"left_circuit", "right_sockets"} and not fits(safe, box):
            continue
        x0, y0, x1, y1 = box
        if kind in {"left_screen", "right_screen"}:
            draw_screen(draw, box, 72 if kind.startswith("left") else 73)
        elif kind in {"left_buttons", "right_buttons"}:
            gap = max(10, (y1 - y0) // 13)
            h = (y1 - y0 - gap * 2) // 3
            scheme = [(PALETTE["red"], PALETTE["red_light"]), (PALETTE["mint"], PALETTE["mint_light"]), (PALETTE["yellow"], PALETTE["yellow_light"])]
            if kind == "left_buttons":
                scheme = [(PALETTE["yellow"], PALETTE["yellow_light"]), (PALETTE["red"], PALETTE["red_light"]), (PALETTE["mint"], PALETTE["mint_light"])]
            for i, (fill, light) in enumerate(scheme):
                yy = y0 + i * (h + gap)
                rounded_button(draw, (x0, yy, x1, yy + h), fill, light)
        elif kind == "left_circuit":
            points = [
                tx((85, 930), viewbox, size),
                tx((170, 930), viewbox, size),
                tx((170, 820), viewbox, size),
                tx((92, 820), viewbox, size),
                tx((92, 690), viewbox, size),
                tx((188, 690), viewbox, size),
            ]
            draw_circuit(draw, points, [PALETTE["red"], PALETTE["mint"], PALETTE["yellow"]])
        elif kind == "left_slider":
            draw_slider(draw, box, [(0.30, PALETTE["mint"], PALETTE["mint_light"]), (0.77, PALETTE["yellow"], PALETTE["yellow_light"])])
        elif kind == "right_bars":
            gap = max(8, (y1 - y0) // 14)
            h = (y1 - y0 - gap * 3) // 4
            for i, (fill, light) in enumerate([(PALETTE["yellow"], PALETTE["yellow_light"]), (PALETTE["red"], PALETTE["red_light"]), (PALETTE["mint"], PALETTE["mint_light"]), (PALETTE["red"], PALETTE["red_light"])]):
                yy = y0 + i * (h + gap)
                rounded_button(draw, (x0, yy, x1, yy + h), fill, light, radius=10)
        elif kind == "right_switches":
            for n, (color, light) in enumerate([(PALETTE["red"], PALETTE["red_light"]), (PALETTE["yellow"], PALETTE["yellow_light"]), (PALETTE["mint"], PALETTE["mint_light"])]):
                draw_toggle(draw, (x0 + (n + 1) * (x1 - x0) // 4, y1 - 15), 0.78, color, light)
            for n in range(3):
                draw_socket(draw, (x0 + 72 + n * 150, y0 + 65), 25)
        elif kind == "right_sockets":
            for n, y in enumerate([y0 + 40, (y0 + y1) // 2, y1 - 45]):
                draw_socket(draw, (x0 + 42 + (n % 2) * 24, y), 24)
        elif kind == "right_lower_left":
            draw_slider(draw, (x0, y0, x1, y0 + 44), [(0.42, PALETTE["mint"], PALETTE["mint_light"])])
            draw_slider(draw, (x0 + 20, y0 + 120, x1 - 10, y0 + 164), [(0.68, PALETTE["yellow"], PALETTE["yellow_light"])])
            rounded_button(draw, (x0 + 24, y0 + 255, x1 - 36, y0 + 318), PALETTE["red"], PALETTE["red_light"], radius=12)
        elif kind == "right_lower_right":
            draw_screen(draw, (x0, y0, x1, y0 + 175), 74)
            rounded_button(draw, (x0 + 5, y0 + 235, x1 - 4, y0 + 295), PALETTE["mint"], PALETTE["mint_light"], radius=10)
        elif kind == "center_dial":
            draw_dial(draw, ((x0 + x1) // 2, (y0 + y1) // 2), min(x1 - x0, y1 - y0) // 2, angle=-1.15)

    place_layer(canvas, layer, allowed_mask)


def make_debug(art: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image, line_image: Image.Image) -> Image.Image:
    debug = art.convert("RGBA")
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 254
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[allowed] = (0, 160, 255, 22)
    tint[holes] = (255, 0, 150, 95)
    debug.alpha_composite(Image.fromarray(tint, "RGBA"))
    debug.alpha_composite(line_image)
    return debug.convert("RGB")


def metrics(art: Image.Image, allowed_mask: Image.Image, hole_mask: Image.Image) -> dict[str, object]:
    rgb = np.asarray(art.convert("RGB")).astype(np.int16)
    painted = ((255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])) > 24
    allowed = np.asarray(allowed_mask) > 0
    holes = np.asarray(hole_mask) > 0
    outside = int((painted & ~allowed & ~holes).sum())
    in_holes = int((painted & holes).sum())
    coverage = round(100 * int((painted & allowed).sum()) / max(1, int(allowed.sum())), 2)
    return {
        "verdict": "PASS" if outside == 0 and in_holes == 0 and coverage > 35 else "REVIEW",
        "outside_nonwhite_pixels": outside,
        "cutout_nonwhite_pixels": in_holes,
        "paintable_coverage_pct": coverage,
    }


def create_candidate(svg_name: str, target_width: int, seed: int) -> dict[str, object]:
    svg = svg_path(svg_name)
    geometry, records, allowed_geom, hole_geom = classify_svg(svg)
    size = image_size(geometry.viewbox, target_width)
    allowed_mask = draw_geom_mask(allowed_geom, geometry.viewbox, size)
    hole_mask = draw_geom_mask(hole_geom, geometry.viewbox, size)

    art = watercolor_body(allowed_mask, seed)
    add_beveled_edges(art, allowed_mask, hole_mask, records, geometry.viewbox, size)
    if svg_name == "np01-front-bottom.svg":
        draw_np01_front_bottom(art, allowed_mask, geometry.viewbox)
    else:
        draw_np01_back_top(art, allowed_mask, geometry.viewbox)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    allowed_binary = allowed_mask.point(lambda value: 255 if value > 0 else 0)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    art = Image.composite(art, white, allowed_binary)
    art = Image.composite(white, art, hole_binary)

    lines = Image.new("RGBA", size, (255, 255, 255, 0))
    draw_records_lines(lines, records, geometry.viewbox, size, 4, (0, 0, 0, 255))
    clean = art.copy()
    clean.alpha_composite(lines)
    debug = make_debug(art, allowed_mask, hole_mask, lines)

    stem = svg.stem
    prefix = f"{stem}-checkpoint-v1"
    generated = TASK / "outputs/generated" / f"{prefix}.png"
    final_art = TASK / "outputs/final" / f"{prefix}-artwork-only.png"
    clean_path = TASK / "outputs/final" / f"{prefix}-clean-black-lines.png"
    debug_path = TASK / "outputs/reviews" / f"{prefix}-debug-mask.png"
    meta_path = TASK / "outputs/reviews" / f"{prefix}-metadata.json"
    for path in [generated, final_art, clean_path, debug_path, meta_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
    art.convert("RGB").save(generated)
    art.convert("RGB").save(final_art)
    clean.convert("RGB").save(clean_path)
    debug.save(debug_path)

    metadata = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "svg": str(svg.relative_to(ROOT)),
        "svg_sha256": sha256(svg),
        "candidate": str(generated.relative_to(ROOT)),
        "artwork_only": str(final_art.relative_to(ROOT)),
        "clean_black_lines": str(clean_path.relative_to(ROOT)),
        "debug_mask": str(debug_path.relative_to(ROOT)),
        "style_packet": str((TASK / "style-packet/style-packet.json").relative_to(ROOT)),
        "source_style_refs": [
            str(path.relative_to(ROOT))
            for path in sorted((TASK / "refs").glob("*.png"))
        ],
        "viewbox": list(geometry.viewbox),
        "output_dimensions": f"{size[0]}x{size[1]}",
        "contours": [
            {
                "source_type": record.source_type,
                "index": record.index,
                "role": record.role,
                "area": round(record.area, 2),
                "bounds": [round(value, 2) for value in record.bounds],
            }
            for record in records
        ],
        "metrics": metrics(art, allowed_mask, hole_mask),
        "method_note": "Checkpoint-only geometry-native watercolor rendering; image-generation model pass should follow after approval if user wants richer synthesis.",
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata"] = str(meta_path.relative_to(ROOT))
    return metadata


def make_contact_sheet(metadata: list[dict[str, object]]) -> Path:
    images = [Image.open(ROOT / str(item["artwork_only"])).convert("RGB") for item in metadata]
    thumbs = []
    for image in images:
        max_h = 860
        scale = min(1.0, max_h / image.height)
        thumbs.append(image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS))
    pad = 36
    label_h = 42
    width = sum(image.width for image in thumbs) + pad * (len(thumbs) + 1)
    height = max(image.height for image in thumbs) + pad * 2 + label_h
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    x = pad
    for image, item in zip(thumbs, metadata):
        sheet.paste(image, (x, pad + label_h))
        draw.text((x, pad), Path(str(item["svg"])).name, fill=(10, 45, 85))
        x += image.width + pad
    path = TASK / "checkpoints/checkpoint-01-two-illustrations.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def main() -> int:
    candidates = [
        create_candidate("np01-back-top.svg", target_width=1120, seed=6101),
        create_candidate("np01-front-bottom.svg", target_width=920, seed=6102),
    ]
    sheet = make_contact_sheet(candidates)
    summary = {
        "checkpoint": str(sheet.relative_to(ROOT)),
        "candidates": candidates,
    }
    summary_path = TASK / "checkpoints/checkpoint-01-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
