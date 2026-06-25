#!/usr/bin/env python3
"""Build a verified review board for Berlin hotel-base wave 2 candidates."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SRC = Path("tasks/berlin-hotel-base/work/src.png")
WAVE2 = Path("tasks/berlin-hotel-base/wave2")
RESULTS = WAVE2 / "results"
BOX = (3162, 2582, 4082, 2845)
ZOOM = (3050, 2480, 4120, 2900)


@dataclass
class CandidateResult:
    method: str
    path: str
    status: str
    outside_max: int
    outside_nonzero: int
    inside_nonzero: int
    preview: str
    zoom: str


def load_font(size: int = 28) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def verify(src: np.ndarray, cand: np.ndarray, box: tuple[int, int, int, int]) -> tuple[str, int, int, int]:
    if src.shape != cand.shape:
        return "FAIL_SHAPE", -1, -1, 0
    x0, y0, x1, y1 = box
    diff = np.abs(cand.astype(np.int16) - src.astype(np.int16))
    outside = diff.copy()
    outside[y0:y1, x0:x1, :] = 0
    outside_max = int(outside.max())
    outside_nonzero = int(np.count_nonzero(outside))
    inside_nonzero = int(np.count_nonzero(diff[y0:y1, x0:x1, :]))
    status = "PASS" if outside_max == 0 and outside_nonzero == 0 and inside_nonzero > 0 else "FAIL"
    return status, outside_max, outside_nonzero, inside_nonzero


def find_candidates(src_size: tuple[int, int]) -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(WAVE2.glob("w2_*/*.png")):
        if path.parent.name == "w2_verifier_board":
            continue
        if path.name.startswith("_"):
            continue
        try:
            with Image.open(path) as im:
                if im.size == src_size:
                    candidates.append(path)
        except OSError:
            continue
    return candidates


def label_image(im: Image.Image, label: str, font: ImageFont.ImageFont) -> Image.Image:
    pad = 12
    header_h = 52
    out = Image.new("RGB", (im.width, im.height + header_h), "white")
    out.paste(im.convert("RGB"), (0, header_h))
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, out.width, header_h), fill=(246, 246, 242))
    draw.text((pad, 10), label, fill=(160, 0, 0), font=font)
    return out


def make_preview(im: Image.Image, max_w: int = 760) -> Image.Image:
    scale = max_w / im.width
    return im.resize((max_w, int(im.height * scale)), Image.Resampling.LANCZOS)


def make_board(results: list[CandidateResult], cols: int = 2, attr: str = "preview", out_name: str = "wave2_review_board.png") -> None:
    passed = [r for r in results if r.status == "PASS"]
    if not passed:
        return
    font = load_font(26)
    tiles = []
    for r in passed:
        im = Image.open(getattr(r, attr)).convert("RGB")
        if attr == "zoom":
            im = im.resize((760, int(im.height * 760 / im.width)), Image.Resampling.LANCZOS)
        label = f"{r.method}: {Path(r.path).name}"
        tiles.append(label_image(im, label, font))

    cell_w = max(tile.width for tile in tiles)
    cell_h = max(tile.height for tile in tiles)
    rows = (len(tiles) + cols - 1) // cols
    board = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    for idx, tile in enumerate(tiles):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        board.paste(tile, (x, y))
    board.save(RESULTS / out_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--box", default=",".join(map(str, BOX)))
    args = parser.parse_args()
    box = tuple(int(v) for v in args.box.split(","))
    if len(box) != 4:
        raise SystemExit("--box must be x0,y0,x1,y1")

    RESULTS.mkdir(parents=True, exist_ok=True)
    preview_dir = RESULTS / "previews"
    preview_dir.mkdir(exist_ok=True)

    src_img = Image.open(SRC).convert("RGB")
    src = np.asarray(src_img)
    results: list[CandidateResult] = []
    for path in find_candidates(src_img.size):
        method = path.parent.name
        try:
            cand_img = Image.open(path).convert("RGB")
        except OSError as exc:
            results.append(
                CandidateResult(
                    method=method,
                    path=str(path),
                    status=f"SKIP_UNREADABLE:{exc.__class__.__name__}",
                    outside_max=-1,
                    outside_nonzero=-1,
                    inside_nonzero=0,
                    preview="",
                    zoom="",
                )
            )
            continue
        status, outside_max, outside_nonzero, inside_nonzero = verify(src, np.asarray(cand_img), box)
        stem = f"{method}__{path.stem}"
        preview_path = preview_dir / f"{stem}_full.png"
        zoom_path = preview_dir / f"{stem}_zoom.png"
        make_preview(cand_img).save(preview_path)
        cand_img.crop(ZOOM).save(zoom_path)
        results.append(
            CandidateResult(
                method=method,
                path=str(path),
                status=status,
                outside_max=outside_max,
                outside_nonzero=outside_nonzero,
                inside_nonzero=inside_nonzero,
                preview=str(preview_path),
                zoom=str(zoom_path),
            )
        )

    (RESULTS / "wave2_results.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2) + "\n",
        encoding="utf-8",
    )
    md = ["# Wave 2 Results", ""]
    for r in results:
        md.append(
            f"- {r.status} `{r.method}` `{Path(r.path).name}` "
            f"outside_max={r.outside_max} outside_nonzero={r.outside_nonzero} "
            f"inside_nonzero={r.inside_nonzero}"
        )
    (RESULTS / "wave2_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    make_board(results, cols=2, attr="preview", out_name="wave2_review_board.png")
    make_board(results, cols=2, attr="zoom", out_name="wave2_zoom_board.png")
    print(f"scanned={len(results)} pass={sum(r.status == 'PASS' for r in results)} results={RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
