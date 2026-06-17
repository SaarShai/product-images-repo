#!/usr/bin/env python3
"""Build rough SVG-aware Berlin placement option mockups.

These are review artifacts, not final artwork exports. They place approved v2
elements behind the template preview so composition risks can be discussed
before a final SVG-constrained render.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
ELEMENTS_PATH = ROOT / "outputs/generated/20260616-berlin-elements-v2.png"
TEMPLATE_PATH = ROOT / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
OUT_DIR = ROOT / "outputs/reviews/placement-options"


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
F_LABEL = font(24, True)
F_SMALL = font(18)


def transparent_crop(sheet: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    crop = sheet.crop(box).convert("RGBA")
    pixels = crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = pixels[x, y]
            # Fade out the paper-white sheet background while preserving pale art.
            whiteness = min(r, g, b)
            if whiteness > 248:
                pixels[x, y] = (r, g, b, 0)
            elif whiteness > 238:
                pixels[x, y] = (r, g, b, int(a * (248 - whiteness) / 10))
    alpha = crop.getchannel("A").filter(ImageFilter.GaussianBlur(0.7))
    crop.putalpha(alpha)
    return crop


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = img.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def paste_fit(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    fitted = fit(img, (x2 - x1, y2 - y1))
    canvas.alpha_composite(fitted, (x1 + (x2 - x1 - fitted.width) // 2, y1 + (y2 - y1 - fitted.height) // 2))


def build_overlay() -> Image.Image:
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
    x1, y1, x2, y2 = max(0, min(xs) - 30), max(0, min(ys) - 30), min(template.width, max(xs) + 30), min(template.height, max(ys) + 30)
    crop = template.crop((x1, y1, x2, y2))
    crop = crop.resize((1660, int(1660 * crop.height / crop.width)), Image.Resampling.LANCZOS)
    # Make overlay strong enough for review but not so strong it hides art.
    r, g, b, a = crop.split()
    a = a.point(lambda v: min(210, int(v * 1.7)))
    crop.putalpha(a)
    return crop


def annotate(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((46, 28), title, font=F_TITLE, fill=(30, 31, 29))
    draw.text((48, 78), subtitle, font=F_SMALL, fill=(75, 75, 70))
    draw.text((48, 1160), "Review mockup only: not clipped final artwork, not production approval.", font=F_SMALL, fill=(90, 90, 84))


def draw_top_contour(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]]) -> None:
    draw.line(pts, fill=(52, 145, 68, 190), width=6, joint="curve")


def make_option(name: str, title: str, subtitle: str, placements: dict[str, tuple[int, int, int, int]], contour: list[tuple[int, int]]) -> Path:
    sheet = Image.open(ELEMENTS_PATH).convert("RGBA")
    parts = {
        "tv": transparent_crop(sheet, (40, 25, 165, 610)),
        "gate": transparent_crop(sheet, (185, 165, 625, 595)),
        "dom": transparent_crop(sheet, (610, 110, 960, 615)),
        "church": transparent_crop(sheet, (945, 105, 1155, 625)),
        "hotel": transparent_crop(sheet, (1160, 80, 1515, 625)),
        "train": transparent_crop(sheet, (55, 630, 825, 725)),
        "rail": transparent_crop(sheet, (55, 730, 835, 790)),
        "stone": transparent_crop(sheet, (55, 800, 835, 875)),
        "water": transparent_crop(sheet, (55, 890, 850, 990)),
        "bridge": transparent_crop(sheet, (875, 610, 1485, 885)),
    }
    canvas = Image.new("RGBA", (1800, 1220), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    annotate(draw, title, subtitle)
    for key in ["water", "stone", "rail", "train", "bridge", "tv", "gate", "dom", "church", "hotel"]:
        if key in placements:
            paste_fit(canvas, parts[key], placements[key])
    draw = ImageDraw.Draw(canvas)
    draw_top_contour(draw, contour)
    overlay = build_overlay()
    canvas.alpha_composite(overlay, (70, 185))
    # Simple panel labels for review.
    draw.rounded_rectangle((100, 975, 440, 1032), radius=12, fill=(255, 255, 255, 220), outline=(190, 190, 180), width=2)
    draw.rounded_rectangle((470, 975, 1250, 1032), radius=12, fill=(255, 255, 255, 220), outline=(190, 190, 180), width=2)
    draw.rounded_rectangle((1280, 975, 1690, 1032), radius=12, fill=(255, 255, 255, 220), outline=(190, 190, 180), width=2)
    draw.text((124, 991), "left: TV tower + gate", font=F_SMALL, fill=(45, 45, 42))
    draw.text((494, 991), "center: Dom + church + saloon arch", font=F_SMALL, fill=(45, 45, 42))
    draw.text((1304, 991), "right: hotel with lower base", font=F_SMALL, fill=(45, 45, 42))
    out = OUT_DIR / f"{name}.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def make_contact_sheet(paths: list[Path]) -> Path:
    thumbs = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((900, 610), Image.Resampling.LANCZOS)
        thumbs.append((path, img))
    sheet = Image.new("RGB", (960, 1980), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    y = 28
    for path, img in thumbs:
        draw.text((34, y), path.stem, font=F_LABEL, fill=(35, 35, 32))
        sheet.paste(img, (30, y + 38))
        y += 645
    out = OUT_DIR / "placement-options-contact-sheet.png"
    sheet.save(out, quality=95)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    option_paths = [
        make_option(
            "placement-option-a-conservative",
            "Option A: Conservative Template-Safe",
            "Whole landmarks kept well inside panels; run-through strips are quiet at seams.",
            {
                "tv": (110, 270, 245, 845),
                "gate": (245, 520, 510, 805),
                "dom": (600, 285, 910, 760),
                "church": (900, 280, 1115, 755),
                "hotel": (1285, 270, 1655, 845),
                "train": (115, 800, 1120, 895),
                "rail": (100, 875, 1180, 930),
                "stone": (95, 920, 1210, 985),
                "water": (540, 960, 1240, 1040),
                "bridge": (620, 665, 1120, 850),
            },
            [(110, 285), (210, 235), (320, 375), (620, 320), (800, 250), (1010, 335), (1330, 270), (1640, 295)],
        ),
        make_option(
            "placement-option-b-scenic",
            "Option B: Connected Scenic Set",
            "More continuous scene; buildings scale larger, bridge and water help bind center/right.",
            {
                "tv": (95, 265, 225, 825),
                "gate": (205, 490, 555, 815),
                "dom": (560, 245, 950, 765),
                "church": (900, 255, 1125, 760),
                "hotel": (1245, 245, 1675, 850),
                "train": (105, 785, 1050, 885),
                "rail": (95, 875, 1220, 925),
                "stone": (90, 925, 1265, 990),
                "water": (700, 925, 1460, 1040),
                "bridge": (740, 665, 1390, 875),
            },
            [(105, 285), (200, 235), (365, 365), (610, 290), (785, 235), (1000, 330), (1270, 305), (1625, 275)],
        ),
        make_option(
            "placement-option-c-arch-runthrough",
            "Option C: Saloon Arch + Run-Through",
            "Central bridge arch is dominant; low U-Bahn/rail/water carry the set across all panels.",
            {
                "tv": (120, 275, 245, 825),
                "gate": (235, 520, 510, 805),
                "dom": (555, 255, 900, 720),
                "church": (900, 265, 1110, 735),
                "hotel": (1280, 275, 1665, 845),
                "train": (105, 810, 1420, 900),
                "rail": (95, 885, 1490, 940),
                "stone": (92, 935, 1500, 995),
                "water": (500, 960, 1520, 1050),
                "bridge": (555, 625, 1240, 860),
            },
            [(110, 285), (210, 245), (340, 370), (600, 295), (760, 245), (1005, 330), (1320, 315), (1635, 280)],
        ),
    ]
    contact = make_contact_sheet(option_paths)
    for path in option_paths:
        print(path)
    print(contact)


if __name__ == "__main__":
    main()
