#!/usr/bin/env python3
"""Create compact per-SVG review sheets for bottom batch candidates."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "tasks/space-svg-exports-batch"
SUMMARY = TASK / "checkpoints/batch-bottom-summary.json"


def make_sheet(svg_stem: str, items: list[dict[str, object]]) -> Path:
    pairs = []
    for item in items:
        art = Image.open(ROOT / str(item["artwork_only"])).convert("RGB")
        debug = Image.open(ROOT / str(item["debug_mask"])).convert("RGB")
        pairs.append((item, art, debug))

    max_h = 900
    prepared = []
    for item, art, debug in pairs:
        scale = min(1.0, max_h / art.height)
        size = (round(art.width * scale), round(art.height * scale))
        prepared.append(
            (
                item,
                art.resize(size, Image.Resampling.LANCZOS),
                debug.resize(size, Image.Resampling.LANCZOS),
            )
        )

    pad = 28
    label_h = 44
    cell_w = max(max(art.width, debug.width) for _, art, debug in prepared)
    width = pad * 3 + cell_w * 2
    height = pad * 3 + label_h * 2 + max(art.height + debug.height for _, art, debug in prepared)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)

    for col, (item, art, debug) in enumerate(prepared):
        x = pad + col * (cell_w + pad)
        y = pad
        label = f"{svg_stem} v{item['variant']} art"
        draw.text((x, y), label, fill=(10, 45, 85))
        sheet.paste(art, (x, y + label_h))
        y = y + label_h + art.height + pad
        draw.text((x, y), f"{svg_stem} v{item['variant']} debug", fill=(10, 45, 85))
        sheet.paste(debug, (x, y + label_h))

    out = TASK / "checkpoints" / f"{svg_stem}-review-sheet.png"
    sheet.save(out)
    return out


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    by_svg: dict[str, list[dict[str, object]]] = {}
    for item in summary["candidates"]:
        stem = Path(str(item["svg"])).stem
        by_svg.setdefault(stem, []).append(item)
    sheets = [make_sheet(stem, sorted(items, key=lambda item: int(item["variant"]))) for stem, items in sorted(by_svg.items())]
    for sheet in sheets:
        print(sheet.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
