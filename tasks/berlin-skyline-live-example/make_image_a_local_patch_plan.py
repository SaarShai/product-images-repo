#!/usr/bin/env python3
"""Create an SVG-locked local-patch plan for Berlin Image A.

This is a review artifact, not final production art. It registers the exact SVG
overlay to the dense landmark mass in Image A and marks the bounded cleanup
zones that remain after the geometry audit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TASK = Path("tasks/berlin-skyline-live-example")
IMAGE_A = TASK / "refs/user-feedback/20260616-image-a-artwork-only.png"
TEMPLATE_PREVIEW = TASK / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
OUT_DIR = TASK / "outputs/reviews/dimension-repair"


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


TITLE = font(31, True)
HEAD = font(22, True)
BODY = font(18)
SMALL = font(15)


def nonwhite_bbox(im: Image.Image, threshold: int = 24, pad: int = 0) -> tuple[int, int, int, int]:
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    mask = np.abs(rgb - 255).sum(axis=2) > threshold
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    return (
        max(int(xs.min()) - pad, 0),
        max(int(ys.min()) - pad, 0),
        min(int(xs.max()) + 1 + pad, im.width),
        min(int(ys.max()) + 1 + pad, im.height),
    )


def dense_bbox(im: Image.Image) -> tuple[int, int, int, int]:
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    strong = np.abs(rgb - 255).sum(axis=2) > 100
    col = strong.sum(axis=0)
    row = strong.sum(axis=1)
    xs = np.where(col > im.height * 0.01)[0]
    ys = np.where(row > im.width * 0.01)[0]
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def template_layers() -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    template = Image.open(TEMPLATE_PREVIEW).convert("RGBA")
    bbox = nonwhite_bbox(template, threshold=24, pad=8)
    crop = template.crop(bbox)
    rgb = np.asarray(crop.convert("RGB"), dtype=np.int16)
    alpha_src = np.asarray(crop.getchannel("A"))
    nonwhite = (alpha_src > 5) & (np.abs(rgb - 255).sum(axis=2) > 30)
    dark = (alpha_src > 5) & (rgb[:, :, 0] < 90) & (rgb[:, :, 1] < 90) & (rgb[:, :, 2] < 90)

    guides = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    guides[nonwhite] = np.concatenate(
        [
            rgb[nonwhite].astype(np.uint8),
            np.full((int(nonwhite.sum()), 1), 205, dtype=np.uint8),
        ],
        axis=1,
    )

    contour = np.zeros_like(guides)
    contour[dark] = (0, 92, 255, 245)
    return Image.fromarray(guides), Image.fromarray(contour), bbox


def register_to_dense(art: Image.Image, layer: Image.Image, aspect: float) -> tuple[Image.Image, tuple[int, int, int, int], tuple[int, int, int, int]]:
    dense = dense_bbox(art)
    overlay_w = art.width
    overlay_h = round(overlay_w / aspect)
    overlay_x = 0
    overlay_y = round((dense[1] + dense[3] - overlay_h) / 2)
    resized = layer.resize((overlay_w, overlay_h), Image.Resampling.LANCZOS)
    return resized, (overlay_x, overlay_y, overlay_x + overlay_w, overlay_y + overlay_h), dense


def alpha_box(
    base: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    width: int = 4,
) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rounded_rectangle(box, radius=7, fill=fill, outline=outline, width=width)
    base.alpha_composite(overlay)


def callout(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    target: tuple[int, int],
    text: str,
    fill: tuple[int, int, int],
) -> None:
    x, y = xy
    lines = text.split("\n")
    w = max(draw.textlength(line, font=SMALL) for line in lines) + 20
    h = 18 * len(lines) + 14
    draw.line((x + min(w, 80), y + h, target[0], target[1]), fill=fill + (210,), width=2)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=6, fill=(255, 255, 255, 232), outline=fill + (210,), width=2)
    yy = y + 7
    for line in lines:
        draw.text((x + 10, yy), line, font=SMALL, fill=fill)
        yy += 18


def make_plan() -> tuple[Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art = Image.open(IMAGE_A).convert("RGBA")
    guides, contour, template_bbox = template_layers()
    aspect = contour.width / contour.height
    guides_registered, overlay, dense = register_to_dense(art, guides, aspect)
    contour_registered, _, _ = register_to_dense(art, contour, aspect)

    clean = art.copy()
    clean.alpha_composite(contour_registered, (overlay[0], overlay[1]))
    clean_path = OUT_DIR / "image-a-svg-locked-clean-contour-base.png"
    clean.save(clean_path)

    reviewed = art.copy()
    reviewed.alpha_composite(guides_registered, (overlay[0], overlay[1]))
    reviewed.alpha_composite(contour_registered, (overlay[0], overlay[1]))

    # Bounded patch zones in Image A coordinates after dense registration.
    alpha_box(reviewed, (35, 70, 190, 275), (58, 181, 74, 20), (58, 181, 74, 225))
    alpha_box(reviewed, (378, 168, 710, 230), (58, 181, 74, 18), (58, 181, 74, 205))
    alpha_box(reviewed, (0, 844, 1048, 922), (255, 120, 0, 28), (255, 120, 0, 220))
    alpha_box(reviewed, (142, 372, 230, 520), (237, 28, 36, 24), (237, 28, 36, 230))
    alpha_box(reviewed, (410, 445, 592, 622), (0, 92, 255, 18), (0, 92, 255, 210))
    alpha_box(reviewed, (770, 585, 1040, 800), (255, 188, 0, 28), (255, 188, 0, 220))
    alpha_box(reviewed, (875, 430, 920, 858), (58, 181, 74, 14), (58, 181, 74, 180), width=3)

    draw = ImageDraw.Draw(reviewed, "RGBA")
    callout(draw, (205, 78), (112, 118), "reduce TV tower;\nkeep left of red center", (42, 130, 55))
    callout(draw, (704, 118), (640, 188), "trace dome/spires\nwithout crop", (42, 130, 55))
    callout(draw, (44, 790), (255, 865), "contain loose\nwater wash", (190, 85, 0))
    callout(draw, (650, 806), (825, 660), "restore hotel lower\nleft/base crop", (160, 115, 0))
    callout(draw, (730, 458), (900, 585), "hotel red center OK:\nno iconic feature", (42, 130, 55))
    callout(draw, (240, 548), (177, 438), "nudge horses statue\nclear of red center", (180, 30, 38))
    callout(draw, (235, 646), (510, 510), "align bridge to\nmiddle of door flaps", (0, 84, 190))

    header = 156
    pad = 30
    canvas = Image.new("RGB", (reviewed.width + pad * 2, reviewed.height + header + pad), "white")
    cdraw = ImageDraw.Draw(canvas)
    cdraw.text((pad, 22), "Image A: SVG-Locked Local Patch Plan", font=TITLE, fill=(25, 28, 33))
    cdraw.text(
        (pad, 64),
        "Verdict: preserve Image A. The geometry is close after dense-landmark registration; patch bounded risk zones.",
        font=BODY,
        fill=(72, 78, 86),
    )
    cdraw.text((pad, 104), "Green = acceptable/contour notes; orange = bottom/base repair; red = feature safety; blue = arch symmetry.", font=BODY, fill=(72, 78, 86))
    canvas.paste(reviewed.convert("RGB"), (pad, header))

    plan_path = OUT_DIR / "image-a-svg-locked-local-patch-plan.png"
    canvas.save(plan_path)

    brief_path = TASK / "prompts/image-a-svg-locked-local-patch-brief.md"
    brief_path.write_text(
        "\n".join(
            [
                "# Image A SVG-Locked Local Patch Brief",
                "",
                "Use Image A as the composition and style base. Do not restart the skyline from scratch.",
                "",
                "## Geometry Verdict",
                "",
                f"- Dense landmark bbox: `{dense}`",
                f"- Dense landmark aspect: `{(dense[2] - dense[0]) / (dense[3] - dense[1]):.3f}`",
                f"- SVG active bbox from template preview: `{template_bbox}`",
                f"- SVG active aspect: `{aspect:.3f}`",
                f"- Registered overlay rect on Image A: `{overlay}`",
                "",
                "## Required Local Patches",
                "",
                "- Preserve the horizontal landmark composition and watercolor style from Image A.",
                "- Reduce the TV tower height/scale so it rises only moderately above the top contour and stays on the left side of the panel, not over the red center.",
                "- Adapt the top contour to trace the domes, church spires, and hotel roof cleanly. Door-panel buildings are the reference for acceptable height additions above the contour.",
                "- Keep the sky/removable background white.",
                "- Trim or contain the loose lower water wash inside the real SVG bottom boundary.",
                "- Keep non-iconic/filler detail in red-center lanes when it does not crop a specific feature. The hotel red-center lane is acceptable because it contains quiet facade detail.",
                "- Nudge the horses statue in the left narrow panel slightly away from the red center.",
                "- Complete/restore the lower hotel base so the Ritz/Beisheim building reads whole.",
                "- Align the right-side bridge span to the middle of the saloon door flaps for symmetry, if the adjustment can stay natural.",
                "- Do not draw production guide strokes into the final artwork; overlay the real SVG afterward.",
                "",
                "## Review Artifacts",
                "",
                f"- Clean contour base: `{clean_path}`",
                f"- Patch plan overlay: `{plan_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report_path = OUT_DIR / "image-a-svg-fit-and-local-patch-report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Image A SVG Fit And Local Patch Report",
                "",
                "Verdict: LOCAL PATCH / REGISTRATION WORKFLOW.",
                "",
                "Image A should be preserved as the composition and style base. It is not a broad geometry failure.",
                "",
                f"- Dense landmark bbox: `{dense}`",
                f"- Dense landmark aspect: `{(dense[2] - dense[0]) / (dense[3] - dense[1]):.3f}`",
                f"- SVG active aspect: `{aspect:.3f}`",
                f"- Registered overlay rect: `{overlay}`",
                "",
                "Remaining bounded risks:",
                "",
                "- TV tower currently extends too far above the contour and should be reduced while staying left of the panel red center;",
                "- top contour must be adapted to the actual landmark silhouette, with only controlled feature overflow;",
                "- loose water wash extends beyond the bottom boundary;",
                "- the hotel red-center lane is acceptable because it does not contain important/iconic features;",
                "- the hotel lower/base section is cropped on the left side of the narrow panel and should be restored;",
                "- the horses statue slightly overlaps the left-panel red center and should be nudged clear;",
                "- the right-side bridge should align to the middle of the door flaps for symmetry where possible.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"clean={clean_path}")
    print(f"plan={plan_path}")
    print(f"brief={brief_path}")
    print(f"report={report_path}")
    print(f"dense_bbox={dense} dense_aspect={(dense[2] - dense[0]) / (dense[3] - dense[1]):.3f}")
    print(f"svg_aspect={aspect:.3f} overlay={overlay}")
    return clean_path, plan_path, brief_path


if __name__ == "__main__":
    make_plan()
