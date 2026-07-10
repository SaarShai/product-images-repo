#!/usr/bin/env python3
"""v10 Semantic-Skeleton CFD + paper subtraction (GLM-5.2 rethink).

STOP: no more flood/rim threshold iteration.

Architecture (GLM ranked #1):
  1. Chromatic skeleton (chroma > T) dilated → sure FG trimap.
  2. All near-paper (outer + enclosed) → sure BG trimap.
  3. PyMatting closed-form on unknown band.
  4. Algebraic paper subtraction on soft pixels, then flatten alpha
     (partials become paint-colored opaque — not white halo).

Optional: intersect / union with BRIA hard mask if present.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from pymatting import estimate_alpha_cf
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

REPO = Path(__file__).resolve().parents[2]
PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)


@dataclass
class Params:
    chroma_fg_min: float = 12.0
    chroma_dilate_px: int = 8
    paper_luma_min: float = 248.0
    paper_chroma_max: float = 4.0
    flatten_alpha_min: float = 0.12  # below → transparent
    bria_fg_min: int = 200  # optional sure-FG boost from BRIA
    use_bria: bool = True
    cg_maxiter: int = 200


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(
        np.float32
    )
    chroma = (rgb.max(2) - rgb.min(2)).astype(np.float32)
    return luma, chroma


def paper_mean(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    py, px = max(12, h // 50), max(12, w // 50)
    samples = np.concatenate(
        [
            rgb[:py, :px].reshape(-1, 3),
            rgb[:py, -px:].reshape(-1, 3),
            rgb[-py:, :px].reshape(-1, 3),
            rgb[-py:, -px:].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)
    return samples.mean(0)


def build_trimap(rgb: np.ndarray, bria: np.ndarray | None, p: Params) -> np.ndarray:
    luma, chroma = luma_chroma(rgb)
    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max)

    skeleton = chroma >= p.chroma_fg_min
    if p.chroma_dilate_px > 0:
        skeleton = ndi.binary_dilation(skeleton, iterations=p.chroma_dilate_px)

    fg = skeleton & ~paper
    if bria is not None and p.use_bria:
        # BRIA sure-FG only where not paper (don't let BRIA claim paper)
        fg |= (bria >= p.bria_fg_min) & ~paper

    # Sure BG = all paper (outer + enclosed). This is the key vs flood-only.
    bg = paper & ~fg

    # Conflict: if both, prefer FG only when chromatic; else BG
    both = fg & bg
    if both.any():
        fg[both] = chroma[both] >= p.chroma_fg_min
        bg[both] = ~fg[both]

    trimap = np.full(rgb.shape[:2], 0.5, dtype=np.float64)
    trimap[bg] = 0.0
    trimap[fg] = 1.0
    return trimap


def paper_subtract(rgb: np.ndarray, alpha: np.ndarray, paper: np.ndarray) -> np.ndarray:
    """FG = (obs - (1-a)*paper) / a  for soft pixels."""
    a = np.clip(alpha, 0, 1).astype(np.float32)
    out = rgb.astype(np.float32).copy()
    soft = (a > 1e-3) & (a < 0.999)
    if not soft.any():
        return rgb.copy()
    aa = a[soft][:, None]
    un = (rgb[soft].astype(np.float32) - (1.0 - aa) * paper.astype(np.float32)[None, :]) / aa
    out[soft] = np.clip(un, 0, 255)
    return out.astype(np.uint8)


def run_pipeline(
    rgb: np.ndarray, bria: np.ndarray | None, p: Params
) -> tuple[np.ndarray, dict[str, Any]]:
    mean = paper_mean(rgb)
    trimap = build_trimap(rgb, bria, p)

    image = rgb.astype(np.float64) / 255.0
    alpha = estimate_alpha_cf(
        image,
        trimap,
        cg_kwargs={"maxiter": p.cg_maxiter, "rtol": 1e-5},
    )
    alpha = np.clip(alpha, 0.0, 1.0).astype(np.float32)

    rgb_out = paper_subtract(rgb, alpha, mean)

    # Flatten: soft → opaque paint-colored; near-zero → transparent
    hard = alpha >= p.flatten_alpha_min
    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.where(hard, 255, 0).astype(np.uint8)
    # Clear RGB where transparent
    rgba[~hard, :3] = 0

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "trimap_fg_pct": float(100.0 * (trimap == 1.0).mean()),
        "trimap_bg_pct": float(100.0 * (trimap == 0.0).mean()),
        "trimap_unk_pct": float(100.0 * (trimap == 0.5).mean()),
        "soft_before_flatten_pct": float(100.0 * ((alpha > 0.05) & (alpha < 0.95)).mean()),
        "opaque_pct": float(100.0 * hard.mean()),
        "transparent_pct": float(100.0 * (~hard).mean()),
        "semi_pct": 0.0,
        "params": asdict(p),
    }
    return rgba, metrics, trimap, alpha


def composite_preview(rgba: np.ndarray, bg: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.float32)
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    return np.clip(rgb * a[:, :, None] + bg.astype(np.float32) * (1.0 - a[:, :, None]), 0, 255).astype(
        np.uint8
    )


def save_full(path: Path, rgba: np.ndarray, bg: np.ndarray, max_side: int) -> None:
    prev = Image.fromarray(composite_preview(rgba, bg), "RGB")
    w, h = prev.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        prev = prev.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    prev.save(path, quality=93)


def make_review(path: Path, rgba: np.ndarray, x: int, y: int, w: int, h: int, scale: int = 3) -> None:
    patch = rgba[y : y + h, x : x + w]
    white = np.full(patch.shape[:2] + (3,), 255, dtype=np.uint8)
    gray = np.full(patch.shape[:2] + (3,), 140, dtype=np.uint8)
    black = np.zeros_like(gray)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    board = np.concatenate(
        [
            composite_preview(patch, white),
            composite_preview(patch, gray),
            composite_preview(patch, black),
            composite_preview(patch, mag),
        ],
        axis=1,
    )
    im = Image.fromarray(board, "RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=93)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bria", action="store_true")
    ap.add_argument("--chroma", type=float, default=12.0)
    ap.add_argument("--dilate", type=int, default=8)
    ap.add_argument("--flatten", type=float, default=0.12)
    ap.add_argument("--full-max", type=int, default=3600)
    args = ap.parse_args()
    p = Params(
        chroma_fg_min=args.chroma,
        chroma_dilate_px=args.dilate,
        flatten_alpha_min=args.flatten,
        use_bria=not args.no_bria,
    )

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)

    bria = None
    bria_path = (
        PRODUCT
        / "Images/candidates/image14-research/candidates/14-01-bria-rmbg-alpha-matting-hard180.png"
    )
    if p.use_bria and bria_path.exists():
        bria_im = Image.open(bria_path)
        if bria_im.mode == "RGBA":
            bria_a = bria_im.split()[-1]
        else:
            bria_a = bria_im.convert("L")
        bria_a = bria_a.resize((rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST)
        bria = np.asarray(bria_a, dtype=np.uint8)

    rgba, metrics, trimap, alpha = run_pipeline(rgb, bria, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-cfd-v10"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    tag = f"c{int(p.chroma_fg_min)}-d{p.chroma_dilate_px}-f{p.flatten_alpha_min}"
    out_png = out_dir / f"14-cfd-v10-{tag}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Debug trimap contact
    tvis = np.zeros((*trimap.shape, 3), dtype=np.uint8)
    tvis[trimap == 0.0] = (0, 0, 255)  # BG blue
    tvis[trimap == 1.0] = (0, 255, 0)  # FG green
    tvis[trimap == 0.5] = (128, 128, 128)  # unknown gray
    Image.fromarray(tvis, "RGB").resize(
        (tvis.shape[1] // 2, tvis.shape[0] // 2), Image.Resampling.NEAREST
    ).save(review / "17-cfd-v10-trimap.jpg", quality=90)

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    save_full(review / "17-cfd-v10-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / "17-cfd-v10-full-magenta.jpg", rgba, mag, args.full_max)
    h = rgba.shape[0]
    save_full(review / "17-cfd-v10-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], args.full_max)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
    ]:
        make_review(review / f"17-cfd-v10-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-cfd-v10"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
