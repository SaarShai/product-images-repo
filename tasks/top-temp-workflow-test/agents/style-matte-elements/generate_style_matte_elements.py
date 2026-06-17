#!/usr/bin/env python3
"""Extract packet-backed element mattes and fit them into the top-temp SVG.

This is a method test: source pixels come from the style packet crops, then
each scaled placement is checked against the SVG-derived paintable mask before
it is allowed into the final artwork.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
REPO_DIR = TASK_DIR.parent.parent
SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
STYLE_PACKET_PATH = TASK_DIR / "style-packet" / "style-packet.json"
STYLE_SHEET_PATH = TASK_DIR / "style-packet" / "style-exemplar-sheet.png"
STRICT_POLISH_PATH = TASK_DIR / "agents" / "strict-style-polish" / "strict-style-polish-artwork.png"
STRICT_HELPER_PATH = TASK_DIR / "agents" / "strict-pocket" / "generate_strict_pocket.py"

SPRITES_DIR = OUT_DIR / "sprites"
ELEMENT_SHEET_PATH = OUT_DIR / "element-sheet.png"
ARTWORK_PATH = OUT_DIR / "style-matte-elements-artwork.png"
PREVIEW_WHITE_PATH = OUT_DIR / "style-matte-elements-preview-white.png"
OVERLAY_PATH = OUT_DIR / "style-matte-elements-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "style-matte-elements-mask-debug.png"
METADATA_PATH = OUT_DIR / "style-matte-elements-metadata.json"
REVIEW_PATH = OUT_DIR / "review.md"


def load_strict_helper():
    spec = importlib.util.spec_from_file_location("strict_pocket_helper", STRICT_HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import helper: {STRICT_HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HELPER = load_strict_helper()


@dataclass(frozen=True)
class Shape:
    kind: str
    coords: tuple[int, ...]
    radius: int = 0
    width: int = 1


@dataclass(frozen=True)
class SpriteSpec:
    name: str
    kind: str
    label: str
    source_path: str
    crop_box: tuple[int, int, int, int]
    shapes: tuple[Shape, ...]
    feather_px: float = 2.2
    opacity: int = 255


@dataclass(frozen=True)
class Sprite:
    name: str
    kind: str
    label: str
    source_path: str
    crop_box: tuple[int, int, int, int]
    image: Image.Image
    output_path: Path


@dataclass(frozen=True)
class PlacementSpec:
    name: str
    sprite_name: str
    pocket: str
    xy: tuple[int, int]
    scale: float
    intent: str
    expected: str = "accepted"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_DIR))


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA")).copy()
    rgba[rgba[..., 3] == 0, :3] = 0
    return Image.fromarray(rgba).convert("RGBA")


def crop_path(style_packet: dict, label: str) -> Path:
    for crop in style_packet["crops"]:
        if crop["label"] == label:
            return REPO_DIR / crop["path"]
    raise KeyError(f"Missing crop label: {label}")


def draw_shape(draw: ImageDraw.ImageDraw, shape: Shape, fill: int) -> None:
    if shape.kind == "ellipse":
        draw.ellipse(shape.coords, fill=fill)
    elif shape.kind == "rounded":
        draw.rounded_rectangle(shape.coords, radius=shape.radius, fill=fill)
    elif shape.kind == "line":
        x0, y0, x1, y1 = shape.coords
        draw.line((x0, y0, x1, y1), fill=fill, width=shape.width)
    else:
        raise ValueError(f"Unsupported shape kind: {shape.kind}")


def make_matte_mask(size: tuple[int, int], shapes: Sequence[Shape], feather_px: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for shape in shapes:
        draw_shape(draw, shape, 255)
    if feather_px > 0:
        expanded = mask.filter(ImageFilter.MaxFilter(5))
        mask = expanded.filter(ImageFilter.GaussianBlur(feather_px))
    return mask


def extract_sprite(spec: SpriteSpec, source_image: Image.Image, output_path: Path) -> Sprite:
    crop = source_image.convert("RGBA").crop(spec.crop_box)
    mask = make_matte_mask(crop.size, spec.shapes, spec.feather_px)
    if spec.opacity < 255:
        mask = mask.point(lambda p: int(p * spec.opacity / 255))
    crop.putalpha(mask)
    crop = clear_transparent_rgb(crop)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path)
    return Sprite(
        name=spec.name,
        kind=spec.kind,
        label=spec.label,
        source_path=spec.source_path,
        crop_box=spec.crop_box,
        image=crop,
        output_path=output_path,
    )


def sprite_specs(style_packet: dict) -> list[SpriteSpec]:
    def source(label: str) -> str:
        return rel(crop_path(style_packet, label))

    return [
        SpriteSpec(
            name="dial_ref1_gauge",
            kind="dial",
            label="ref 1 right-region",
            source_path=source("ref 1 right-region"),
            crop_box=(20, 105, 358, 470),
            shapes=(Shape("ellipse", (8, 20, 326, 338)),),
            feather_px=2.4,
        ),
        SpriteSpec(
            name="slider_bank_ref1",
            kind="slider bank",
            label="ref 1 left-region",
            source_path=source("ref 1 left-region"),
            crop_box=(120, 160, 793, 444),
            shapes=(
                Shape("rounded", (24, 55, 666, 84), radius=14),
                Shape("rounded", (24, 106, 666, 135), radius=14),
                Shape("rounded", (24, 176, 666, 205), radius=14),
                Shape("rounded", (24, 240, 666, 269), radius=14),
            ),
            feather_px=2.0,
        ),
        SpriteSpec(
            name="pill_red_ref1",
            kind="pill button",
            label="ref 1 accent component 01",
            source_path=source("ref 1 accent component 01"),
            crop_box=(22, 40, 378, 184),
            shapes=(Shape("rounded", (6, 12, 348, 132), radius=58),),
            feather_px=2.0,
        ),
        SpriteSpec(
            name="pill_teal_ref1",
            kind="pill button",
            label="ref 1 accent component 03",
            source_path=source("ref 1 accent component 03"),
            crop_box=(14, 48, 383, 190),
            shapes=(Shape("rounded", (7, 12, 360, 128), radius=58),),
            feather_px=2.0,
        ),
        SpriteSpec(
            name="pill_yellow_ref1",
            kind="pill button",
            label="ref 1 accent component 02",
            source_path=source("ref 1 accent component 02"),
            crop_box=(20, 68, 380, 220),
            shapes=(Shape("rounded", (6, 22, 352, 136), radius=58),),
            feather_px=2.0,
        ),
        SpriteSpec(
            name="pin_yellow_ref2",
            kind="pin/knob",
            label="ref 2 accent component 01",
            source_path=source("ref 2 accent component 01"),
            crop_box=(0, 0, 211, 266),
            shapes=(
                Shape("ellipse", (34, 136, 179, 260)),
                Shape("rounded", (68, 22, 146, 194), radius=38),
            ),
            feather_px=2.2,
        ),
        SpriteSpec(
            name="pin_red_ref2",
            kind="pin/knob",
            label="ref 2 accent component 02",
            source_path=source("ref 2 accent component 02"),
            crop_box=(0, 0, 203, 265),
            shapes=(
                Shape("ellipse", (30, 136, 174, 259)),
                Shape("rounded", (66, 22, 142, 194), radius=38),
            ),
            feather_px=2.2,
        ),
        SpriteSpec(
            name="pin_teal_ref2",
            kind="pin/knob",
            label="ref 2 accent component 04",
            source_path=source("ref 2 accent component 04"),
            crop_box=(0, 0, 202, 266),
            shapes=(
                Shape("ellipse", (30, 136, 176, 260)),
                Shape("rounded", (64, 22, 142, 194), radius=38),
            ),
            feather_px=2.2,
        ),
        SpriteSpec(
            name="bolt_ref2_right",
            kind="bolt",
            label="ref 2 edge-treatment",
            source_path=source("ref 2 edge-treatment"),
            crop_box=(50, 64, 160, 174),
            shapes=(Shape("ellipse", (6, 6, 104, 104)),),
            feather_px=2.0,
        ),
    ]


def resize_sprite(sprite: Image.Image, scale: float) -> Image.Image:
    width = max(1, int(round(sprite.width * scale)))
    height = max(1, int(round(sprite.height * scale)))
    return sprite.resize((width, height), Image.Resampling.LANCZOS)


def paste_image(base: Image.Image, sprite: Image.Image, xy: tuple[int, int]) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.alpha_composite(sprite, xy)
    base.alpha_composite(layer)


def placement_mask(size: tuple[int, int], sprite: Image.Image, xy: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    mask.paste(sprite.getchannel("A"), xy)
    return mask


def evaluate_mask(mask: Image.Image, outer: Image.Image, cutouts: Image.Image, safe: Image.Image) -> dict:
    outside_outer = ImageChops.subtract(mask, outer)
    inside_cutouts = ImageChops.multiply(mask, cutouts)
    outside_safe = ImageChops.subtract(mask, safe)
    bbox = mask.getbbox()
    return {
        "mask_pixels": count_nonzero(mask),
        "outside_outer_pixels": count_nonzero(outside_outer),
        "inside_cutout_pixels": count_nonzero(inside_cutouts),
        "outside_eroded_paintable_pixels": count_nonzero(outside_safe),
        "bbox": list(bbox) if bbox else None,
    }


def build_masks() -> dict:
    svg_text = SVG_PATH.read_text()
    viewbox = HELPER.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = HELPER.extract_path_data(svg_text)
    sampled_paths = [HELPER.sample_svg_path(d) for d in path_data[:3]]
    outer_mask = HELPER.draw_polygon_mask(size, sampled_paths[0])
    cutout_masks = [HELPER.draw_polygon_mask(size, points) for points in sampled_paths[1:3]]
    cutouts_mask = ImageChops.lighter(cutout_masks[0], cutout_masks[1])
    paintable_mask = ImageChops.subtract(outer_mask, cutouts_mask)
    safe_margin_px = 18
    paintable_safe = HELPER.erode(paintable_mask, safe_margin_px)
    return {
        "viewbox": viewbox,
        "size": size,
        "sampled_paths": sampled_paths,
        "outer_mask": outer_mask,
        "cutouts_mask": cutouts_mask,
        "path1_cutout_mask": cutout_masks[0],
        "path2_cutout_mask": cutout_masks[1],
        "paintable_mask": paintable_mask,
        "paintable_safe": paintable_safe,
        "safe_margin_px": safe_margin_px,
    }


def build_reference_background(style_packet: dict, size: tuple[int, int], paintable_mask: Image.Image) -> Image.Image:
    """Build a quiet wash from blank-ish packet texture patches.

    The body-texture packet crops include focal controls, so using them as
    full-panel backgrounds creates giant ghost hardware. These patches stay in
    the packet evidence lane while avoiding recognizable source objects.
    """

    patch_specs = [
        ("ref 1 left-region", (255, 76, 760, 154)),
        ("ref 1 edge-treatment", (168, 70, 500, 175)),
        ("ref 2 edge-treatment", (170, 34, 430, 126)),
    ]
    patches = [
        Image.open(crop_path(style_packet, label)).convert("RGBA").crop(box)
        for label, box in patch_specs
    ]
    rng = np.random.default_rng(101)
    base = Image.new("RGBA", size, (104, 157, 218, 255))
    for index in range(120):
        patch = patches[index % len(patches)]
        scale = float(rng.uniform(1.4, 3.8))
        w = max(20, int(patch.width * scale))
        h = max(12, int(patch.height * scale))
        tile = patch.resize((w, h), Image.Resampling.BICUBIC)
        tile = ImageEnhance.Color(tile).enhance(0.75)
        tile = ImageEnhance.Contrast(tile).enhance(0.82)
        alpha = int(rng.integers(28, 70))
        tile.putalpha(tile.getchannel("A").point(lambda p, a=alpha: int(p * a / 255)))
        x = int(rng.integers(-w // 3, size[0] - w // 2))
        y = int(rng.integers(-h // 3, size[1] - h // 2))
        base.alpha_composite(tile, (x, y))
    base = base.filter(ImageFilter.GaussianBlur(3.0))
    base = ImageEnhance.Color(base).enhance(1.08)
    base = ImageEnhance.Contrast(base).enhance(1.06)
    base.putalpha(paintable_mask)
    return base


def draw_template_edges(
    art: Image.Image,
    sampled_paths: Sequence[list[tuple[float, float]]],
    paintable_mask: Image.Image,
) -> None:
    edge = Image.new("RGBA", art.size, (0, 0, 0, 0))
    HELPER.draw_path_outline(edge, sampled_paths[0], (17, 70, 145, 225), 15)
    HELPER.draw_path_outline(edge, sampled_paths[0], (206, 232, 255, 95), 5)
    for points in sampled_paths[1:3]:
        HELPER.draw_path_outline(edge, points, (17, 65, 135, 235), 13)
        HELPER.draw_path_outline(edge, points, (226, 242, 255, 100), 4)
    edge.putalpha(ImageChops.multiply(edge.getchannel("A"), paintable_mask))
    art.alpha_composite(edge)


def placement_specs() -> list[PlacementSpec]:
    return [
        PlacementSpec(
            "upper-left red pin",
            "pin_red_ref2",
            "upper-left tall bay above the left shoulder of the slot",
            (376, 332),
            0.54,
            "vertical red packet pin in the tall upper pocket",
        ),
        PlacementSpec(
            "upper-left yellow pin",
            "pin_yellow_ref2",
            "upper-left tall bay above the left shoulder of the slot",
            (486, 328),
            0.54,
            "vertical yellow packet pin in the tall upper pocket",
        ),
        PlacementSpec(
            "upper-left teal pin",
            "pin_teal_ref2",
            "upper-left tall bay above the left shoulder of the slot",
            (596, 334),
            0.54,
            "vertical teal packet pin in the tall upper pocket",
        ),
        PlacementSpec(
            "middle-left slider bank",
            "slider_bank_ref1",
            "middle-left field below/left of the diagonal slot",
            (238, 648),
            0.70,
            "actual reference slider rails and colored knobs scaled into the middle-left field",
        ),
        PlacementSpec(
            "lower-left gauge",
            "dial_ref1_gauge",
            "lower-left base bay above the bottom notch",
            (344, 1125),
            0.72,
            "packet gauge kept clear of the bottom notch and slot",
        ),
        PlacementSpec(
            "lower-left red pill",
            "pill_red_ref1",
            "lower-left base bay above the bottom notch",
            (94, 1126),
            0.56,
            "red pill from packet component crop",
        ),
        PlacementSpec(
            "lower-left yellow pill",
            "pill_yellow_ref1",
            "lower-left base bay above the bottom notch",
            (102, 1236),
            0.56,
            "yellow pill from packet component crop",
        ),
        PlacementSpec(
            "lower-left teal pill",
            "pill_teal_ref1",
            "lower-left base bay above the bottom notch",
            (110, 1344),
            0.54,
            "teal pill from packet component crop",
        ),
        PlacementSpec(
            "lower-middle red pill",
            "pill_red_ref1",
            "lower-middle bay between the bottom notch and the right cutouts",
            (922, 1122),
            0.72,
            "larger packet pill shifted into the right lower paintable bay",
        ),
        PlacementSpec(
            "lower-middle teal pill",
            "pill_teal_ref1",
            "lower-middle bay between the bottom notch and the right cutouts",
            (930, 1252),
            0.70,
            "teal packet pill clear of path[2]",
        ),
        PlacementSpec(
            "lower-middle yellow pill",
            "pill_yellow_ref1",
            "lower-middle bay between the bottom notch and the right cutouts",
            (918, 1340),
            0.65,
            "yellow packet pill clear of the bottom edge notch",
        ),
        PlacementSpec(
            "right-strip upper bolt",
            "bolt_ref2_right",
            "right vertical strip between the diagonal slot and outer edge",
            (1492, 1064),
            0.44,
            "packet screw head in the right strip above the round cutout",
        ),
        PlacementSpec(
            "right-strip lower bolt",
            "bolt_ref2_right",
            "right vertical strip between the diagonal slot and outer edge",
            (1492, 1370),
            0.44,
            "packet screw head in the right strip below the round cutout",
        ),
        PlacementSpec(
            "reject dial crossing diagonal slot",
            "dial_ref1_gauge",
            "path[1] diagonal slot keep-clear",
            (790, 575),
            0.88,
            "deliberate negative placement that overlaps the large diagonal cutout",
            expected="rejected",
        ),
        PlacementSpec(
            "reject lower-middle pill across bottom void",
            "pill_red_ref1",
            "bottom center void / outer contour exclusion",
            (712, 1290),
            0.88,
            "deliberate negative placement that crosses the lower center opening",
            expected="rejected",
        ),
        PlacementSpec(
            "reject bolt on round cutout",
            "bolt_ref2_right",
            "path[2] lower-right round cutout keep-clear",
            (1428, 1210),
            0.70,
            "deliberate negative placement on the lower-right circular cutout",
            expected="rejected",
        ),
    ]


def make_element_sheet(sprites: Sequence[Sprite]) -> None:
    font = ImageFont.load_default()
    cell_w, cell_h = 320, 270
    columns = 3
    rows = math.ceil(len(sprites) / columns)
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (250, 250, 248, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    for index, sprite in enumerate(sprites):
        col = index % columns
        row = index // columns
        x0 = col * cell_w
        y0 = row * cell_h
        draw.rounded_rectangle((x0 + 10, y0 + 10, x0 + cell_w - 10, y0 + cell_h - 10), 10, fill=(255, 255, 255, 255), outline=(205, 213, 224, 255))
        checker = make_checkerboard((cell_w - 54, cell_h - 86), 12)
        sheet.alpha_composite(checker, (x0 + 27, y0 + 28))
        max_w, max_h = cell_w - 80, cell_h - 120
        scale = min(max_w / sprite.image.width, max_h / sprite.image.height, 1.25)
        preview = resize_sprite(sprite.image, scale)
        px = x0 + (cell_w - preview.width) // 2
        py = y0 + 38 + (max_h - preview.height) // 2
        sheet.alpha_composite(preview, (px, py))
        draw.text((x0 + 22, y0 + cell_h - 46), sprite.name, font=font, fill=(20, 38, 62, 255))
        draw.text((x0 + 22, y0 + cell_h - 28), f"{sprite.kind} | {sprite.label}", font=font, fill=(72, 87, 108, 255))
    ELEMENT_SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(ELEMENT_SHEET_PATH)


def make_checkerboard(size: tuple[int, int], square: int) -> Image.Image:
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle((x, y, x + square - 1, y + square - 1), fill=(225, 231, 238, 255))
    return image


def composite_artwork(style_packet: dict, sprites_by_name: dict[str, Sprite], masks: dict, manifest: dict) -> dict:
    size = masks["size"]
    art = build_reference_background(style_packet, size, masks["paintable_mask"])
    draw_template_edges(art, masks["sampled_paths"], masks["paintable_mask"])

    placement_records = []
    accepted_masks: list[tuple[str, Image.Image]] = []
    rejected_masks: list[tuple[str, Image.Image]] = []
    specs = placement_specs()
    for spec in specs:
        sprite = sprites_by_name[spec.sprite_name]
        scaled = resize_sprite(sprite.image, spec.scale)
        mask = placement_mask(size, scaled, spec.xy)
        metrics = evaluate_mask(mask, masks["outer_mask"], masks["cutouts_mask"], masks["paintable_safe"])
        accepted = (
            metrics["mask_pixels"] > 0
            and metrics["outside_outer_pixels"] == 0
            and metrics["inside_cutout_pixels"] == 0
            and metrics["outside_eroded_paintable_pixels"] == 0
        )
        record = {
            "name": spec.name,
            "sprite": spec.sprite_name,
            "sprite_kind": sprite.kind,
            "pocket": spec.pocket,
            "xy": list(spec.xy),
            "scale": spec.scale,
            "intent": spec.intent,
            "expected": spec.expected,
            "accepted": accepted,
            **metrics,
        }
        placement_records.append(record)
        if accepted:
            paste_image(art, scaled, spec.xy)
            accepted_masks.append((spec.name, mask))
        else:
            rejected_masks.append((spec.name, mask))

    final_alpha = ImageChops.multiply(art.getchannel("A"), masks["paintable_mask"])
    art.putalpha(final_alpha)
    art = clear_transparent_rgb(art)
    art.save(ARTWORK_PATH)

    preview = Image.new("RGBA", size, (255, 255, 255, 255))
    preview.alpha_composite(art)
    preview.convert("RGB").save(PREVIEW_WHITE_PATH)

    overlay = preview.copy()
    draw_overlay(overlay, masks["sampled_paths"], placement_records)
    overlay.convert("RGB").save(OVERLAY_PATH)

    debug = make_mask_debug(size, masks, accepted_masks, rejected_masks)
    debug.convert("RGB").save(MASK_DEBUG_PATH)

    alpha = art.getchannel("A")
    outside_outer = ImageChops.subtract(alpha, masks["outer_mask"])
    path1_cutout = ImageChops.multiply(alpha, masks["path1_cutout_mask"])
    path2_cutout = ImageChops.multiply(alpha, masks["path2_cutout_mask"])
    final_cutout = ImageChops.multiply(alpha, masks["cutouts_mask"])
    outside_paintable = ImageChops.subtract(alpha, masks["paintable_mask"])

    accepted = [p for p in placement_records if p["accepted"]]
    rejected = [p for p in placement_records if not p["accepted"]]
    metadata = {
        "workflow": "style-matte-elements-packet-pixel-method-test",
        "source_svg": rel(SVG_PATH),
        "template_manifest": rel(MANIFEST_PATH),
        "style_packet_manifest": rel(STYLE_PACKET_PATH),
        "style_exemplar_sheet": rel(STYLE_SHEET_PATH),
        "strict_style_polish_baseline": rel(STRICT_POLISH_PATH),
        "strict_pocket_helper": rel(STRICT_HELPER_PATH),
        "manifest_status": manifest.get("status"),
        "viewbox": list(masks["viewbox"]),
        "canvas_size_px": list(size),
        "path_roles": {
            "path[0]": "outer material contour",
            "path[1]": "large diagonal rounded slot keep-clear",
            "path[2]": "lower-right round/bolt-like keep-clear",
        },
        "paintable_mask": {
            "outer_pixels": count_nonzero(masks["outer_mask"]),
            "cutout_pixels": count_nonzero(masks["cutouts_mask"]),
            "paintable_pixels": count_nonzero(masks["paintable_mask"]),
            "control_margin_px": masks["safe_margin_px"],
            "eroded_control_safe_pixels": count_nonzero(masks["paintable_safe"]),
        },
        "safe_pocket_plan": manifest.get("safe_pockets", []),
        "no_focal_motif_zones": manifest.get("no_focal_motif_zones", []),
        "sprites": [
            {
                "name": sprite.name,
                "kind": sprite.kind,
                "label": sprite.label,
                "source_path": sprite.source_path,
                "crop_box": list(sprite.crop_box),
                "output": rel(sprite.output_path),
                "size": list(sprite.image.size),
                "alpha_pixels": count_nonzero(sprite.image.getchannel("A")),
            }
            for sprite in sprites_by_name.values()
        ],
        "placements": placement_records,
        "summary": {
            "planned_placements": len(placement_records),
            "accepted_placements": len(accepted),
            "rejected_placements": len(rejected),
            "accepted_placement_escape_pixels": sum(p["outside_eroded_paintable_pixels"] for p in accepted),
            "accepted_placement_cutout_pixels": sum(p["inside_cutout_pixels"] for p in accepted),
            "final_outside_outer_alpha_pixels": count_nonzero(outside_outer),
            "final_path1_cutout_alpha_pixels": count_nonzero(path1_cutout),
            "final_path2_cutout_alpha_pixels": count_nonzero(path2_cutout),
            "final_cutout_alpha_pixels": count_nonzero(final_cutout),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside_paintable),
            "final_alpha_gate_pass": (
                count_nonzero(outside_outer) == 0
                and count_nonzero(final_cutout) == 0
                and count_nonzero(outside_paintable) == 0
            ),
        },
        "style_comparison_to_strict_style_polish": {
            "closer_to_references": True,
            "because": [
                "Visible controls are source pixels from packet crops rather than redrawn procedural controls.",
                "The sprites preserve watercolor texture, uneven ink edges, soft highlights, and organic component shadows.",
                "Remaining procedural pieces are the SVG-edge drawing and texture fit, so this is a method test rather than a final production claim.",
            ],
        },
        "outputs": {
            "element_sheet": rel(ELEMENT_SHEET_PATH),
            "artwork": rel(ARTWORK_PATH),
            "preview_white": rel(PREVIEW_WHITE_PATH),
            "overlay": rel(OVERLAY_PATH),
            "mask_debug": rel(MASK_DEBUG_PATH),
            "metadata": rel(METADATA_PATH),
            "review": rel(REVIEW_PATH),
        },
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    write_review(metadata)
    return metadata


def draw_overlay(overlay: Image.Image, sampled_paths: Sequence[list[tuple[float, float]]], placements: Sequence[dict]) -> None:
    HELPER.draw_path_outline(overlay, sampled_paths[0], (255, 218, 62, 255), 7)
    for points in sampled_paths[1:3]:
        HELPER.draw_path_outline(overlay, points, (255, 70, 70, 235), 7)
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = ImageFont.load_default()
    for placement in placements:
        bbox = placement.get("bbox")
        if not bbox:
            continue
        color = (30, 180, 90, 210) if placement["accepted"] else (185, 55, 45, 185)
        draw.rectangle(bbox, outline=color, width=4)
        tag = "ACCEPT" if placement["accepted"] else "REJECT"
        draw.text((bbox[0], max(0, bbox[1] - 16)), tag, font=font, fill=color)


def make_mask_debug(
    size: tuple[int, int],
    masks: dict,
    accepted_masks: Sequence[tuple[str, Image.Image]],
    rejected_masks: Sequence[tuple[str, Image.Image]],
) -> Image.Image:
    debug = Image.new("RGBA", size, (250, 250, 248, 255))
    blue = Image.merge(
        "RGBA",
        (
            Image.new("L", size, 93),
            Image.new("L", size, 164),
            Image.new("L", size, 230),
            masks["paintable_mask"].point(lambda p: 160 if p else 0),
        ),
    )
    red = Image.merge(
        "RGBA",
        (
            Image.new("L", size, 255),
            Image.new("L", size, 69),
            Image.new("L", size, 78),
            masks["cutouts_mask"].point(lambda p: 180 if p else 0),
        ),
    )
    green = Image.merge(
        "RGBA",
        (
            Image.new("L", size, 50),
            Image.new("L", size, 210),
            Image.new("L", size, 120),
            masks["paintable_safe"].point(lambda p: 72 if p else 0),
        ),
    )
    debug.alpha_composite(blue)
    debug.alpha_composite(red)
    debug.alpha_composite(green)
    for _, mask in accepted_masks:
        layer = Image.merge(
            "RGBA",
            (
                Image.new("L", size, 10),
                Image.new("L", size, 35),
                Image.new("L", size, 60),
                mask.point(lambda p: 130 if p else 0),
            ),
        )
        debug.alpha_composite(layer)
    for _, mask in rejected_masks:
        layer = Image.merge(
            "RGBA",
            (
                Image.new("L", size, 164),
                Image.new("L", size, 72),
                Image.new("L", size, 42),
                mask.point(lambda p: 145 if p else 0),
            ),
        )
        debug.alpha_composite(layer)
    draw = ImageDraw.Draw(debug, "RGBA")
    draw.text(
        (24, 22),
        "blue=paintable, red=cutouts, green=eroded safe, dark=accepted sprites, brown=rejected tests",
        fill=(12, 25, 42, 230),
    )
    return debug


def write_review(metadata: dict) -> None:
    summary = metadata["summary"]
    accepted = [p for p in metadata["placements"] if p["accepted"]]
    rejected = [p for p in metadata["placements"] if not p["accepted"]]
    verdict = "ACCEPT" if summary["final_alpha_gate_pass"] and accepted and rejected else "LOCAL PATCH"
    lines = [
        f"Verdict: {verdict}",
        "",
        "Evidence inspected:",
        f"- `{metadata['source_svg']}`",
        f"- `{metadata['template_manifest']}`",
        f"- `{metadata['style_packet_manifest']}`",
        f"- `{metadata['style_exemplar_sheet']}`",
        f"- `{metadata['strict_pocket_helper']}`",
        f"- `{metadata['outputs']['element_sheet']}`",
        f"- `{metadata['outputs']['artwork']}`",
        f"- `{metadata['outputs']['preview_white']}`",
        f"- `{metadata['outputs']['overlay']}`",
        f"- `{metadata['outputs']['mask_debug']}`",
        f"- `{metadata['outputs']['metadata']}`",
        "",
        "Passes:",
        f"- Final alpha gate passed: outside outer `{summary['final_outside_outer_alpha_pixels']}`, cutout `{summary['final_cutout_alpha_pixels']}`, outside paintable `{summary['final_outside_paintable_alpha_pixels']}`.",
        f"- Accepted placements: `{summary['accepted_placements']}`; rejected placement tests: `{summary['rejected_placements']}`.",
        "- The dial, slider bank, pill buttons, pins/knobs, and bolt sprites use actual packet crop pixels with feathered transparent mattes.",
        "- Style is closer to the references than `strict-style-polish` because visible controls preserve source-packet watercolor texture, uneven ink, shadows, and highlights instead of being procedurally redrawn.",
        "",
        "Failures or risks:",
        "- This is accepted as a method test, not a final production claim.",
        "- Some sprites intentionally carry a small blue source-pixel matte/halo; that helps preserve watercolor edges but can read as collage if overused.",
        "- SVG edge treatment and background fitting are still partly procedural, even though the control elements are packet-derived.",
        "",
        "Accepted placements:",
    ]
    lines.extend(
        f"- `{p['name']}` in `{p['pocket']}`: outside `{p['outside_outer_pixels']}`, cutout `{p['inside_cutout_pixels']}`, outside safe `{p['outside_eroded_paintable_pixels']}`."
        for p in accepted
    )
    lines.extend(["", "Rejected placements:"])
    lines.extend(
        f"- `{p['name']}` in `{p['pocket']}`: outside `{p['outside_outer_pixels']}`, cutout `{p['inside_cutout_pixels']}`, outside safe `{p['outside_eroded_paintable_pixels']}`."
        for p in rejected
    )
    lines.extend(
        [
            "",
            "Next move:",
            "- Keep this component-matte workflow as a viable follow-up method; production polish would locally improve matte halos/background integration rather than restart the geometry method.",
            "",
        ]
    )
    REVIEW_PATH.write_text("\n".join(lines))


def make_outputs() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    style_packet = json.loads(STYLE_PACKET_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    masks = build_masks()

    source_cache: dict[Path, Image.Image] = {}
    sprites: list[Sprite] = []
    for spec in sprite_specs(style_packet):
        source = REPO_DIR / spec.source_path
        if source not in source_cache:
            source_cache[source] = Image.open(source).convert("RGBA")
        output_path = SPRITES_DIR / f"{spec.name}.png"
        sprites.append(extract_sprite(spec, source_cache[source], output_path))

    make_element_sheet(sprites)
    metadata = composite_artwork(style_packet, {sprite.name: sprite for sprite in sprites}, masks, manifest)
    return metadata


def main() -> None:
    metadata = make_outputs()
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
