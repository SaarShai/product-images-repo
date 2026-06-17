#!/usr/bin/env python3
"""Build labeled contact sheet(s) of all experiment results from the results DB.

Reads results.jsonl, picks each record's actual image (raw preferred, else exact),
lays them out in a grid sorted by region-IoU desc, with a caption per cell
(id / model / region-IoU / verdict). Paginates so each sheet stays legible.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "space-np01-front-bottom-02"
JSONL = TASK / "RESULTS" / "results.jsonl"
OUTDIR = TASK / "RESULTS" / "contact-sheets"

CELL_W, IMG_H, CAP_H = 200, 440, 64
COLS = 6
PER_SHEET = 30  # 6x5


def load_font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def resolve_img(rec) -> Path | None:
    for key in ("image_path_raw", "image_path_exact"):
        v = rec.get(key)
        if not v or v in ("unknown", "n/a"):
            continue
        p = Path(v)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return p
    return None


def main() -> int:
    include_orphans = "--with-orphans" in sys.argv
    rows = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
    if not include_orphans:
        rows = [r for r in rows if r.get("method") != "raw-model-output-uncataloged"]

    items = []
    for r in rows:
        img = resolve_img(r)
        if img is None:
            continue
        items.append((r, img))

    # sort by region_iou desc; non-numeric last
    def key(it):
        v = it[0].get("region_iou")
        return -float(v) if isinstance(v, (int, float)) else 1.0
    items.sort(key=key)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    f_id = load_font(15)
    f_meta = load_font(14)
    sheets = []
    for pg in range((len(items) + PER_SHEET - 1) // PER_SHEET):
        chunk = items[pg * PER_SHEET:(pg + 1) * PER_SHEET]
        rows_n = (len(chunk) + COLS - 1) // COLS
        W = COLS * CELL_W
        H = rows_n * (IMG_H + CAP_H) + 40
        sheet = Image.new("RGB", (W, H), (250, 250, 248))
        d = ImageDraw.Draw(sheet)
        d.text((10, 10), f"space-np01-front-bottom-02 — results contact sheet (page {pg+1}) — sorted by region-IoU",
                fill=(20, 20, 20), font=f_meta)
        for i, (rec, img) in enumerate(chunk):
            cx = (i % COLS) * CELL_W
            cy = (i // COLS) * (IMG_H + CAP_H) + 40
            try:
                im = Image.open(img).convert("RGB")
            except Exception:
                continue
            im.thumbnail((CELL_W - 16, IMG_H - 8), Image.LANCZOS)
            ox = cx + (CELL_W - im.width) // 2
            sheet.paste(im, (ox, cy + 4))
            riou = rec.get("region_iou")
            riou_s = f"{riou:.3f}" if isinstance(riou, (int, float)) else str(riou)
            verdict = rec.get("verdict", "?")
            color = (10, 120, 10) if verdict == "PASS" else (170, 30, 30) if verdict == "FAIL" else (110, 110, 110)
            ty = cy + IMG_H
            d.text((cx + 6, ty), rec["id"][:30], fill=(0, 0, 0), font=f_id)
            d.text((cx + 6, ty + 18), f"{rec.get('model','?')[:22]}", fill=(60, 60, 60), font=f_meta)
            d.text((cx + 6, ty + 36), f"rIoU={riou_s}  {verdict}", fill=color, font=f_meta)
        out = OUTDIR / f"contact-sheet-p{pg+1}.png"
        sheet.save(out)
        sheets.append(str(out.relative_to(ROOT)))
        print(out.relative_to(ROOT), sheet.size)
    print(f"{len(items)} images across {len(sheets)} sheet(s); orphans={'in' if include_orphans else 'out'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
