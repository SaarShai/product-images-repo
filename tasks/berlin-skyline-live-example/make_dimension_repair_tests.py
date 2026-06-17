#!/usr/bin/env python3
"""Build dimension-repair tests from the user's best Berlin skyline option.

These outputs are review artifacts. They test whether the visually best
generated option can be structurally registered back to the authoritative SVG
template, and whether a restart map can keep the liked composition while using
the exact SVG proportions.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
BEST_PATH = ROOT / "refs/user-feedback/20260616-best-option-dimension-drift.png"
TEMPLATE_PREVIEW_PATH = ROOT / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
ELEMENTS_PATH = ROOT / "outputs/generated/20260616-berlin-elements-v2.png"
OUT_DIR = ROOT / "outputs/reviews/dimension-repair"


# SVG coordinate facts from source/template.svg. Keep these as explicit numbers
# so the review report shows the template is the authority, not the screenshot.
SVG_X_MIN = 1137.68
SVG_X_MAX = 7527.32
SVG_Y_MIN = 2350.15
SVG_Y_MAX = 6717.08
SVG_SEPARATOR_Y = 4094.78
SVG_LEFT_X1 = 1137.68
SVG_LEFT_X2 = 2781.78
SVG_CENTER_X1 = 2825.81
SVG_CENTER_X2 = 5846.45
SVG_RIGHT_X1 = 5883.22
SVG_RIGHT_X2 = 7527.32
SVG_SALOON_SPLIT_X = 4336.13


# Detected from the attached screenshot with dark vertical line projections.
SRC_CONTENT_BOX = (60, 41, 2770, 1513)
SRC_LEFT_PANEL = (62, 43, 776, 1510)
SRC_CENTER_PANEL = (776, 43, 2052, 1510)
SRC_RIGHT_PANEL = (2052, 43, 2767, 1510)
SRC_RED_SEPARATOR_Y = 758


CONTENT_W = 2214
CONTENT_H = round(CONTENT_W / ((SVG_X_MAX - SVG_X_MIN) / (SVG_Y_MAX - SVG_Y_MIN)))
CANVAS_W = CONTENT_W + 160
CANVAS_H = CONTENT_H + 190
CONTENT_X0 = 80
CONTENT_Y0 = 80


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    choices = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for choice in choices:
        try:
            return ImageFont.truetype(choice, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_HEAD = font(24, True)
F_BODY = font(18)
F_SMALL = font(15)


def svg_to_target(x: float, y: float) -> tuple[int, int]:
    sx = CONTENT_W / (SVG_X_MAX - SVG_X_MIN)
    sy = CONTENT_H / (SVG_Y_MAX - SVG_Y_MIN)
    return (round(CONTENT_X0 + (x - SVG_X_MIN) * sx), round(CONTENT_Y0 + (y - SVG_Y_MIN) * sy))


def svg_x(x: float) -> int:
    return svg_to_target(x, SVG_Y_MIN)[0]


def svg_y(y: float) -> int:
    return svg_to_target(SVG_X_MIN, y)[1]


def template_crop() -> Image.Image:
    template = Image.open(TEMPLATE_PREVIEW_PATH).convert("RGBA")
    arr = np.asarray(template.convert("RGB"))
    mask = (arr.min(axis=2) < 245) | ((255 - arr).sum(axis=2) > 40)
    ys, xs = np.where(mask)
    crop = template.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return crop.resize((CONTENT_W, CONTENT_H), Image.Resampling.LANCZOS)


def line_overlay() -> Image.Image:
    crop = template_crop()
    src = np.asarray(crop.convert("RGBA"))
    out = np.zeros_like(src)
    rgb = src[:, :, :3]
    alpha = src[:, :, 3]
    nonwhite = (alpha > 5) & ((rgb.min(axis=2) < 245) | ((255 - rgb).sum(axis=2) > 35))
    out[:, :, :3] = rgb
    out[:, :, 3] = np.where(nonwhite, np.minimum(235, alpha * 2), 0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def production_black_overlay() -> Image.Image:
    crop = template_crop()
    src = np.asarray(crop.convert("RGBA"))
    rgb = src[:, :, :3]
    alpha = src[:, :, 3]
    dark_neutral = (alpha > 5) & (rgb.max(axis=2) < 170) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 60)
    out = np.zeros_like(src)
    out[:, :, :3] = (28, 28, 26)
    out[:, :, 3] = np.where(dark_neutral, 220, 0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def base(title: str, subtitle: str) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((32, 24), title, font=F_TITLE, fill=(28, 29, 27))
    draw.text((34, 66), subtitle, font=F_BODY, fill=(70, 70, 66))
    return canvas


def paste_template(canvas: Image.Image, guides: Image.Image | None = None) -> None:
    canvas.alpha_composite(guides or line_overlay(), (CONTENT_X0, CONTENT_Y0))


def draw_dimension_markers(canvas: Image.Image) -> None:
    draw = ImageDraw.Draw(canvas, "RGBA")
    sep_y = svg_y(SVG_SEPARATOR_Y)
    draw.line((CONTENT_X0, sep_y, CONTENT_X0 + CONTENT_W, sep_y), fill=(0, 82, 255, 190), width=4)
    draw.text((CONTENT_X0 + 14, sep_y + 8), "exact SVG separator y", font=F_SMALL, fill=(0, 82, 255, 235))
    for x, label in [
        (svg_x(SVG_CENTER_X1), "center left edge"),
        (svg_x(SVG_CENTER_X2), "center right edge"),
        (svg_x(SVG_SALOON_SPLIT_X), "saloon split"),
    ]:
        draw.line((x, CONTENT_Y0, x, CONTENT_Y0 + CONTENT_H), fill=(0, 82, 255, 120), width=3)
        draw.text((x + 6, CONTENT_Y0 + 12), label, font=F_SMALL, fill=(0, 82, 255, 210))


def save(canvas: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(path, quality=95)
    return path


def option_baseline_overlay() -> Path:
    best = Image.open(BEST_PATH).convert("RGBA")
    crop = best.crop(SRC_CONTENT_BOX)

    canvas = base(
        "Diagnostic: Best Option vs Exact SVG Aspect",
        "Left is the attached option frame; right is the exact SVG target aspect at the same content height.",
    )
    # Build a wider comparison canvas.
    side_w = 1060
    side_h = round(side_w / (crop.width / crop.height))
    comp = Image.new("RGBA", (2360, 930), (255, 255, 255, 255))
    draw = ImageDraw.Draw(comp)
    draw.text((34, 24), "Attached/generated frame", font=F_HEAD, fill=(40, 40, 38))
    draw.text((1220, 24), "Exact SVG frame", font=F_HEAD, fill=(40, 40, 38))
    src_thumb = crop.resize((side_w, side_h), Image.Resampling.LANCZOS)
    comp.alpha_composite(src_thumb, (34, 72))
    tgt_h = side_h
    tgt_w = round(tgt_h * ((SVG_X_MAX - SVG_X_MIN) / (SVG_Y_MAX - SVG_Y_MIN)))
    template = template_crop().resize((tgt_w, tgt_h), Image.Resampling.LANCZOS)
    comp.alpha_composite(template, (1220, 72))
    draw = ImageDraw.Draw(comp)
    src_aspect = crop.width / crop.height
    svg_aspect = (SVG_X_MAX - SVG_X_MIN) / (SVG_Y_MAX - SVG_Y_MIN)
    draw.text((34, 72 + side_h + 16), f"generated aspect: {src_aspect:.3f}", font=F_BODY, fill=(60, 60, 55))
    draw.text((1220, 72 + tgt_h + 16), f"SVG aspect: {svg_aspect:.3f}", font=F_BODY, fill=(60, 60, 55))
    draw.text((34, 72 + side_h + 44), "Diagnosis: generated frame is too wide/squat.", font=F_BODY, fill=(170, 50, 45))
    out = OUT_DIR / "diagnostic-best-vs-svg-aspect.png"
    return save(comp, out)


def option_global_aspect() -> Path:
    best = Image.open(BEST_PATH).convert("RGBA")
    crop = best.crop(SRC_CONTENT_BOX)
    resized = crop.resize((CONTENT_W, CONTENT_H), Image.Resampling.LANCZOS)
    canvas = base(
        "Option 1: Global SVG-Aspect Registration",
        "The liked image is squeezed back to the exact SVG content aspect, then checked with exact template guides.",
    )
    canvas.alpha_composite(resized, (CONTENT_X0, CONTENT_Y0))
    paste_template(canvas)
    draw_dimension_markers(canvas)
    draw = ImageDraw.Draw(canvas)
    draw.text((34, CANVAS_H - 58), "Passes: overall SVG aspect. Fails/risk: distorts all artwork and still carries generated guide artifacts.", font=F_BODY, fill=(80, 80, 76))
    return save(canvas, OUT_DIR / "repair-option-1-global-svg-aspect.png")


def option_panel_remap() -> Path:
    best = Image.open(BEST_PATH).convert("RGBA")
    canvas = base(
        "Option 2: Panel-by-Panel Remap",
        "Each generated physical panel is remapped into the exact SVG panel boxes to test salvage by registration.",
    )
    content = Image.new("RGBA", (CONTENT_W, CONTENT_H), (255, 255, 255, 255))
    targets = [
        (SRC_LEFT_PANEL, (svg_x(SVG_LEFT_X1), CONTENT_Y0, svg_x(SVG_LEFT_X2), CONTENT_Y0 + CONTENT_H)),
        (SRC_CENTER_PANEL, (svg_x(SVG_CENTER_X1), CONTENT_Y0, svg_x(SVG_CENTER_X2), CONTENT_Y0 + CONTENT_H)),
        (SRC_RIGHT_PANEL, (svg_x(SVG_RIGHT_X1), CONTENT_Y0, svg_x(SVG_RIGHT_X2), CONTENT_Y0 + CONTENT_H)),
    ]
    # Target coordinates include canvas offset; convert for local content paste.
    for src_box, tgt_box_canvas in targets:
        x1, y1, x2, y2 = tgt_box_canvas
        tgt_box = (x1 - CONTENT_X0, y1 - CONTENT_Y0, x2 - CONTENT_X0, y2 - CONTENT_Y0)
        part = best.crop(src_box).resize((tgt_box[2] - tgt_box[0], tgt_box[3] - tgt_box[1]), Image.Resampling.LANCZOS)
        content.alpha_composite(part, (tgt_box[0], tgt_box[1]))
    canvas.alpha_composite(content, (CONTENT_X0, CONTENT_Y0))
    paste_template(canvas)
    draw_dimension_markers(canvas)
    draw = ImageDraw.Draw(canvas)
    draw.text((34, CANVAS_H - 58), "Passes: exact physical panel boxes. Fails/risk: seam discontinuities and warped landmarks at panel boundaries.", font=F_BODY, fill=(80, 80, 76))
    return save(canvas, OUT_DIR / "repair-option-2-panel-remap.png")


def transparent_crop(sheet: Image.Image, box: tuple[int, int, int, int], strength: float = 1.0) -> Image.Image:
    crop = sheet.crop(box).convert("RGB")
    crop = ImageEnhance.Contrast(crop).enhance(1.42)
    crop = ImageEnhance.Color(crop).enhance(1.08).convert("RGBA")
    arr = np.asarray(crop.convert("RGB")).astype(np.int16)
    dist = (255 - arr[:, :, 0]) + (255 - arr[:, :, 1]) + (255 - arr[:, :, 2])
    alpha = np.clip((dist - 12) * 10 * strength, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.35))
    crop.putalpha(alpha_img)
    return crop


def paste_fit(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int], anchor: str = "center") -> None:
    x1, y1, x2, y2 = box
    fitted = img.copy()
    fitted.thumbnail((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)
    x = x1 + (x2 - x1 - fitted.width) // 2
    if anchor == "bottom":
        y = y2 - fitted.height
    elif anchor == "top":
        y = y1
    else:
        y = y1 + (y2 - y1 - fitted.height) // 2
    canvas.alpha_composite(fitted, (x, y))


def option_svg_locked_map() -> Path:
    sheet = Image.open(ELEMENTS_PATH).convert("RGBA")
    parts = {
        "tv": transparent_crop(sheet, (40, 25, 165, 610), 1.3),
        "gate": transparent_crop(sheet, (185, 165, 625, 595), 1.3),
        "dom": transparent_crop(sheet, (610, 110, 960, 615), 1.25),
        "church": transparent_crop(sheet, (945, 105, 1155, 625), 1.25),
        "hotel": transparent_crop(sheet, (1160, 80, 1515, 625), 1.28),
        "train": transparent_crop(sheet, (55, 630, 825, 725), 1.25),
        "rail": transparent_crop(sheet, (55, 730, 835, 790), 1.15),
        "stone": transparent_crop(sheet, (55, 800, 835, 875), 1.1),
        "water": transparent_crop(sheet, (55, 890, 850, 990), 1.08),
        "bridge": transparent_crop(sheet, (875, 610, 1485, 885), 1.25),
    }

    canvas = base(
        "Option 3: SVG-Locked Restart Composition Map",
        "Rebuild the liked top-option composition inside the exact SVG proportions instead of fixing generated geometry.",
    )
    art = Image.new("RGBA", (CONTENT_W, CONTENT_H), (255, 255, 255, 0))
    def box(x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
        return (round(x1 * CONTENT_W), round(y1 * CONTENT_H), round(x2 * CONTENT_W), round(y2 * CONTENT_H))

    placements = [
        ("water", box(0.23, 0.80, 0.94, 0.94), "center"),
        ("stone", box(0.03, 0.76, 0.94, 0.86), "center"),
        ("rail", box(0.03, 0.71, 0.94, 0.78), "center"),
        ("train", box(0.02, 0.65, 0.68, 0.74), "center"),
        ("bridge", box(0.38, 0.56, 0.77, 0.76), "center"),
        ("tv", box(0.03, 0.05, 0.13, 0.60), "bottom"),
        ("gate", box(0.10, 0.44, 0.27, 0.64), "bottom"),
        ("dom", box(0.33, 0.13, 0.51, 0.59), "bottom"),
        ("church", box(0.55, 0.13, 0.70, 0.62), "bottom"),
        ("hotel", box(0.76, 0.15, 0.97, 0.67), "bottom"),
    ]
    for key, b, anchor in placements:
        paste_fit(art, parts[key], b, anchor)
    canvas.alpha_composite(art, (CONTENT_X0, CONTENT_Y0))

    # Draw the liked/adapted top contour idea, but in exact template scale.
    draw = ImageDraw.Draw(canvas, "RGBA")
    contour_points = [
        svg_to_target(SVG_LEFT_X1, 2720),
        svg_to_target(1500, 2500),
        svg_to_target(2050, 2960),
        svg_to_target(2825, 3030),
        svg_to_target(3700, 2405),
        svg_to_target(4500, 2460),
        svg_to_target(5250, 2920),
        svg_to_target(5883, 3050),
        svg_to_target(6420, 2670),
        svg_to_target(7527, 2820),
    ]
    draw.line(contour_points, fill=(42, 150, 65, 210), width=7, joint="curve")
    paste_template(canvas, production_black_overlay())
    draw_dimension_markers(canvas)
    draw.text((34, CANVAS_H - 58), "Passes: exact SVG aspect, separator, and panel boxes. Use this as a redraw map, not final art.", font=F_BODY, fill=(80, 80, 76))
    return save(canvas, OUT_DIR / "repair-option-3-svg-locked-composition-map.png")


def make_contact(paths: list[Path]) -> Path:
    thumbs: list[tuple[Path, Image.Image]] = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((760, 520), Image.Resampling.LANCZOS)
        thumbs.append((path, img))
    sheet = Image.new("RGB", (1580, 1820), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    draw.text((36, 28), "Berlin Skyline Dimension Repair Tests", font=F_TITLE, fill=(28, 29, 27))
    draw.text((38, 72), "Tests from user-approved visual direction back to exact SVG geometry.", font=F_BODY, fill=(70, 70, 66))
    positions = [(36, 130), (810, 130), (36, 720), (810, 720)]
    for (path, img), (x, y) in zip(thumbs, positions):
        draw.text((x, y), path.stem, font=F_HEAD, fill=(40, 40, 38))
        sheet.paste(img, (x, y + 34))
    out = OUT_DIR / "dimension-repair-contact-sheet.png"
    sheet.save(out, quality=95)
    return out


def write_report(paths: list[Path], contact: Path) -> Path:
    source_w = SRC_CONTENT_BOX[2] - SRC_CONTENT_BOX[0]
    source_h = SRC_CONTENT_BOX[3] - SRC_CONTENT_BOX[1]
    source_aspect = source_w / source_h
    svg_aspect = (SVG_X_MAX - SVG_X_MIN) / (SVG_Y_MAX - SVG_Y_MIN)
    width_factor = svg_aspect / source_aspect
    source_sep_ratio = (SRC_RED_SEPARATOR_Y - SRC_CONTENT_BOX[1]) / source_h
    svg_sep_ratio = (SVG_SEPARATOR_Y - SVG_Y_MIN) / (SVG_Y_MAX - SVG_Y_MIN)
    report = OUT_DIR / "dimension-repair-report.md"
    lines = [
        "# Berlin Skyline Dimension Repair Report",
        "",
        "Date: 2026-06-16",
        "",
        "## Diagnosis",
        "",
        f"- Attached/generated content aspect: `{source_aspect:.3f}`.",
        f"- Exact SVG content aspect: `{svg_aspect:.3f}`.",
        f"- To match SVG aspect at the same height, the generated frame needs about `{width_factor:.3f}x` horizontal scale.",
        f"- Generated red separator ratio from top: `{source_sep_ratio:.3f}`.",
        f"- Exact SVG top/bottom separator ratio from top: `{svg_sep_ratio:.3f}`.",
        "- Interpretation: the liked option is visually valuable, but it redrew the physical template too wide/squat and placed the bottom sub-panels too low.",
        "",
        "## Test Artifacts",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.relative_to(ROOT)}`")
    lines.append(f"- `{contact.relative_to(ROOT)}`")
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            "- Option 1 is useful as a quick proof that global aspect registration fixes the largest dimensional drift, but it distorts every building.",
            "- Option 2 is useful as a salvage test, but panel seams and local warping are likely too visible for final art.",
            "- Option 3 is the best next method: restart from the liked composition inside the exact SVG proportions, then ask the image model for artwork-only redraw while the SVG overlay remains locked outside the model output.",
        ]
    )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        option_baseline_overlay(),
        option_global_aspect(),
        option_panel_remap(),
        option_svg_locked_map(),
    ]
    contact = make_contact(paths)
    report = write_report(paths, contact)
    for path in [*paths, contact, report]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
