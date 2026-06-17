#!/usr/bin/env python3
"""Correct SVG overlay for the OpenAI (Codex) train-tunnel edit of Image A.

Reuses the exact-SVG-aspect helpers from make_image_a_correct_svg_overlay.py so
the guide proportions still come from the source SVG coordinate bounds, not from
the square preview PNG or the generated-art bbox. Only the artwork and output
paths differ.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

TASK = Path("tasks/berlin-skyline-live-example")
ART_PATH = TASK / "refs/user-feedback/20260617-image-a-train-tunnel-edit.png"
OUT_DIR = TASK / "outputs/reviews/train-exit-repair"

# Load the canonical overlay module to reuse its helpers + exact SVG bounds.
_spec = importlib.util.spec_from_file_location(
    "image_a_overlay", str(TASK / "make_image_a_correct_svg_overlay.py")
)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art = Image.open(ART_PATH).convert("RGBA")
    art_bbox = M.nonwhite_bbox(art, threshold=34, pad=8)
    guides, template_bbox, preview_aspect = M.guide_layer()
    overlay_box = M.place_width_centered(art_bbox)

    clean = M.overlay_art(art, guides, overlay_box, draw_boxes=False)
    diagnostic = M.overlay_art(art, guides, overlay_box, draw_boxes=True)
    draw = ImageDraw.Draw(diagnostic, "RGBA")
    draw.rectangle(art_bbox, outline=(237, 28, 36, 190), width=3)

    clean_path = OUT_DIR / "openai-edit-correct-svg-overlay-clean.png"
    diag_path = OUT_DIR / "openai-edit-correct-svg-overlay-diagnostic.png"
    clean.convert("RGB").save(clean_path)
    M.labelled_canvas(
        diagnostic,
        "OpenAI tunnel edit + Correct SVG Overlay",
        "Guide overlay scaled from exact SVG content aspect (not the square preview).",
        art_bbox,
        overlay_box,
    ).save(diag_path)

    print(f"art={ART_PATH}")
    print(f"art_bbox={art_bbox}")
    print(f"svg_aspect={M.SVG_ASPECT:.3f}")
    print(f"overlay_box={overlay_box}")
    print(f"wrote={clean_path}")
    print(f"wrote={diag_path}")


if __name__ == "__main__":
    main()
