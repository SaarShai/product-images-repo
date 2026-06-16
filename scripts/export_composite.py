#!/usr/bin/env python3
"""Export placed artwork and template overlays from one scale/offset recipe."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from make_overlay_preview import fit_contain, fit_cover, scale_artwork, transparent_guides


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def black_line_overlay(template: Image.Image, threshold: int = 96) -> Image.Image:
    rgba = template.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            is_blackish = red <= threshold and green <= threshold and blue <= threshold
            if is_blackish and alpha:
                pixels[x, y] = (red, green, blue, alpha)
            else:
                pixels[x, y] = (255, 255, 255, 0)
    return rgba


def fit_overlay(overlay: Image.Image, width: int, height: int, fit: str) -> Image.Image:
    if fit == "cover":
        return fit_cover(overlay, width, height)
    return fit_contain(overlay, width, height)


def save_rgb(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path)


def export_set(
    image_path: Path,
    template_path: Path,
    output_dir: Path,
    prefix: str,
    fit: str,
    art_scale: float,
    art_scale_x: float | None,
    art_scale_y: float | None,
    art_offset_x: int,
    art_offset_y: int,
    score_json: Path | None = None,
) -> dict[str, str | float | int]:
    base = Image.open(image_path).convert("RGBA")
    placed = scale_artwork(
        base,
        art_scale,
        art_offset_x,
        art_offset_y,
        scale_x=art_scale_x,
        scale_y=art_scale_y,
    )
    template = Image.open(template_path)

    full_guides = fit_overlay(transparent_guides(template, 248), placed.width, placed.height, fit)
    black_lines = fit_overlay(black_line_overlay(template), placed.width, placed.height, fit)

    guides_preview = placed.copy()
    guides_preview.alpha_composite(full_guides)

    clean_lines_preview = placed.copy()
    clean_lines_preview.alpha_composite(black_lines)

    artwork_path = output_dir / f"{prefix}-artwork-only.png"
    clean_lines_path = output_dir / f"{prefix}-clean-black-lines.png"
    guides_path = output_dir / f"{prefix}-full-guides.png"
    metadata_path = output_dir / f"{prefix}-metadata.json"

    save_rgb(placed, artwork_path)
    save_rgb(clean_lines_preview, clean_lines_path)
    save_rgb(guides_preview, guides_path)

    metadata: dict[str, str | float | int] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": " ".join(sys.argv),
        "source_image": str(image_path.relative_to(ROOT) if image_path.is_relative_to(ROOT) else image_path),
        "source_sha256": sha256(image_path),
        "source_dimensions": f"{base.width}x{base.height}",
        "template": str(template_path.relative_to(ROOT) if template_path.is_relative_to(ROOT) else template_path),
        "template_sha256": sha256(template_path),
        "fit": fit,
        "art_scale": art_scale,
        "art_scale_x": art_scale_x if art_scale_x is not None else art_scale,
        "art_scale_y": art_scale_y if art_scale_y is not None else art_scale,
        "art_offset_x": art_offset_x,
        "art_offset_y": art_offset_y,
        "output_dimensions": f"{placed.width}x{placed.height}",
        "artwork_only": str(artwork_path.relative_to(ROOT)),
        "clean_black_lines": str(clean_lines_path.relative_to(ROOT)),
        "full_guides": str(guides_path.relative_to(ROOT)),
    }
    if score_json is not None:
        metadata["score_json"] = str(score_json.relative_to(ROOT) if score_json.is_relative_to(ROOT) else score_json)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata["metadata"] = str(metadata_path.relative_to(ROOT))
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="Generated artwork PNG")
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "assets/templates/previews/two-panel-template-cropped.png",
        help="Template guide PNG with white background",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "tasks/castle-panels/outputs/final",
        help="Directory for exported files",
    )
    parser.add_argument("--prefix", default="current-best")
    parser.add_argument("--fit", choices=("cover", "contain"), default="cover")
    parser.add_argument("--art-scale", type=float, default=0.90)
    parser.add_argument("--art-scale-x", type=float)
    parser.add_argument("--art-scale-y", type=float)
    parser.add_argument("--art-offset-x", type=int, default=0)
    parser.add_argument("--art-offset-y", type=int, default=50)
    parser.add_argument("--score-json", type=Path, help="Optional candidate score JSON to link in metadata")
    args = parser.parse_args()

    image_path = args.image if args.image.is_absolute() else ROOT / args.image
    template_path = args.template if args.template.is_absolute() else ROOT / args.template
    output_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    score_json = None
    if args.score_json is not None:
        score_json = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json

    metadata = export_set(
        image_path=image_path,
        template_path=template_path,
        output_dir=output_dir,
        prefix=args.prefix,
        fit=args.fit,
        art_scale=args.art_scale,
        art_scale_x=args.art_scale_x,
        art_scale_y=args.art_scale_y,
        art_offset_x=args.art_offset_x,
        art_offset_y=args.art_offset_y,
        score_json=score_json,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
