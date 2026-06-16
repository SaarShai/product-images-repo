#!/usr/bin/env python3
"""Trace safe top-contour candidates from a placed artwork PNG."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path

from PIL import Image, ImageDraw

from make_overlay_preview import fit_cover, transparent_guides


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Variant:
    name: str
    label: str
    color: tuple[int, int, int]
    clearance: int
    min_radius: int
    avg_radius: int
    avg_passes: int
    ramp_width: int


VARIANTS = [
    Variant(
        name="tight",
        label="Tight artwork silhouette",
        color=(0, 96, 255),
        clearance=22,
        min_radius=6,
        avg_radius=6,
        avg_passes=1,
        ramp_width=70,
    ),
    Variant(
        name="production",
        label="Production silhouette",
        color=(255, 96, 0),
        clearance=26,
        min_radius=14,
        avg_radius=12,
        avg_passes=2,
        ramp_width=70,
    ),
]


def is_painted(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    white_distance = (255 - red) + (255 - green) + (255 - blue)
    spread = max(pixel) - min(pixel)
    return (white_distance > 28 and (spread > 4 or min(pixel) < 246)) or min(pixel) < 238


def top_profile(image: Image.Image, x0: int, x1: int, y_limit: int) -> list[int]:
    profile: list[int] = []
    last_seen = y_limit
    for x in range(x0, x1 + 1):
        top = None
        for y in range(y_limit):
            if is_painted(image.getpixel((x, y))):
                top = y
                break
        if top is None:
            top = last_seen
        last_seen = top
        profile.append(top)
    return profile


def moving_average(values: list[float], radius: int, passes: int) -> list[float]:
    smoothed = [float(value) for value in values]
    for _ in range(passes):
        next_values: list[float] = []
        for index in range(len(smoothed)):
            start = max(0, index - radius)
            end = min(len(smoothed), index + radius + 1)
            window = smoothed[start:end]
            next_values.append(sum(window) / len(window))
        smoothed = next_values
    return smoothed


def build_candidate(
    profile: list[int],
    variant: Variant,
    handoff_y: int,
    y_min: int,
) -> tuple[list[float], list[float]]:
    limit = [max(y_min, top - variant.clearance) for top in profile]

    envelope: list[float] = []
    for index in range(len(limit)):
        start = max(0, index - variant.min_radius)
        end = min(len(limit), index + variant.min_radius + 1)
        envelope.append(float(min(limit[start:end])))

    candidate = moving_average(envelope, variant.avg_radius, variant.avg_passes)
    candidate = [min(candidate[index], limit[index]) for index in range(len(candidate))]

    candidate[0] = float(handoff_y)
    candidate[-1] = float(handoff_y)

    for index in range(1, min(variant.ramp_width, len(candidate))):
        progress = index / variant.ramp_width
        ramp = ((1 - progress) ** 2 * handoff_y) + ((1 - (1 - progress) ** 2) * candidate[index])
        candidate[index] = min(ramp, limit[index])

    for offset in range(1, min(variant.ramp_width, len(candidate))):
        index = len(candidate) - 1 - offset
        progress = offset / variant.ramp_width
        ramp = ((1 - progress) ** 2 * handoff_y) + ((1 - (1 - progress) ** 2) * candidate[index])
        candidate[index] = min(ramp, limit[index])

    return candidate, limit


def sampled_points(x0: int, x1: int, y_values: list[float], step: int) -> list[tuple[float, float]]:
    points = [(float(x0 + index), y_values[index]) for index in range(0, len(y_values), step)]
    if points[-1][0] != x1:
        points.append((float(x1), y_values[-1]))
    return points


def path_data(points: list[tuple[float, float]]) -> str:
    first_x, first_y = points[0]
    commands = [f"M {first_x:.2f} {first_y:.2f}"]
    commands.extend(f"L {x:.2f} {y:.2f}" for x, y in points[1:])
    return " ".join(commands)


def write_svg(path: Path, points: list[tuple[float, float]], variant: Variant, width: int, height: int) -> None:
    stroke = f"rgb({variant.color[0]}, {variant.color[1]}, {variant.color[2]})"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="A2 top contour traced from artwork silhouette {variant.name}">
  <title>A2 top contour traced from artwork silhouette - {variant.name}</title>
  <desc>Single open vector path replacing only the top contour segment. It is generated from the placed artwork top silhouette, with clearance so the line does not pass through painted illustration pixels.</desc>
  <path id="a2_top_contour_art_silhouette_{variant.name}" d="{path_data(points)}" fill="none" stroke="{stroke}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
</svg>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def guide_overlay(template_path: Path, width: int, height: int) -> Image.Image:
    template = Image.open(template_path)
    guides = transparent_guides(template, 248)
    return fit_cover(guides, width, height)


def draw_preview(
    base: Image.Image,
    guides: Image.Image,
    points: list[tuple[float, float]],
    variant: Variant,
    out_path: Path,
    profile: list[int] | None = None,
    x0: int | None = None,
) -> None:
    preview = base.convert("RGBA")
    preview.alpha_composite(guides)
    draw = ImageDraw.Draw(preview)
    if profile is not None and x0 is not None:
        profile_points = [(x0 + index, value) for index, value in enumerate(profile)]
        draw.line(profile_points, fill=(255, 0, 180, 165), width=1)
    draw.line(points, fill=variant.color + (255,), width=5, joint="curve")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    preview.convert("RGB").save(out_path)


def painted_centerline_hits(
    image: Image.Image,
    points: list[tuple[float, float]],
    sample_spacing: float = 2.0,
) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        distance = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, round(distance / sample_spacing))
        for step in range(steps):
            progress = step / steps
            x = x1 + (x2 - x1) * progress
            y = y1 + (y2 - y1) * progress
            xi = max(0, min(image.width - 1, round(x)))
            yi = max(0, min(image.height - 1, round(y)))
            if is_painted(image.getpixel((xi, yi))):
                hits.append((xi, yi))
    last_x, last_y = points[-1]
    xi = max(0, min(image.width - 1, round(last_x)))
    yi = max(0, min(image.height - 1, round(last_y)))
    if is_painted(image.getpixel((xi, yi))):
        hits.append((xi, yi))
    return hits


def make_sheet(previews: list[tuple[Variant, Path]], out_path: Path) -> None:
    images = [Image.open(path).convert("RGB") for _, path in previews]
    label_h = 34
    gutter = 28
    sheet = Image.new(
        "RGB",
        (sum(image.width for image in images) + gutter * (len(images) - 1), max(image.height for image in images) + label_h),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    x = 0
    for (variant, _), image in zip(previews, images):
        draw.text((x + 12, 10), variant.label, fill=variant.color)
        sheet.paste(image, (x, label_h))
        x += image.width + gutter
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artwork", type=Path, help="Placed A2 artwork PNG")
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "assets/templates/previews/two-panel-template-cropped.png",
        help="Template guide PNG used for review previews",
    )
    parser.add_argument("--x0", type=int, default=62)
    parser.add_argument("--x1", type=int, default=792)
    parser.add_argument("--handoff-y", type=int, default=433)
    parser.add_argument("--scan-y-limit", type=int, default=700)
    parser.add_argument("--y-min", type=int, default=5)
    parser.add_argument("--sample-step", type=int, default=2)
    parser.add_argument("--prefix", help="Output filename prefix")
    parser.add_argument("--debug-profile", action="store_true", help="Draw the detected top silhouette in magenta")
    args = parser.parse_args()

    artwork_path = args.artwork if args.artwork.is_absolute() else ROOT / args.artwork
    template_path = args.template if args.template.is_absolute() else ROOT / args.template
    prefix = args.prefix or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-a2-top-contour-art-silhouette"

    image = Image.open(artwork_path).convert("RGB")
    profile = top_profile(image, args.x0, args.x1, args.scan_y_limit)
    guides = guide_overlay(template_path, image.width, image.height)

    previews: list[tuple[Variant, Path]] = []
    report_lines = [
        f"source={artwork_path.relative_to(ROOT) if artwork_path.is_relative_to(ROOT) else artwork_path}",
        f"template={template_path.relative_to(ROOT) if template_path.is_relative_to(ROOT) else template_path}",
        f"span=({args.x0},{args.x1}) handoff_y={args.handoff_y} scan_y_limit={args.scan_y_limit}",
        f"top_profile_y_range=({min(profile)},{max(profile)})",
        "",
    ]

    for variant in VARIANTS:
        y_values, limit = build_candidate(profile, variant, args.handoff_y, args.y_min)
        points = sampled_points(args.x0, args.x1, y_values, args.sample_step)
        violations = [
            (args.x0 + index, y_values[index], limit[index], profile[index])
            for index in range(len(y_values))
            if y_values[index] > limit[index] + 0.01
        ]
        hits = painted_centerline_hits(image, points)

        svg_path = ROOT / "tasks/castle-panels/outputs/final" / f"{prefix}-{variant.name}.svg"
        preview_path = ROOT / "tasks/castle-panels/outputs/reviews" / f"{prefix}-{variant.name}-preview.png"
        debug_path = ROOT / "tasks/castle-panels/outputs/reviews" / f"{prefix}-{variant.name}-debug.png"

        write_svg(svg_path, points, variant, image.width, image.height)
        draw_preview(image, guides, points, variant, preview_path)
        draw_preview(image, guides, points, variant, debug_path, profile=profile, x0=args.x0)
        previews.append((variant, preview_path))

        report_lines.extend(
            [
                f"{variant.name}: clearance={variant.clearance} min_radius={variant.min_radius} avg_radius={variant.avg_radius} avg_passes={variant.avg_passes}",
                f"{variant.name}: points={len(points)} candidate_y_range=({min(y_values):.2f},{max(y_values):.2f})",
                f"{variant.name}: source_limit_violations={len(violations)} painted_centerline_hits={len(hits)}",
                f"{variant.name}: svg={svg_path.relative_to(ROOT)}",
                f"{variant.name}: preview={preview_path.relative_to(ROOT)}",
                f"{variant.name}: debug={debug_path.relative_to(ROOT)}",
                "",
            ]
        )

    sheet_path = ROOT / "tasks/castle-panels/outputs/reviews" / f"{prefix}-review-sheet.png"
    make_sheet(previews, sheet_path)
    report_lines.append(f"sheet={sheet_path.relative_to(ROOT)}")

    report_path = ROOT / "tasks/castle-panels/outputs/reviews" / f"{prefix}-report.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(report_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
