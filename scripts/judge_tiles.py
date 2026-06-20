#!/usr/bin/env python3
"""Prepare a candidate for RELIABLE VLM judging. The Read tool downsamples large/tall images, so a
judge handed the whole panel can't resolve a mid-panel feature and HALLUCINATES (proven: a window
present mid-height was scored "absent"). This emits:
  - context.png   : whole panel downscaled (layout/composition only)
  - tile_*.png    : HIGH-DPI overlapping vertical (and, if wide, horizontal) tiles at ~native res
  - region_*.png  : optional hi-DPI crops of named regions (e.g. the window) from --regions
plus manifest.json with each file's panel-fraction bbox so a judge knows where it is.

Judges must read the TILES for any presence/position/detail check, the context only for composition.

  judge_tiles.py --candidate C.png --out DIR [--rows 3] [--overlap 0.12] [--regions "window:0,0.30,0.62,0.62"]
"""
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path
from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--rows", type=int, default=0, help="vertical tiles (0=auto from aspect)")
    ap.add_argument("--overlap", type=float, default=0.12)
    ap.add_argument("--min-tile", type=int, default=900, help="upscale a tile below this on long side")
    ap.add_argument("--regions", default="", help="name:fx0,fy0,fx1,fy1;... fractional bboxes")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    im = Image.open(a.candidate).convert("RGB")
    W, H = im.size
    rows = a.rows or max(1, round(H / W))            # ~square tiles
    man = {"candidate": str(a.candidate), "size": [W, H], "context": "context.png", "tiles": [], "regions": []}

    ctx = im.copy(); ctx.thumbnail((900, 900)); ctx.save(a.out / "context.png")

    step = H / rows
    ov = int(step * a.overlap)
    for i in range(rows):
        y0 = max(0, int(i * step) - ov); y1 = min(H, int((i + 1) * step) + ov)
        t = im.crop((0, y0, W, y1))
        if max(t.size) < a.min_tile:
            s = a.min_tile / max(t.size); t = t.resize((int(t.width * s), int(t.height * s)))
        name = f"tile_{i}.png"; t.save(a.out / name)
        man["tiles"].append({"file": name, "frac_bbox": [0.0, round(y0 / H, 3), 1.0, round(y1 / H, 3)]})

    # Counter VLM positional-anchoring bias: shuffle the ORDER tiles are LISTED
    # (not the tile files, not their bboxes — each entry carries its own
    # frac_bbox, so listing order has no spatial meaning). DETERMINISTIC: seed
    # from a hash of the candidate filename so re-runs on the same candidate are
    # stable and reproducible (no random/time-based seed).
    seed = int(hashlib.sha256(Path(a.candidate).name.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    random.Random(seed).shuffle(man["tiles"])

    for spec in [s for s in a.regions.split(";") if s.strip()]:
        name, rest = spec.split(":"); fx0, fy0, fx1, fy1 = (float(v) for v in rest.split(","))
        box = (int(fx0 * W), int(fy0 * H), int(fx1 * W), int(fy1 * H))
        r = im.crop(box)
        if max(r.size) < a.min_tile:
            s = a.min_tile / max(r.size); r = r.resize((int(r.width * s), int(r.height * s)))
        fn = f"region_{name}.png"; r.save(a.out / fn)
        man["regions"].append({"name": name, "file": fn, "frac_bbox": [fx0, fy0, fx1, fy1]})

    (a.out / "manifest.json").write_text(json.dumps(man, indent=2))
    print(f"tiles={len(man['tiles'])} regions={len(man['regions'])} ctx=context.png -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
