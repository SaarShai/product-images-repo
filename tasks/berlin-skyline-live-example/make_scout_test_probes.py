#!/usr/bin/env python3
"""Build bold early scout probes for the Berlin skyline composition.

These are deliberately cheap review images. They are not final artwork and do
not claim production fit. Their job is to test whether a composition route is
legible enough to justify a full image-generation pass.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
ELEMENTS_PATH = ROOT / "outputs/generated/20260616-berlin-elements-v2.png"
REFERENCE_RENDER_PATH = ROOT / "refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg"
TEMPLATE_PATH = ROOT / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
OUT_DIR = ROOT / "outputs/reviews/scout-tests"


CANVAS_SIZE = (1800, 1220)
GUIDE_ORIGIN = (70, 185)


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


F_TITLE = font(38, True)
F_LABEL = font(22, True)
F_SMALL = font(18)
F_TINY = font(15)


def art_crop(sheet: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Crop an element and remove only near-paper-white pixels."""
    crop = sheet.crop(box).convert("RGBA")
    rgb = np.asarray(crop.convert("RGB")).astype(np.int16)
    distance_from_white = (255 - rgb[:, :, 0]) + (255 - rgb[:, :, 1]) + (255 - rgb[:, :, 2])
    alpha = np.clip((distance_from_white - 14) * 13, 0, 255).astype(np.uint8)
    alpha = Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(0.45))
    crop.putalpha(alpha)
    crop = ImageEnhance.Contrast(crop).enhance(1.16)
    crop = ImageEnhance.Color(crop).enhance(1.05)
    return crop


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = img.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def fit_fill(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = img.copy().convert("RGB")
    scale = max(size[0] / copy.width, size[1] / copy.height)
    resized = copy.resize((round(copy.width * scale), round(copy.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - size[0]) // 2)
    top = max(0, (resized.height - size[1]) // 2)
    return resized.crop((left, top, left + size[0], top + size[1]))


def paste_fit(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int], anchor: str = "center") -> None:
    x1, y1, x2, y2 = box
    fitted = fit(img, (x2 - x1, y2 - y1))
    if anchor == "bottom":
        y = y2 - fitted.height
    elif anchor == "top":
        y = y1
    else:
        y = y1 + (y2 - y1 - fitted.height) // 2
    x = x1 + (x2 - x1 - fitted.width) // 2
    canvas.alpha_composite(fitted, (x, y))


def build_guide_overlay(alpha_scale: float = 1.9) -> Image.Image:
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    pix = template.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(template.height):
        for x in range(template.width):
            r, g, b, a = pix[x, y]
            if a > 10 and min(r, g, b) < 245:
                xs.append(x)
                ys.append(y)
    box = (
        max(0, min(xs) - 30),
        max(0, min(ys) - 30),
        min(template.width, max(xs) + 30),
        min(template.height, max(ys) + 30),
    )
    crop = template.crop(box)
    crop = crop.resize((1660, round(1660 * crop.height / crop.width)), Image.Resampling.LANCZOS)
    r, g, b, a = crop.split()
    a = a.point(lambda v: min(230, round(v * alpha_scale)))
    crop.putalpha(a)
    return crop


def elements() -> dict[str, Image.Image]:
    sheet = Image.open(ELEMENTS_PATH).convert("RGBA")
    return {
        "tv": art_crop(sheet, (35, 18, 175, 612)),
        "gate": art_crop(sheet, (180, 158, 628, 605)),
        "dom": art_crop(sheet, (600, 98, 970, 618)),
        "church": art_crop(sheet, (945, 92, 1160, 628)),
        "hotel": art_crop(sheet, (1155, 65, 1535, 630)),
        "train": art_crop(sheet, (40, 628, 840, 728)),
        "rail": art_crop(sheet, (40, 728, 850, 795)),
        "stone": art_crop(sheet, (40, 797, 850, 878)),
        "water": art_crop(sheet, (40, 888, 855, 995)),
        "bridge": art_crop(sheet, (865, 600, 1500, 900)),
    }


def base(title: str, subtitle: str) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((44, 24), title, font=F_TITLE, fill=(30, 30, 28))
    draw.text((46, 74), subtitle, font=F_SMALL, fill=(72, 72, 66))
    draw.text((46, 1164), "Scout test only: composition evidence, not clipped final artwork or production approval.", font=F_SMALL, fill=(80, 80, 74))
    return canvas


def finish(canvas: Image.Image, contour: list[tuple[int, int]], callout: str, out: Path) -> Path:
    draw = ImageDraw.Draw(canvas)
    draw.line(contour, fill=(36, 135, 61, 210), width=7, joint="curve")
    draw.rounded_rectangle((48, 1010, 560, 1116), radius=12, fill=(255, 255, 255, 225), outline=(170, 170, 160), width=2)
    draw.text((68, 1028), "Decision this tests", font=F_LABEL, fill=(45, 45, 42))
    draw.multiline_text((68, 1060), callout, font=F_TINY, fill=(45, 45, 42), spacing=4)
    canvas.alpha_composite(build_guide_overlay(), GUIDE_ORIGIN)
    canvas.convert("RGB").save(out, quality=95)
    return out


def probe_reference_remix() -> Path:
    canvas = base(
        "Scout 0: Whole-Reference Remix",
        "Tests whether the original Berlin render should be used as a whole-scene composition map.",
    )
    ref = Image.open(REFERENCE_RENDER_PATH).convert("RGB")
    # Exclude the separate green clock/traffic-tower panel on the right.
    city_render = ref.crop((0, 0, 820, ref.height))
    fitted = fit_fill(city_render, (1510, 770)).convert("RGBA")
    fitted.putalpha(230)
    canvas.alpha_composite(fitted, (150, 250))
    return finish(
        canvas,
        [(120, 295), (255, 230), (370, 365), (610, 285), (820, 240), (1015, 322), (1310, 275), (1655, 305)],
        "Pass if it gives the clearest overall scene rhythm.\nFail if it feels like a rectangular crop we would later fight.",
        OUT_DIR / "scout-0-whole-reference-remix.png",
    )


def probe_reference_rhythm(parts: dict[str, Image.Image]) -> Path:
    canvas = base(
        "Scout 1: Reference-Faithful Rhythm",
        "Keeps the reference order: TV tower/gate, Dom/church, hotel; train is low and quiet.",
    )
    placements = [
        ("water", (100, 925, 1490, 1045), "bottom"),
        ("stone", (95, 870, 1480, 950), "center"),
        ("rail", (95, 826, 1480, 885), "center"),
        ("train", (85, 740, 1220, 850), "center"),
        ("bridge", (635, 640, 1240, 850), "center"),
        ("tv", (105, 245, 255, 805), "bottom"),
        ("gate", (250, 455, 565, 820), "bottom"),
        ("dom", (560, 255, 925, 740), "bottom"),
        ("church", (890, 265, 1125, 760), "bottom"),
        ("hotel", (1260, 245, 1665, 865), "bottom"),
    ]
    for key, box, anchor in placements:
        paste_fit(canvas, parts[key], box, anchor)
    return finish(
        canvas,
        [(112, 290), (215, 238), (350, 365), (585, 292), (760, 242), (1000, 335), (1320, 290), (1645, 310)],
        "Pass if original render hierarchy survives in 3 panels.\nFail if it remains three separate postcards.",
        OUT_DIR / "scout-1-reference-faithful-rhythm.png",
    )


def probe_arch_hero(parts: dict[str, Image.Image]) -> Path:
    canvas = base(
        "Scout 2: Strong Saloon-Arch Hero",
        "Stress-tests the bridge/viaduct as the central saloon-door feature.",
    )
    placements = [
        ("water", (390, 895, 1480, 1055), "center"),
        ("stone", (80, 890, 1540, 972), "center"),
        ("rail", (80, 832, 1540, 890), "center"),
        ("train", (70, 770, 1515, 870), "center"),
        ("bridge", (470, 558, 1305, 852), "center"),
        ("dom", (555, 235, 895, 668), "bottom"),
        ("church", (905, 235, 1120, 668), "bottom"),
        ("tv", (120, 270, 245, 820), "bottom"),
        ("gate", (250, 560, 520, 810), "bottom"),
        ("hotel", (1290, 305, 1665, 860), "bottom"),
    ]
    for key, box, anchor in placements:
        paste_fit(canvas, parts[key], box, anchor)
    return finish(
        canvas,
        [(110, 300), (215, 255), (355, 380), (575, 300), (735, 245), (995, 330), (1330, 330), (1645, 285)],
        "Pass if the orange arch area becomes meaningful.\nFail if the bridge crowds landmarks or feels gimmicky.",
        OUT_DIR / "scout-2-strong-saloon-arch-hero.png",
    )


def probe_continuous_band(parts: dict[str, Image.Image]) -> Path:
    canvas = base(
        "Scout 3: Continuous City Band",
        "Tests train, rail, water, and bridge as the spine that unifies all panels.",
    )
    placements = [
        ("water", (60, 900, 1660, 1055), "center"),
        ("stone", (55, 850, 1665, 930), "center"),
        ("rail", (55, 805, 1665, 862), "center"),
        ("train", (55, 720, 1670, 835), "center"),
        ("bridge", (720, 610, 1540, 880), "center"),
        ("tv", (105, 238, 245, 790), "bottom"),
        ("gate", (235, 425, 585, 770), "bottom"),
        ("dom", (560, 220, 960, 720), "bottom"),
        ("church", (880, 255, 1128, 740), "bottom"),
        ("hotel", (1225, 220, 1665, 835), "bottom"),
    ]
    for key, box, anchor in placements:
        paste_fit(canvas, parts[key], box, anchor)
    return finish(
        canvas,
        [(105, 288), (205, 238), (360, 358), (590, 275), (785, 225), (1015, 315), (1255, 275), (1650, 255)],
        "Pass if the set reads as one continuous Berlin scene.\nFail if train details create seam/cut-line risks.",
        OUT_DIR / "scout-3-continuous-city-band.png",
    )


def make_contact(paths: list[Path]) -> Path:
    thumbs: list[tuple[Path, Image.Image]] = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((820, 560), Image.Resampling.LANCZOS)
        thumbs.append((path, image))

    sheet = Image.new("RGB", (1760, 1280), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    draw.text((38, 28), "Berlin Skyline Scout Tests", font=F_TITLE, fill=(30, 30, 28))
    draw.text((40, 78), "Early proof board: intentionally different composition routes before full generation.", font=F_SMALL, fill=(72, 72, 66))
    positions = [(40, 130), (900, 130), (40, 700), (900, 700)]
    for (path, image), (x, y) in zip(thumbs, positions):
        draw.text((x, y), path.stem, font=F_LABEL, fill=(35, 35, 32))
        sheet.paste(image, (x, y + 34))
    out = OUT_DIR / "scout-tests-contact-sheet.png"
    sheet.save(out, quality=95)
    return out


def mean_diff(path_a: Path, path_b: Path) -> float:
    a = Image.open(path_a).convert("RGB").resize((480, 326), Image.Resampling.BILINEAR)
    b = Image.open(path_b).convert("RGB").resize((480, 326), Image.Resampling.BILINEAR)
    diff = np.asarray(ImageChops.difference(a, b)).astype(np.float32)
    return float(diff.mean())


def write_report(paths: list[Path], contact: Path) -> Path:
    report = OUT_DIR / "scout-test-report.md"
    lines = [
        "# Berlin Skyline Scout Test Report",
        "",
        "Date: 2026-06-16",
        "",
        "Purpose: answer whether the current placement-wireframe route is strong enough to justify a full image-generation pass.",
        "",
        "## Artifacts",
        "",
    ]
    for path in paths:
        lines.append(f"- `{path.relative_to(ROOT)}`")
    lines.append(f"- `{contact.relative_to(ROOT)}`")
    lines.extend(["", "## Pairwise Mean Pixel Difference", ""])
    for a, b in combinations(paths, 2):
        lines.append(f"- `{a.name}` vs `{b.name}`: {mean_diff(a, b):.2f} / 255")
    lines.extend(
        [
            "",
            "Interpretation: the previous placement options were useful inventory maps but too visually similar/faint for a full-generation decision. These scout tests are deliberately bolder; they should be judged by whether one route reads within a few seconds.",
            "",
            "## Proceed Criteria",
            "",
            "- A route has visibly distinct hierarchy, not just labels.",
            "- Landmarks remain whole within their physical panels.",
            "- Run-through elements read as infrastructure, not cropped focal subjects.",
            "- The saloon arch has either a clear useful role or is intentionally quiet.",
            "- The image-generation input should be a composition map plus style references, not a final crop.",
        ]
    )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parts = elements()
    paths = [
        probe_reference_remix(),
        probe_reference_rhythm(parts),
        probe_arch_hero(parts),
        probe_continuous_band(parts),
    ]
    contact = make_contact(paths)
    report = write_report(paths, contact)
    for path in [*paths, contact, report]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
