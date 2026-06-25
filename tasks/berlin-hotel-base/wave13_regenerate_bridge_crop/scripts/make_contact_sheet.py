#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    out = ImageOps.contain(img.convert("RGB"), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(out, ((size[0] - out.width) // 2, (size[1] - out.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--provider", choices=["openai", "nano"])
    parser.add_argument("--round", dest="round_id")
    parser.add_argument("--thumb-w", type=int, default=360)
    parser.add_argument("--thumb-h", type=int, default=242)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    if args.provider:
        rows = [r for r in rows if r.get("provider") == args.provider]
    if args.round_id:
        rows = [r for r in rows if r.get("round") == args.round_id]
    rows = [r for r in rows if r.get("status") == "ok" and Path(r["output"]).exists()]
    rows.sort(key=lambda r: (r.get("provider", ""), int(r.get("template_id", 0))))
    if not rows:
        raise SystemExit("no rows to render")
    cols = 4
    label_h = 32
    pad = 18
    w = cols * args.thumb_w + (cols + 1) * pad
    rows_n = math.ceil(len(rows) / cols)
    h = rows_n * (args.thumb_h + label_h) + (rows_n + 1) * pad
    sheet = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        col = i % cols
        rr = i // cols
        x = pad + col * (args.thumb_w + pad)
        y = pad + rr * (args.thumb_h + label_h + pad)
        img = Image.open(row["output"])
        sheet.paste(fit(img, (args.thumb_w, args.thumb_h)), (x, y + label_h))
        draw.text((x, y), f"{row['provider']} t{int(row['template_id']):02d} {row.get('size')}", fill=(150, 0, 0))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
