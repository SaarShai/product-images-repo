#!/usr/bin/env python3
"""Prepare and bound external image-edit outputs for the wave3 probe."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent
BERLIN_ROOT = ROOT.parents[2]
WAVE3_ROOT = ROOT.parents[1]
REPO_ROOT = BERLIN_ROOT.parents[1]
BASELINE = (
    BERLIN_ROOT / "wave2" / "BANKED_CURRENT_BEST" / "berlin_hotel_base_current_best.png"
)
VERIFY = WAVE3_ROOT / "verify_wave3.py"

ISSUE_BOXES = {
    "sphere_ghost": (190, 1120, 470, 1580),
    "foreground": (0, 2050, 620, 2920),
}
ZOOM_BOX = (0, 900, 860, 3050)


def load_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def make_mask(size: tuple[int, int], feather: int = 18) -> Image.Image:
    hard = Image.new("L", size, 0)
    draw = ImageDraw.Draw(hard)
    for box in ISSUE_BOXES.values():
        draw.rectangle(box, fill=255)
    if feather <= 0:
        return hard
    soft = hard.filter(ImageFilter.GaussianBlur(feather))
    return Image.composite(soft, hard, hard)


def prepare_assets() -> None:
    base = load_rgb(BASELINE)
    mask = make_mask(base.size)
    hard = make_mask(base.size, feather=0)
    base.save(ROOT / "baseline_copy_readonly.png")
    mask.save(ROOT / "issue_mask_feathered.png")
    hard.save(ROOT / "issue_mask_hard.png")
    base.crop(ZOOM_BOX).save(ROOT / "baseline_issue_zoom.png")
    mask.crop(ZOOM_BOX).save(ROOT / "issue_mask_zoom.png")


def composite(raw_path: Path, out_path: Path, crop_path: Path) -> None:
    base = load_rgb(BASELINE)
    raw = load_rgb(raw_path)
    if raw.size != base.size:
        raw = raw.resize(base.size, Image.Resampling.LANCZOS)
    mask = make_mask(base.size)
    cand = Image.composite(raw, base, mask)
    cand.save(out_path)
    cand.crop(ZOOM_BOX).save(crop_path)


def verify(candidate: Path, log_path: Path) -> int:
    proc = subprocess.run(
        ["python3", str(VERIFY), "--candidate", str(candidate)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path.write_text(proc.stdout + proc.stderr)
    return proc.returncode


def diff_summary(raw_path: Path, summary_path: Path) -> None:
    base = load_rgb(BASELINE)
    raw = load_rgb(raw_path)
    resized = raw.resize(base.size, Image.Resampling.LANCZOS) if raw.size != base.size else raw
    base_arr = np.asarray(base, dtype=np.int16)
    raw_arr = np.asarray(resized, dtype=np.int16)
    delta = np.abs(raw_arr - base_arr)
    changed = np.any(delta > 0, axis=2)
    ys, xs = np.where(changed)
    bbox = None if len(xs) == 0 else (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    summary_path.write_text(
        "\n".join(
            [
                f"raw_path={raw_path}",
                f"raw_size={raw.size}",
                f"baseline_size={base.size}",
                f"raw_resized_for_bounded_composite={raw.size != base.size}",
                f"raw_changed_bbox_after_optional_resize={bbox}",
                f"raw_max_delta={int(delta.max()) if delta.size else 0}",
            ]
        )
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--crop", type=Path)
    parser.add_argument("--verify-log", type=Path)
    parser.add_argument("--raw-summary", type=Path)
    args = parser.parse_args()

    if args.prepare:
        prepare_assets()
        return 0

    if not all([args.raw, args.candidate, args.crop, args.verify_log, args.raw_summary]):
        parser.error("--raw, --candidate, --crop, --verify-log, and --raw-summary are required")

    composite(args.raw, args.candidate, args.crop)
    diff_summary(args.raw, args.raw_summary)
    return verify(args.candidate, args.verify_log)


if __name__ == "__main__":
    raise SystemExit(main())
