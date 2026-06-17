#!/usr/bin/env python3
"""Direct style-packet crop collage fitted into the top-temp SVG geometry.

This tests a crop-first alternative to the procedural strict-style-polish pass:
real packet crops provide the wash, edge texture, region detail, and accent
components; SVG-derived masks remain the geometry authority.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
REPO_DIR = TASK_DIR.parent.parent

SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"
STYLE_PACKET_PATH = TASK_DIR / "style-packet" / "style-packet.json"
STYLE_SHEET_PATH = TASK_DIR / "style-packet" / "style-exemplar-sheet.png"
STRICT_STYLE_METADATA_PATH = (
    TASK_DIR / "agents" / "strict-style-polish" / "strict-style-polish-metadata.json"
)

ARTWORK_PATH = OUT_DIR / "style-crop-collage-artwork.png"
PREVIEW_WHITE_PATH = OUT_DIR / "style-crop-collage-preview-white.png"
OVERLAY_PATH = OUT_DIR / "style-crop-collage-overlay.png"
MASK_DEBUG_PATH = OUT_DIR / "style-crop-collage-mask-debug.png"
METADATA_PATH = OUT_DIR / "style-crop-collage-metadata.json"
REVIEW_PATH = OUT_DIR / "review.md"

TOKEN_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
)


@dataclass(frozen=True)
class CropChoice:
    type: str
    label_contains: str


@dataclass(frozen=True)
class Placement:
    name: str
    crop_type: str
    label_contains: str
    box: tuple[int, int, int, int]
    pocket: str
    opacity: float
    mask_kind: str
    feather_px: float
    focus: tuple[float, float] = (0.5, 0.5)


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_DIR))


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def parse_viewbox(svg_text: str) -> tuple[float, float, float, float]:
    match = re.search(r'viewBox="([^"]+)"', svg_text)
    if not match:
        raise ValueError("SVG has no viewBox")
    values = [float(part) for part in re.split(r"[,\s]+", match.group(1).strip())]
    if len(values) != 4:
        raise ValueError(f"Unexpected viewBox: {match.group(1)}")
    return tuple(values)  # type: ignore[return-value]


def extract_path_data(svg_text: str) -> list[str]:
    paths = re.findall(r"<path\b[^>]*\sd=\"([^\"]+)\"", svg_text)
    if len(paths) < 3:
        raise ValueError(f"Expected at least 3 SVG paths, found {len(paths)}")
    return paths


def cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    return (
        mt * mt * mt * p0[0]
        + 3 * mt * mt * t * p1[0]
        + 3 * mt * t * t * p2[0]
        + t * t * t * p3[0],
        mt * mt * mt * p0[1]
        + 3 * mt * mt * t * p1[1]
        + 3 * mt * t * t * p2[1]
        + t * t * t * p3[1],
    )


def sample_svg_path(d: str, curve_steps: int = 32) -> list[tuple[float, float]]:
    tokens = TOKEN_RE.findall(d)
    points: list[tuple[float, float]] = []
    i = 0
    command = ""
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    last_cubic_ctrl: tuple[float, float] | None = None
    previous_command = ""

    def read_float() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    def has_number() -> bool:
        return i < len(tokens) and not is_command(tokens[i])

    while i < len(tokens):
        if is_command(tokens[i]):
            command = tokens[i]
            i += 1

        cmd = command
        absolute = cmd.isupper()
        op = cmd.upper()

        if op == "M":
            first = True
            while has_number():
                x, y = read_float(), read_float()
                if not absolute:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                if first:
                    start = current
                    first = False
                points.append(current)
                command = "L" if absolute else "l"
            last_cubic_ctrl = None
            previous_command = "M"
            continue

        if op == "L":
            while has_number():
                x, y = read_float(), read_float()
                if not absolute:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "L"
            continue

        if op == "H":
            while has_number():
                x = read_float()
                if not absolute:
                    x += current[0]
                current = (x, current[1])
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "H"
            continue

        if op == "V":
            while has_number():
                y = read_float()
                if not absolute:
                    y += current[1]
                current = (current[0], y)
                points.append(current)
            last_cubic_ctrl = None
            previous_command = "V"
            continue

        if op == "C":
            while has_number():
                x1, y1 = read_float(), read_float()
                x2, y2 = read_float(), read_float()
                x, y = read_float(), read_float()
                if not absolute:
                    x1 += current[0]
                    y1 += current[1]
                    x2 += current[0]
                    y2 += current[1]
                    x += current[0]
                    y += current[1]
                p0, p1, p2, p3 = current, (x1, y1), (x2, y2), (x, y)
                for step in range(1, curve_steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
            previous_command = "C"
            continue

        if op == "S":
            while has_number():
                x2, y2 = read_float(), read_float()
                x, y = read_float(), read_float()
                if previous_command in {"C", "S"} and last_cubic_ctrl is not None:
                    x1 = 2 * current[0] - last_cubic_ctrl[0]
                    y1 = 2 * current[1] - last_cubic_ctrl[1]
                else:
                    x1, y1 = current
                if not absolute:
                    x2 += current[0]
                    y2 += current[1]
                    x += current[0]
                    y += current[1]
                p0, p1, p2, p3 = current, (x1, y1), (x2, y2), (x, y)
                for step in range(1, curve_steps + 1):
                    points.append(cubic(p0, p1, p2, p3, step / curve_steps))
                current = p3
                last_cubic_ctrl = p2
            previous_command = "S"
            continue

        if op == "Q":
            while has_number():
                x1, y1 = read_float(), read_float()
                x, y = read_float(), read_float()
                if not absolute:
                    x1 += current[0]
                    y1 += current[1]
                    x += current[0]
                    y += current[1]
                p0, q, p3 = current, (x1, y1), (x, y)
                for step in range(1, curve_steps + 1):
                    t = step / curve_steps
                    mt = 1.0 - t
                    points.append(
                        (
                            mt * mt * p0[0] + 2 * mt * t * q[0] + t * t * p3[0],
                            mt * mt * p0[1] + 2 * mt * t * q[1] + t * t * p3[1],
                        )
                    )
                current = p3
                last_cubic_ctrl = None
            previous_command = "Q"
            continue

        if op == "Z":
            current = start
            points.append(start)
            last_cubic_ctrl = None
            previous_command = "Z"
            command = ""
            continue

        raise ValueError(f"Unsupported SVG path command: {cmd}")

    if points and points[0] != points[-1]:
        points.append(points[0])
    return points


def draw_polygon_mask(size: tuple[int, int], points: Iterable[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon([(round(x), round(y)) for x, y in points], fill=255)
    return mask


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def erode(mask: Image.Image, pixels: int) -> Image.Image:
    return mask.filter(ImageFilter.MinFilter(pixels * 2 + 1))


def dilate(mask: Image.Image, pixels: int) -> Image.Image:
    return mask.filter(ImageFilter.MaxFilter(pixels * 2 + 1))


def mask_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    return ImageChops.multiply(a.convert("L"), b.convert("L"))


def mask_subtract(a: Image.Image, b: Image.Image) -> Image.Image:
    return ImageChops.subtract(a.convert("L"), b.convert("L"))


def soften_mask(mask: Image.Image, blur_px: float, levels: float = 1.0) -> Image.Image:
    result = mask.convert("L")
    if blur_px > 0:
        result = result.filter(ImageFilter.GaussianBlur(blur_px))
    if levels != 1.0:
        arr = np.asarray(result).astype(np.float32) * levels
        result = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return result


def rounded_rect_mask(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    radius: int,
    base_mask: Image.Image,
    blur_px: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    mask = mask_multiply(mask, base_mask)
    return soften_mask(mask, blur_px)


def ellipse_mask(
    size: tuple[int, int],
    box: tuple[int, int, int, int],
    base_mask: Image.Image,
    blur_px: float,
) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    mask = mask_multiply(mask, base_mask)
    return soften_mask(mask, blur_px)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def crop_index(style_packet: dict) -> dict[str, list[dict]]:
    by_type: dict[str, list[dict]] = {}
    for crop in style_packet["crops"]:
        by_type.setdefault(crop["type"], []).append(crop)
    return by_type


def choose_crop(by_type: dict[str, list[dict]], crop_type: str, label_contains: str = "") -> dict:
    candidates = by_type.get(crop_type, [])
    if not candidates:
        raise ValueError(f"No crop of type {crop_type!r}")
    needle = label_contains.lower()
    if needle:
        for crop in candidates:
            if needle in crop["label"].lower() or needle in crop["path"].lower():
                return crop
    return candidates[0]


def load_crop(crop: dict) -> Image.Image:
    path = REPO_DIR / crop["path"]
    return Image.open(path).convert("RGBA")


def crop_to_box(image: Image.Image, size: tuple[int, int], focus: tuple[float, float]) -> Image.Image:
    image = image.convert("RGBA")
    image = ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(max(0.0, min(1.0, focus[0])), max(0.0, min(1.0, focus[1]))),
    )
    image = ImageEnhance.Color(image).enhance(1.04)
    return ImageEnhance.Contrast(image).enhance(1.03)


def non_white_mask(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGBA"))
    rgb = arr[..., :3].astype(np.int16)
    alpha = arr[..., 3]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    saturation = maxc - minc
    not_white = ~((rgb[..., 0] > 241) & (rgb[..., 1] > 241) & (rgb[..., 2] > 241))
    keep = not_white & (alpha > 0) & ((saturation > 8) | (maxc < 238))
    return Image.fromarray(keep.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))


def accent_content_mask(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGBA"))
    rgb = arr[..., :3].astype(np.int16)
    alpha = arr[..., 3]
    h, w = rgb.shape[:2]
    border = np.concatenate(
        [
            rgb[: max(1, h // 12), :, :].reshape(-1, 3),
            rgb[-max(1, h // 12) :, :, :].reshape(-1, 3),
            rgb[:, : max(1, w // 12), :].reshape(-1, 3),
            rgb[:, -max(1, w // 12) :, :].reshape(-1, 3),
        ],
        axis=0,
    )
    median_bg = np.median(border, axis=0)
    dist = np.sqrt(np.sum((rgb - median_bg) ** 2, axis=2))
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    saturation = maxc - minc
    red = (rgb[..., 0] > 165) & (rgb[..., 0] > rgb[..., 1] + 22) & (rgb[..., 0] > rgb[..., 2] + 16)
    yellow = (rgb[..., 0] > 170) & (rgb[..., 1] > 115) & (rgb[..., 2] < 145)
    mint = (rgb[..., 1] > 130) & (rgb[..., 2] > 110) & (rgb[..., 0] < 170)
    white_highlight = (maxc > 218) & (minc > 170) & (dist > 24)
    blue_panel = (
        (rgb[..., 2] > rgb[..., 0] + 18)
        & (rgb[..., 2] > rgb[..., 1] + 8)
        & (rgb[..., 1] > 70)
        & (rgb[..., 2] > 115)
    )
    keep = red | yellow | mint | white_highlight
    keep &= ~blue_panel
    keep &= alpha > 0
    keep &= ~((rgb[..., 0] > 244) & (rgb[..., 1] > 244) & (rgb[..., 2] > 244))
    mask = Image.fromarray(keep.astype(np.uint8) * 255)
    mask = mask.filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(2.6))
    return mask


def body_content_mask(image: Image.Image) -> Image.Image:
    mask = non_white_mask(image)
    return mask.filter(ImageFilter.GaussianBlur(1.5))


def content_mask(image: Image.Image, kind: str) -> Image.Image:
    if kind == "accent":
        return accent_content_mask(image)
    if kind in {"region", "edge"}:
        return non_white_mask(image).filter(ImageFilter.GaussianBlur(2.0))
    return body_content_mask(image)


def local_edge_fade(size: tuple[int, int], kind: str) -> Image.Image:
    width, height = size
    if kind == "accent":
        inset = max(3, min(width, height) // 24)
        blur_px = max(1.0, inset / 2)
    elif kind == "edge":
        inset = max(8, min(width, height) // 12)
        blur_px = max(3.0, inset / 1.5)
    else:
        inset = max(32, min(width, height) // 7)
        blur_px = max(18.0, inset / 1.25)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    box = (inset, inset, max(inset + 1, width - inset), max(inset + 1, height - inset))
    radius = max(12, min(width, height) // 8)
    draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(blur_px))


def apply_alpha(image: Image.Image, alpha: Image.Image) -> Image.Image:
    result = image.convert("RGBA").copy()
    result.putalpha(alpha.convert("L"))
    return result


def make_cover_layer(
    crop: dict,
    size: tuple[int, int],
    alpha_mask: Image.Image,
    opacity: float,
    mask_kind: str,
    focus: tuple[float, float] = (0.5, 0.5),
    blur_px: float = 0.0,
) -> tuple[Image.Image, dict]:
    local = crop_to_box(load_crop(crop), size, focus)
    if blur_px > 0:
        local = local.filter(ImageFilter.GaussianBlur(blur_px))
    local_content = content_mask(local, mask_kind)
    alpha = mask_multiply(local_content, alpha_mask)
    alpha_arr = np.asarray(alpha).astype(np.float32) * opacity
    alpha = Image.fromarray(np.clip(alpha_arr, 0, 255).astype(np.uint8))
    layer = apply_alpha(local, alpha)
    return layer, {
        "crop_label": crop["label"],
        "crop_type": crop["type"],
        "crop_path": crop["path"],
        "mask_kind": mask_kind,
        "opacity": opacity,
        "alpha_pixels": count_nonzero(alpha),
    }


def paste_patch(
    art: Image.Image,
    placement: Placement,
    crop: dict,
    pocket_mask: Image.Image,
    safe_mask: Image.Image,
    paintable_mask: Image.Image,
) -> tuple[Image.Image, dict, Image.Image]:
    x0, y0, x1, y1 = placement.box
    patch_size = (x1 - x0, y1 - y0)
    local_crop = crop_to_box(load_crop(crop), patch_size, placement.focus)
    source_alpha = content_mask(local_crop, placement.mask_kind)
    local_pocket = pocket_mask.crop(placement.box)
    if placement.feather_px > 0:
        source_alpha = source_alpha.filter(ImageFilter.GaussianBlur(placement.feather_px))
    source_alpha = mask_multiply(source_alpha, local_edge_fade(patch_size, placement.mask_kind))
    clipped_local_alpha = mask_multiply(source_alpha, local_pocket)
    clipped_arr = np.asarray(clipped_local_alpha).astype(np.float32) * placement.opacity
    clipped_local_alpha = Image.fromarray(np.clip(clipped_arr, 0, 255).astype(np.uint8))

    patch = Image.new("RGBA", art.size, (0, 0, 0, 0))
    patch_local = apply_alpha(local_crop, clipped_local_alpha)
    patch.alpha_composite(patch_local, dest=(x0, y0))

    patch_alpha = patch.getchannel("A")
    outside_safe = count_nonzero(mask_subtract(patch_alpha, safe_mask))
    outside_paintable = count_nonzero(mask_subtract(patch_alpha, paintable_mask))
    retained_source = count_nonzero(source_alpha)
    retained_final = count_nonzero(clipped_local_alpha)
    retained_ratio = retained_final / retained_source if retained_source else 0.0

    art = Image.alpha_composite(art, patch)
    metadata = {
        "name": placement.name,
        "pocket": placement.pocket,
        "crop_label": crop["label"],
        "crop_type": crop["type"],
        "crop_path": crop["path"],
        "box": list(placement.box),
        "opacity": placement.opacity,
        "mask_kind": placement.mask_kind,
        "feather_px": placement.feather_px,
        "source_alpha_pixels": retained_source,
        "retained_alpha_pixels": retained_final,
        "retained_alpha_ratio": round(retained_ratio, 4),
        "outside_safe_pixels_after_pocket_mask": outside_safe,
        "outside_paintable_pixels_after_pocket_mask": outside_paintable,
        "rectangular_artifact_risk": retained_ratio < 0.72 or placement.mask_kind == "region",
    }
    return art, metadata, patch_alpha


def draw_path_outline(
    layer: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int,
) -> None:
    coords = [(round(x), round(y)) for x, y in points]
    ImageDraw.Draw(layer, "RGBA").line(coords, fill=color, width=width, joint="curve")


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGBA")).copy()
    arr[arr[..., 3] == 0, :3] = 0
    return Image.fromarray(arr)


def build_masks() -> dict:
    svg_text = SVG_PATH.read_text()
    viewbox = parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    sampled_paths = [sample_svg_path(path_d) for path_d in extract_path_data(svg_text)[:3]]

    outer_mask = draw_polygon_mask(size, sampled_paths[0])
    path1_cutout_mask = draw_polygon_mask(size, sampled_paths[1])
    path2_cutout_mask = draw_polygon_mask(size, sampled_paths[2])
    cutouts_mask = ImageChops.lighter(path1_cutout_mask, path2_cutout_mask)
    paintable_mask = mask_subtract(outer_mask, cutouts_mask)
    safe_mask = erode(paintable_mask, 20)

    return {
        "viewbox": viewbox,
        "size": size,
        "sampled_paths": sampled_paths,
        "outer_mask": outer_mask,
        "path1_cutout_mask": path1_cutout_mask,
        "path2_cutout_mask": path2_cutout_mask,
        "cutouts_mask": cutouts_mask,
        "paintable_mask": paintable_mask,
        "safe_mask": safe_mask,
    }


def build_pocket_masks(size: tuple[int, int], safe_mask: Image.Image) -> dict[str, Image.Image]:
    pockets = {
        "upper-left tall bay above the left shoulder of the slot": rounded_rect_mask(
            size, (70, 72, 755, 575), 92, safe_mask, 24
        ),
        "middle-left field below/left of the diagonal slot": rounded_rect_mask(
            size, (76, 590, 780, 1058), 70, safe_mask, 26
        ),
        "lower-left base bay above the bottom notch": rounded_rect_mask(
            size, (62, 1052, 665, 1492), 76, safe_mask, 24
        ),
        "lower-middle bay between the bottom notch and the right cutouts": rounded_rect_mask(
            size, (730, 1030, 1338, 1490), 72, safe_mask, 24
        ),
        "right vertical strip between the diagonal slot and outer edge": rounded_rect_mask(
            size, (1368, 1010, 1578, 1480), 54, safe_mask, 20
        ),
        "lower-left gauge oval": ellipse_mask(size, (225, 1095, 680, 1495), safe_mask, 18),
    }
    return pockets


def make_collage() -> tuple[Image.Image, dict, list[Image.Image]]:
    manifest = load_json(MANIFEST_PATH)
    style_packet = load_json(STYLE_PACKET_PATH)
    by_type = crop_index(style_packet)
    masks = build_masks()
    size = masks["size"]
    paintable_mask = masks["paintable_mask"]
    safe_mask = masks["safe_mask"]
    cutouts_mask = masks["cutouts_mask"]
    path1_cutout_mask = masks["path1_cutout_mask"]
    path2_cutout_mask = masks["path2_cutout_mask"]
    pocket_masks = build_pocket_masks(size, safe_mask)

    art = Image.new("RGBA", size, (0, 0, 0, 0))
    operations: list[dict] = []
    debug_patch_masks: list[Image.Image] = []

    body_1 = choose_crop(by_type, "body-texture", "ref 1")
    body_2 = choose_crop(by_type, "body-texture", "ref 2")
    full_1 = choose_crop(by_type, "full-panel", "ref 1")
    full_2 = choose_crop(by_type, "full-panel", "ref 2")

    body_layer_1, meta = make_cover_layer(body_1, size, paintable_mask, 0.92, "body", (0.35, 0.52), 0.0)
    meta["name"] = "base crop wash from ref 1 body texture"
    operations.append(meta)
    art = Image.alpha_composite(art, body_layer_1)

    body_layer_2, meta = make_cover_layer(body_2, size, paintable_mask, 0.42, "body", (0.66, 0.47), 0.0)
    meta["name"] = "secondary crop wash from ref 2 body texture"
    operations.append(meta)
    art = Image.alpha_composite(art, body_layer_2)

    full_wash_mask = soften_mask(paintable_mask, 3)
    full_layer, meta = make_cover_layer(full_1, size, full_wash_mask, 0.05, "region", (0.5, 0.5), 42.0)
    meta["name"] = "blurred full-panel color inheritance wash"
    operations.append(meta)
    art = Image.alpha_composite(art, full_layer)

    edge_ring = mask_multiply(mask_subtract(masks["outer_mask"], erode(masks["outer_mask"], 34)), paintable_mask)
    cutout_ring = mask_multiply(mask_subtract(dilate(cutouts_mask, 20), cutouts_mask), paintable_mask)
    edge_mask = ImageChops.lighter(edge_ring, cutout_ring).filter(ImageFilter.GaussianBlur(2.0))
    edge_crop = choose_crop(by_type, "edge-treatment", "ref 2")
    edge_layer, meta = make_cover_layer(edge_crop, size, edge_mask, 0.62, "edge", (0.2, 0.24), 0.0)
    meta["name"] = "edge-treatment crop ring for outer and cutout ink bloom"
    operations.append(meta)
    art = Image.alpha_composite(art, edge_layer)

    placements = [
        Placement(
            "upper-left ref2 region wash with knob vocabulary",
            "left-region",
            "ref 2",
            (65, 74, 758, 575),
            "upper-left tall bay above the left shoulder of the slot",
            0.14,
            "region",
            5.0,
            (0.36, 0.48),
        ),
        Placement(
            "middle-left ref1 slider region",
            "left-region",
            "ref 1",
            (92, 588, 764, 1056),
            "middle-left field below/left of the diagonal slot",
            0.24,
            "region",
            6.0,
            (0.46, 0.58),
        ),
        Placement(
            "lower-left cropped gauge region",
            "left-region",
            "ref 2",
            (130, 1058, 690, 1492),
            "lower-left gauge oval",
            0.24,
            "region",
            5.5,
            (0.35, 0.50),
        ),
        Placement(
            "lower-middle ref1 large button region",
            "center-region",
            "ref 1",
            (780, 1038, 1282, 1488),
            "lower-middle bay between the bottom notch and the right cutouts",
            0.28,
            "region",
            5.0,
            (0.48, 0.52),
        ),
        Placement(
            "right strip ref1 line and gauge texture",
            "right-region",
            "ref 1",
            (1356, 1020, 1582, 1480),
            "right vertical strip between the diagonal slot and outer edge",
            0.16,
            "region",
            7.0,
            (0.86, 0.54),
        ),
        Placement(
            "upper-left yellow standing pin",
            "accent-component",
            "ref 2 accent component 01",
            (470, 135, 568, 330),
            "upper-left tall bay above the left shoulder of the slot",
            0.96,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "upper-left red standing pin",
            "accent-component",
            "ref 2 accent component 02",
            (365, 160, 465, 350),
            "upper-left tall bay above the left shoulder of the slot",
            0.92,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "upper-left teal standing pin",
            "accent-component",
            "ref 2 accent component 04",
            (582, 155, 682, 350),
            "upper-left tall bay above the left shoulder of the slot",
            0.90,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "middle-left yellow pill crop",
            "accent-component",
            "ref 1 accent component 04",
            (176, 700, 454, 775),
            "middle-left field below/left of the diagonal slot",
            0.95,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "middle-left orange pill crop",
            "accent-component",
            "ref 1 accent component 05",
            (205, 802, 510, 880),
            "middle-left field below/left of the diagonal slot",
            0.95,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "middle-left coral pill crop",
            "accent-component",
            "ref 1 accent component 07",
            (154, 905, 468, 984),
            "middle-left field below/left of the diagonal slot",
            0.95,
            "accent",
            0.8,
            (0.5, 0.5),
        ),
        Placement(
            "lower-middle red large button crop",
            "accent-component",
            "ref 1 accent component 01",
            (930, 1095, 1234, 1188),
            "lower-middle bay between the bottom notch and the right cutouts",
            0.95,
            "accent",
            0.9,
            (0.5, 0.5),
        ),
        Placement(
            "lower-middle mint large button crop",
            "accent-component",
            "ref 1 accent component 03",
            (904, 1212, 1270, 1318),
            "lower-middle bay between the bottom notch and the right cutouts",
            0.95,
            "accent",
            0.9,
            (0.5, 0.5),
        ),
        Placement(
            "lower-middle yellow large button crop",
            "accent-component",
            "ref 1 accent component 02",
            (910, 1350, 1248, 1450),
            "lower-middle bay between the bottom notch and the right cutouts",
            0.95,
            "accent",
            0.9,
            (0.5, 0.5),
        ),
        Placement(
            "right-strip screw corner crop",
            "edge-treatment",
            "ref 2",
            (1422, 1082, 1578, 1250),
            "right vertical strip between the diagonal slot and outer edge",
            0.34,
            "edge",
            1.5,
            (0.86, 0.12),
        ),
    ]

    placement_meta: list[dict] = []
    for placement in placements:
        crop = choose_crop(by_type, placement.crop_type, placement.label_contains)
        pocket_mask = pocket_masks[placement.pocket]
        art, meta, patch_alpha = paste_patch(
            art,
            placement,
            crop,
            pocket_mask,
            safe_mask,
            paintable_mask,
        )
        placement_meta.append(meta)
        debug_patch_masks.append(patch_alpha)

    line_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    sampled_paths = masks["sampled_paths"]
    draw_path_outline(line_layer, sampled_paths[0], (15, 67, 139, 205), 11)
    draw_path_outline(line_layer, sampled_paths[0], (204, 233, 255, 80), 4)
    for points in sampled_paths[1:3]:
        draw_path_outline(line_layer, points, (14, 63, 129, 205), 10)
        draw_path_outline(line_layer, points, (230, 245, 255, 85), 4)
    line_layer.putalpha(mask_multiply(line_layer.getchannel("A"), paintable_mask))
    art = Image.alpha_composite(art, line_layer)

    final_alpha = mask_multiply(art.getchannel("A"), paintable_mask)
    art.putalpha(final_alpha)
    art = clear_transparent_rgb(art)

    outside_outer_alpha = count_nonzero(mask_subtract(art.getchannel("A"), masks["outer_mask"]))
    outside_paintable_alpha = count_nonzero(mask_subtract(art.getchannel("A"), paintable_mask))
    path1_alpha = count_nonzero(mask_multiply(art.getchannel("A"), path1_cutout_mask))
    path2_alpha = count_nonzero(mask_multiply(art.getchannel("A"), path2_cutout_mask))
    cutout_alpha = count_nonzero(mask_multiply(art.getchannel("A"), cutouts_mask))
    risky_regions = [p for p in placement_meta if p["rectangular_artifact_risk"]]

    strict_style = load_json(STRICT_STYLE_METADATA_PATH) if STRICT_STYLE_METADATA_PATH.exists() else {}
    metadata = {
        "workflow": "style-crop-collage-direct-packet-crops",
        "source_svg": repo_rel(SVG_PATH),
        "template_manifest": repo_rel(MANIFEST_PATH),
        "style_packet": repo_rel(STYLE_PACKET_PATH),
        "style_exemplar_sheet": repo_rel(STYLE_SHEET_PATH),
        "baseline_for_comparison": repo_rel(STRICT_STYLE_METADATA_PATH)
        if STRICT_STYLE_METADATA_PATH.exists()
        else None,
        "manifest_status": manifest.get("status"),
        "viewbox": list(masks["viewbox"]),
        "canvas_size_px": list(size),
        "path_roles": {
            "path[0]": "outer material contour",
            "path[1]": "large diagonal rounded slot keep-clear",
            "path[2]": "lower-right round/bolt-like keep-clear",
        },
        "mask_pixels": {
            "outer_pixels": count_nonzero(masks["outer_mask"]),
            "path1_cutout_pixels": count_nonzero(path1_cutout_mask),
            "path2_cutout_pixels": count_nonzero(path2_cutout_mask),
            "combined_cutout_pixels": count_nonzero(cutouts_mask),
            "paintable_pixels": count_nonzero(paintable_mask),
            "eroded_safe_pixels": count_nonzero(safe_mask),
        },
        "safe_pocket_plan": manifest.get("safe_pockets", []),
        "no_focal_motif_zones": manifest.get("no_focal_motif_zones", []),
        "crop_source_operations": operations,
        "placements": placement_meta,
        "summary": {
            "body_crop_layers": 3,
            "edge_crop_layers": 1,
            "pocket_placements": len(placement_meta),
            "placements_with_rectangular_artifact_risk": len(risky_regions),
            "final_outside_outer_alpha_pixels": outside_outer_alpha,
            "final_path1_cutout_alpha_pixels": path1_alpha,
            "final_path2_cutout_alpha_pixels": path2_alpha,
            "final_cutout_alpha_pixels": cutout_alpha,
            "final_outside_paintable_alpha_pixels": outside_paintable_alpha,
            "strict_style_polish_final_cutout_alpha_pixels": strict_style.get("summary", {}).get(
                "final_cutout_alpha_pixels"
            ),
            "strict_style_polish_final_outside_paintable_alpha_pixels": strict_style.get(
                "summary", {}
            ).get("final_outside_paintable_alpha_pixels"),
        },
        "comparison_to_strict_style_polish": [
            "This method inherits real packet crop texture and hardware shapes more directly than strict-style-polish.",
            "Strict-style-polish is visually cleaner and more internally coherent because every component was redrawn for the geometry.",
            "The crop collage has stronger reference DNA but more visible scale/perspective mismatch and potential soft rectangular seams.",
        ],
        "visual_risks": [
            "Feathered region crops can leave subtle rectangular value shifts, especially in the middle-left and lower-middle pockets.",
            "Some component crops retain source lighting and scale that do not fully agree with adjacent pocket texture.",
            "The exact SVG guardrail clears alpha perfectly, but crop-derived motifs close to pocket masks can still look locally clipped.",
        ],
        "outputs": {
            "artwork": ARTWORK_PATH.name,
            "preview_white": PREVIEW_WHITE_PATH.name,
            "overlay": OVERLAY_PATH.name,
            "mask_debug": MASK_DEBUG_PATH.name,
            "metadata": METADATA_PATH.name,
            "review": REVIEW_PATH.name,
        },
        "method_notes": [
            "All source imagery comes from style-packet crops: full/body/edge/region/accent crop types are used.",
            "White crop margins are removed from region and edge crops before feathered pocket placement.",
            "Accent crops use a foreground mask against their border color so colored controls transfer without most blue source rectangles.",
            "The final SVG paintable mask is used only as an exact alpha export guardrail after crop-aware pocket composition.",
        ],
    }
    return art, metadata, debug_patch_masks


def make_preview_white(art: Image.Image) -> Image.Image:
    preview = Image.new("RGBA", art.size, (255, 255, 255, 255))
    preview.alpha_composite(art)
    return preview.convert("RGB")


def make_overlay(art: Image.Image) -> Image.Image:
    masks = build_masks()
    overlay = make_preview_white(art).convert("RGBA")
    draw_path_outline(overlay, masks["sampled_paths"][0], (255, 214, 69, 255), 7)
    draw_path_outline(overlay, masks["sampled_paths"][1], (255, 73, 73, 235), 7)
    draw_path_outline(overlay, masks["sampled_paths"][2], (255, 73, 73, 235), 7)
    d = ImageDraw.Draw(overlay, "RGBA")
    d.rectangle((0, 0, art.size[0] - 1, art.size[1] - 1), outline=(48, 48, 48, 85), width=2)
    d.text((24, 22), "yellow=outer contour, red=SVG cutouts", fill=(0, 0, 0, 210))
    return overlay


def make_mask_debug(metadata: dict, patch_masks: list[Image.Image]) -> Image.Image:
    masks = build_masks()
    size = masks["size"]
    paintable_mask = masks["paintable_mask"]
    cutouts_mask = masks["cutouts_mask"]
    safe_mask = masks["safe_mask"]
    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 92),
                Image.new("L", size, 169),
                Image.new("L", size, 235),
                paintable_mask.point(lambda p: 210 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 255),
                Image.new("L", size, 70),
                Image.new("L", size, 70),
                cutouts_mask.point(lambda p: 230 if p else 0),
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 58),
                Image.new("L", size, 224),
                Image.new("L", size, 116),
                safe_mask.point(lambda p: 60 if p else 0),
            ),
        )
    )
    colors = [
        (230, 54, 168),
        (255, 160, 35),
        (40, 40, 40),
        (116, 62, 230),
        (20, 180, 190),
    ]
    for idx, patch_mask in enumerate(patch_masks):
        r, g, b = colors[idx % len(colors)]
        debug.alpha_composite(
            Image.merge(
                "RGBA",
                (
                    Image.new("L", size, r),
                    Image.new("L", size, g),
                    Image.new("L", size, b),
                    patch_mask.point(lambda p: min(145, p) if p else 0),
                ),
            )
        )
    d = ImageDraw.Draw(debug, "RGBA")
    d.text(
        (24, 22),
        "blue=paintable, red=cutouts, green=eroded safe mask, colored=actual crop patch alpha",
        fill=(0, 0, 0, 220),
    )
    d.text(
        (24, 54),
        f"forbidden alpha: outside={metadata['summary']['final_outside_paintable_alpha_pixels']} "
        f"cutouts={metadata['summary']['final_cutout_alpha_pixels']}",
        fill=(0, 0, 0, 220),
    )
    return debug


def write_review(metadata: dict) -> None:
    summary = metadata["summary"]
    output_paths = {
        key: repo_rel(OUT_DIR / value)
        for key, value in metadata["outputs"].items()
        if key != "review"
    }
    review = f"""Verdict: LOCAL PATCH

Evidence inspected:
- `{metadata["source_svg"]}`
- `{metadata["template_manifest"]}`
- `{metadata["style_packet"]}`
- `{metadata["style_exemplar_sheet"]}`
- `{output_paths["artwork"]}`
- `{output_paths["preview_white"]}`
- `{output_paths["overlay"]}`
- `{output_paths["mask_debug"]}`
- `{output_paths["metadata"]}`
- `tasks/top-temp-workflow-test/agents/strict-style-polish/strict-style-polish-artwork.png`
- `tasks/top-temp-workflow-test/agents/strict-style-polish/strict-style-polish-metadata.json`

Passes:
- Final geometry gate is clean: outside-paintable alpha pixels = {summary["final_outside_paintable_alpha_pixels"]}, path[1] cutout alpha pixels = {summary["final_path1_cutout_alpha_pixels"]}, path[2] cutout alpha pixels = {summary["final_path2_cutout_alpha_pixels"]}.
- The candidate uses real style-packet crops across all requested families: full-panel wash, body texture, edge treatment, left/center/right region crops, and accent-component crops.
- Feathered pocket masks and accent foreground extraction keep most source crop rectangles from landing as hard boxes.
- Compared with strict-style-polish, this visibly carries more of the reference crop texture and actual rounded-button/pin vocabulary.

Failures or risks:
- This is not as cohesive as direct procedural strict-style-polish; crop lighting, scale, and perspective vary between pockets.
- {summary["placements_with_rectangular_artifact_risk"]} region placements are marked as rectangular-artifact risks because broad source regions can leave subtle value seams even after feathering.
- Some accents inherit their original blue crop surroundings in softened form, so a production version would need either stronger foreground extraction or generated isolated elements.

Next move:
- Keep strict-style-polish as the cleaner production baseline, but use this crop-collage method as a style-recovery patch source or as input to an elements-first style agent; do not replace the accepted procedural baseline without a seam cleanup pass.
"""
    REVIEW_PATH.write_text(review)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art, metadata, patch_masks = make_collage()
    preview_white = make_preview_white(art)
    overlay = make_overlay(art)
    mask_debug = make_mask_debug(metadata, patch_masks)

    art.save(ARTWORK_PATH)
    preview_white.save(PREVIEW_WHITE_PATH)
    overlay.save(OVERLAY_PATH)
    mask_debug.save(MASK_DEBUG_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n")
    write_review(metadata)
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
