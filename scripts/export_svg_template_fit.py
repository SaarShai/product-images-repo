#!/usr/bin/env python3
"""Clip generated artwork into simple SVG template paths and verify fit.

This is intentionally small and dependency-light. It supports the path commands
used by the Screenery door SVGs seen in this repo: M/L/H/V/C/S/Z, absolute or
relative, plus polygon cutouts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
try:
    import shapely  # noqa: F401  (imported transitively via svg_classify; fail fast with a clear hint)
except ImportError:
    print("This script requires /usr/bin/python3 (PATH python3 lacks shapely). Re-run with /usr/bin/python3.", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify  # noqa: E402 — authoritative cutout-vs-paintable classifier, reused by read_template()


ROOT = Path(__file__).resolve().parents[1]
COMMAND_RE = re.compile(r"[MmLlHhVvCcSsZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
NUMBER_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


Point = tuple[float, float]


@dataclass
class TemplateGeometry:
    viewbox: tuple[float, float, float, float]
    paths: list[list[Point]]
    polygons: list[list[Point]]


@dataclass
class FitMetrics:
    verdict: str
    output_dimensions: str
    panel_coverage_pct: float
    outside_nonwhite_pixels: int
    center_gap_nonwhite_pixels: int
    hex_clear_nonwhite_pixels: int
    hex_clearance_px: int
    center_gap_bbox: list[int] | None
    path_bboxes: list[list[float]]
    polygon_bboxes: list[list[float]]
    notes: list[str]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


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


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    x = (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0])
    y = (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1])
    return (x, y)


def apply_relative(point: Point, current: Point, relative: bool) -> Point:
    if not relative:
        return point
    return (current[0] + point[0], current[1] + point[1])


def parse_path_d(data: str, curve_steps: int = 28) -> list[list[Point]]:
    tokens = COMMAND_RE.findall(data.replace(",", " "))
    index = 0
    command: str | None = None
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    current_poly: list[Point] = []
    subpaths: list[list[Point]] = []
    last_control: Point | None = None  # reflected control point, C/S chains only

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
            implicit = "l" if relative else "L"
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
            command = implicit
            last_control = None
        elif upper == "L":
            while index < len(tokens) and not is_command(tokens[index]):
                point, index = read_pair(tokens, index)
                current = apply_relative(point, current, relative)
                current_poly.append(current)
            last_control = None
        elif upper == "H":
            while index < len(tokens) and not is_command(tokens[index]):
                x, index = read_number(tokens, index)
                current = (current[0] + x, current[1]) if relative else (x, current[1])
                current_poly.append(current)
            last_control = None
        elif upper == "V":
            while index < len(tokens) and not is_command(tokens[index]):
                y, index = read_number(tokens, index)
                current = (current[0], current[1] + y) if relative else (current[0], y)
                current_poly.append(current)
            last_control = None
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
                last_control = p2
        elif upper == "S":
            # smooth cubic curveto: first control point is the reflection of
            # the previous C/S control point through the current point (or
            # the current point itself if the previous command wasn't C/S).
            while index < len(tokens) and not is_command(tokens[index]):
                control_2, index = read_pair(tokens, index)
                end, index = read_pair(tokens, index)
                p0 = current
                if last_control is not None:
                    p1 = (2 * p0[0] - last_control[0], 2 * p0[1] - last_control[1])
                else:
                    p1 = p0
                p2 = apply_relative(control_2, current, relative)
                p3 = apply_relative(end, current, relative)
                for step in range(1, curve_steps + 1):
                    current_poly.append(cubic_point(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_control = p2
        elif upper == "Z":
            if current_poly and current_poly[-1] != start:
                current_poly.append(start)
            current = start
            finish_poly()
            command = None
            last_control = None
        else:
            raise ValueError(f"Unsupported SVG path command {command!r}")

    finish_poly()
    return subpaths


def parse_points(value: str) -> list[Point]:
    numbers = [float(item) for item in NUMBER_RE.findall(value)]
    if len(numbers) % 2:
        raise ValueError(f"Odd number of polygon coordinates: {value}")
    return list(zip(numbers[0::2], numbers[1::2]))


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def read_template(svg_path: Path) -> TemplateGeometry:
    """Read panel (paintable) + cutout (hole) geometry from a template SVG.

    Classifies every shape (<path>, <polygon>, <rect>, ...) the same way
    scripts/svg_classify.py does for the template-manifest gate (contained-by
    or bitten-into a larger contour => internal_cutout hole; the largest
    contour and any other large standalone contour => paintable), instead of
    treating every <path>/<polygon> element as paintable. Reusing that
    classifier — rather than this file's older path/polygon-only,
    classification-blind reader — fixes two structural blind spots found on
    the princess narrow panel 02 template (geometry-evidentiary-princess-n02
    Finding B): (a) <rect> cutouts were ignored entirely, and (b) internal
    cutout <path> elements were unioned INTO the paintable panel mask instead
    of being excluded as holes.

    Transform note: svg_classify.extract_shapes applies each element's full
    CTM (ancestor <g transform="..."> chains) via svg_geometry.iter_with_ctm,
    so the returned coordinates — for <path>, <polygon>, AND <rect> alike —
    are already transform-correct. That is a strict improvement over this
    file's OTHER parser (parse_path_d(), still used directly by callers/tests
    below), which never applied transforms at all.

    <rect> caveat: svg_classify.classify() treats bare <rect> elements as
    annotation overlays (keep_clear_zone / no_focal_motif_zone), which is
    correct for the Screenery skyline/door templates it was built for, but
    wrong here — this template's <rect> elements ARE real die-cut cutouts
    (Finding B(a)). We relabel rect shapes to kind="polygon" before handing
    them to classify() so they go through the SAME contained-by/bitten-into
    contour-containment test a cutout <path>/<polygon> gets, rather than
    reimplementing that geometric test locally.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    viewbox_text = root.attrib.get("viewBox")
    if not viewbox_text:
        width = float(root.attrib["width"])
        height = float(root.attrib["height"])
        viewbox = (0.0, 0.0, width, height)
    else:
        parts = [float(item) for item in viewbox_text.replace(",", " ").split()]
        if len(parts) != 4:
            raise ValueError(f"Unexpected viewBox: {viewbox_text}")
        viewbox = tuple(parts)  # type: ignore[assignment]

    _, shapes = svg_classify.extract_shapes(svg_path)
    for shape in shapes:
        if shape.kind == "rect" and shape.polygon is not None:
            shape.kind = "polygon"
    shapes = svg_classify.classify(shapes)

    paths: list[list[Point]] = []
    polygons: list[list[Point]] = []
    for shape in shapes:
        if shape.polygon is None:
            continue  # lines/guides carry no fill area, not panel geometry
        points = list(shape.polygon.exterior.coords)
        if shape.role == "internal_cutout":
            polygons.append(points)
        elif shape.role in ("outer_contour", "paintable_region"):
            paths.append(points)

    if not paths:
        raise ValueError(f"No path panels found in {svg_path}")
    return TemplateGeometry(viewbox=viewbox, paths=paths, polygons=polygons)


def bbox(points: list[Point]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def transform_points(
    points: list[Point],
    viewbox: tuple[float, float, float, float],
    width: int,
    height: int,
    aa: int,
) -> list[tuple[int, int]]:
    min_x, min_y, box_w, box_h = viewbox
    scale_x = width / box_w
    scale_y = height / box_h
    return [
        (
            round((point[0] - min_x) * scale_x * aa),
            round((point[1] - min_y) * scale_y * aa),
        )
        for point in points
    ]


def clearance_px(viewbox: tuple[float, float, float, float], width: int, height: int, units: float, aa: int) -> int:
    _, _, box_w, box_h = viewbox
    px = units * ((width / box_w) + (height / box_h)) / 2.0
    return max(0, round(px * aa))


def resize_mask(mask: Image.Image, width: int, height: int) -> Image.Image:
    return mask.resize((width, height), Image.Resampling.LANCZOS)


def build_masks(
    geometry: TemplateGeometry,
    width: int,
    height: int,
    aa: int,
    hex_clearance_units: float,
) -> tuple[Image.Image, Image.Image, int]:
    panel_hr = Image.new("L", (width * aa, height * aa), 0)
    panel_draw = ImageDraw.Draw(panel_hr)
    for path in geometry.paths:
        panel_draw.polygon(transform_points(path, geometry.viewbox, width, height, aa), fill=255)

    hole_hr = Image.new("L", panel_hr.size, 0)
    hole_draw = ImageDraw.Draw(hole_hr)
    for polygon in geometry.polygons:
        hole_draw.polygon(transform_points(polygon, geometry.viewbox, width, height, aa), fill=255)

    clear_px = clearance_px(geometry.viewbox, width, height, hex_clearance_units, aa)
    if clear_px:
        size = max(3, (clear_px * 2) + 1)
        if size % 2 == 0:
            size += 1
        try:
            import cv2  # type: ignore[import-not-found]

            kernel = np.ones((size, size), dtype=np.uint8)
            hole_hr = Image.fromarray(cv2.dilate(np.asarray(hole_hr), kernel, iterations=1))
        except Exception:
            hole_hr = hole_hr.filter(ImageFilter.MaxFilter(size=size))

    artwork_hr = ImageChops.subtract(panel_hr, hole_hr)
    return resize_mask(artwork_hr, width, height), resize_mask(hole_hr, width, height), round(clear_px / aa)


def place_artwork(source: Image.Image, width: int, height: int, scale_x: float, scale_y: float, offset_x: int, offset_y: int) -> Image.Image:
    source = source.convert("RGBA")
    resized = source.resize(
        (round(width * scale_x), round(height * scale_y)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    left = (width - resized.width) // 2 + offset_x
    top = (height - resized.height) // 2 + offset_y
    canvas.alpha_composite(resized, (left, top))
    return canvas


def draw_template_lines(
    geometry: TemplateGeometry,
    width: int,
    height: int,
    aa: int,
    stroke_width_units: float,
) -> Image.Image:
    line_hr = Image.new("RGBA", (width * aa, height * aa), (255, 255, 255, 0))
    draw = ImageDraw.Draw(line_hr)
    _, _, box_w, box_h = geometry.viewbox
    stroke_px = max(1, round(stroke_width_units * ((width / box_w) + (height / box_h)) / 2.0 * aa))
    for path in geometry.paths:
        points = transform_points(path, geometry.viewbox, width, height, aa)
        draw.line(points, fill=(0, 0, 0, 255), width=stroke_px)
    for polygon in geometry.polygons:
        points = transform_points(polygon, geometry.viewbox, width, height, aa)
        draw.line(points + points[:1], fill=(0, 0, 0, 255), width=stroke_px)
    return line_hr.resize((width, height), Image.Resampling.LANCZOS)


def nonwhite_mask(image: Image.Image, threshold: int = 24) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    white_distance = (255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])
    return white_distance > threshold


def mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def viewbox_bbox_to_pixels(
    box: tuple[float, float, float, float],
    viewbox: tuple[float, float, float, float],
    width: int,
    height: int,
) -> list[int]:
    min_x, min_y, box_w, box_h = viewbox
    x0, y0, x1, y1 = box
    return [
        round((x0 - min_x) * width / box_w),
        round((y0 - min_y) * height / box_h),
        round((x1 - min_x) * width / box_w),
        round((y1 - min_y) * height / box_h),
    ]


def center_gap_bbox(geometry: TemplateGeometry, width: int, height: int) -> list[int] | None:
    path_boxes = sorted([bbox(path) for path in geometry.paths], key=lambda item: item[0])
    if len(path_boxes) < 2:
        return None
    left = path_boxes[0]
    right = path_boxes[-1]
    gap = (left[2], min(left[1], right[1]), right[0], max(left[3], right[3]))
    pixels = viewbox_bbox_to_pixels(gap, geometry.viewbox, width, height)
    if pixels[2] <= pixels[0]:
        return None
    return pixels


def build_debug(
    artwork: Image.Image,
    artwork_mask: Image.Image,
    hole_mask: Image.Image,
    lines: Image.Image,
    gap_bbox: list[int] | None,
) -> Image.Image:
    debug = artwork.convert("RGBA")
    mask_np = np.asarray(artwork_mask) > 3
    hole_np = np.asarray(hole_mask) > 3
    tint = np.zeros((debug.height, debug.width, 4), dtype=np.uint8)
    tint[mask_np] = (0, 180, 255, 24)
    tint[hole_np] = (255, 0, 160, 90)
    debug.alpha_composite(Image.fromarray(tint))
    draw = ImageDraw.Draw(debug)
    if gap_bbox:
        draw.rectangle(gap_bbox, outline=(0, 180, 0, 255), width=2)
    debug.alpha_composite(lines)
    return debug.convert("RGB")


def compute_metrics(
    artwork: Image.Image,
    artwork_mask: Image.Image,
    hole_mask: Image.Image,
    geometry: TemplateGeometry,
    clear_px: int,
) -> FitMetrics:
    painted = nonwhite_mask(artwork)
    allowed = np.asarray(artwork_mask) > 0
    hole_clear = np.asarray(hole_mask) > 0
    outside_nonwhite = int((painted & ~allowed & ~hole_clear).sum())
    hex_clear_nonwhite = int((painted & hole_clear).sum())

    gap = center_gap_bbox(geometry, artwork.width, artwork.height)
    gap_nonwhite = 0
    if gap:
        x0, y0, x1, y1 = gap
        gap_nonwhite = int(painted[max(0, y0) : min(artwork.height, y1 + 1), max(0, x0) : min(artwork.width, x1 + 1)].sum())

    panel_area = int(allowed.sum())
    panel_coverage = round(100.0 * int((painted & allowed).sum()) / panel_area, 2) if panel_area else 0.0
    notes: list[str] = []
    if outside_nonwhite:
        notes.append("painted pixels escaped the SVG-derived panel mask")
    if gap_nonwhite:
        notes.append("center gap is not clean white in artwork-only export")
    if hex_clear_nonwhite:
        notes.append("hex cutout clearance contains painted pixels")
    if panel_coverage < 60:
        notes.append("panel interiors look underfilled")

    verdict = "PASS"
    if outside_nonwhite or gap_nonwhite or hex_clear_nonwhite or panel_coverage < 60:
        verdict = "FAIL"

    return FitMetrics(
        verdict=verdict,
        output_dimensions=f"{artwork.width}x{artwork.height}",
        panel_coverage_pct=panel_coverage,
        outside_nonwhite_pixels=outside_nonwhite,
        center_gap_nonwhite_pixels=gap_nonwhite,
        hex_clear_nonwhite_pixels=hex_clear_nonwhite,
        hex_clearance_px=clear_px,
        center_gap_bbox=gap,
        path_bboxes=[list(item) for item in sorted((bbox(path) for path in geometry.paths), key=lambda item: item[0])],
        polygon_bboxes=[list(item) for item in sorted((bbox(poly) for poly in geometry.polygons), key=lambda item: item[0])],
        notes=notes,
    )


def save_rgb(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path)


def export_svg_template_fit(
    image_path: Path,
    svg_path: Path,
    out_dir: Path,
    prefix: str,
    output_width: int | None,
    output_height: int | None,
    art_scale_x: float,
    art_scale_y: float,
    art_offset_x: int,
    art_offset_y: int,
    hex_clearance_units: float,
    stroke_width_units: float,
) -> dict[str, object]:
    source = Image.open(image_path).convert("RGBA")
    width = output_width or source.width
    height = output_height or source.height
    geometry = read_template(svg_path)
    placed = place_artwork(source, width, height, art_scale_x, art_scale_y, art_offset_x, art_offset_y)
    artwork_mask, hole_mask, clear_px = build_masks(geometry, width, height, aa=4, hex_clearance_units=hex_clearance_units)

    white = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    clipped = Image.composite(placed, white, artwork_mask)
    hole_binary = hole_mask.point(lambda value: 255 if value > 0 else 0)
    clipped = Image.composite(white, clipped, hole_binary)
    gap = center_gap_bbox(geometry, width, height)
    if gap:
        gap_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(gap_mask).rectangle(gap, fill=255)
        clipped = Image.composite(white, clipped, gap_mask)
    lines = draw_template_lines(geometry, width, height, aa=4, stroke_width_units=stroke_width_units)
    clean = clipped.copy()
    clean.alpha_composite(lines)
    debug = build_debug(clipped, artwork_mask, hole_mask, lines, gap)
    # Measure the RAW placed candidate, not `clipped` — `clipped` has already
    # had the hole/gap regions force-painted white (it's the clean deliverable
    # export), so checking it for hole/outside violations is a structural
    # no-op: it can never see what the candidate actually painted there. This
    # was the second half of Finding B's false PASS (0 violations even once
    # cutouts are classified correctly) — the gate must see the candidate
    # BEFORE this file launders it, or "holes that must stay clear" has no teeth.
    metrics = compute_metrics(placed, artwork_mask, hole_mask, geometry, clear_px)

    out_dir.mkdir(parents=True, exist_ok=True)
    artwork_path = out_dir / f"{prefix}-artwork-only.png"
    clean_path = out_dir / f"{prefix}-clean-black-lines.png"
    debug_path = out_dir / f"{prefix}-debug-mask.png"
    metadata_path = out_dir / f"{prefix}-metadata.json"

    save_rgb(clipped, artwork_path)
    save_rgb(clean, clean_path)
    save_rgb(debug, debug_path)

    metadata: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": " ".join(sys.argv),
        "source_image": str(image_path.relative_to(ROOT) if image_path.is_relative_to(ROOT) else image_path),
        "source_sha256": sha256(image_path),
        "source_dimensions": f"{source.width}x{source.height}",
        "template_svg": str(svg_path.relative_to(ROOT) if svg_path.is_relative_to(ROOT) else svg_path),
        "template_sha256": sha256(svg_path),
        "template_viewbox": list(geometry.viewbox),
        "art_scale_x": art_scale_x,
        "art_scale_y": art_scale_y,
        "art_offset_x": art_offset_x,
        "art_offset_y": art_offset_y,
        "hex_clearance_units": hex_clearance_units,
        "stroke_width_units": stroke_width_units,
        "artwork_only": str(artwork_path.relative_to(ROOT) if artwork_path.is_relative_to(ROOT) else artwork_path),
        "clean_black_lines": str(clean_path.relative_to(ROOT) if clean_path.is_relative_to(ROOT) else clean_path),
        "debug_mask": str(debug_path.relative_to(ROOT) if debug_path.is_relative_to(ROOT) else debug_path),
        "metrics": asdict(metrics),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata"] = str(metadata_path.relative_to(ROOT) if metadata_path.is_relative_to(ROOT) else metadata_path)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="Generated artwork image")
    parser.add_argument("--template-svg", required=True, type=Path, help="SVG containing panel path(s) and polygon cutout(s)")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "tasks/baci-door/outputs/final")
    parser.add_argument("--prefix", default="svg-template-fit")
    parser.add_argument("--output-width", type=int)
    parser.add_argument("--output-height", type=int)
    parser.add_argument("--art-scale-x", type=float, default=1.0)
    parser.add_argument("--art-scale-y", type=float, default=1.0)
    parser.add_argument("--art-offset-x", type=int, default=0)
    parser.add_argument("--art-offset-y", type=int, default=0)
    parser.add_argument("--hex-clearance-units", type=float, default=5.0)
    parser.add_argument("--stroke-width-units", type=float, default=2.0)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    metadata = export_svg_template_fit(
        image_path=resolve(args.image),
        svg_path=resolve(args.template_svg),
        out_dir=resolve(args.out_dir),
        prefix=args.prefix,
        output_width=args.output_width,
        output_height=args.output_height,
        art_scale_x=args.art_scale_x,
        art_scale_y=args.art_scale_y,
        art_offset_x=args.art_offset_x,
        art_offset_y=args.art_offset_y,
        hex_clearance_units=args.hex_clearance_units,
        stroke_width_units=args.stroke_width_units,
    )
    print(json.dumps(metadata, indent=2))
    metrics = metadata["metrics"]
    assert isinstance(metrics, dict)
    print(
        "MECHANICAL PASS ONLY: inspect artwork_only, clean_black_lines, debug_mask, "
        "and any cutout crop sheet before approving production.",
        file=sys.stderr,
    )
    print(
        "Review artifacts: "
        f"{metadata.get('artwork_only')} | {metadata.get('clean_black_lines')} | {metadata.get('debug_mask')}",
        file=sys.stderr,
    )
    if args.require_pass and metrics["verdict"] != "PASS":
        print(f"SVG template fit failed: {metrics['verdict']} {metrics.get('notes', [])}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
