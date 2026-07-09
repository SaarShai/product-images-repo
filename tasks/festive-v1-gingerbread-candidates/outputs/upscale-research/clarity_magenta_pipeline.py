#!/usr/bin/env python3
"""Magenta-bg cutout → cream → (optional downsample) → fal clarity 4x → transparent.

Matches best-C-clarity-transparent: clarity rebuilds detail at ~4x from a
SMALL soft source. Large soft sources must be downsampled first; 2x alone
only enlarges blur.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

REPO = next(
    p for p in Path(__file__).resolve().parents if (p / "scripts" / "reupscale.py").exists()
)
VENV = REPO / ".venv-gen" / "bin" / "python"
REUPSCALE = REPO / "scripts" / "reupscale.py"

CREAM = np.array([252.0, 249.0, 240.0], dtype=np.float32)
PROMPT = (
    "gingerbread cookie cutout with thick white piped royal icing border, "
    "holly leaves berries candy ornaments sugar pearls, crisp watercolor "
    "illustration detail, sharp cookie texture, clean edges, masterpiece"
)
NEG = (
    "blurry, smeared, melted, soft focus, plastic, jpeg artifacts, "
    "oversharpened, noise, warped, extra objects, text, watermark, magenta"
)


def is_magenta(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    return (r > 170) & (b > 170) & (g < 140) & (r > g + 30) & (b > g + 30)


def is_cream(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    sat = rgb.max(2) - rgb.min(2)
    return (r > 245) & (g > 242) & (b > 228) & (sat < 22)


def magenta_to_cream(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(np.float32)
    mag = is_magenta(a)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    near = (r > 150) & (b > 140) & (g < 160) & (r > g + 15) & (b > g + 10)
    near = near & ndimage.binary_dilation(mag, iterations=2)
    bg = mag | near
    fg = ~bg
    lab, n = ndimage.label(fg)
    if n:
        sizes = [(lab == i).sum() for i in range(1, n + 1)]
        keep = lab == (int(np.argmax(sizes)) + 1)
        for i, s in enumerate(sizes, 1):
            if s >= 200:
                keep |= lab == i
        bg = ~keep
    out = a.copy()
    out[bg] = CREAM
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
    return {
        "size": im.size,
        "magenta_pct": float(100 * mag.mean()),
        "bg_pct": float(100 * bg.mean()),
        "cream_path": str(dst),
    }


def maybe_downsample(cream: Path, dst: Path, target_short: int) -> dict:
    """Downsample so min(w,h) ~= target_short (like C's 224-wide source)."""
    im = Image.open(cream).convert("RGB")
    w, h = im.size
    short = min(w, h)
    if short <= target_short + 20:
        shutil.copy2(cream, dst)
        return {"size": (w, h), "scaled": False, "path": str(dst)}
    scale = target_short / short
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im.resize((nw, nh), Image.Resampling.LANCZOS).save(dst)
    return {"size": (nw, nh), "scaled": True, "from": (w, h), "path": str(dst)}


def cream_to_transparent(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(np.float32)
    cream = is_cream(a)
    mag = is_magenta(a)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    pink_fringe = (r > 160) & (b > 140) & (g < 170) & (r > g + 20) & (b > g + 10)
    bg = cream | mag | pink_fringe
    fg = ~bg
    lab, n = ndimage.label(ndimage.binary_opening(fg, iterations=1))
    if n == 0:
        lab, n = ndimage.label(fg)
    keep = np.zeros_like(fg)
    if n:
        sizes = [(lab == i).sum() for i in range(1, n + 1)]
        for i, s in enumerate(sizes, 1):
            if s >= 150:
                keep |= lab == i
    if not keep.any():
        keep = fg
    keep = ndimage.binary_closing(keep, iterations=2)
    dist = ndimage.distance_transform_edt(keep)
    alpha = np.clip(dist / 1.8, 0, 1.0)
    alpha = ndimage.gaussian_filter(alpha, 0.4)
    alpha[ndimage.binary_erosion(keep, iterations=2)] = 1.0
    alpha[~keep] = 0
    edge = keep & ~ndimage.binary_erosion(keep, iterations=2)
    mag_edge = edge & ((r > g + 25) & (b > g + 15) & (g < 180))
    alpha[mag_edge] = 0
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    rgba[rgba[:, :, 3] < 8, :3] = 0
    rgba[rgba[:, :, 3] < 8, 3] = 0
    Image.fromarray(rgba).save(dst)
    return {
        "size": Image.open(dst).size,
        "transparent_pct": float(100 * (rgba[:, :, 3] == 0).mean()),
        "opaque_pct": float(100 * (rgba[:, :, 3] == 255).mean()),
        "out": str(dst),
    }


def run_clarity(cream: Path, out: Path, factor: float = 4.0, creativity: float = 0.2, resemblance: float = 0.9) -> None:
    cmd = [
        str(VENV), str(REUPSCALE),
        "--image", str(cream), "--out", str(out),
        "--creativity", str(creativity),
        "--resemblance", str(resemblance),
        "--factor", str(factor),
        "--steps", "22",
        "--prompt", PROMPT,
        "--neg", NEG,
    ]
    print("[pipeline]", " ".join(cmd[:8]), f"factor={factor} creat={creativity} res={resemblance}", flush=True)
    subprocess.check_call(cmd)


def process_one(
    src: Path,
    work: Path,
    slug: str,
    factor: float,
    copy_dirs: list[Path],
    target_short: int = 240,
    creativity: float = 0.25,
    resemblance: float = 0.85,
) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    cream = work / f"{slug}-cream.png"
    cream_small = work / f"{slug}-cream-small.png"
    clarity = work / f"{slug}-clarity.png"
    final = work / f"{slug}-clarity-transparent.png"

    info: dict = {"src": str(src), "slug": slug}
    info["cream"] = magenta_to_cream(src, cream)
    info["downsample"] = maybe_downsample(cream, cream_small, target_short)
    run_clarity(cream_small, clarity, factor=factor, creativity=creativity, resemblance=resemblance)
    info["clarity_size"] = Image.open(clarity).size
    info["transparent"] = cream_to_transparent(clarity, final)

    prev = Image.new("RGBA", info["transparent"]["size"], (252, 249, 240, 255))
    prev.alpha_composite(Image.open(final).convert("RGBA"))
    prev_path = work / f"{slug}-clarity-preview.png"
    prev.save(prev_path)
    info["preview"] = str(prev_path)
    info["final"] = str(final)

    for d in copy_dirs:
        d.mkdir(parents=True, exist_ok=True)
        for p in (final, prev_path):
            shutil.copy2(p, d / p.name)
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--factor", type=float, default=4.0)
    ap.add_argument("--target-short", type=int, default=240,
                    help="downsample cream so min side ~= this before clarity 4x (C used ~224)")
    ap.add_argument("--creativity", type=float, default=0.25)
    ap.add_argument("--resemblance", type=float, default=0.85)
    ap.add_argument("--copy", action="append", default=[])
    a = ap.parse_args()
    info = process_one(
        Path(a.src), Path(a.work), a.slug, a.factor,
        [Path(c) for c in a.copy],
        target_short=a.target_short,
        creativity=a.creativity,
        resemblance=a.resemblance,
    )
    print(
        "DONE", info["slug"],
        "small", info["downsample"]["size"],
        "clarity", info["clarity_size"],
        "final", info["final"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
