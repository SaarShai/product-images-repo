#!/usr/bin/env python3
"""Build ONE labeled INPUTS board for a generation round.

Given a round directory laid out by convention:

    <round>/handle/style-handle.yaml   # role-tagged reference manifest
    <round>/handle/<file>              # the reference images themselves
    <round>/guides/*.png               # geometry / layout guides
    <round>/prompts/*.md                # per-arm prompt text

... this composes a single tiled board showing every reference image (role +
filename + provenance in a gutter label), every guide, and each prompt
rendered as a readable wrapped text panel — so a user can see exactly what
went INTO a generation round without opening each file by hand.

Output: <round>/INPUTS-<round>.jpg  (round name = the round dir's basename).

Usage:
    python3 scripts/inputs_board.py <round_dir> [--out PATH]
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H = 340, 280
GUTTER_H = 70
COLS = 3
BG = (250, 250, 248)
GUTTER_BG = (238, 240, 242)
TEXT_FG = (40, 44, 52)
TEXT_MUTED = (90, 94, 102)
PANEL_BG = (255, 255, 255)
PANEL_BORDER = (210, 212, 216)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_PATH_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_PATH_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def load_handle_rows(handle_dir: Path) -> list[dict]:
    manifest_path = handle_dir / "style-handle.yaml"
    if not manifest_path.exists():
        return []
    with manifest_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("rows", []) or []


def collect_reference_items(round_dir: Path) -> list[dict]:
    """Reference images from handle/, in manifest order, with role+provenance."""
    handle_dir = round_dir / "handle"
    rows = load_handle_rows(handle_dir)
    items = []
    for row in rows:
        fname = row.get("file", "")
        path = handle_dir / fname
        if not path.exists() or not path.is_file():
            continue
        items.append(
            {
                "kind": "reference",
                "path": path,
                "role": row.get("role", ""),
                "filename": fname,
                "provenance": row.get("provenance", ""),
            }
        )
    return items


def collect_guide_items(round_dir: Path) -> list[dict]:
    guides_dir = round_dir / "guides"
    items = []
    if not guides_dir.exists():
        return items
    for path in sorted(guides_dir.glob("*.png")):
        items.append(
            {
                "kind": "guide",
                "path": path,
                "role": "guide",
                "filename": path.name,
                "provenance": "",
            }
        )
    return items


def collect_prompt_items(round_dir: Path) -> list[dict]:
    prompts_dir = round_dir / "prompts"
    items = []
    if not prompts_dir.exists():
        return items
    for path in sorted(prompts_dir.glob("*.md")):
        items.append(
            {
                "kind": "prompt",
                "path": path,
                "role": "prompt",
                "filename": path.name,
                "provenance": "",
            }
        )
    return items


def _draw_image_tile(sheet: Image.Image, draw: ImageDraw.ImageDraw, item: dict, x0: int, y0: int) -> None:
    label_font = _font(14)
    role_font = _font(15, bold=True)
    muted_font = _font(11)

    thumb = Image.open(item["path"]).convert("RGB")
    thumb.thumbnail((CELL_W - 20, CELL_H - 20), Image.Resampling.LANCZOS)
    tx = x0 + (CELL_W - thumb.width) // 2
    ty = y0 + (CELL_H - thumb.height) // 2
    sheet.paste(thumb, (tx, ty))

    gutter_y = y0 + CELL_H
    draw.rectangle((x0, gutter_y, x0 + CELL_W, gutter_y + GUTTER_H), fill=GUTTER_BG)

    role_label = item["role"] or "-"
    draw.text((x0 + 10, gutter_y + 6), role_label.upper(), fill=TEXT_FG, font=role_font)
    draw.text((x0 + 10, gutter_y + 26), item["filename"][:44], fill=TEXT_FG, font=label_font)

    provenance = item.get("provenance") or ""
    if provenance:
        wrapped = textwrap.wrap(provenance, width=54)[:2]
        py = gutter_y + 44
        for line in wrapped:
            draw.text((x0 + 10, py), line, fill=TEXT_MUTED, font=muted_font)
            py += 13


def _draw_prompt_panel(sheet: Image.Image, draw: ImageDraw.ImageDraw, item: dict, x0: int, y0: int) -> None:
    title_font = _font(16, bold=True)
    body_font = _font(12)

    draw.rectangle((x0, y0, x0 + CELL_W, y0 + CELL_H + GUTTER_H), fill=PANEL_BG, outline=PANEL_BORDER)
    draw.rectangle((x0, y0, x0 + CELL_W, y0 + 26), fill=GUTTER_BG)
    draw.text((x0 + 10, y0 + 4), f"PROMPT: {item['filename']}", fill=TEXT_FG, font=title_font)

    text = item["path"].read_text(encoding="utf-8")
    wrapped_lines: list[str] = []
    for para in text.splitlines():
        if not para.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(para, width=56))

    body_y = y0 + 34
    max_y = y0 + CELL_H + GUTTER_H - 12
    line_h = 15
    for line in wrapped_lines:
        if body_y > max_y - line_h:
            draw.text((x0 + 10, body_y), "…", fill=TEXT_MUTED, font=body_font)
            break
        draw.text((x0 + 10, body_y), line, fill=TEXT_FG, font=body_font)
        body_y += line_h


def build_board(round_dir: Path, out_path: Path) -> Path:
    reference_items = collect_reference_items(round_dir)
    guide_items = collect_guide_items(round_dir)
    prompt_items = collect_prompt_items(round_dir)

    image_items = reference_items + guide_items
    n_image_cells = len(image_items)
    n_prompt_cells = len(prompt_items)
    total_cells = n_image_cells + n_prompt_cells

    if total_cells == 0:
        raise ValueError(f"no reference/guide/prompt inputs found under {round_dir}")

    rows = max(1, -(-total_cells // COLS))
    row_font = _font(20, bold=True)

    header_h = 40
    sheet_w = COLS * CELL_W
    sheet_h = header_h + rows * (CELL_H + GUTTER_H)
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 8), f"INPUTS — {round_dir.name}", fill=TEXT_FG, font=row_font)

    all_items = image_items + prompt_items
    for index, item in enumerate(all_items):
        col = index % COLS
        row = index // COLS
        x0 = col * CELL_W
        y0 = header_h + row * (CELL_H + GUTTER_H)

        if item["kind"] == "prompt":
            _draw_prompt_panel(sheet, draw, item, x0, y0)
        else:
            _draw_image_tile(sheet, draw, item, x0, y0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out_path, quality=92)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round_dir", type=Path, help="Round directory (handle/, guides/, prompts/)")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: <round>/INPUTS-<round>.jpg)")
    args = parser.parse_args(argv)

    round_dir = args.round_dir.resolve()
    if not round_dir.exists():
        print(f"error: round dir not found: {round_dir}", file=sys.stderr)
        return 2

    out_path = args.out or (round_dir / f"INPUTS-{round_dir.name}.jpg")
    build_board(round_dir, out_path)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
