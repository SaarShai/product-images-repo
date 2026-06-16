#!/usr/bin/env python3
"""Create a guide-overlay preview from a generated image and template PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def transparent_guides(template: Image.Image, threshold: int) -> Image.Image:
    rgba = template.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if red >= threshold and green >= threshold and blue >= threshold:
                pixels[x, y] = (255, 255, 255, 0)
            else:
                pixels[x, y] = (red, green, blue, alpha)
    return rgba


def fit_cover(source: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / source.width, height / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def fit_contain(source: Image.Image, width: int, height: int) -> Image.Image:
    scale = min(width / source.width, height / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    left = (width - resized.width) // 2
    top = (height - resized.height) // 2
    canvas.alpha_composite(resized, (left, top))
    return canvas


def scale_artwork(
    source: Image.Image,
    scale: float,
    offset_x: int,
    offset_y: int,
    scale_x: float | None = None,
    scale_y: float | None = None,
) -> Image.Image:
    sx = scale if scale_x is None else scale_x
    sy = scale if scale_y is None else scale_y
    if sx == 1 and sy == 1 and offset_x == 0 and offset_y == 0:
        return source

    resized = source.resize(
        (round(source.width * sx), round(source.height * sy)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", source.size, (255, 255, 255, 255))
    left = (source.width - resized.width) // 2 + offset_x
    top = (source.height - resized.height) // 2 + offset_y
    canvas.alpha_composite(resized, (left, top))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="Generated image to review")
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "assets/templates/previews/two-panel-template-cropped.png",
        help="Template guide PNG with white background",
    )
    parser.add_argument("--out", type=Path, help="Output PNG path")
    parser.add_argument(
        "--fit",
        choices=("cover", "contain"),
        default="cover",
        help="How to scale the template overlay to the generated image",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=248,
        help="RGB threshold for making template background transparent",
    )
    parser.add_argument(
        "--art-scale",
        type=float,
        default=1.0,
        help="Scale generated artwork before overlaying fixed template guides",
    )
    parser.add_argument(
        "--art-scale-x",
        type=float,
        help="Override horizontal artwork scale before overlaying fixed template guides",
    )
    parser.add_argument(
        "--art-scale-y",
        type=float,
        help="Override vertical artwork scale before overlaying fixed template guides",
    )
    parser.add_argument(
        "--art-offset-x",
        type=int,
        default=0,
        help="Horizontal artwork offset after scaling, in output pixels",
    )
    parser.add_argument(
        "--art-offset-y",
        type=int,
        default=0,
        help="Vertical artwork offset after scaling, in output pixels",
    )
    args = parser.parse_args()

    image_path = args.image if args.image.is_absolute() else ROOT / args.image
    template_path = args.template if args.template.is_absolute() else ROOT / args.template
    out_path = args.out
    if out_path is None:
        out_path = image_path.with_name(f"{image_path.stem}-template-overlay.png")
    elif not out_path.is_absolute():
        out_path = ROOT / out_path

    base = Image.open(image_path).convert("RGBA")
    base = scale_artwork(
        base,
        args.art_scale,
        args.art_offset_x,
        args.art_offset_y,
        scale_x=args.art_scale_x,
        scale_y=args.art_scale_y,
    )
    guides = transparent_guides(Image.open(template_path), args.threshold)
    if args.fit == "cover":
        overlay = fit_cover(guides, base.width, base.height)
    else:
        overlay = fit_contain(guides, base.width, base.height)

    result = base.copy()
    result.alpha_composite(overlay)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
