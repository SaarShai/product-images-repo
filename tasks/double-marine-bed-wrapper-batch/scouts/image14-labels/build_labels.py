#!/usr/bin/env python3
"""Build sparse, manually chosen image14 FG/BG correction labels.

The label raster is generated only from the explicit coordinate list below.
The source, Photoshop alpha, and diagnostic are read for dimensions, review
rendering, and post-build validation; they are never thresholded or copied into
the annotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


WIDTH = 941
HEIGHT = 1672
SIZE = (WIDTH, HEIGHT)
TRANSPARENT = (0, 0, 0, 0)
RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)

SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/"
    "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)
PHOTOSHOP_ALPHA = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/image14-research/"
    "photoshop-scout/image14-photoshop-auto-mask-alpha.png"
)
DIAGNOSTIC = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/image14-research/"
    "photoshop-scout/diagnostic-high-confidence-deletion-overlay-red.png"
)
PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/bg-assisted-v1/"
    "image14-labels"
)

EXPECTED_INPUT_HASHES = {
    "source": "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d",
    "photoshop_alpha": "7401e09a30114df78af20ba92b8634860c1b1fc367df0064ec6cd819f51a972c",
    "diagnostic": "36025cabdc707039d12c32769014265a749855f19c4217b2c01a4c34c46a62aa",
}

# Coordinates are inclusive pixel centers in the native 941x1672 raster,
# origin at upper-left. Each was selected by native visual inspection.
RED_STROKES = [
    {
        "id": "R1",
        "points": [(58, 1503), (105, 1525)],
        "width": 13,
        "reason": "left sandy wash immediately outside the reef base",
    },
    {
        "id": "R2",
        "points": [(568, 1509), (529, 1537)],
        "width": 13,
        "reason": "painted sand between the central shell and front wash",
    },
    {
        "id": "R3",
        "points": [(628, 1552), (679, 1561)],
        "width": 13,
        "reason": "right-center sandy watercolor footprint below shell details",
    },
    {
        "id": "R4",
        "points": [(262, 1595), (325, 1595)],
        "width": 13,
        "reason": "lower-left painted wash beneath the starfish",
    },
    {
        "id": "R5",
        "points": [(874, 1534), (834, 1538)],
        "width": 13,
        "reason": "right sandy wash immediately outside the reef base",
    },
]

# Intentionally empty. Native visual review found no broad, clearly blank region
# that Photoshop kept: retained near-white loci were tiny and touched painted
# structures or highlights, so they remain unknown rather than forced blue.
BLUE_STROKES: list[dict[str, object]] = []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs() -> tuple[Image.Image, Image.Image, Image.Image, dict[str, str]]:
    paths = {
        "source": SOURCE,
        "photoshop_alpha": PHOTOSHOP_ALPHA,
        "diagnostic": DIAGNOSTIC,
    }
    hashes = {name: sha256(path) for name, path in paths.items()}
    if hashes != EXPECTED_INPUT_HASHES:
        raise RuntimeError(
            "Input hash mismatch; refusing to build labels against changed inputs: "
            + json.dumps(hashes, indent=2, sort_keys=True)
        )

    source = Image.open(SOURCE)
    alpha = Image.open(PHOTOSHOP_ALPHA)
    diagnostic = Image.open(DIAGNOSTIC)
    if source.size != SIZE or alpha.size != SIZE or diagnostic.size != SIZE:
        raise RuntimeError(
            f"Expected all inputs to be {SIZE}; got source={source.size}, "
            f"alpha={alpha.size}, diagnostic={diagnostic.size}"
        )
    if source.mode != "RGB" or alpha.mode != "L" or diagnostic.mode != "RGB":
        raise RuntimeError(
            "Unexpected input modes: "
            f"source={source.mode}, alpha={alpha.mode}, diagnostic={diagnostic.mode}"
        )
    return source.copy(), alpha.copy(), diagnostic.copy(), hashes


def draw_mask(strokes: list[dict[str, object]]) -> Image.Image:
    mask = Image.new("1", SIZE, 0)
    draw = ImageDraw.Draw(mask)
    for stroke in strokes:
        draw.line(
            stroke["points"],
            fill=1,
            width=int(stroke["width"]),
        )
    return mask


def build_annotation() -> tuple[Image.Image, Image.Image, Image.Image]:
    red_mask = draw_mask(RED_STROKES)
    blue_mask = draw_mask(BLUE_STROKES)
    if ImageChops.logical_and(red_mask, blue_mask).getbbox() is not None:
        raise RuntimeError("Red and blue correction masks overlap")

    annotation = Image.new("RGBA", SIZE, TRANSPARENT)
    annotation.paste(RED, (0, 0), red_mask)
    annotation.paste(BLUE, (0, 0), blue_mask)
    return annotation, red_mask, blue_mask


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def fit_panel(image: Image.Image, box: tuple[int, int]) -> Image.Image:
    return ImageOps.contain(image.convert("RGB"), box, Image.Resampling.LANCZOS)


def make_contact_sheet(
    source: Image.Image,
    diagnostic: Image.Image,
    overlay: Image.Image,
) -> Image.Image:
    sheet = Image.new("RGB", (1500, 1190), (236, 238, 241))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(24)
    caption_font = load_font(17)
    small_font = load_font(15)
    draw.text(
        (30, 18),
        "Image 14 sparse correction labels — red = sure FG deleted; blue = sure BG kept",
        fill=(20, 24, 30),
        font=title_font,
    )
    draw.text(
        (30, 50),
        "5 red strokes / 0 blue strokes / native 941×1672 / lower crop y=1400..1639",
        fill=(70, 76, 86),
        font=small_font,
    )

    full_images = [source, diagnostic, overlay]
    full_captions = ["Original source", "Photoshop deletion diagnostic", "Source + correction labels"]
    crop_images = [
        source.crop((0, 1400, WIDTH, 1640)),
        diagnostic.crop((0, 1400, WIDTH, 1640)),
        overlay.crop((0, 1400, WIDTH, 1640)),
    ]
    crop_captions = ["Native sand crop", "Diagnostic sand crop", "Correction crop (all five strokes)"]

    for column in range(3):
        x = 25 + column * 495
        draw.rounded_rectangle((x, 86, x + 470, 927), radius=10, fill="white")
        full = fit_panel(full_images[column], (440, 782))
        sheet.paste(full, (x + (470 - full.width) // 2, 115))
        draw.text((x + 15, 94), full_captions[column], fill=(20, 24, 30), font=caption_font)

        draw.rounded_rectangle((x, 948, x + 470, 1160), radius=10, fill="white")
        crop = fit_panel(crop_images[column], (440, 150))
        sheet.paste(crop, (x + (470 - crop.width) // 2, 988))
        draw.text((x + 15, 958), crop_captions[column], fill=(20, 24, 30), font=caption_font)

    return sheet


def validate(
    annotation: Image.Image,
    red_mask: Image.Image,
    blue_mask: Image.Image,
    alpha: Image.Image,
    diagnostic: Image.Image,
) -> dict[str, object]:
    if annotation.size != SIZE or annotation.mode != "RGBA":
        raise RuntimeError(f"Bad annotation shape/mode: {annotation.size} {annotation.mode}")

    counts = Counter(annotation.getdata())
    allowed = {TRANSPARENT, RED, BLUE}
    unexpected = set(counts) - allowed
    if unexpected:
        raise RuntimeError(f"Unexpected annotation colors: {sorted(unexpected)}")

    # Pillow mode "1" histograms use bin 1 (not bin 255) for selected pixels.
    red_count = red_mask.histogram()[1]
    blue_count = blue_mask.histogram()[1]
    overlap_count = ImageChops.logical_and(red_mask, blue_mask).histogram()[1]
    if red_count != 3215:
        raise RuntimeError(f"Expected 3215 red pixels from explicit strokes, got {red_count}")
    if blue_count != 0 or overlap_count != 0:
        raise RuntimeError(
            f"Expected zero blue/nonoverlap; blue={blue_count}, overlap={overlap_count}"
        )

    diagnostic_red_count = 0
    alpha_zero_count = 0
    for selected, diagnostic_pixel, alpha_pixel in zip(
        red_mask.getdata(), diagnostic.getdata(), alpha.getdata()
    ):
        if selected:
            diagnostic_red_count += diagnostic_pixel == (255, 0, 0)
            alpha_zero_count += alpha_pixel == 0
    if diagnostic_red_count != red_count or alpha_zero_count != red_count:
        raise RuntimeError(
            "A sure-FG stroke escaped the visually selected deleted-foreground loci: "
            f"diagnostic_red={diagnostic_red_count}/{red_count}, "
            f"alpha_zero={alpha_zero_count}/{red_count}"
        )

    total = WIDTH * HEIGHT
    return {
        "mode": annotation.mode,
        "dimensions": [WIDTH, HEIGHT],
        "total_pixels": total,
        "unknown_transparent_pixels": counts[TRANSPARENT],
        "red_pixels": counts[RED],
        "blue_pixels": counts[BLUE],
        "red_blue_overlap_pixels": overlap_count,
        "labeled_pixels": red_count + blue_count,
        "labeled_fraction": (red_count + blue_count) / total,
        "labeled_percent": 100.0 * (red_count + blue_count) / total,
        "red_stroke_count": len(RED_STROKES),
        "blue_stroke_count": len(BLUE_STROKES),
        "stroke_width_pixels": sorted({int(stroke["width"]) for stroke in RED_STROKES}),
        "red_pixels_on_pure_red_diagnostic": diagnostic_red_count,
        "red_pixels_on_proposal_alpha_zero": alpha_zero_count,
        "allowed_colors_rgba": [list(TRANSPARENT), list(RED), list(BLUE)],
        "observed_color_counts": {
            ",".join(map(str, color)): count
            for color, count in sorted(counts.items())
        },
    }


def save_outputs(
    destination: Path,
    annotation: Image.Image,
    overlay: Image.Image,
    contact_sheet: Image.Image,
    metadata: dict[str, object],
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    annotation.save(destination / "image14-correction-labels-rgba.png")
    overlay.save(destination / "image14-correction-labels-overlay-native.png")
    contact_sheet.save(destination / "image14-labels-review-contact-sheet.png")
    (destination / "image14-labels-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Scout output directory (default: this script's directory)",
    )
    parser.add_argument(
        "--product-dir",
        type=Path,
        default=PRODUCT_DIR,
        help="Product candidate output directory",
    )
    args = parser.parse_args()

    source, alpha, diagnostic, input_hashes = load_inputs()
    annotation, red_mask, blue_mask = build_annotation()
    overlay = Image.alpha_composite(source.convert("RGBA"), annotation)
    contact_sheet = make_contact_sheet(source, diagnostic, overlay)
    checks = validate(annotation, red_mask, blue_mask, alpha, diagnostic)

    metadata: dict[str, object] = {
        "schema_version": 1,
        "coordinate_convention": "inclusive pixel centers; origin upper-left; x then y",
        "generation_method": (
            "Explicit hand-selected polylines drawn on an empty RGBA canvas; "
            "no source-color thresholding and no candidate-alpha copying"
        ),
        "source_path": str(SOURCE),
        "photoshop_alpha_path": str(PHOTOSHOP_ALPHA),
        "diagnostic_path": str(DIAGNOSTIC),
        "input_sha256": input_hashes,
        "red_strokes": RED_STROKES,
        "blue_strokes": BLUE_STROKES,
        "blue_omission_reason": (
            "No visually certain broad blank-background region was retained by Photoshop; "
            "tiny retained near-white loci touch painted structures/highlights and remain unknown."
        ),
        "checks": checks,
    }

    save_outputs(args.work_dir, annotation, overlay, contact_sheet, metadata)
    if args.product_dir.resolve() != args.work_dir.resolve():
        save_outputs(args.product_dir, annotation, overlay, contact_sheet, metadata)

    source_hash_after = sha256(SOURCE)
    if source_hash_after != input_hashes["source"]:
        raise RuntimeError("Source changed during build")

    result = {
        "status": "built_and_structurally_verified",
        "work_dir": str(args.work_dir.resolve()),
        "product_dir": str(args.product_dir.resolve()),
        "source_sha256_after": source_hash_after,
        **checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
