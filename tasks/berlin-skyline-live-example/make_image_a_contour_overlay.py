#!/usr/bin/env python3
"""Build SVG-contour overlay diagnostics for the latest Berlin Image A."""

from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TASK = Path("tasks/berlin-skyline-live-example")
SRC_IMAGE = Path(
    "/var/folders/0j/0fv2szdj15xg_wbgl96cbf_r0000gn/T/"
    "TemporaryItems/NSIRD_screencaptureui_qM2GMq/"
    "Screenshot 2026-06-16 at 23.43.53.png"
)
TEMPLATE_PREVIEW = TASK / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
REF_COPY = TASK / "refs/user-feedback/20260616-image-a-artwork-only.png"
OUT_DIR = TASK / "outputs/reviews/dimension-repair"


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = load_font(26)
SMALL_FONT = load_font(19)


def nonwhite_bbox(im: Image.Image, threshold: int = 32, pad: int = 0) -> tuple[int, int, int, int]:
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    delta = np.abs(rgb - 255).sum(axis=2)
    mask = delta > threshold
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    x0 = max(int(xs.min()) - pad, 0)
    y0 = max(int(ys.min()) - pad, 0)
    x1 = min(int(xs.max()) + 1 + pad, im.width)
    y1 = min(int(ys.max()) + 1 + pad, im.height)
    return (x0, y0, x1, y1)


def template_layers() -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    template = Image.open(TEMPLATE_PREVIEW).convert("RGBA")
    bbox = nonwhite_bbox(template, threshold=24, pad=8)
    crop = template.crop(bbox)
    rgb = np.asarray(crop.convert("RGB"), dtype=np.int16)

    nonwhite = np.abs(rgb - 255).sum(axis=2) > 30
    dark = (rgb[:, :, 0] < 85) & (rgb[:, :, 1] < 85) & (rgb[:, :, 2] < 85)

    contour = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    contour[dark] = (0, 92, 255, 245)

    guides = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    guides[nonwhite] = np.concatenate(
        [
            rgb[nonwhite].astype(np.uint8),
            np.full((int(nonwhite.sum()), 1), 205, dtype=np.uint8),
        ],
        axis=1,
    )

    return Image.fromarray(contour), Image.fromarray(guides), bbox


def resize_layer(layer: Image.Image, size: tuple[int, int]) -> Image.Image:
    return layer.resize(size, Image.Resampling.LANCZOS)


def label_canvas(title: str, body: str, image: Image.Image) -> Image.Image:
    pad = 26
    header_h = 94
    out = Image.new("RGB", (image.width + pad * 2, image.height + header_h + pad), "white")
    draw = ImageDraw.Draw(out)
    draw.text((pad, 18), title, font=FONT, fill=(25, 28, 33))
    draw.text((pad, 54), body, font=SMALL_FONT, fill=(80, 86, 94))
    out.paste(image.convert("RGB"), (pad, header_h))
    return out


def direct_overlay(
    art: Image.Image,
    contour: Image.Image,
    guides: Image.Image,
    art_bbox: tuple[int, int, int, int],
    svg_aspect: float,
    mode: str,
) -> Image.Image:
    x0, y0, x1, y1 = art_bbox
    art_w = x1 - x0
    art_h = y1 - y0

    if mode == "height":
        # Height-locked registration preserves the real SVG aspect and makes
        # width drift visible instead of hiding it by stretching the template.
        overlay_h = art_h
        overlay_w = round(overlay_h * svg_aspect)
        overlay_x = round((x0 + x1 - overlay_w) / 2)
        overlay_y = y0
        title = "Image A + exact SVG overlay, height locked"
        body = "SVG height matches detected artwork height; side overflow reveals aspect mismatch."
    elif mode == "width":
        overlay_w = art_w
        overlay_h = round(overlay_w / svg_aspect)
        overlay_x = x0
        overlay_y = round((y0 + y1 - overlay_h) / 2)
        title = "Image A + exact SVG overlay, width locked"
        body = "SVG width matches detected artwork width; vertical gap reveals extra height/water/placement drift."
    else:
        raise ValueError(f"unsupported overlay mode: {mode}")

    canvas = art.convert("RGBA")
    canvas.alpha_composite(resize_layer(guides, (overlay_w, overlay_h)), (overlay_x, overlay_y))
    canvas.alpha_composite(resize_layer(contour, (overlay_w, overlay_h)), (overlay_x, overlay_y))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 0, 0, 180), width=3)
    draw.rectangle(
        [overlay_x, overlay_y, overlay_x + overlay_w - 1, overlay_y + overlay_h - 1],
        outline=(0, 92, 255, 230),
        width=4,
    )
    return label_canvas(title, body, canvas)


def svg_aspect_registration(
    art: Image.Image,
    contour: Image.Image,
    guides: Image.Image,
    art_bbox: tuple[int, int, int, int],
    svg_aspect: float,
) -> Image.Image:
    x0, y0, x1, y1 = art_bbox
    crop = art.crop((x0, y0, x1, y1)).convert("RGBA")
    target_h = y1 - y0
    target_w = round(target_h * svg_aspect)
    registered = Image.new("RGBA", (target_w, target_h), "white")
    registered.alpha_composite(crop.resize((target_w, target_h), Image.Resampling.LANCZOS), (0, 0))
    registered.alpha_composite(resize_layer(guides, (target_w, target_h)), (0, 0))
    registered.alpha_composite(resize_layer(contour, (target_w, target_h)), (0, 0))
    return label_canvas(
        "Repair option 1 diagnostic: global SVG-aspect registration",
        "The artwork is globally compressed to the SVG content aspect before applying the true contour.",
        registered,
    )


def contour_only_overlay(
    art: Image.Image,
    contour: Image.Image,
    art_bbox: tuple[int, int, int, int],
    svg_aspect: float,
    mode: str,
    labelled: bool = True,
) -> Image.Image:
    x0, y0, x1, y1 = art_bbox
    art_w = x1 - x0
    art_h = y1 - y0
    if mode == "height":
        overlay_h = art_h
        overlay_w = round(overlay_h * svg_aspect)
        overlay_x = round((x0 + x1 - overlay_w) / 2)
        overlay_y = y0
        body = "Only the SVG black production contour is overlaid in blue; guide colors are hidden."
    elif mode == "width":
        overlay_w = art_w
        overlay_h = round(overlay_w / svg_aspect)
        overlay_x = x0
        overlay_y = round((y0 + y1 - overlay_h) / 2)
        body = "Width-locked contour-only view; useful for judging panel split and bottom-height mismatch."
    else:
        raise ValueError(f"unsupported contour mode: {mode}")
    canvas = art.convert("RGBA")
    canvas.alpha_composite(resize_layer(contour, (overlay_w, overlay_h)), (overlay_x, overlay_y))
    if not labelled:
        return canvas.convert("RGB")
    return label_canvas(
        "Image A + production contour only",
        body,
        canvas,
    )


def contact_sheet(images: list[Image.Image], captions: list[str]) -> Image.Image:
    thumb_w = 760
    gap = 28
    caption_h = 42
    thumbs = []
    for im in images:
        scale = thumb_w / im.width
        thumb_h = round(im.height * scale)
        thumbs.append(im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS))

    sheet_w = thumb_w * len(thumbs) + gap * (len(thumbs) + 1)
    sheet_h = max(t.height for t in thumbs) + caption_h + gap * 2
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
    draw = ImageDraw.Draw(sheet)
    x = gap
    for thumb, caption in zip(thumbs, captions):
        draw.text((x, gap), caption, font=SMALL_FONT, fill=(32, 36, 42))
        sheet.paste(thumb.convert("RGB"), (x, gap + caption_h))
        x += thumb_w + gap
    return sheet


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REF_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_IMAGE, REF_COPY)

    art = Image.open(REF_COPY).convert("RGBA")
    contour, guides, template_bbox = template_layers()
    svg_aspect = contour.width / contour.height
    art_bbox = nonwhite_bbox(art, threshold=34, pad=8)

    outputs = {
        "image-a-contour-only-overlay.png": contour_only_overlay(art, contour, art_bbox, svg_aspect, "height"),
        "image-a-contour-only-width-locked.png": contour_only_overlay(art, contour, art_bbox, svg_aspect, "width"),
        "image-a-clean-contour-only-width-locked.png": contour_only_overlay(
            art, contour, art_bbox, svg_aspect, "width", labelled=False
        ),
        "image-a-direct-svg-overlay-height-locked.png": direct_overlay(
            art, contour, guides, art_bbox, svg_aspect, "height"
        ),
        "image-a-direct-svg-overlay-width-locked.png": direct_overlay(
            art, contour, guides, art_bbox, svg_aspect, "width"
        ),
        "image-a-global-svg-aspect-registration.png": svg_aspect_registration(
            art, contour, guides, art_bbox, svg_aspect
        ),
    }

    for name, image in outputs.items():
        image.save(OUT_DIR / name)

    contact = contact_sheet(
        [
            outputs["image-a-contour-only-overlay.png"],
            outputs["image-a-contour-only-width-locked.png"],
            outputs["image-a-direct-svg-overlay-height-locked.png"],
            outputs["image-a-direct-svg-overlay-width-locked.png"],
            outputs["image-a-global-svg-aspect-registration.png"],
        ],
        [
            "A. contour only, height",
            "B. contour only, width",
            "C. full overlay, height",
            "D. full overlay, width",
            "E. option 1 registration",
        ],
    )
    contact.save(OUT_DIR / "image-a-overlay-contact-sheet.png")

    report = OUT_DIR / "image-a-overlay-report.md"
    x0, y0, x1, y1 = art_bbox
    tx0, ty0, tx1, ty1 = template_bbox
    report.write_text(
        "\n".join(
            [
                "# Image A Contour Overlay Report",
                "",
                f"- Source image copy: `{REF_COPY}`",
                f"- Template preview: `{TEMPLATE_PREVIEW}`",
                f"- Detected Image A artwork bbox: `{art_bbox}`",
                f"- Detected Image A artwork aspect: `{(x1 - x0) / (y1 - y0):.3f}`",
                f"- Template active bbox in preview: `{template_bbox}`",
                f"- Template active aspect: `{(tx1 - tx0) / (ty1 - ty0):.3f}`",
                "",
                "## Outputs",
                "",
                "- `image-a-contour-only-overlay.png`",
                "- `image-a-contour-only-width-locked.png`",
                "- `image-a-clean-contour-only-width-locked.png`",
                "- `image-a-direct-svg-overlay-height-locked.png`",
                "- `image-a-direct-svg-overlay-width-locked.png`",
                "- `image-a-global-svg-aspect-registration.png`",
                "- `image-a-overlay-contact-sheet.png`",
                "",
                "## Reading",
                "",
                "The direct overlay preserves the exact SVG aspect and makes dimension drift visible.",
                "The global SVG-aspect registration is a diagnostic for repair option 1, not final art approval.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"source_copy={REF_COPY}")
    print(f"art_bbox={art_bbox} art_aspect={(x1 - x0) / (y1 - y0):.3f}")
    print(f"template_bbox={template_bbox} template_aspect={(tx1 - tx0) / (ty1 - ty0):.3f}")
    for name in outputs:
        print(f"wrote={OUT_DIR / name}")
    print(f"wrote={OUT_DIR / 'image-a-overlay-contact-sheet.png'}")
    print(f"wrote={report}")


if __name__ == "__main__":
    main()
