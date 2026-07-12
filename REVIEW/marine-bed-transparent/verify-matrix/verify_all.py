#!/usr/bin/env python3
"""
Uniform gate harness for the green-key shoot-out.

Applies IDENTICAL, deterministic gates to all 6 candidates. All masks
(background / art / boundary-band / bubble regions / hue strata) are derived
ONLY from the FROZEN source raw (raw_green_P1.png) — never from any
candidate — so every candidate is judged against the same ground truth.

ΔE: uses skimage.color.deltaE_cie76 (CIE76 / Euclidean-in-Lab ΔE) if
skimage is importable in the running interpreter; otherwise falls back to
a hand-rolled ΔE76 implementation (RGB->Lab via colorsys-free matrix math).
This run: skimage is available (checked at runtime, reported in verdict.json
under "deltaE_impl").

Usage:
    .venv-bg/bin/python3 REVIEW/marine-bed-transparent/verify-matrix/verify_all.py

Outputs (written next to this script):
    verdict.json   - every raw number, per candidate, per gate
    VERDICT.md     - ranked table + PASS/FAIL per gate + one-line defect summary
    BOARD-verify.png - all 6 candidates over magenta, labeled, + defect heatmap row
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # .../product images repo

RAW_PATH = REPO_ROOT / "REVIEW/marine-bed-transparent/chroma-lane/raws/raw_green_P1.png"

CANDIDATES = {
    "A_keyed-v3": REPO_ROOT / "REVIEW/marine-bed-transparent/chroma-lane/keyed-v3/keyed_green_P1.png",
    "B_classic": REPO_ROOT / "REVIEW/marine-bed-transparent/verify-matrix/laneB-classic/keyed_classic.png",
    "C_vitmatte": REPO_ROOT / "REVIEW/marine-bed-transparent/verify-matrix/laneC-vitmatte/keyed_rgba.png",
    "D1_bria-rmbg": REPO_ROOT / "REVIEW/marine-bed-transparent/verify-matrix/laneD-ml/bria-rmbg.png",
    "D2_birefnet": REPO_ROOT / "REVIEW/marine-bed-transparent/verify-matrix/laneD-ml/birefnet-general.png",
    "E_ffmpeg-chroma": REPO_ROOT / "REVIEW/marine-bed-transparent/verify-matrix/laneE-standard/ffmpeg_chroma_0x00FF00_0.10_0.05.png",
}

OUT_JSON = HERE / "verdict.json"
OUT_MD = HERE / "VERDICT.md"
OUT_BOARD = HERE / "BOARD-verify.png"

# ---- thresholds (fixed, identical for every candidate) ----------------
BG_DELTAE_MAX = 3.0       # source pixel counted "definitely background" if ΔE(vs modal green) < this
ART_DELTAE_MIN = 15.0     # source pixel counted "definitely art" if ΔE(vs modal green) > this
GREEN_DOMINANCE = 30.0    # G > max(R,B) + this => "greenish" test for residual-green gate
ALPHA_RESIDUAL_THRESH = 0.5
ALPHA_DELETED_THRESH = 0.5
BAND_PX = 3               # boundary band width in px
BORDER_STRIP_PX = 3
BORDER_ALPHA_THRESH = 0.1
RECOMP_ALPHA_LEAK_THRESH = 0.02
EROSION_INTERIOR_PX = 6   # erode art mask this much to get "safely interior" pixels for despill-confinement gate

MODAL_GREEN = np.array([2.0, 240.0, 8.0])

# ---- ΔE implementation --------------------------------------------------
try:
    from skimage.color import rgb2lab, deltaE_cie76
    DELTAE_IMPL = "skimage.color.deltaE_cie76"

    def rgb_to_lab(rgb_uint8_or_float):
        arr = np.asarray(rgb_uint8_or_float, dtype=np.float64) / 255.0
        return rgb2lab(arr)

    def delta_e(lab_a, lab_b):
        return deltaE_cie76(lab_a, lab_b)

except ImportError:
    DELTAE_IMPL = "hand-rolled ΔE76 (skimage unavailable)"

    def _srgb_to_linear(c):
        c = np.clip(c, 0, 1)
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

    def rgb_to_lab(rgb_uint8_or_float):
        arr = np.asarray(rgb_uint8_or_float, dtype=np.float64) / 255.0
        lin = _srgb_to_linear(arr)
        R, G, B = lin[..., 0], lin[..., 1], lin[..., 2]
        X = R * 0.4124564 + G * 0.3575761 + B * 0.1804375
        Y = R * 0.2126729 + G * 0.7151522 + B * 0.0721750
        Z = R * 0.0193339 + G * 0.1191920 + B * 0.9503041
        Xn, Yn, Zn = 0.95047, 1.0, 1.08883
        xr, yr, zr = X / Xn, Y / Yn, Z / Zn

        def f(t):
            d = 6.0 / 29.0
            return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4.0 / 29.0)

        fx, fy, fz = f(xr), f(yr), f(zr)
        L = 116 * fy - 16
        a = 500 * (fx - fy)
        b = 200 * (fy - fz)
        return np.stack([L, a, b], axis=-1)

    def delta_e(lab_a, lab_b):
        d = lab_a - lab_b
        return np.sqrt((d ** 2).sum(axis=-1))


def largest_component_px(mask):
    if not mask.any():
        return 0
    lbl, n = ndi.label(mask)
    if n == 0:
        return 0
    sizes = ndi.sum(mask, lbl, index=range(1, n + 1))
    return int(sizes.max())


def load_rgba(path):
    im = Image.open(path).convert("RGBA")
    arr = np.array(im).astype(np.float64)
    rgb = arr[..., :3]
    alpha = arr[..., 3] / 255.0
    return rgb, alpha


def main():
    raw_rgb = np.array(Image.open(RAW_PATH).convert("RGB")).astype(np.float64)
    H, W, _ = raw_rgb.shape
    raw_lab = rgb_to_lab(raw_rgb)
    modal_lab = rgb_to_lab(MODAL_GREEN.reshape(1, 1, 3))[0, 0]

    source_deltaE = delta_e(raw_lab, np.broadcast_to(modal_lab, raw_lab.shape))

    # ---- source-derived ground-truth masks (SAME for every candidate) ----
    bg_mask = source_deltaE < BG_DELTAE_MAX               # definitely background
    art_mask = source_deltaE > ART_DELTAE_MIN             # definitely art
    n_art_px = int(art_mask.sum())

    # boundary band: pixels within BAND_PX of the art/bg border, derived from art_mask
    art_dil = ndi.binary_dilation(art_mask, iterations=BAND_PX)
    art_ero = ndi.binary_erosion(art_mask, iterations=BAND_PX)
    band_mask = art_dil & ~art_ero  # ring straddling the source silhouette edge
    band_in_art = band_mask & art_mask
    band_in_bg = band_mask & ~art_mask

    interior_mask = ndi.binary_erosion(art_mask, iterations=EROSION_INTERIOR_PX)

    # hue strata within interior_mask, from source RAW colors (yellow=seahorse, warm-pale=sand)
    R, G, B = raw_rgb[..., 0], raw_rgb[..., 1], raw_rgb[..., 2]
    maxc = raw_rgb.max(axis=-1)
    minc = raw_rgb.min(axis=-1)
    delta = maxc - minc
    hue = np.zeros((H, W))
    nz = delta > 1e-6
    rc = np.zeros((H, W)); gc = np.zeros((H, W)); bc = np.zeros((H, W))
    with np.errstate(divide="ignore", invalid="ignore"):
        rc[nz] = (maxc[nz] - R[nz]) / delta[nz]
        gc[nz] = (maxc[nz] - G[nz]) / delta[nz]
        bc[nz] = (maxc[nz] - B[nz]) / delta[nz]
    is_r_max = (R == maxc) & nz
    is_g_max = (G == maxc) & (~is_r_max) & nz
    is_b_max = (~is_r_max) & (~is_g_max) & nz
    hue = np.where(is_r_max, bc - gc, hue)
    hue = np.where(is_g_max, 2.0 + rc - bc, hue)
    hue = np.where(is_b_max, 4.0 + gc - rc, hue)
    hue = (hue / 6.0) % 1.0
    hue_deg = hue * 360.0
    sat = np.where(maxc > 0, delta / np.maximum(maxc, 1e-6), 0.0)
    val = maxc / 255.0

    # yellow (seahorse): hue ~40-65deg, decently saturated
    yellow_stratum = interior_mask & (hue_deg >= 35) & (hue_deg <= 70) & (sat > 0.25) & (val > 0.25)
    # warm-pale (sand): low saturation, warm hue, mid-high value
    warm_pale_stratum = interior_mask & (sat < 0.30) & (val > 0.45) & (hue_deg < 90)

    # bubble auto-detect: bluish circular regions in upper half of source
    upper_half = np.zeros((H, W), dtype=bool)
    upper_half[: H // 2, :] = True
    bluish = (B > R + 10) & (B > G) & (val > 0.35) & upper_half & ~bg_mask
    bluish_clean = ndi.binary_opening(bluish, iterations=2)
    lbl_bub, n_bub = ndi.label(bluish_clean)
    bubble_regions = []
    if n_bub > 0:
        sizes = ndi.sum(bluish_clean, lbl_bub, index=range(1, n_bub + 1))
        order = np.argsort(sizes)[::-1]
        for idx in order[:3]:
            comp_id = idx + 1
            size = sizes[idx]
            if size < 25:
                continue
            ys, xs = np.where(lbl_bub == comp_id)
            cy, cx = ys.mean(), xs.mean()
            r_est = np.sqrt(size / np.pi)
            bubble_regions.append({
                "center": (float(cy), float(cx)),
                "radius_est": float(r_est),
                "size_px": int(size),
            })

    def bubble_masks(region, ring_factor=1.6):
        cy, cx = region["center"]
        r = max(region["radius_est"], 3.0)
        yy, xx = np.mgrid[0:H, 0:W]
        dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        core = dist <= r
        ring = (dist > r) & (dist <= r * ring_factor)
        return core, ring

    border_strip = np.zeros((H, W), dtype=bool)
    border_strip[:BORDER_STRIP_PX, :] = True
    border_strip[-BORDER_STRIP_PX:, :] = True
    border_strip[:, :BORDER_STRIP_PX] = True
    border_strip[:, -BORDER_STRIP_PX:] = True

    results = {}
    heatmaps = {}  # name -> HxWx3 uint8 (red=residual green, blue=deleted art)

    for name, path in CANDIDATES.items():
        rgb, alpha = load_rgba(path)
        cand_lab = rgb_to_lab(rgb)
        deltaE_vs_source = delta_e(cand_lab, raw_lab)

        Rc, Gc, Bc = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        greenish = Gc > np.maximum(Rc, Bc) + GREEN_DOMINANCE

        # ---- gate 1: residual green ----
        residual_mask = (alpha > ALPHA_RESIDUAL_THRESH) & greenish & bg_mask
        g1_count = int(residual_mask.sum())
        g1_max_comp = largest_component_px(residual_mask)

        # ---- gate 2: deleted art ----
        deleted_mask = art_mask & (alpha < ALPHA_DELETED_THRESH)
        g2_count = int(deleted_mask.sum())
        g2_max_comp = largest_component_px(deleted_mask)
        g2_pct_of_art = (g2_count / n_art_px * 100.0) if n_art_px else 0.0

        # ---- gate 3: rim ----
        greenness_cand = Gc - np.maximum(Rc, Bc)
        band_greenness_mean = float(greenness_cand[band_mask].mean()) if band_mask.any() else float("nan")
        interior_greenness_mean = float(greenness_cand[interior_mask].mean()) if interior_mask.any() else float("nan")
        rim_greenness_delta = band_greenness_mean - interior_greenness_mean
        band_deltaE_mean = float(deltaE_vs_source[band_mask].mean()) if band_mask.any() else float("nan")

        # ---- gate 4: despill confinement ----
        despill_interior_mean = float(deltaE_vs_source[interior_mask].mean()) if interior_mask.any() else float("nan")
        despill_yellow_mean = (
            float(deltaE_vs_source[yellow_stratum].mean()) if yellow_stratum.any() else float("nan")
        )
        despill_warm_pale_mean = (
            float(deltaE_vs_source[warm_pale_stratum].mean()) if warm_pale_stratum.any() else float("nan")
        )

        # ---- gate 5: recomposition ----
        bg_leak_pct = float((alpha[bg_mask] > RECOMP_ALPHA_LEAK_THRESH).mean() * 100.0) if bg_mask.any() else 0.0
        if band_mask.any():
            a_band = alpha[band_mask][..., None]
            recon = a_band * rgb[band_mask] + (1 - a_band) * MODAL_GREEN.reshape(1, 3)
            src_band = raw_rgb[band_mask]
            diff = np.abs(recon - src_band).max(axis=-1)
            recomp_band_p95 = float(np.percentile(diff, 95))
        else:
            recomp_band_p95 = float("nan")

        # ---- gate 6: bubbles ----
        bubble_report = []
        for i, region in enumerate(bubble_regions):
            core, ring = bubble_masks(region)
            core_alpha_mean = float(alpha[core].mean()) if core.any() else float("nan")
            ring_alpha_mean = float(alpha[ring].mean()) if ring.any() else float("nan")
            greenish_in_bubble = int((greenish & core & (alpha > 0.5)).sum())
            bubble_report.append({
                "index": i,
                "center_yx": region["center"],
                "radius_est_px": region["radius_est"],
                "core_alpha_mean": core_alpha_mean,
                "ring_alpha_mean": ring_alpha_mean,
                "core_minus_ring_alpha": (core_alpha_mean - ring_alpha_mean)
                if not (np.isnan(core_alpha_mean) or np.isnan(ring_alpha_mean)) else float("nan"),
                "greenish_tint_px_in_core": greenish_in_bubble,
            })

        # ---- gate 7: border occupancy ----
        border_occ_pct = float((alpha[border_strip] > BORDER_ALPHA_THRESH).mean() * 100.0)

        results[name] = {
            "residual_green": {"count_px": g1_count, "max_component_px": g1_max_comp, "target": 0,
                                "pass": g1_count == 0},
            "deleted_art": {"count_px": g2_count, "max_component_px": g2_max_comp,
                             "pct_of_art_px": g2_pct_of_art, "target_pct": 0.1,
                             "pass": g2_pct_of_art < 0.1},
            "rim": {"band_greenness_mean": band_greenness_mean,
                    "interior_greenness_mean": interior_greenness_mean,
                    "rim_greenness_delta": rim_greenness_delta,
                    "band_deltaE_vs_source_mean": band_deltaE_mean,
                    "pass": rim_greenness_delta < 5.0},
            "despill_confinement": {"interior_deltaE_mean": despill_interior_mean,
                                     "yellow_stratum_deltaE_mean": despill_yellow_mean,
                                     "yellow_stratum_px": int(yellow_stratum.sum()),
                                     "warm_pale_stratum_deltaE_mean": despill_warm_pale_mean,
                                     "warm_pale_stratum_px": int(warm_pale_stratum.sum()),
                                     "pass": (not np.isnan(despill_interior_mean)) and despill_interior_mean < 3.0},
            "recomposition": {"bg_alpha_leak_pct": bg_leak_pct,
                               "band_recomp_p95_abs_err": recomp_band_p95,
                               "pass": bg_leak_pct < 1.0},
            "bubbles": {"regions": bubble_report,
                        "n_bubbles_detected": len(bubble_regions),
                        "pass": all((b["greenish_tint_px_in_core"] == 0) for b in bubble_report) if bubble_report else None},
            "border_occupancy": {"pct": border_occ_pct, "target_pct": 2.0, "pass": border_occ_pct < 2.0},
        }

        # heatmap: red = residual green, blue = deleted art
        heat = np.zeros((H, W, 3), dtype=np.uint8)
        heat[residual_mask] = [255, 0, 0]
        heat[deleted_mask] = [0, 0, 255]
        heatmaps[name] = heat

    verdict = {
        "source_raw": str(RAW_PATH.relative_to(REPO_ROOT)),
        "deltaE_impl": DELTAE_IMPL,
        "thresholds": {
            "bg_deltaE_max": BG_DELTAE_MAX,
            "art_deltaE_min": ART_DELTAE_MIN,
            "green_dominance": GREEN_DOMINANCE,
            "alpha_residual_thresh": ALPHA_RESIDUAL_THRESH,
            "alpha_deleted_thresh": ALPHA_DELETED_THRESH,
            "band_px": BAND_PX,
            "border_strip_px": BORDER_STRIP_PX,
            "border_alpha_thresh": BORDER_ALPHA_THRESH,
            "recomp_alpha_leak_thresh": RECOMP_ALPHA_LEAK_THRESH,
            "erosion_interior_px": EROSION_INTERIOR_PX,
        },
        "source_masks": {
            "n_art_px": n_art_px,
            "n_bg_px": int(bg_mask.sum()),
            "n_band_px": int(band_mask.sum()),
            "n_interior_px": int(interior_mask.sum()),
            "n_yellow_stratum_px": int(yellow_stratum.sum()),
            "n_warm_pale_stratum_px": int(warm_pale_stratum.sum()),
            "n_bubbles_detected": len(bubble_regions),
            "bubble_regions": bubble_regions,
        },
        "candidates": results,
    }

    OUT_JSON.write_text(json.dumps(verdict, indent=2))

    # ---- VERDICT.md ranked table ----
    def score_row(name):
        r = results[name]
        fails = sum(
            1 for gate in ("residual_green", "deleted_art", "rim", "despill_confinement",
                            "recomposition", "border_occupancy")
            if r[gate]["pass"] is False
        )
        if r["bubbles"]["pass"] is False:
            fails += 1
        return fails

    ranking = sorted(CANDIDATES.keys(), key=lambda n: (score_row(n), n))

    lines = []
    lines.append("# Green-key shoot-out — VERDICT")
    lines.append("")
    lines.append(f"Source raw: `{verdict['source_raw']}`  ")
    lines.append(f"ΔE implementation: `{DELTAE_IMPL}`")
    lines.append("")
    lines.append("## Ranked table (fewest gate failures first)")
    lines.append("")
    header = ["Candidate", "residual-green", "deleted-art", "rim", "despill-confine",
               "recomposition", "bubbles", "border-occ", "# FAILS"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))

    def mark(v):
        if v is True:
            return "PASS"
        if v is False:
            return "FAIL"
        return "N/A"

    for name in ranking:
        r = results[name]
        row = [
            name,
            mark(r["residual_green"]["pass"]),
            mark(r["deleted_art"]["pass"]),
            mark(r["rim"]["pass"]),
            mark(r["despill_confinement"]["pass"]),
            mark(r["recomposition"]["pass"]),
            mark(r["bubbles"]["pass"]),
            mark(r["border_occupancy"]["pass"]),
            str(score_row(name)),
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Per-candidate defect summary")
    lines.append("")
    for name in ranking:
        r = results[name]
        defects = []
        if r["residual_green"]["pass"] is False:
            defects.append(f"residual green {r['residual_green']['count_px']}px (max blob {r['residual_green']['max_component_px']}px)")
        if r["deleted_art"]["pass"] is False:
            defects.append(f"deleted art {r['deleted_art']['pct_of_art_px']:.3f}% of art (max blob {r['deleted_art']['max_component_px']}px)")
        if r["rim"]["pass"] is False:
            defects.append(f"rim halo Δgreenness {r['rim']['rim_greenness_delta']:.1f}")
        if r["despill_confinement"]["pass"] is False:
            defects.append(f"despill leak ΔE {r['despill_confinement']['interior_deltaE_mean']:.2f} (interior)")
        if r["recomposition"]["pass"] is False:
            defects.append(f"bg alpha leak {r['recomposition']['bg_alpha_leak_pct']:.2f}%")
        if r["bubbles"]["pass"] is False:
            defects.append("bubble greenish tint detected")
        if r["border_occupancy"]["pass"] is False:
            defects.append(f"border occupancy {r['border_occupancy']['pct']:.2f}%")
        summary = "; ".join(defects) if defects else "clean — no gate failures"
        lines.append(f"- **{name}**: {summary}")

    OUT_MD.write_text("\n".join(lines) + "\n")

    # ---- BOARD-verify.png ----
    magenta = np.array([255, 0, 255], dtype=np.uint8)
    thumb_scale = 0.4
    thumb_w, thumb_h = int(W * thumb_scale), int(H * thumb_scale)
    pad = 10
    label_h = 24
    n = len(CANDIDATES)
    board_w = n * (thumb_w + pad) + pad
    board_h = (thumb_h + label_h) * 2 + pad * 3
    board = Image.new("RGB", (board_w, board_h), (30, 30, 30))
    draw = ImageDraw.Draw(board)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for i, name in enumerate(CANDIDATES.keys()):
        rgb, alpha = load_rgba(CANDIDATES[name])
        a = alpha[..., None]
        comp = (a * rgb + (1 - a) * magenta.reshape(1, 1, 3)).astype(np.uint8)
        comp_im = Image.fromarray(comp).resize((thumb_w, thumb_h), Image.LANCZOS)
        x = pad + i * (thumb_w + pad)
        y = pad + label_h
        board.paste(comp_im, (x, y))
        draw.text((x, pad), name, fill=(255, 255, 255), font=font)

        heat_im = Image.fromarray(heatmaps[name]).resize((thumb_w, thumb_h), Image.NEAREST)
        y2 = pad * 2 + label_h * 2 + thumb_h
        board.paste(heat_im, (x, y2))
        draw.text((x, y2 - label_h), "defects (red=residual-green blue=deleted-art)",
                   fill=(200, 200, 200), font=font)

    board.save(OUT_BOARD)

    print(json.dumps({"ranking": ranking}, indent=2))
    print(f"\nWrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_BOARD}")


if __name__ == "__main__":
    main()
