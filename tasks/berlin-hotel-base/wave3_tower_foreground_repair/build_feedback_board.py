#!/usr/bin/env python3
"""Build a compact labeled feedback board for the wave3 shortlist."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
BASELINE = (ROOT / "../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png").resolve()
SHORT = ROOT / "shortlist"
RESULTS = ROOT / "results"
CONTEXT = (0, 900, 860, 3050)

ENTRIES = [
    ("base", BASELINE),
    ("S01 subtle poles", SHORT / "s01_refined_combo_sphere_poles_soft.png"),
    ("S02 clone cleanup", SHORT / "s02_refined_combo_neighbor_clone.png"),
    ("S03 haze tint", SHORT / "s03_refined_balanced_subtle_haze.png"),
    ("S04 worker safe", SHORT / "s04_worker_watercolor_plus_conservative_fg.png"),
    ("S05 worker stronger fg", SHORT / "s05_worker_watercolor_plus_sampled_fg.png"),
    ("S06 stronger sphere", SHORT / "s06_worker_strong_sphere_plus_conservative_fg.png"),
    ("S07 softwash fg", SHORT / "s07_worker_watercolor_plus_softwash_fg.png"),
    ("S08 safest combo", SHORT / "s08_refined_sphere_plus_foreground_conservative.png"),
    ("S09 OpenAI redraw", SHORT / "s09_openai_bounded_external.png"),
]


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


def main() -> None:
    cols = 5
    cell_w = 340
    cell_h = 890
    rows = (len(ENTRIES) + cols - 1) // cols
    board = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    label_font = font(26)
    small_font = font(18)
    for idx, (label, path) in enumerate(ENTRIES):
        tile = Image.new("RGB", (cell_w, cell_h), "white")
        d = ImageDraw.Draw(tile)
        d.text((12, 10), label, fill=(145, 0, 0), font=label_font)
        if label != "base":
            d.text((12, 42), Path(path).stem, fill=(95, 95, 95), font=small_font)
        crop = Image.open(path).convert("RGB").crop(CONTEXT)
        crop.thumbnail((cell_w, cell_h - 72), Image.Resampling.LANCZOS)
        tile.paste(crop, ((cell_w - crop.width) // 2, 72))
        board.paste(tile, ((idx % cols) * cell_w, (idx // cols) * cell_h))
    RESULTS.mkdir(parents=True, exist_ok=True)
    board.save(RESULTS / "wave3_feedback_board.png")
    print(RESULTS / "wave3_feedback_board.png")


if __name__ == "__main__":
    main()
