#!/usr/bin/env python3
"""v10c = v10b + forced edge unknown band.

v10b got global unk~5.6% but fringe ROIs were still binary FG|BG abutting,
so CF soft alpha stayed ~0.15% and white rim survived.

v10c: erode FG + strip BG near chromatic paint so fringe is unknown for CF.
Then CF → algebraic paper subtraction → flatten soft→opaque paint RGB.
"""

from __future__ import annotations

import argparse
import json
import time
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
    chroma_fg_min: float = 14.0
    chroma_dilate_px: int = 2
    paper_luma_min: float = 248.0
    paper_chroma_max: float = 4.0
    enclosed_paper_clearance_px: int = 0
    bria_fg_min: int = 200
    bria_erode_px: int = 8
    # Force unknown band around paint edges (critical vs binary fringe).
    edge_unknown_px: int = 6
    use_bria: bool = True
    flatten_alpha_min: float = 0.15
    cg_maxiter: int = 300
    half_res: bool = False


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


def border_connected(mask: np.ndarray) -> np.ndarray:
    labeled, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    border_labels = set()
    border_labels.update(labeled[0, :].tolist())
    border_labels.update(labeled[-1, :].tolist())
    border_labels.update(labeled[:, 0].tolist())
    border_labels.update(labeled[:, -1].tolist())
    border_labels.discard(0)
    if not border_labels:
        return np.zeros_like(mask, dtype=bool)
    return np.isin(labeled, list(border_labels))


def build_trimap(rgb: np.ndarray, bria: np.ndarray | None, p: Params) -> np.ndarray:
    luma, chroma = luma_chroma(rgb)
    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max)
    chromatic = chroma >= p.chroma_fg_min

    skeleton = chromatic
    if p.chroma_dilate_px > 0:
        skeleton = ndi.binary_dilation(skeleton, iterations=p.chroma_dilate_px)
    fg_seed = skeleton & ~paper

    if bria is not None and p.use_bria:
        bria_sure = bria >= p.bria_fg_min
        if p.bria_erode_px > 0:
            bria_sure = ndi.binary_erosion(bria_sure, iterations=p.bria_erode_px)
        fg_seed |= bria_sure & ~paper

    bg_seed = border_connected(paper)

    if p.enclosed_paper_clearance_px > 0:
        dist = ndi.distance_transform_edt(~chromatic)
        far_paper = paper & (dist >= p.enclosed_paper_clearance_px) & ~fg_seed
        bg_seed |= far_paper

    fg = fg_seed
    bg = bg_seed
    if p.edge_unknown_px > 0:
        n = p.edge_unknown_px
        if fg.any():
            fg = ndi.binary_erosion(fg, iterations=n)
        protect = ndi.binary_dilation(chromatic | fg_seed, iterations=n)
        bg = bg & ~protect

    both = fg & bg
    if both.any():
        fg[both] = chroma[both] >= p.chroma_fg_min
        bg[both] = ~fg[both]

    trimap = np.full(rgb.shape[:2], 0.5, dtype=np.float64)
    trimap[bg] = 0.0
    trimap[fg] = 1.0
    return trimap


def paper_subtract(rgb: np.ndarray, alpha: np.ndarray, paper: np.ndarray) -> np.ndarray:
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
) -> tuple[np.ndarray, dict[str, Any], np.ndarray, np.ndarray]:
    mean = paper_mean(rgb)
    t0 = time.time()
    trimap = build_trimap(rgb, bria, p)
    t_trimap = time.time() - t0

    unk = float((trimap == 0.5).mean() * 100.0)
    print(
        f"[trimap] fg={(trimap==1).mean()*100:.3f}% bg={(trimap==0).mean()*100:.3f}% "
        f"unk={unk:.3f}% ({t_trimap:.1f}s)"
    )

    image = rgb.astype(np.float64) / 255.0
    t1 = time.time()
    alpha = estimate_alpha_cf(
        image,
        trimap,
        cg_kwargs={"maxiter": p.cg_maxiter, "rtol": 1e-5},
    )
    alpha = np.clip(alpha, 0.0, 1.0).astype(np.float32)
    t_cf = time.time() - t1
    print(f"[cf] done in {t_cf:.1f}s  soft={((alpha>0.05)&(alpha<0.95)).mean()*100:.3f}%")

    rgb_out = paper_subtract(rgb, alpha, mean)

    hard = alpha >= p.flatten_alpha_min
    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.where(hard, 255, 0).astype(np.uint8)
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
        "cf_seconds": float(t_cf),
        "trimap_seconds": float(t_trimap),
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


def upsample_rgba(rgba: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    im = Image.fromarray(rgba, "RGBA")
    up = im.resize(size, Image.Resampling.NEAREST)
    return np.asarray(up, dtype=np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-bria", action="store_true")
    ap.add_argument("--chroma", type=float, default=14.0)
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--bria-erode", type=int, default=8)
    ap.add_argument("--edge-unk", type=int, default=6)
    ap.add_argument("--clearance", type=int, default=0)
    ap.add_argument("--flatten", type=float, default=0.15)
    ap.add_argument("--full-max", type=int, default=3600)
    ap.add_argument("--half", action="store_true")
    ap.add_argument("--tag", type=str, default="v10c-edgeunk")
    ap.add_argument("--prefix", type=str, default="18-cfd-v10c")
    args = ap.parse_args()

    p = Params(
        chroma_fg_min=args.chroma,
        chroma_dilate_px=args.dilate,
        bria_erode_px=args.bria_erode,
        edge_unknown_px=args.edge_unk,
        enclosed_paper_clearance_px=args.clearance,
        flatten_alpha_min=args.flatten,
        use_bria=not args.no_bria,
        half_res=args.half,
    )

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    print(f"[load] {rgb_path}")
    rgb_full = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    print(f"[load] rgb {rgb_full.shape[1]}x{rgb_full.shape[0]}")

    bria_full = None
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
        bria_a = bria_a.resize((rgb_full.shape[1], rgb_full.shape[0]), Image.Resampling.NEAREST)
        bria_full = np.asarray(bria_a, dtype=np.uint8)
        print(f"[load] bria {bria_full.shape[1]}x{bria_full.shape[0]}")

    if p.half_res:
        h, w = rgb_full.shape[:2]
        rgb = np.asarray(
            Image.fromarray(rgb_full).resize((w // 2, h // 2), Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        bria = None
        if bria_full is not None:
            bria = np.asarray(
                Image.fromarray(bria_full).resize((w // 2, h // 2), Image.Resampling.NEAREST),
                dtype=np.uint8,
            )
        p_run = Params(
            **{
                **asdict(p),
                "chroma_dilate_px": max(1, p.chroma_dilate_px // 2),
                "bria_erode_px": max(1, p.bria_erode_px // 2),
                "edge_unknown_px": max(2, p.edge_unknown_px // 2),
                "enclosed_paper_clearance_px": p.enclosed_paper_clearance_px // 2,
            }
        )
        print(f"[half] working at {rgb.shape[1]}x{rgb.shape[0]}")
    else:
        rgb = rgb_full
        bria = bria_full
        p_run = p

    rgba_work, metrics, trimap, alpha = run_pipeline(rgb, bria, p_run)

    if p.half_res:
        rgba = upsample_rgba(rgba_work, (rgb_full.shape[1], rgb_full.shape[0]))
        trimap_full = np.asarray(
            Image.fromarray((trimap * 2).astype(np.uint8), "L").resize(
                (rgb_full.shape[1], rgb_full.shape[0]), Image.Resampling.NEAREST
            ),
            dtype=np.float64,
        ) / 2.0
        metrics["half_res"] = True
        metrics["work_size"] = [int(rgb.shape[1]), int(rgb.shape[0])]
    else:
        rgba = rgba_work
        trimap_full = trimap
        metrics["half_res"] = False
        metrics["work_size"] = [int(rgb.shape[1]), int(rgb.shape[0])]

    out_dir = REPO / "Images/candidates/image14-research/fusion-cfd-v10"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    tag = args.tag
    out_png = out_dir / f"14-cfd-{tag}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    metrics_path = out_dir / f"{out_png.stem}-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"[save] {out_png}")

    tvis = np.zeros((*trimap_full.shape, 3), dtype=np.uint8)
    tvis[trimap_full == 0.0] = (0, 0, 255)
    tvis[trimap_full == 1.0] = (0, 255, 0)
    unk_mask = ~(np.isclose(trimap_full, 0.0) | np.isclose(trimap_full, 1.0))
    tvis[unk_mask] = (128, 128, 128)
    Image.fromarray(tvis, "RGB").resize(
        (tvis.shape[1] // 2, tvis.shape[0] // 2), Image.Resampling.NEAREST
    ).save(review / f"{args.prefix}-trimap.jpg", quality=90)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgba.shape[1] / x8_w, rgba.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    rois = {
        "cut00": sx8(3601, 6253, 320, 400),
        "fringe_pink": sx8(4355 - 128, 5013 - 128, 256, 256),
        "enclosed_tri": sx8(6452 - 128, 5548 - 128, 256, 256),
    }
    for name, (x, y, ww, hh) in rois.items():
        crop = tvis[y : y + hh, x : x + ww]
        Image.fromarray(crop, "RGB").resize(
            (crop.shape[1] * 4, crop.shape[0] * 4), Image.Resampling.NEAREST
        ).save(review / f"{args.prefix}-trimap-{name}.jpg", quality=90)

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    save_full(review / f"{args.prefix}-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / f"{args.prefix}-full-magenta.jpg", rgba, mag, args.full_max)
    h = rgba.shape[0]
    save_full(review / f"{args.prefix}-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], args.full_max)
    save_full(review / f"{args.prefix}-upper-magenta.jpg", rgba[: h // 2], mag[: h // 2], args.full_max)

    for name, box in rois.items():
        make_review(review / f"{args.prefix}-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-cfd-v10"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)
    (drive / metrics_path.name).write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps({"out_png": str(out_png.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
