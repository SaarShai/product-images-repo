#!/usr/bin/env python3
"""Place isolated style-agent elements into SVG-derived safe pockets.

This harness assumes a style/image-generation agent has already produced
transparent PNG elements. It owns only geometry: fit each element into a desired
box, prove the transformed alpha is inside an eroded paintable mask, reject
unsafe elements before compositing, then export review artifacts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


sys.dont_write_bytecode = True

OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
REPO_DIR = TASK_DIR.parent.parent
STRICT_HELPER_PATH = TASK_DIR / "agents" / "strict-pocket" / "generate_strict_pocket.py"

DEFAULT_PLACEMENTS_PATH = OUT_DIR / "placements-demo.json"
DEFAULT_ARTWORK_PATH = OUT_DIR / "style-element-placer-artwork.png"
DEFAULT_PREVIEW_PATH = OUT_DIR / "style-element-placer-preview-white.png"
DEFAULT_OVERLAY_PATH = OUT_DIR / "style-element-placer-overlay.png"
DEFAULT_MASK_DEBUG_PATH = OUT_DIR / "style-element-placer-mask-debug.png"
DEFAULT_METADATA_PATH = OUT_DIR / "style-element-placer-metadata.json"


def load_strict_helper():
    spec = importlib.util.spec_from_file_location("strict_pocket_geometry", STRICT_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load strict-pocket helper: {STRICT_HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STRICT = load_strict_helper()


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_DIR.resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str | None, *, base_dir: Path) -> Path | None:
    if value is None:
        return None
    raw = Path(value).expanduser()
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([base_dir / raw, TASK_DIR / raw, REPO_DIR / raw, Path.cwd() / raw])
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not resolve path {value!r} from {base_dir}")


def multiply_alpha(alpha: Image.Image, factor: float) -> Image.Image:
    if factor >= 0.999:
        return alpha
    arr = np.asarray(alpha).astype(np.float32)
    arr = np.clip(arr * factor, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def make_canvas_masks(svg_path: Path, margin_px: int) -> dict[str, Any]:
    svg_text = svg_path.read_text()
    viewbox = STRICT.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = STRICT.extract_path_data(svg_text)
    if len(path_data) < 3:
        raise ValueError(f"Expected at least 3 SVG paths, found {len(path_data)}")

    sampled_paths = [STRICT.sample_svg_path(d) for d in path_data[:3]]
    outer_mask = STRICT.draw_polygon_mask(size, sampled_paths[0])
    cutout_masks = [STRICT.draw_polygon_mask(size, points) for points in sampled_paths[1:3]]
    cutouts_mask = ImageChops.lighter(cutout_masks[0], cutout_masks[1])
    paintable_mask = ImageChops.subtract(outer_mask, cutouts_mask)
    eroded_paintable_mask = STRICT.erode(paintable_mask, margin_px)

    return {
        "viewbox": viewbox,
        "size": size,
        "sampled_paths": sampled_paths,
        "outer_mask": outer_mask,
        "cutouts_mask": cutouts_mask,
        "paintable_mask": paintable_mask,
        "eroded_paintable_mask": eroded_paintable_mask,
    }


def fit_image_to_box(image: Image.Image, box: list[int], fit: str) -> tuple[Image.Image, tuple[int, int, int, int]]:
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"Invalid placement box: {box}")
    target_size = (x1 - x0, y1 - y0)
    source = image.convert("RGBA")

    if fit == "stretch":
        fitted = source.resize(target_size, Image.Resampling.LANCZOS)
        actual_box = (x0, y0, x1, y1)
        return fitted, actual_box
    if fit != "contain":
        raise ValueError(f"Unsupported fit mode {fit!r}; expected 'contain' or 'stretch'")

    fitted = ImageOps.contain(source, target_size, Image.Resampling.LANCZOS)
    px = x0 + (target_size[0] - fitted.width) // 2
    py = y0 + (target_size[1] - fitted.height) // 2
    return fitted, (px, py, px + fitted.width, py + fitted.height)


def alpha_from_element(image: Image.Image, alpha_mode: str, alpha_threshold: int) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha_mode == "existing":
        return alpha.point(lambda p: 255 if p > alpha_threshold else 0)
    if alpha_mode == "white-to-alpha":
        arr = np.asarray(rgba).astype(np.int16)
        rgb = arr[:, :, :3]
        existing = arr[:, :, 3]
        white_distance = 255 - rgb.min(axis=2)
        keyed = np.clip(white_distance * 3, 0, existing).astype(np.uint8)
        keyed[existing <= alpha_threshold] = 0
        return Image.fromarray(keyed)
    if alpha_mode == "luma-key":
        arr = np.asarray(rgba).astype(np.int16)
        rgb = arr[:, :, :3]
        existing = arr[:, :, 3]
        luma = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]).astype(np.int16)
        keyed = np.clip((245 - luma) * 3, 0, existing).astype(np.uint8)
        keyed[existing <= alpha_threshold] = 0
        return Image.fromarray(keyed)
    raise ValueError(f"Unsupported alpha mode {alpha_mode!r}")


def layer_for_element(
    image_path: Path,
    box: list[int],
    canvas_size: tuple[int, int],
    *,
    fit: str,
    alpha_mode: str,
    alpha_threshold: int,
    opacity: float,
) -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    image = Image.open(image_path).convert("RGBA")
    fitted, actual_box = fit_image_to_box(image, box, fit)
    alpha = alpha_from_element(fitted, alpha_mode, alpha_threshold)
    alpha = multiply_alpha(alpha, opacity)
    fitted.putalpha(ImageChops.multiply(fitted.getchannel("A"), alpha))

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    alpha_layer = Image.new("L", canvas_size, 0)
    layer.alpha_composite(fitted, (actual_box[0], actual_box[1]))
    alpha_layer.paste(alpha, (actual_box[0], actual_box[1]))
    return layer, alpha_layer, actual_box


def evaluate_alpha(alpha: Image.Image, masks: dict[str, Any]) -> dict[str, Any]:
    outside_outer = ImageChops.subtract(alpha, masks["outer_mask"])
    inside_cutouts = ImageChops.multiply(alpha, masks["cutouts_mask"])
    outside_eroded = ImageChops.subtract(alpha, masks["eroded_paintable_mask"])
    return {
        "alpha_pixels": count_nonzero(alpha),
        "outside_outer_alpha_pixels": count_nonzero(outside_outer),
        "inside_cutout_alpha_pixels": count_nonzero(inside_cutouts),
        "outside_eroded_paintable_alpha_pixels": count_nonzero(outside_eroded),
        "alpha_bbox": list(alpha.getbbox()) if alpha.getbbox() else None,
    }


def rgb_from_hex(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected 6-digit hex color, got {value!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def build_palette_watercolor_background(
    size: tuple[int, int], paintable_mask: Image.Image, palette_hex: list[str]
) -> Image.Image:
    width, height = size
    fallback = ["#8ab3e2", "#6a93d9", "#3f71b6", "#d3e2f2"]
    blues = [rgb_from_hex(color) for color in palette_hex if color.lower() in {
        "#79a4de",
        "#6a93d9",
        "#8ab3e2",
        "#5784cd",
        "#3f71b6",
        "#295a9c",
        "#aec7e9",
        "#d3e2f2",
    }]
    colors = blues[:4] if len(blues) >= 4 else [rgb_from_hex(color) for color in fallback]
    light, mid, dark, highlight = [np.array(color, dtype=np.float32) for color in colors]

    rng = np.random.default_rng(4107)
    small = rng.normal(0, 1, (math.ceil(height / 38), math.ceil(width / 38)))
    small = (small - small.min()) / (small.max() - small.min())
    noise = Image.fromarray(np.uint8(small * 255)).resize(size, Image.Resampling.BICUBIC)
    noise = noise.filter(ImageFilter.GaussianBlur(8))
    n = np.asarray(noise).astype(np.float32) / 255.0
    rgb = (light * (1 - n[..., None]) + mid * n[..., None]).astype(np.float32)
    rgb = np.where(n[..., None] > 0.72, (rgb * 0.82 + dark * 0.18), rgb)
    rgb = np.where(n[..., None] < 0.20, (rgb * 0.86 + highlight * 0.14), rgb)
    rgb = np.clip(rgb + rng.normal(0, 4, rgb.shape), 0, 255).astype(np.uint8)
    image = Image.fromarray(rgb).convert("RGBA")

    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(wash, "RGBA")
    for _ in range(70):
        cx = int(rng.integers(30, width - 30))
        cy = int(rng.integers(30, height - 30))
        rx = int(rng.integers(80, 260))
        ry = int(rng.integers(35, 155))
        color = dark if rng.random() < 0.34 else highlight
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=tuple(color.astype(int)) + (int(rng.integers(8, 28)),))
    wash = wash.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(image, wash)
    image.putalpha(paintable_mask)
    return image


def build_background(
    size: tuple[int, int],
    paintable_mask: Image.Image,
    background_spec: dict[str, Any],
    palette_hex: list[str],
    *,
    base_dir: Path,
) -> Image.Image:
    kind = background_spec.get("kind", "transparent")
    if kind == "transparent":
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if kind == "palette-watercolor":
        return build_palette_watercolor_background(size, paintable_mask, palette_hex)
    if kind != "texture-fit":
        raise ValueError(f"Unsupported background kind {kind!r}")

    texture_path = resolve_path(background_spec.get("texture_image"), base_dir=base_dir)
    if texture_path is None:
        raise RuntimeError("texture-fit background requires texture_image")

    texture = Image.open(texture_path).convert("RGB")
    texture = ImageOps.fit(texture, size, Image.Resampling.BICUBIC)
    texture = ImageEnhance.Color(texture).enhance(0.95)
    texture = ImageEnhance.Contrast(texture).enhance(0.92)
    texture = texture.filter(ImageFilter.GaussianBlur(0.4))
    background = texture.convert("RGBA")
    background.putalpha(paintable_mask)
    return background


def draw_path_outline(layer: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    coords = [(round(x), round(y)) for x, y in points]
    draw.line(coords, fill=color, width=width, joint="curve")


def add_template_edge_lines(art: Image.Image, masks: dict[str, Any]) -> Image.Image:
    line_layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw_path_outline(line_layer, masks["sampled_paths"][0], (19, 72, 146, 205), 15)
    draw_path_outline(line_layer, masks["sampled_paths"][0], (218, 239, 255, 95), 5)
    for points in masks["sampled_paths"][1:3]:
        draw_path_outline(line_layer, points, (18, 64, 130, 220), 11)
        draw_path_outline(line_layer, points, (234, 247, 255, 105), 4)
    line_layer.putalpha(ImageChops.multiply(line_layer.getchannel("A"), masks["paintable_mask"]))
    return Image.alpha_composite(art, line_layer)


def make_preview(art: Image.Image) -> Image.Image:
    preview = Image.new("RGBA", art.size, (255, 255, 255, 255))
    return Image.alpha_composite(preview, art)


def make_overlay(art: Image.Image, masks: dict[str, Any], placement_records: list[dict[str, Any]]) -> Image.Image:
    overlay = make_preview(art)
    for points, color, width in [
        (masks["sampled_paths"][0], (255, 219, 85, 255), 7),
        (masks["sampled_paths"][1], (255, 76, 76, 245), 7),
        (masks["sampled_paths"][2], (255, 76, 76, 245), 7),
    ]:
        draw_path_outline(overlay, points, color, width)

    draw = ImageDraw.Draw(overlay, "RGBA")
    for record in placement_records:
        box = record["actual_box"]
        color = (36, 177, 92, 230) if record["accepted"] else (222, 55, 55, 230)
        draw.rectangle(box, outline=color, width=5)
    draw.rectangle((0, 0, art.size[0] - 1, art.size[1] - 1), outline=(42, 42, 42, 80), width=2)
    return overlay


def make_mask_debug(masks: dict[str, Any], placement_records: list[dict[str, Any]]) -> Image.Image:
    size = masks["size"]
    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 82),
                Image.new("L", size, 158),
                Image.new("L", size, 226),
                masks["paintable_mask"].point(lambda p: 160 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 255),
                Image.new("L", size, 74),
                Image.new("L", size, 74),
                masks["cutouts_mask"].point(lambda p: 185 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 55),
                Image.new("L", size, 220),
                Image.new("L", size, 120),
                masks["eroded_paintable_mask"].point(lambda p: 82 if p else 0),
            ),
        )
    )

    for record in placement_records:
        alpha = record["_alpha_layer"]
        if record["accepted"]:
            rgb = (0, 0, 0)
            opacity = 150
        else:
            rgb = (150, 48, 42)
            opacity = 135
        debug.alpha_composite(
            Image.merge(
                "RGBA",
                (
                    Image.new("L", size, rgb[0]),
                    Image.new("L", size, rgb[1]),
                    Image.new("L", size, rgb[2]),
                    alpha.point(lambda p: opacity if p else 0),
                ),
            )
        )

    draw = ImageDraw.Draw(debug, "RGBA")
    draw.text(
        (24, 22),
        "blue=paintable, red=cutouts, green=eroded safe mask, black=accepted alpha, brown=rejected alpha",
        fill=(0, 0, 0, 215),
    )
    return debug


def write_outputs(placements_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    spec = json.loads(placements_path.read_text())
    base_dir = placements_path.parent

    svg_path = resolve_path(spec.get("template_svg", "source/template.svg"), base_dir=base_dir)
    manifest_path = resolve_path(spec.get("template_manifest", "template-manifest.json"), base_dir=base_dir)
    style_packet_path = resolve_path(spec.get("style_packet_manifest", "style-packet/style-packet.json"), base_dir=base_dir)
    if svg_path is None or manifest_path is None or style_packet_path is None:
        raise RuntimeError("template_svg, template_manifest, and style_packet_manifest are required")

    margin_px = int(spec.get("control_margin_px", args.margin_px))
    masks = make_canvas_masks(svg_path, margin_px)
    manifest = json.loads(manifest_path.read_text())
    style_packet = json.loads(style_packet_path.read_text())

    art = build_background(
        masks["size"],
        masks["paintable_mask"],
        spec.get("background", {}),
        style_packet.get("palette_hex", []),
        base_dir=base_dir,
    )
    if spec.get("draw_template_edge_lines", True):
        art = add_template_edge_lines(art, masks)

    placement_records: list[dict[str, Any]] = []
    for placement in spec.get("placements", []):
        image_path = resolve_path(placement.get("image"), base_dir=base_dir)
        if image_path is None:
            raise RuntimeError(f"Placement {placement.get('id', '<unknown>')} has no image")
        layer, alpha_layer, actual_box = layer_for_element(
            image_path,
            placement["box"],
            masks["size"],
            fit=placement.get("fit", "contain"),
            alpha_mode=placement.get("alpha_mode", spec.get("alpha_mode", "existing")),
            alpha_threshold=int(placement.get("alpha_threshold", spec.get("alpha_threshold", args.alpha_threshold))),
            opacity=float(placement.get("opacity", 1.0)),
        )
        metrics = evaluate_alpha(alpha_layer, masks)
        accepted = (
            metrics["alpha_pixels"] > 0
            and metrics["outside_outer_alpha_pixels"] == 0
            and metrics["inside_cutout_alpha_pixels"] == 0
            and metrics["outside_eroded_paintable_alpha_pixels"] == 0
        )
        record = {
            "id": placement.get("id"),
            "label": placement.get("label", placement.get("id")),
            "role": placement.get("role"),
            "source_image": rel(image_path),
            "requested_box": placement["box"],
            "actual_box": list(actual_box),
            "fit": placement.get("fit", "contain"),
            "alpha_mode": placement.get("alpha_mode", spec.get("alpha_mode", "existing")),
            "accepted": accepted,
            "rejection_reason": None if accepted else rejection_reason(metrics),
            **metrics,
            "_alpha_layer": alpha_layer,
        }
        placement_records.append(record)
        if accepted:
            art = Image.alpha_composite(art, layer)

    final_alpha = ImageChops.multiply(art.getchannel("A"), masks["paintable_mask"])
    art.putalpha(final_alpha)

    preview = make_preview(art)
    overlay = make_overlay(art, masks, placement_records)
    debug = make_mask_debug(masks, placement_records)

    outside_outer_final = ImageChops.subtract(art.getchannel("A"), masks["outer_mask"])
    inside_cutouts_final = ImageChops.multiply(art.getchannel("A"), masks["cutouts_mask"])
    outside_paintable_final = ImageChops.subtract(art.getchannel("A"), masks["paintable_mask"])

    clean_records = []
    for record in placement_records:
        visible_record = dict(record)
        visible_record.pop("_alpha_layer", None)
        clean_records.append(visible_record)

    accepted_records = [record for record in clean_records if record["accepted"]]
    rejected_records = [record for record in clean_records if not record["accepted"]]
    metadata = {
        "workflow": "style-element-placer",
        "purpose": "geometry-only placement harness for future style-agent isolated PNG elements",
        "source_svg": rel(svg_path),
        "template_manifest": rel(manifest_path),
        "style_packet_manifest": rel(style_packet_path),
        "style_packet_contact_sheets": style_packet.get("contact_sheets", {}),
        "manifest_status": manifest.get("status"),
        "viewbox": list(masks["viewbox"]),
        "canvas_size_px": list(masks["size"]),
        "control_margin_px": margin_px,
        "paintable_mask": {
            "outer_pixels": count_nonzero(masks["outer_mask"]),
            "cutout_pixels": count_nonzero(masks["cutouts_mask"]),
            "paintable_pixels": count_nonzero(masks["paintable_mask"]),
            "eroded_paintable_pixels": count_nonzero(masks["eroded_paintable_mask"]),
        },
        "path_roles": {
            "path[0]": "outer material contour",
            "path[1]": "large diagonal rounded slot keep-clear",
            "path[2]": "lower-right round/bolt-like keep-clear",
        },
        "safe_pocket_plan": manifest.get("safe_pockets", []),
        "no_focal_motif_zones": manifest.get("no_focal_motif_zones", []),
        "placements": clean_records,
        "summary": {
            "planned_placements": len(clean_records),
            "accepted_placements": len(accepted_records),
            "rejected_placements": len(rejected_records),
            "accepted_outside_eroded_paintable_alpha_pixels": sum(
                record["outside_eroded_paintable_alpha_pixels"] for record in accepted_records
            ),
            "accepted_inside_cutout_alpha_pixels": sum(
                record["inside_cutout_alpha_pixels"] for record in accepted_records
            ),
            "final_outside_outer_alpha_pixels": count_nonzero(outside_outer_final),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside_paintable_final),
            "final_cutout_alpha_pixels": count_nonzero(inside_cutouts_final),
        },
        "method_notes": [
            "Style agents supply isolated PNG element candidates and style provenance.",
            "This geometry placer never asks a style agent to understand SVG paths or cutout roles.",
            "Each transformed element alpha is evaluated against the eroded paintable mask before drawing.",
            "Rejected placements are kept out of the artwork and shown only in overlay/debug artifacts.",
            "The final alpha mask is an export guardrail after pre-draw placement checks.",
        ],
        "outputs": {
            "artwork": DEFAULT_ARTWORK_PATH.name,
            "preview_white": DEFAULT_PREVIEW_PATH.name,
            "overlay": DEFAULT_OVERLAY_PATH.name,
            "mask_debug": DEFAULT_MASK_DEBUG_PATH.name,
            "metadata": DEFAULT_METADATA_PATH.name,
        },
    }

    DEFAULT_ARTWORK_PATH.parent.mkdir(parents=True, exist_ok=True)
    art.save(DEFAULT_ARTWORK_PATH)
    preview.save(DEFAULT_PREVIEW_PATH)
    overlay.save(DEFAULT_OVERLAY_PATH)
    debug.save(DEFAULT_MASK_DEBUG_PATH)
    DEFAULT_METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")

    return metadata


def rejection_reason(metrics: dict[str, Any]) -> str:
    if metrics["alpha_pixels"] == 0:
        return "empty transformed alpha"
    reasons = []
    if metrics["outside_outer_alpha_pixels"]:
        reasons.append("outside outer contour")
    if metrics["inside_cutout_alpha_pixels"]:
        reasons.append("inside internal cutout")
    if metrics["outside_eroded_paintable_alpha_pixels"]:
        reasons.append("outside eroded paintable mask")
    return "; ".join(reasons) if reasons else "unknown geometry rejection"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--placements",
        type=Path,
        default=DEFAULT_PLACEMENTS_PATH,
        help="Placement JSON with element image paths and desired boxes.",
    )
    parser.add_argument("--margin-px", type=int, default=18, help="Fallback erosion margin in pixels.")
    parser.add_argument("--alpha-threshold", type=int, default=8, help="Alpha threshold for element masks.")
    parser.add_argument("--require-pass", action="store_true", help="Exit non-zero unless final alpha checks pass.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = write_outputs(args.placements.resolve(), args)
    print(json.dumps(metadata["summary"], indent=2))
    if args.require_pass:
        summary = metadata["summary"]
        failed = (
            summary["final_outside_outer_alpha_pixels"] != 0
            or summary["final_outside_paintable_alpha_pixels"] != 0
            or summary["final_cutout_alpha_pixels"] != 0
            or summary["rejected_placements"] == 0
        )
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
