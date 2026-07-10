#!/usr/bin/env python3
"""LaMa mask-locked paper reconstruct → delta FG (image14 fork-1).

Erase ONLY approximate art (dilated); lock true outer paper pixels;
run real LaMa generative inpaint; delta = |src − paper|; soft/binary alpha.

MPS note: big-lama.pt TorchScript must load with map_location=cpu then .to(mps).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from scipy import ndimage as ndi
from simple_lama_inpainting.models.model import (
    LAMA_MODEL_URL,
    download_model,
    prepare_img_and_mask,
)

Image.MAX_IMAGE_PIXELS = None


class LamaRunner:
    """Load TorchScript with map_location=cpu (required on Mac MPS)."""

    def __init__(self, device: torch.device) -> None:
        model_path = os.environ.get("LAMA_MODEL") or download_model(LAMA_MODEL_URL)
        self.model = torch.jit.load(model_path, map_location="cpu")
        self.model.eval()
        self.model.to(device)
        self.device = device

    def __call__(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        image_t, mask_t = prepare_img_and_mask(image, mask, self.device)
        with torch.inference_mode():
            inpainted = self.model(image_t, mask_t)
            cur = inpainted[0].permute(1, 2, 0).detach().cpu().numpy()
            cur = np.clip(cur * 255, 0, 255).astype(np.uint8)
            return Image.fromarray(cur)


REPO = Path(__file__).resolve().parents[2]
PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)


@dataclass
class Params:
    paper_chroma_max: float = 8.0
    paper_luma_min: float = 242.0
    paper_dist_max: float = 14.0
    erase_dilate: int = 3
    lama_max_side: int = 2048
    delta_thr: float = 10.0
    soft_lo: float = 6.0
    soft_hi: float = 22.0
    paper_sub_rim: int = 2
    paper_sub_thr: float = 8.0
    small_noise_area: int = 40


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(
        np.float32
    )
    chroma = (rgb.max(2) - rgb.min(2)).astype(np.float32)
    return luma, chroma


def paper_model(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
    return samples.mean(0), np.maximum(samples.std(0), 1.0)


def bg_distance(rgb: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (rgb.astype(np.float32) - mean[None, None, :]) / std[None, None, :]
    return np.sqrt((z * z).sum(2))


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    ids = set(labels[0].tolist()) | set(labels[-1].tolist())
    ids |= set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    ids.discard(0)
    return np.isin(labels, list(ids)) if ids else np.zeros_like(mask, dtype=bool)


def build_erase_mask(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paperish = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (dist <= p.paper_dist_max)
    outer_paper = border_connected(paperish)
    art = ~outer_paper
    erase = art.copy()
    if p.erase_dilate > 0:
        erase = ndi.binary_dilation(erase, iterations=p.erase_dilate)
    erase = erase & ~outer_paper

    meta = {
        "paper_mean_rgb": [float(x) for x in mean],
        "paper_std_rgb": [float(x) for x in std],
        "outer_paper_px": int(outer_paper.sum()),
        "erase_px": int(erase.sum()),
        "erase_pct": float(100.0 * erase.mean()),
    }
    return erase, outer_paper, meta


def pad_to_mod(arr: np.ndarray, mod: int = 8) -> tuple[np.ndarray, tuple[int, int]]:
    h, w = arr.shape[:2]
    nh = (h + mod - 1) // mod * mod
    nw = (w + mod - 1) // mod * mod
    if nh == h and nw == w:
        return arr, (0, 0)
    if arr.ndim == 2:
        out = np.zeros((nh, nw), dtype=arr.dtype)
        out[:h, :w] = arr
    else:
        out = np.zeros((nh, nw, arr.shape[2]), dtype=arr.dtype)
        out[:h, :w] = arr
    return out, (nh - h, nw - w)


def run_lama(
    rgb: np.ndarray,
    erase: np.ndarray,
    lama: LamaRunner,
    max_side: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    h, w = rgb.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        nw, nh = max(8, int(round(w * scale))), max(8, int(round(h * scale)))
        nw, nh = (nw // 8) * 8, (nh // 8) * 8
        rgb_s = np.asarray(
            Image.fromarray(rgb).resize((nw, nh), Image.Resampling.LANCZOS), dtype=np.uint8
        )
        erase_s = (
            np.asarray(
                Image.fromarray((erase.astype(np.uint8) * 255)).resize(
                    (nw, nh), Image.Resampling.NEAREST
                ),
                dtype=np.uint8,
            )
            > 127
        )
    else:
        rgb_s, erase_s = rgb, erase
        nw, nh = w, h

    rgb_p, _ = pad_to_mod(rgb_s, 8)
    erase_p, _ = pad_to_mod(erase_s.astype(np.uint8) * 255, 8)
    img = Image.fromarray(rgb_p, "RGB")
    mask = Image.fromarray(erase_p, "L")

    t0 = time.time()
    out = lama(img, mask)
    elapsed = time.time() - t0
    paper_s = np.asarray(out, dtype=np.uint8)[:nh, :nw]

    if scale < 1.0:
        paper = np.asarray(
            Image.fromarray(paper_s).resize((w, h), Image.Resampling.LANCZOS), dtype=np.uint8
        )
    else:
        paper = paper_s

    locked = paper.copy()
    locked[~erase] = rgb[~erase]

    info = {
        "lama_scale": float(scale),
        "lama_wh": [int(nw), int(nh)],
        "lama_seconds": float(elapsed),
        "device": str(lama.device),
    }
    return locked, info


def delta_alpha(
    rgb: np.ndarray,
    paper: np.ndarray,
    erase: np.ndarray,
    outer_paper: np.ndarray,
    p: Params,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    delta = np.abs(rgb.astype(np.float32) - paper.astype(np.float32)).max(axis=2)
    soft = np.clip((delta - p.soft_lo) / max(1e-6, (p.soft_hi - p.soft_lo)), 0.0, 1.0)
    soft[outer_paper] = 0.0
    soft[(~erase) & (delta < p.delta_thr)] = 0.0

    if p.paper_sub_rim > 0:
        rim = erase & ~ndi.binary_erosion(erase, iterations=p.paper_sub_rim)
        mean, _ = paper_model(rgb)
        d_paper = np.sqrt(((rgb.astype(np.float32) - mean[None, None, :]) ** 2).sum(2))
        soft[rim & (d_paper < p.paper_sub_thr) & (delta < p.soft_hi)] *= 0.35
        soft[rim & (d_paper < p.paper_sub_thr * 0.6)] = 0.0

    fg = soft >= 0.5
    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_noise_area
        keep[0] = False
        fg = keep[labels]
        soft = soft * fg.astype(np.float32)

    mean, _ = paper_model(rgb)
    alpha = soft.copy()
    rgb_out = rgb.copy().astype(np.float32)
    partial = (alpha > 0.02) & (alpha < 0.98)
    if partial.any():
        a = np.maximum(alpha[partial], 1e-3)[:, None]
        unb = (rgb[partial].astype(np.float32) - (1.0 - a) * mean[None, :]) / a
        rgb_out[partial] = np.clip(unb, 0, 255)

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(rgb_out, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)

    metrics = {
        "delta_mean_erase": float(delta[erase].mean()) if erase.any() else 0.0,
        "delta_p50_erase": float(np.median(delta[erase])) if erase.any() else 0.0,
        "delta_p90_erase": float(np.percentile(delta[erase], 90)) if erase.any() else 0.0,
        "opaque_pct": float(100.0 * (rgba[:, :, 3] == 255).mean()),
        "transparent_pct": float(100.0 * (rgba[:, :, 3] == 0).mean()),
        "semi_pct": float(100.0 * ((rgba[:, :, 3] > 0) & (rgba[:, :, 3] < 255)).mean()),
        "fg_px": int((rgba[:, :, 3] > 0).sum()),
    }
    return rgba, delta, metrics


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
    ap.add_argument("--lama-max", type=int, default=2048)
    ap.add_argument("--erase-dilate", type=int, default=3)
    ap.add_argument("--soft-lo", type=float, default=6.0)
    ap.add_argument("--soft-hi", type=float, default=22.0)
    ap.add_argument("--delta-thr", type=float, default=10.0)
    ap.add_argument("--full-max", type=int, default=3600)
    ap.add_argument("--device", type=str, default="")
    ap.add_argument("--tag", type=str, default="a")
    args = ap.parse_args()

    p = Params(
        lama_max_side=args.lama_max,
        erase_dilate=args.erase_dilate,
        soft_lo=args.soft_lo,
        soft_hi=args.soft_hi,
        delta_thr=args.delta_thr,
    )

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    erase, outer_paper, mask_meta = build_erase_mask(rgb, p)

    if args.device:
        device = torch.device(args.device)
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    print(f"loading LaMa on {device} …", flush=True)
    lama = LamaRunner(device=device)
    paper, lama_info = run_lama(rgb, erase, lama, p.lama_max_side)
    rgba, delta, delta_meta = delta_alpha(rgb, paper, erase, outer_paper, p)

    metrics: dict[str, Any] = {
        **mask_meta,
        **lama_info,
        **delta_meta,
        "params": asdict(p),
        "tag": args.tag,
        "source": str(rgb_path),
    }

    out_dir = REPO / "Images/candidates/image14-research/fusion-lama-v12"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    stem = f"14-lama-v12-{args.tag}-x4"
    out_png = out_dir / f"{stem}.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    Image.fromarray(paper, "RGB").save(out_dir / f"{stem}-paper-estimate.png", optimize=True)
    Image.fromarray((erase.astype(np.uint8) * 255), "L").save(out_dir / f"{stem}-erase-mask.png")
    dvis = np.clip(delta / 40.0 * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(dvis, "L").save(out_dir / f"{stem}-delta.png")
    overlay = rgb.copy()
    overlay[erase] = (overlay[erase].astype(np.float32) * 0.45 + np.array([255, 40, 40]) * 0.55).astype(
        np.uint8
    )
    Image.fromarray(overlay, "RGB").save(
        out_dir / f"{stem}-erase-overlay.jpg", quality=85, optimize=True
    )

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    prefix = f"21-lama-v12-{args.tag}"
    save_full(review / f"{prefix}-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / f"{prefix}-full-magenta.jpg", rgba, mag, args.full_max)
    h = rgba.shape[0]
    save_full(review / f"{prefix}-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], args.full_max)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
    ]:
        make_review(review / f"{prefix}-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-lama-v12"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)
    (drive / f"{stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps({"out_png": str(out_png.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
