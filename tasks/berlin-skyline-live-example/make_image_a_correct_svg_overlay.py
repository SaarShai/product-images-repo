#!/usr/bin/env python3
"""Create a clean, SVG-dimension-locked overlay for Berlin Image A.

This fixes the diagnostic-only overlays that let a raster template preview or
dense-art registration decide the guide dimensions. The source SVG coordinate
facts remain the authority for aspect and panel ratios.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TASK = Path("tasks/berlin-skyline-live-example")
ART_PATH = TASK / "refs/user-feedback/20260616-image-a-artwork-only.png"
TEMPLATE_PREVIEW = TASK / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
OUT_DIR = TASK / "outputs/reviews/dimension-repair"

# Exact visible template bounds from source/template.svg, previously extracted
# from the authoritative SVG for the dimension-repair diagnostics.
SVG_X_MIN = 1137.68
SVG_X_MAX = 7527.32
SVG_Y_MIN = 2350.15
SVG_Y_MAX = 6717.08
SVG_ASPECT = (SVG_X_MAX - SVG_X_MIN) / (SVG_Y_MAX - SVG_Y_MIN)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE = font(30, True)
BODY = font(18)
SMALL = font(15)


def nonwhite_bbox(im: Image.Image, threshold: int = 34, pad: int = 0) -> tuple[int, int, int, int]:
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    delta = np.abs(rgb - 255).sum(axis=2)
    mask = delta > threshold
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    return (
        max(int(xs.min()) - pad, 0),
        max(int(ys.min()) - pad, 0),
        min(int(xs.max()) + 1 + pad, im.width),
        min(int(ys.max()) + 1 + pad, im.height),
    )


def guide_layer() -> tuple[Image.Image, tuple[int, int, int, int], float]:
    template = Image.open(TEMPLATE_PREVIEW).convert("RGBA")
    bbox = nonwhite_bbox(template, threshold=24, pad=8)
    crop = template.crop(bbox)
    src = np.asarray(crop.convert("RGBA"))
    rgb = src[:, :, :3]
    alpha = src[:, :, 3]
    nonwhite = (alpha > 5) & (np.abs(rgb.astype(np.int16) - 255).sum(axis=2) > 30)

    layer = np.zeros_like(src)
    layer[:, :, :3] = rgb
    layer[:, :, 3] = np.where(nonwhite, 220, 0).astype(np.uint8)
    preview_aspect = crop.width / crop.height
    return Image.fromarray(layer), bbox, preview_aspect


def place_width_centered(art_bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = art_bbox
    overlay_w = x1 - x0
    overlay_h = round(overlay_w / SVG_ASPECT)
    overlay_x = x0
    overlay_y = round(y0 + ((y1 - y0) - overlay_h) / 2)
    return (overlay_x, overlay_y, overlay_x + overlay_w, overlay_y + overlay_h)


def overlay_art(
    art: Image.Image,
    guides: Image.Image,
    overlay_box: tuple[int, int, int, int],
    draw_boxes: bool,
) -> Image.Image:
    x0, y0, x1, y1 = overlay_box
    out = art.convert("RGBA")
    resized = guides.resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
    out.alpha_composite(resized, (x0, y0))

    if draw_boxes:
        draw = ImageDraw.Draw(out, "RGBA")
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(0, 92, 255, 230), width=3)
    return out


def labelled_canvas(
    image: Image.Image,
    title: str,
    body: str,
    art_bbox: tuple[int, int, int, int],
    overlay_box: tuple[int, int, int, int],
) -> Image.Image:
    pad = 28
    header_h = 116
    out = Image.new("RGB", (image.width + pad * 2, image.height + header_h + pad), "white")
    draw = ImageDraw.Draw(out)
    draw.text((pad, 20), title, font=TITLE, fill=(24, 27, 32))
    draw.text((pad, 60), body, font=BODY, fill=(70, 76, 84))
    draw.text(
        (pad, 86),
        f"art bbox={art_bbox} | overlay box={overlay_box} | exact SVG aspect={SVG_ASPECT:.3f}",
        font=SMALL,
        fill=(88, 94, 102),
    )
    out.paste(image.convert("RGB"), (pad, header_h))
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art = Image.open(ART_PATH).convert("RGBA")
    art_bbox = nonwhite_bbox(art, threshold=34, pad=8)
    guides, template_bbox, preview_aspect = guide_layer()
    overlay_box = place_width_centered(art_bbox)

    clean = overlay_art(art, guides, overlay_box, draw_boxes=False)
    diagnostic_base = overlay_art(art, guides, overlay_box, draw_boxes=True)
    draw = ImageDraw.Draw(diagnostic_base, "RGBA")
    draw.rectangle(art_bbox, outline=(237, 28, 36, 190), width=3)

    clean_path = OUT_DIR / "image-a-correct-svg-overlay-clean.png"
    diagnostic_path = OUT_DIR / "image-a-correct-svg-overlay-diagnostic.png"
    report_path = OUT_DIR / "image-a-correct-svg-overlay-report.md"

    clean.convert("RGB").save(clean_path)
    labelled_canvas(
        diagnostic_base,
        "Image A + Correct SVG Overlay",
        "Full guide overlay scaled from exact SVG content aspect, not from the square PNG preview.",
        art_bbox,
        overlay_box,
    ).save(diagnostic_path)

    report_path.write_text(
        "\n".join(
            [
                "# Image A Correct SVG Overlay Report",
                "",
                f"- Artwork: `{ART_PATH}`",
                f"- Template SVG: `{TASK / 'source/template.svg'}`",
                f"- Template preview used only for guide pixels: `{TEMPLATE_PREVIEW}`",
                f"- Template preview active bbox: `{template_bbox}`",
                f"- Template preview active aspect: `{preview_aspect:.3f}`",
                f"- Exact SVG coordinate bounds: `({SVG_X_MIN}, {SVG_Y_MIN})` to `({SVG_X_MAX}, {SVG_Y_MAX})`",
                f"- Exact SVG content aspect: `{SVG_ASPECT:.3f}`",
                f"- Detected artwork bbox: `{art_bbox}`",
                f"- Correct overlay box: `{overlay_box}`",
                "",
                "## Outputs",
                "",
                f"- Clean overlay: `{clean_path}`",
                f"- Diagnostic overlay: `{diagnostic_path}`",
                "",
                "## Interpretation",
                "",
                "This overlay preserves the real SVG proportions. The square PNG preview is used only as a source for visible guide strokes.",
                "If the user wants this same overlay on a newer generated artwork, that candidate must be available as a local image file first.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"art_bbox={art_bbox}")
    print(f"template_preview_bbox={template_bbox} preview_aspect={preview_aspect:.3f}")
    print(f"svg_aspect={SVG_ASPECT:.3f}")
    print(f"overlay_box={overlay_box}")
    print(f"wrote={clean_path}")
    print(f"wrote={diagnostic_path}")
    print(f"wrote={report_path}")


if __name__ == "__main__":
    main()
