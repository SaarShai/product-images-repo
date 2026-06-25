#!/usr/bin/env python3
"""Build review boards for wave3 variants."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
BASELINE = (ROOT / "../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png").resolve()
RESULTS = ROOT / "results"
CONTEXT_CROP = (0, 900, 860, 3050)
SPHERE_CROP = (120, 1040, 520, 1660)
FOREGROUND_CROP = (0, 1960, 760, 3040)


def font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def label_cell(img: Image.Image, label: str, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 7), label, fill=(145, 0, 0), font=font(22))
    max_h = height - 42
    scale = min(width / img.width, max_h / img.height)
    resized = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((width - resized.width) // 2, 38))
    return canvas


def make_context_board(entries: list[tuple[str, Path]], out: Path) -> None:
    cell_w, cell_h = 300, 790
    cols = 4
    rows = (len(entries) + cols - 1) // cols
    board = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for idx, (label, path) in enumerate(entries):
        img = Image.open(path).convert("RGB").crop(CONTEXT_CROP)
        cell = label_cell(img, label, cell_w, cell_h)
        board.paste(cell, ((idx % cols) * cell_w, (idx // cols) * cell_h))
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out)


def make_detail_board(entries: list[tuple[str, Path]], out: Path) -> None:
    label_w, sphere_w, fg_w = 260, 260, 360
    row_h = 310
    header_h = 38
    board = Image.new("RGB", (label_w + sphere_w + fg_w, header_h + len(entries) * row_h), "white")
    d = ImageDraw.Draw(board)
    f = font(22)
    d.text((10, 7), "variant", fill=(80, 80, 80), font=f)
    d.text((label_w + 10, 7), "sphere", fill=(80, 80, 80), font=f)
    d.text((label_w + sphere_w + 10, 7), "foreground", fill=(80, 80, 80), font=f)
    for idx, (label, path) in enumerate(entries):
        y = header_h + idx * row_h
        img = Image.open(path).convert("RGB")
        d.rectangle((0, y, board.width, y + row_h), outline=(230, 230, 230))
        d.text((10, y + 15), label, fill=(145, 0, 0), font=font(20))
        sphere = img.crop(SPHERE_CROP)
        fg = img.crop(FOREGROUND_CROP)
        sphere.thumbnail((sphere_w - 16, row_h - 16), Image.Resampling.LANCZOS)
        fg.thumbnail((fg_w - 16, row_h - 16), Image.Resampling.LANCZOS)
        board.paste(sphere, (label_w + (sphere_w - sphere.width) // 2, y + (row_h - sphere.height) // 2))
        board.paste(fg, (label_w + sphere_w + (fg_w - fg.width) // 2, y + (row_h - fg.height) // 2))
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra-dir", action="append", type=Path, default=[])
    parser.add_argument("--only-dir", action="append", type=Path, default=[])
    parser.add_argument("--prefix", default="wave3_review_board")
    args = parser.parse_args()

    entries: list[tuple[str, Path]] = [("baseline current best", BASELINE)]
    directories = args.only_dir if args.only_dir else [ROOT / "local_variants", *args.extra_dir]
    for directory in directories:
        if directory.exists():
            for path in sorted(directory.glob("*.png")):
                if path.name.endswith(("_sphere.png", "_foreground.png")):
                    continue
                entries.append((path.stem, path))

    make_context_board(entries, RESULTS / f"{args.prefix}_context.png")
    make_detail_board(entries, RESULTS / f"{args.prefix}_details.png")
    print(f"wrote boards for {len(entries)} entries to {RESULTS}")


if __name__ == "__main__":
    main()
