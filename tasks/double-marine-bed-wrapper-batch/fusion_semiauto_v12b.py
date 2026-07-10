#!/usr/bin/env python3
"""v12b Semi-auto sure-FG / sure-BG → PyMatting CF → algebraic unmatte.

Tweak of v12 auto probe: edge-unknown band + no FG grow + rim-kill.
Accepts optional user seed PNGs (red=FG, blue=BG).
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

DEFAULT_RGB = PRODUCT / (
    "Images/candidates/batch-x8-hard180/x4-rgb/"
    "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
)
DEFAULT_BRIA = PRODUCT / (
    "Images/candidates/image14-research/candidates/"
    "14-01-bria-rmbg-alpha-matting-hard180.png"
)


@dataclass
class Params:
    chroma_fg_min: float = 16.0
    dark_luma_max: float = 195.0
    fg_dilate_px: int = 0
    bria_fg_min: int = 200
    bria_erode_px: int = 10
    use_bria: bool = True
    grow_fg: bool = False
    edge_unknown_px: int = 5
    paper_luma_min: float = 250.0
    paper_chroma_max: float = 3.0
    enclosed_min_area: int = 80
    seed_red_r_min: int = 160
    seed_red_gb_max: int = 100
    seed_blue_b_min: int = 160
    seed_blue_rg_max: int = 100
    seeds_only: bool = False
    flatten_alpha_min: float = 0.22
    keep_soft_paint: bool = True
    soft_paint_chroma_min: float = 6.0
    soft_paint_luma_max: float = 245.0
    rim_kill_px: int = 3
    rim_luma_min: float = 248.0
    rim_chroma_max: float = 8.0
    cg_maxiter: int = 250
    half_res: bool = False
    small_noise_area: int = 24


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
    border = set(labeled[0].tolist()) | set(labeled[-1].tolist())
    border |= set(labeled[:, 0].tolist()) | set(labeled[:, -1].tolist())
    border.discard(0)
    return np.isin(labeled, list(border)) if border else np.zeros_like(mask, dtype=bool)


def large_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    labeled, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    areas = np.bincount(labeled.ravel())
    keep = areas >= min_area
    keep[0] = False
    return keep[labeled]


def reconstruct_from_seeds(seeds: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(allowed)
    if count == 0:
        return seeds & allowed
    touch = np.unique(labels[seeds & allowed])
    touch = touch[touch != 0]
    if touch.size == 0:
        return seeds & allowed
    return np.isin(labels, touch)


def decode_user_seeds(seed_rgb: np.ndarray, p: Params) -> tuple[np.ndarray, np.ndarray]:
    r, g, b = seed_rgb[:, :, 0], seed_rgb[:, :, 1], seed_rgb[:, :, 2]
    fg = (r >= p.seed_red_r_min) & (g <= p.seed_red_gb_max) & (b <= p.seed_red_gb_max)
    bg = (b >= p.seed_blue_b_min) & (r <= p.seed_blue_rg_max) & (g <= p.seed_blue_rg_max)
    return fg, bg & ~fg


def load_alpha_like(path: Path, size_wh: tuple[int, int]) -> np.ndarray:
    im = Image.open(path)
    a = im.split()[-1] if im.mode == "RGBA" else im.convert("L")
    return np.asarray(a.resize(size_wh, Image.Resampling.NEAREST), dtype=np.uint8)


def build_seeds(
    rgb: np.ndarray,
    bria: np.ndarray | None,
    user_fg: np.ndarray | None,
    user_bg: np.ndarray | None,
    p: Params,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    luma, chroma = luma_chroma(rgb)
    pure = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max)
    fg = np.zeros(rgb.shape[:2], dtype=bool)
    bg = np.zeros(rgb.shape[:2], dtype=bool)
    stats: dict[str, Any] = {}

    if not p.seeds_only:
        auto_fg = ((chroma >= p.chroma_fg_min) | (luma <= p.dark_luma_max)) & ~pure
        if p.fg_dilate_px > 0:
            auto_fg = ndi.binary_dilation(auto_fg, iterations=p.fg_dilate_px) & ~pure
        if bria is not None and p.use_bria:
            bria_sure = bria >= p.bria_fg_min
            if p.bria_erode_px > 0:
                bria_sure = ndi.binary_erosion(bria_sure, iterations=p.bria_erode_px)
            auto_fg |= bria_sure & ~pure
        fg |= auto_fg
        flood_bg = border_connected(pure)
        enclosed_bg = large_components(pure & ~flood_bg, p.enclosed_min_area)
        bg |= flood_bg | enclosed_bg
        stats.update(
            auto_fg_px=int(auto_fg.sum()),
            flood_bg_px=int(flood_bg.sum()),
            enclosed_bg_px=int(enclosed_bg.sum()),
        )
    else:
        stats.update(auto_fg_px=0, flood_bg_px=0, enclosed_bg_px=0)

    if user_fg is not None:
        fg |= user_fg
        stats["user_fg_px"] = int(user_fg.sum())
    else:
        stats["user_fg_px"] = 0
    if user_bg is not None:
        bg |= user_bg
        stats["user_bg_px"] = int(user_bg.sum())
    else:
        stats["user_bg_px"] = 0

    fg &= ~pure
    bg &= ~fg

    if p.grow_fg:
        grown = reconstruct_from_seeds(fg, (~bg) & (~pure | fg))
        stats["grown_fg_px"] = int(grown.sum())
        fg = grown
    else:
        stats["grown_fg_px"] = int(fg.sum())

    if p.small_noise_area > 0:
        labels, n = ndi.label(fg)
        if n:
            areas = np.bincount(labels.ravel())
            keep = areas >= p.small_noise_area
            keep[0] = False
            fg = keep[labels]

    bg &= ~fg

    if p.edge_unknown_px > 0 and not p.seeds_only:
        n = p.edge_unknown_px
        fg_before = fg.copy()
        if fg.any():
            fg = ndi.binary_erosion(fg, iterations=n)
        protect = ndi.binary_dilation(fg_before | (chroma >= p.chroma_fg_min), iterations=n)
        bg = bg & ~protect
        if user_fg is not None:
            fg |= user_fg & ~pure
        if user_bg is not None:
            bg |= user_bg & ~fg
        stats["edge_unknown_px"] = n

    bg &= ~fg
    return fg, bg, stats


def build_trimap(fg: np.ndarray, bg: np.ndarray) -> np.ndarray:
    trimap = np.full(fg.shape, 0.5, dtype=np.float64)
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


def kill_white_rim(rgba: np.ndarray, p: Params) -> np.ndarray:
    if p.rim_kill_px <= 0:
        return rgba
    a = rgba[:, :, 3] > 0
    if not a.any():
        return rgba
    luma, chroma = luma_chroma(rgba[:, :, :3])
    kill = (luma >= p.rim_luma_min) & (chroma <= p.rim_chroma_max) & a
    kill &= ndi.binary_dilation(~a, iterations=p.rim_kill_px) & a
    out = rgba.copy()
    out[kill, :] = 0
    return out


def finalize_rgba(
    rgb: np.ndarray, alpha: np.ndarray, paper: np.ndarray, p: Params
) -> tuple[np.ndarray, np.ndarray]:
    rgb_out = paper_subtract(rgb, alpha, paper)
    a = np.clip(alpha, 0, 1).astype(np.float32)
    luma, chroma = luma_chroma(rgb_out)
    hard = a >= p.flatten_alpha_min
    soft = (a > 1e-3) & (a < p.flatten_alpha_min)
    if p.keep_soft_paint:
        paintish = (chroma >= p.soft_paint_chroma_min) | (luma <= p.soft_paint_luma_max)
        hard |= soft & paintish
    hard &= ~((luma >= p.rim_luma_min) & (chroma <= p.rim_chroma_max) & (a < 0.95))
    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.where(hard, 255, 0).astype(np.uint8)
    rgba[~hard, :3] = 0
    return kill_white_rim(rgba, p), a


def run_pipeline(
    rgb: np.ndarray,
    bria: np.ndarray | None,
    user_fg: np.ndarray | None,
    user_bg: np.ndarray | None,
    p: Params,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray, np.ndarray]:
    mean = paper_mean(rgb)
    work_rgb = rgb
    scale = 1
    if p.half_res:
        scale = 2
        wh = (rgb.shape[1] // 2, rgb.shape[0] // 2)
        work_rgb = np.asarray(Image.fromarray(rgb).resize(wh, Image.Resampling.BILINEAR), dtype=np.uint8)
        if bria is not None:
            bria = np.asarray(Image.fromarray(bria).resize(wh, Image.Resampling.NEAREST), dtype=np.uint8)
        if user_fg is not None:
            user_fg = np.asarray(
                Image.fromarray((user_fg.astype(np.uint8) * 255)).resize(wh, Image.Resampling.NEAREST),
                dtype=bool,
            )
        if user_bg is not None:
            user_bg = np.asarray(
                Image.fromarray((user_bg.astype(np.uint8) * 255)).resize(wh, Image.Resampling.NEAREST),
                dtype=bool,
            )
        mean = paper_mean(work_rgb)

    t0 = time.time()
    fg, bg, seed_stats = build_seeds(work_rgb, bria, user_fg, user_bg, p)
    trimap = build_trimap(fg, bg)
    t_seeds = time.time() - t0
    print(
        f"[seeds] fg={fg.mean()*100:.2f}% bg={bg.mean()*100:.2f}% "
        f"unk={(trimap==0.5).mean()*100:.2f}% ({t_seeds:.1f}s)"
    )

    t1 = time.time()
    alpha = np.clip(
        estimate_alpha_cf(
            work_rgb.astype(np.float64) / 255.0,
            trimap,
            cg_kwargs={"maxiter": p.cg_maxiter, "rtol": 1e-5},
        ),
        0.0,
        1.0,
    ).astype(np.float32)
    t_cf = time.time() - t1
    print(f"[cf] {t_cf:.1f}s soft={((alpha>0.05)&(alpha<0.95)).mean()*100:.2f}%")

    if scale != 1:
        full = (rgb.shape[1], rgb.shape[0])
        alpha = (
            np.asarray(
                Image.fromarray((alpha * 255).astype(np.uint8)).resize(full, Image.Resampling.BILINEAR),
                dtype=np.float32,
            )
            / 255.0
        )
        trimap_up = (
            np.asarray(
                Image.fromarray((trimap * 255).astype(np.uint8)).resize(full, Image.Resampling.NEAREST),
                dtype=np.float64,
            )
            / 255.0
        )
        trimap = np.full(rgb.shape[:2], 0.5, dtype=np.float64)
        trimap[trimap_up < 0.25] = 0.0
        trimap[trimap_up > 0.75] = 1.0
        mean = paper_mean(rgb)

    rgba, alpha_f = finalize_rgba(rgb, alpha, mean, p)
    hard = rgba[:, :, 3] > 0
    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "trimap_fg_pct": float(100.0 * (trimap == 1.0).mean()),
        "trimap_bg_pct": float(100.0 * (trimap == 0.0).mean()),
        "trimap_unk_pct": float(100.0 * (trimap == 0.5).mean()),
        "soft_before_flatten_pct": float(100.0 * ((alpha_f > 0.05) & (alpha_f < 0.95)).mean()),
        "opaque_pct": float(100.0 * hard.mean()),
        "transparent_pct": float(100.0 * (~hard).mean()),
        "semi_pct": 0.0,
        "seed_stats": seed_stats,
        "timing_s": {"seeds": t_seeds, "cf": t_cf},
        "params": asdict(p),
    }
    return rgba, metrics, trimap, alpha_f


def composite_preview(rgba: np.ndarray, bg: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.float32)
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    return np.clip(rgb * a[:, :, None] + bg.astype(np.float32) * (1.0 - a[:, :, None]), 0, 255).astype(
        np.uint8
    )


def save_full(path: Path, rgba: np.ndarray, bg: np.ndarray, max_side: int) -> None:
    prev = Image.fromarray(composite_preview(rgba, bg))
    w, h = prev.size
    s = min(1.0, max_side / max(w, h))
    if s < 1.0:
        prev = prev.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
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
    im = Image.fromarray(board)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=93)


def trimap_vis(trimap: np.ndarray) -> np.ndarray:
    tvis = np.zeros((*trimap.shape, 3), dtype=np.uint8)
    tvis[trimap == 0.0] = (0, 0, 255)
    tvis[trimap == 1.0] = (255, 0, 0)
    tvis[trimap == 0.5] = (128, 128, 128)
    return tvis


def write_seed_template(path: Path, rgb: np.ndarray, opacity: float = 0.35) -> None:
    base = (rgb.astype(np.float32) * (1.0 - opacity) + 255.0 * opacity).astype(np.uint8)
    Image.fromarray(base).save(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rgb", type=Path, default=DEFAULT_RGB)
    ap.add_argument("--bria", type=Path, default=DEFAULT_BRIA)
    ap.add_argument("--no-bria", action="store_true")
    ap.add_argument("--seeds", type=Path, default=None)
    ap.add_argument("--seeds-only", action="store_true")
    ap.add_argument("--grow", action="store_true")
    ap.add_argument("--chroma", type=float, default=16.0)
    ap.add_argument("--dark-luma", type=float, default=195.0)
    ap.add_argument("--paper-luma", type=float, default=250.0)
    ap.add_argument("--paper-chroma", type=float, default=3.0)
    ap.add_argument("--enclosed-min-area", type=int, default=80)
    ap.add_argument("--edge-unknown", type=int, default=5)
    ap.add_argument("--flatten", type=float, default=0.22)
    ap.add_argument("--bria-erode", type=int, default=10)
    ap.add_argument("--rim-kill", type=int, default=3)
    ap.add_argument("--half-res", action="store_true")
    ap.add_argument("--full-max", type=int, default=3600)
    ap.add_argument("--tag", type=str, default="edgeunk")
    ap.add_argument("--write-seed-template", action="store_true")
    args = ap.parse_args()

    p = Params(
        chroma_fg_min=args.chroma,
        dark_luma_max=args.dark_luma,
        paper_luma_min=args.paper_luma,
        paper_chroma_max=args.paper_chroma,
        enclosed_min_area=args.enclosed_min_area,
        edge_unknown_px=args.edge_unknown,
        flatten_alpha_min=args.flatten,
        bria_erode_px=args.bria_erode,
        rim_kill_px=args.rim_kill,
        use_bria=not args.no_bria,
        grow_fg=args.grow,
        seeds_only=args.seeds_only,
        half_res=args.half_res,
    )

    rgb = np.asarray(Image.open(args.rgb).convert("RGB"), dtype=np.uint8)
    h, w = rgb.shape[:2]

    bria = None
    if p.use_bria and args.bria.exists():
        bria = load_alpha_like(args.bria, (w, h))
        print(f"[bria] loaded {args.bria.name}")
    elif p.use_bria:
        print(f"[bria] missing: {args.bria}")

    user_fg = user_bg = None
    if args.seeds is not None:
        seed_im = Image.open(args.seeds).convert("RGB")
        if seed_im.size != (w, h):
            seed_im = seed_im.resize((w, h), Image.Resampling.NEAREST)
        user_fg, user_bg = decode_user_seeds(np.asarray(seed_im, dtype=np.uint8), p)
        print(f"[seeds] user fg={user_fg.sum()} bg={user_bg.sum()}")

    out_dir = REPO / "Images/candidates/image14-research/fusion-semiauto-v12"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    if args.write_seed_template:
        tpl = out_dir / "14-semiauto-v12-seed-template.png"
        write_seed_template(tpl, rgb)
        print(f"[template] {tpl}")

    rgba, metrics, trimap, _ = run_pipeline(rgb, bria, user_fg, user_bg, p)

    tag = args.tag
    if args.half_res:
        tag = f"{tag}-half"
    stem = f"14-semiauto-v12-{tag}-x4"
    out_png = out_dir / f"{stem}.png"
    Image.fromarray(rgba).save(out_png, optimize=True)
    (out_dir / f"{stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    tvis = trimap_vis(trimap)
    Image.fromarray(tvis).resize(
        (max(1, tvis.shape[1] // 2), max(1, tvis.shape[0] // 2)), Image.Resampling.NEAREST
    ).save(review / f"22-semiauto-v12-{tag}-trimap.jpg", quality=90)
    overlay = rgb.copy()
    overlay[trimap == 1.0] = (255, 40, 40)
    overlay[trimap == 0.0] = (40, 40, 255)
    mix = (0.55 * rgb.astype(np.float32) + 0.45 * overlay.astype(np.float32)).astype(np.uint8)
    Image.fromarray(mix).resize(
        (max(1, mix.shape[1] // 2), max(1, mix.shape[0] // 2)), Image.Resampling.BILINEAR
    ).save(review / f"22-semiauto-v12-{tag}-seed-overlay.jpg", quality=90)

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    save_full(review / f"22-semiauto-v12-{tag}-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / f"22-semiauto-v12-{tag}-full-magenta.jpg", rgba, mag, args.full_max)
    save_full(review / f"22-semiauto-v12-{tag}-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], args.full_max)

    x8_w, x8_h = 7528, 13376
    sx, sy = w / x8_w, h / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
    ]:
        make_review(review / f"22-semiauto-v12-{tag}-{name}.jpg", rgba, *box, scale=3)

    (out_dir / "README-seeds.md").write_text(
        """# Semi-auto v12 — painting seeds for the next round

Pixel-auto BG removal is ill-posed on pale watercolor. This tool accepts
**sure FG / sure BG seeds**; everything else is solved by closed-form matting
+ algebraic paper unmatte.

## How to paint seeds

1. Open `14-semiauto-v12-seed-template.png` (or the source RGB) in Preview /
   Photoshop / Krita at **native x4 size** (do not rescale).
2. Paint on a **new layer**:
   - **Red** `(R≥160, G≤100, B≤100)` = sure **foreground** (keep pale wash).
   - **Blue** `(B≥160, R≤100, G≤100)` = sure **background** (paper / holes).
3. Export flat RGB PNG. Soft brushes OK; only saturated red/blue count.
4. Re-run:

```bash
python3 tasks/double-marine-bed-wrapper-batch/fusion_semiauto_v12b.py \\
  --seeds /path/to/your-seeds.png --tag user1 --half-res
```

Optional: `--seeds-only` / `--no-bria` / `--edge-unknown N` / `--rim-kill N`.

## What auto seeds already do

- FG: chroma ≥ 16 or luma ≤ 195 + eroded BRIA (no grow by default).
- BG: border-connected pure paper + large enclosed pure-paper (≥80 px).
- Edge unknown band (~5 px) + rim-kill of near-white opaque boundary pixels.

Paint **only failures**: pale wash deleted → red; paper left opaque → blue.
""",
        encoding="utf-8",
    )

    # Keep canonical script name as symlink/copy for the task deliverable
    canonical = Path(__file__).with_name("fusion_semiauto_v12.py")
    if canonical.resolve() != Path(__file__).resolve():
        canonical.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    drive = PRODUCT / "Images/candidates/image14-research/fusion-semiauto-v12"
    try:
        drive.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba).save(drive / out_png.name, optimize=True)
    except OSError as e:
        print(f"[drive] skip: {e}")

    print(json.dumps({"out_png": str(out_png.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
