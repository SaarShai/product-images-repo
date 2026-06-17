#!/usr/bin/env python3
"""Post-generation SVG safety check for the Method C candidate.

This script does not composite or repair the generated art. It only resizes the
candidate to the SVG viewBox, estimates painted pixels from non-white image
content, and reports/visualizes where those pixels fall against the SVG outer
contour and cutout masks.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
REPO_DIR = TASK_DIR.parent.parent
SVG_PATH = TASK_DIR / "source" / "template.svg"
STRICT_HELPER_PATH = TASK_DIR / "agents" / "strict-pocket" / "generate_strict_pocket.py"
CANDIDATE_PATH = OUT_DIR / "method-c-candidate-01.png"

OVERLAY_PATH = OUT_DIR / "method-c-candidate-01-template-overlay.png"
DEBUG_MASK_PATH = OUT_DIR / "method-c-candidate-01-safety-mask.png"
CUTOUT_CROPS_PATH = OUT_DIR / "method-c-candidate-01-cutout-crops.png"
METADATA_PATH = OUT_DIR / "method-c-candidate-01-safety.json"


def load_strict_helper():
    spec = importlib.util.spec_from_file_location("strict_top_temp", STRICT_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import helper: {STRICT_HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HELPER = load_strict_helper()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_DIR))


def count(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def draw_path(image: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    xy = [(round(x), round(y)) for x, y in points]
    ImageDraw.Draw(image, "RGBA").line(xy, fill=color, width=width, joint="curve")


def nonwhite_mask(image: Image.Image, threshold: int = 24) -> Image.Image:
    arr = np.asarray(image.convert("RGB"))
    distance_from_white = np.max(255 - arr, axis=2)
    mask = np.where(distance_from_white > threshold, 255, 0).astype(np.uint8)
    return Image.fromarray(mask, "L")


def crop_with_label(base: Image.Image, box: tuple[int, int, int, int], label: str) -> Image.Image:
    crop = base.crop(box).convert("RGBA")
    strip = Image.new("RGBA", (crop.width, 28), (255, 255, 255, 255))
    ImageDraw.Draw(strip).text((8, 7), label, fill=(20, 48, 88, 255))
    out = Image.new("RGBA", (crop.width, crop.height + strip.height), (255, 255, 255, 255))
    out.alpha_composite(crop, (0, 0))
    out.alpha_composite(strip, (0, crop.height))
    return out


def main() -> None:
    svg_text = SVG_PATH.read_text()
    viewbox = HELPER.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = HELPER.extract_path_data(svg_text)
    paths = [HELPER.sample_svg_path(d) for d in path_data[:3]]

    outer = HELPER.draw_polygon_mask(size, paths[0])
    diagonal_slot = HELPER.draw_polygon_mask(size, paths[1])
    round_cutout = HELPER.draw_polygon_mask(size, paths[2])
    cutouts = ImageChops.lighter(diagonal_slot, round_cutout)
    paintable = ImageChops.subtract(outer, cutouts)

    candidate = Image.open(CANDIDATE_PATH).convert("RGB")
    resized = candidate.resize(size, Image.Resampling.LANCZOS)
    painted = nonwhite_mask(resized)
    outside_outer = ImageChops.subtract(painted, outer)
    outside_paintable = ImageChops.subtract(painted, paintable)
    diagonal_paint = ImageChops.multiply(painted, diagonal_slot)
    round_paint = ImageChops.multiply(painted, round_cutout)

    overlay = resized.convert("RGBA")
    red_cutout = Image.new("RGBA", size, (255, 0, 0, 0))
    red_cutout.putalpha(ImageChops.multiply(cutouts, painted).point(lambda p: 128 if p else 0))
    overlay.alpha_composite(red_cutout)
    draw_path(overlay, paths[0], (255, 220, 60, 255), 6)
    draw_path(overlay, paths[1], (255, 64, 64, 255), 6)
    draw_path(overlay, paths[2], (255, 64, 64, 255), 6)
    overlay.convert("RGB").save(OVERLAY_PATH)

    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    paint_layer = Image.new("RGBA", size, (60, 120, 210, 0))
    paint_layer.putalpha(painted.point(lambda p: 145 if p else 0))
    outside_layer = Image.new("RGBA", size, (255, 190, 0, 0))
    outside_layer.putalpha(outside_outer.point(lambda p: 190 if p else 0))
    cutout_layer = Image.new("RGBA", size, (255, 0, 0, 0))
    cutout_layer.putalpha(ImageChops.multiply(painted, cutouts).point(lambda p: 220 if p else 0))
    debug.alpha_composite(paint_layer)
    debug.alpha_composite(outside_layer)
    debug.alpha_composite(cutout_layer)
    draw_path(debug, paths[0], (20, 60, 120, 255), 5)
    draw_path(debug, paths[1], (180, 0, 0, 255), 5)
    draw_path(debug, paths[2], (180, 0, 0, 255), 5)
    debug.convert("RGB").save(DEBUG_MASK_PATH)

    crop_source = overlay
    crops = [
        crop_with_label(crop_source, (760, 360, 1535, 1080), "diagonal slot overlay"),
        crop_with_label(crop_source, (1330, 1100, 1570, 1350), "round cutout overlay"),
        crop_with_label(crop_source, (640, 900, 980, 1515), "lower rectangular void"),
    ]
    sheet_width = max(c.width for c in crops)
    sheet_height = sum(c.height for c in crops) + 24 * (len(crops) - 1)
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (255, 255, 255, 255))
    y = 0
    for crop in crops:
        sheet.alpha_composite(crop, ((sheet_width - crop.width) // 2, y))
        y += crop.height + 24
    sheet.convert("RGB").save(CUTOUT_CROPS_PATH)

    metadata = {
        "candidate": rel(CANDIDATE_PATH),
        "source_svg": rel(SVG_PATH),
        "analysis_only": True,
        "candidate_original_size": list(candidate.size),
        "analysis_size": list(size),
        "paint_threshold_distance_from_white": 24,
        "metrics": {
            "painted_pixels": count(painted),
            "outside_outer_pixels": count(outside_outer),
            "outside_paintable_pixels": count(outside_paintable),
            "inside_diagonal_slot_pixels": count(diagonal_paint),
            "inside_round_cutout_pixels": count(round_paint),
        },
        "outputs": {
            "template_overlay": rel(OVERLAY_PATH),
            "safety_mask": rel(DEBUG_MASK_PATH),
            "cutout_crops": rel(CUTOUT_CROPS_PATH),
            "metadata": rel(METADATA_PATH),
        },
        "notes": [
            "This pass does not alter or mask the candidate.",
            "Counts are approximate because the model-painted candidate is not an SVG-registered export.",
            "Red pixels in the overlay/debug image indicate non-white generated paint inside SVG cutout masks after full-canvas resize.",
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata["metrics"], indent=2))


if __name__ == "__main__":
    main()
