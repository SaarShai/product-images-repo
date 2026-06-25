#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "tasks/berlin-hotel-base/wave10_hotel_consistency_ghost_fix/results/v01_hotel_consistency.png"
TASK = ROOT / "tasks/berlin-hotel-base/wave13_regenerate_bridge_crop"
CROP_BOX = (1320, 2360, 2630, 3240)


def edge_mask(size: tuple[int, int], feather: int = 18) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((feather, feather, size[0] - feather, size[1] - feather), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather / 2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ids", required=True, help="comma list like openai:3,nano:12")
    parser.add_argument("--round", dest="round_id", required=True)
    args = parser.parse_args()
    wanted = set()
    for part in args.ids.split(","):
        provider, tid = part.split(":", 1)
        wanted.add((provider, int(tid)))
    rows = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get("round") == args.round_id and (r.get("provider"), int(r.get("template_id"))) in wanted]
    base = Image.open(BASE).convert("RGB")
    cw = CROP_BOX[2] - CROP_BOX[0]
    ch = CROP_BOX[3] - CROP_BOX[1]
    mask = edge_mask((cw, ch))
    out_dir = TASK / "results/final_composites"
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        crop = Image.open(row["output"]).convert("RGB").resize((cw, ch), Image.Resampling.LANCZOS)
        canvas = base.copy()
        region = canvas.crop(CROP_BOX)
        comp = Image.composite(crop, region, mask)
        canvas.paste(comp, CROP_BOX)
        out = out_dir / f"{args.round_id}_{row['provider']}_t{int(row['template_id']):02d}_full.png"
        canvas.save(out)
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
