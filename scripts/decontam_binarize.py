#!/usr/bin/env python3
"""Print-route RGBA decontamination and final alpha binarization.

Order is intentional: clean transition RGB from retained soft alpha first,
optionally upscale, then threshold/erode delivery alpha.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None
REPO = Path(__file__).resolve().parents[1]
DEFAULT_REALESRGAN_BIN = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan"
DEFAULT_REALESRGAN_MODELS = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/models"
DEFAULT_VENV_GEN_PYTHON = REPO / ".venv-gen/bin/python"
ESRGAN_UPSCALE_SCRIPT = REPO / "scripts/esrgan_upscale.py"


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    x = np.asarray(rgb, dtype=np.float32)
    if x.max(initial=0) > 1.0:
        x = x / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1.0 / 2.4)) - 0.055).astype(np.float32)


def linear_srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=np.float32)
    lms = np.empty_like(rgb, dtype=np.float32)
    lms[..., 0] = 0.4122214708 * rgb[..., 0] + 0.5363325363 * rgb[..., 1] + 0.0514459929 * rgb[..., 2]
    lms[..., 1] = 0.2119034982 * rgb[..., 0] + 0.6806995451 * rgb[..., 1] + 0.1073969566 * rgb[..., 2]
    lms[..., 2] = 0.0883024619 * rgb[..., 0] + 0.2817188376 * rgb[..., 1] + 0.6299787005 * rgb[..., 2]
    lms = np.cbrt(np.maximum(lms, 0.0))
    lab = np.empty_like(rgb, dtype=np.float32)
    lab[..., 0] = 0.2104542553 * lms[..., 0] + 0.7936177850 * lms[..., 1] - 0.0040720468 * lms[..., 2]
    lab[..., 1] = 1.9779984951 * lms[..., 0] - 2.4285922050 * lms[..., 1] + 0.4505937099 * lms[..., 2]
    lab[..., 2] = 0.0259040371 * lms[..., 0] + 0.7827717662 * lms[..., 1] - 0.8086757660 * lms[..., 2]
    return lab


def oklab_to_linear_srgb(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float32)
    l_ = lab[..., 0] + 0.3963377774 * lab[..., 1] + 0.2158037573 * lab[..., 2]
    m_ = lab[..., 0] - 0.1055613458 * lab[..., 1] - 0.0638541728 * lab[..., 2]
    s_ = lab[..., 0] - 0.0894841775 * lab[..., 1] - 1.2914855480 * lab[..., 2]
    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3
    rgb = np.empty_like(lab, dtype=np.float32)
    rgb[..., 0] = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    rgb[..., 1] = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    rgb[..., 2] = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return rgb.astype(np.float32)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def parse_hex_color(value: str) -> np.ndarray:
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise argparse.ArgumentTypeError("--bg-color must be #RRGGBB or RRGGBB")
    try:
        return np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--bg-color must be #RRGGBB or RRGGBB") from exc


def donor_window_px(ppi: float | None) -> tuple[float, float]:
    if ppi and ppi > 0:
        return max(1.0, 0.15 / 25.4 * ppi), max(2.0, 0.35 / 25.4 * ppi)
    return 2.0, 4.0


def nearest_support_labels(support: np.ndarray, labels: np.ndarray) -> np.ndarray:
    if not support.any():
        return np.zeros_like(labels, dtype=np.int32)
    _, indices = ndi.distance_transform_edt(~support, return_indices=True)
    return labels[indices[0], indices[1]]


def build_component_donor(rgb_linear: np.ndarray, alpha: np.ndarray, ppi: float | None) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Component-constrained inward donor field in linear-light RGB."""
    support = alpha >= 0.02
    labels, n_labels = ndi.label(support, structure=np.ones((3, 3), dtype=bool))
    nearest_labels = nearest_support_labels(support, labels)
    donor = np.zeros_like(rgb_linear, dtype=np.float32)
    donor_valid = nearest_labels > 0
    min_px, max_px = donor_window_px(ppi)

    if not support.any():
        donor[:] = 0.0
        return donor, donor_valid, {
            "components": 0,
            "donor_min_px": round(float(min_px), 3),
            "donor_max_px": round(float(max_px), 3),
            "fallback_components": 0,
        }

    signed = ndi.distance_transform_edt(support) - ndi.distance_transform_edt(~support)
    core = alpha >= 0.98
    donor_ring = support & core & (signed >= min_px) & (signed <= max_px)
    fallback_components = 0

    if donor_ring.any():
        _, indices = ndi.distance_transform_edt(~donor_ring, return_indices=True)
        ring_labels = labels[indices[0], indices[1]]
        same_component = (nearest_labels > 0) & (ring_labels == nearest_labels)
        donor[same_component] = rgb_linear[indices[0], indices[1]][same_component]
        donor_valid &= same_component
    else:
        donor_valid[:] = False

    for lbl in range(1, n_labels + 1):
        component_target = nearest_labels == lbl
        if not component_target.any():
            continue
        missing = component_target & ~donor_valid
        if not missing.any():
            continue
        component_core = (labels == lbl) & core
        component_source = component_core if component_core.any() else labels == lbl
        donor[missing] = np.median(rgb_linear[component_source], axis=0)
        donor_valid[missing] = True
        fallback_components += 1

    if (~donor_valid).any():
        donor[~donor_valid] = np.median(rgb_linear[support], axis=0)

    return donor, donor_valid, {
        "components": int(n_labels),
        "donor_min_px": round(float(min_px), 3),
        "donor_max_px": round(float(max_px), 3),
        "donor_ring_px": int(donor_ring.sum()),
        "fallback_components": int(fallback_components),
    }


def ridge_unmix(
    rgb_linear: np.ndarray,
    alpha: np.ndarray,
    donor_linear: np.ndarray,
    bg_linear: np.ndarray | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    out = rgb_linear.copy()
    transition = (alpha > 0.02) & (alpha < 0.95)
    a = np.clip(alpha[..., None], 1e-4, 1.0)
    lam = 0.04 * (1.0 - alpha[..., None]) ** 2
    if bg_linear is not None:
        y = rgb_linear - (1.0 - a) * bg_linear.reshape(1, 1, 3)
        f0 = y / a
        solved = (a * y + lam * donor_linear) / (a * a + lam)
    else:
        f0 = rgb_linear
        solved = (a * a * f0 + lam * donor_linear) / (a * a + lam)
    out[transition] = solved[transition]
    below = int((out[transition] < 0.0).sum())
    above = int((out[transition] > 1.0).sum())
    out = np.clip(out, 0.0, 1.0)

    metrics: dict[str, Any] = {
        "transition_px": int(transition.sum()),
        "pre_gamut_below_channel_count": below,
        "pre_gamut_above_channel_count": above,
    }
    if bg_linear is not None and transition.any():
        recomp = alpha[..., None] * out + (1.0 - alpha[..., None]) * bg_linear.reshape(1, 1, 3)
        err = np.abs(recomp - rgb_linear).mean(axis=2)[transition]
        metrics["recomposition_linear_mae"] = round(float(err.mean()), 8)
        metrics["recomposition_linear_p95"] = round(float(np.percentile(err, 95)), 8)
    return out.astype(np.float32), metrics


def despill_oklab(
    fg_linear: np.ndarray,
    donor_linear: np.ndarray,
    observed_linear: np.ndarray,
    alpha: np.ndarray,
    bg_linear: np.ndarray | None,
    tau: float = 0.01,
) -> tuple[np.ndarray, dict[str, Any]]:
    if bg_linear is None:
        return fg_linear, {"enabled": False, "changed_px": 0}

    bg_lab = linear_srgb_to_oklab(bg_linear.reshape(1, 1, 3))[0, 0]
    k = bg_lab[1:3].astype(np.float32)
    norm = float(np.linalg.norm(k))
    if norm < 1e-6:
        return fg_linear, {"enabled": False, "reason": "background_has_no_oklab_chroma", "changed_px": 0}
    k = k / norm

    fg_lab = linear_srgb_to_oklab(fg_linear)
    donor_lab = linear_srgb_to_oklab(donor_linear)
    obs_lab = linear_srgb_to_oklab(observed_linear)

    transition = (alpha > 0.02) & (alpha < 0.95)
    excess = (fg_lab[..., 1] - donor_lab[..., 1]) * k[0] + (fg_lab[..., 2] - donor_lab[..., 2]) * k[1]
    raw_excess = (obs_lab[..., 1] - donor_lab[..., 1]) * k[0] + (obs_lab[..., 2] - donor_lab[..., 2]) * k[1]
    gate = transition & (raw_excess > tau)
    g = 1.0 - smoothstep(0.15, 0.85, alpha)
    remove = g * np.clip(excess - tau, 0.0, 0.04)
    remove = np.where(gate, remove, 0.0)

    fg_lab[..., 1] -= remove * k[0]
    fg_lab[..., 2] -= remove * k[1]
    out = np.clip(oklab_to_linear_srgb(fg_lab), 0.0, 1.0)
    changed = remove > 0
    return out.astype(np.float32), {
        "enabled": True,
        "tau": tau,
        "changed_px": int(changed.sum()),
        "mean_remove": round(float(remove[changed].mean()), 8) if changed.any() else 0.0,
        "max_remove": round(float(remove.max(initial=0.0)), 8),
    }


def extend_rgb_outside_mask(rgb: np.ndarray, mask: np.ndarray, px: int = 3) -> tuple[np.ndarray, dict[str, Any]]:
    labels, n_labels = ndi.label(mask, structure=np.ones((3, 3), dtype=bool))
    if n_labels == 0 or px <= 0:
        return rgb, {"extension_px": 0, "conflict_px": 0}

    out = rgb.copy()
    assigned = labels.astype(np.int32).copy()
    conflict_total = 0
    structure = np.ones((3, 3), dtype=bool)

    for _ in range(px):
        fringe = ndi.binary_dilation(assigned > 0, structure=structure) & (assigned == 0)
        ys, xs = np.where(fringe)
        if len(ys) == 0:
            break
        new_labels = np.zeros(len(ys), dtype=np.int32)
        new_rgb = np.zeros((len(ys), 3), dtype=out.dtype)
        for i, (y, x) in enumerate(zip(ys, xs)):
            y0, y1 = max(0, y - 1), min(mask.shape[0], y + 2)
            x0, x1 = max(0, x - 1), min(mask.shape[1], x + 2)
            neighbor_labels = np.unique(assigned[y0:y1, x0:x1])
            neighbor_labels = neighbor_labels[neighbor_labels > 0]
            if len(neighbor_labels) != 1:
                conflict_total += 1
                continue
            lbl = int(neighbor_labels[0])
            donor = assigned[y0:y1, x0:x1] == lbl
            new_labels[i] = lbl
            new_rgb[i] = np.median(out[y0:y1, x0:x1][donor], axis=0)
        ok = new_labels > 0
        assigned[ys[ok], xs[ok]] = new_labels[ok]
        out[ys[ok], xs[ok]] = new_rgb[ok]

    extension = (assigned > 0) & ~mask
    return out, {"extension_px": int(extension.sum()), "conflict_px": int(conflict_total)}


def ncnn_realesrgan_rgb_if_available(rgb_u8: np.ndarray, tile: int) -> tuple[np.ndarray | None, str]:
    binary = DEFAULT_REALESRGAN_BIN
    models = DEFAULT_REALESRGAN_MODELS
    if not binary.is_file():
        return None, "lanczos_fallback_missing_realesrgan_ncnn_binary"
    if not models.is_dir():
        return None, "lanczos_fallback_missing_realesrgan_ncnn_models"
    with tempfile.TemporaryDirectory(prefix="decontam-realesrgan-") as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / "rgb-input.png"
        output_path = tmp_dir / "rgb-x4.png"
        Image.fromarray(rgb_u8, "RGB").save(input_path)
        command = [
            str(binary),
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-n",
            "realesrgan-x4plus",
            "-m",
            str(models),
            "-s",
            "4",
            "-t",
            str(tile),
            "-f",
            "png",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output_path.is_file():
            stderr_tail = (completed.stderr or completed.stdout or "")[-500:].replace("\n", " ")
            return None, f"lanczos_fallback_realesrgan_ncnn_error:rc={completed.returncode}:{stderr_tail}"
        out = np.array(Image.open(output_path).convert("RGB"))
        expected = (rgb_u8.shape[1] * 4, rgb_u8.shape[0] * 4)
        if out.shape[1] != expected[0] or out.shape[0] != expected[1]:
            return None, f"lanczos_fallback_realesrgan_ncnn_bad_size:{out.shape[1]}x{out.shape[0]}"
        return out, "realesrgan_ncnn_x4plus"


def venv_realesrgan_rgb_if_available(rgb_u8: np.ndarray, scale: float, device: str, tile: int) -> tuple[np.ndarray | None, str]:
    python = DEFAULT_VENV_GEN_PYTHON
    script = ESRGAN_UPSCALE_SCRIPT
    model_path = Path.home() / "models-gen" / "esrgan" / "RealESRGAN_x4plus.pth"
    if not python.is_file():
        return None, "lanczos_fallback_missing_venv_gen_python"
    if not script.is_file():
        return None, "lanczos_fallback_missing_esrgan_upscale_script"
    if not model_path.exists():
        return None, "lanczos_fallback_missing_realesrgan_model"
    with tempfile.TemporaryDirectory(prefix="decontam-realesrgan-venv-") as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / "rgb-input.png"
        output_path = tmp_dir / "rgb-x4.png"
        Image.fromarray(rgb_u8, "RGB").save(input_path)
        command = [
            str(python),
            str(script),
            "--image",
            str(input_path),
            "--out",
            str(output_path),
            "--scale",
            str(scale),
            "--tile",
            str(tile),
            "--device",
            device,
        ]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output_path.is_file():
            stderr_tail = (completed.stderr or completed.stdout or "")[-500:].replace("\n", " ")
            return None, f"lanczos_fallback_realesrgan_venv_error:rc={completed.returncode}:{stderr_tail}"
        out = np.array(Image.open(output_path).convert("RGB"))
        expected = (int(round(rgb_u8.shape[1] * scale)), int(round(rgb_u8.shape[0] * scale)))
        if out.shape[1] != expected[0] or out.shape[0] != expected[1]:
            return None, f"lanczos_fallback_realesrgan_venv_bad_size:{out.shape[1]}x{out.shape[0]}"
        return out, "realesrgan_x4plus_venv_gen"


def esrgan_rgb_if_available(rgb_u8: np.ndarray, scale: float, device: str, tile: int) -> tuple[np.ndarray | None, str]:
    out, method = ncnn_realesrgan_rgb_if_available(rgb_u8, tile)
    if out is not None:
        return out, method
    ncnn_reason = method
    out, method = venv_realesrgan_rgb_if_available(rgb_u8, scale, device, tile)
    if out is not None:
        return out, method
    venv_reason = method
    model_path = Path.home() / "models-gen" / "esrgan" / "RealESRGAN_x4plus.pth"
    if not model_path.exists():
        return None, f"{ncnn_reason};{venv_reason};lanczos_fallback_missing_realesrgan_model"
    try:
        import torch
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
    except Exception as exc:  # pragma: no cover - depends on optional local install
        return None, f"{ncnn_reason};{venv_reason};lanczos_fallback_import_error:{type(exc).__name__}"
    try:  # pragma: no cover - depends on optional local install/hardware
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        up = RealESRGANer(
            scale=4,
            model_path=str(model_path),
            model=model,
            tile=tile,
            tile_pad=10,
            pre_pad=0,
            half=False,
            device=torch.device(device),
        )
        out, _ = up.enhance(rgb_u8[:, :, ::-1], outscale=scale)
        return out[:, :, ::-1], "realesrgan_x4plus_local"
    except Exception as exc:
        return None, f"{ncnn_reason};{venv_reason};lanczos_fallback_runtime_error:{type(exc).__name__}"


def resize_lanczos(arr: np.ndarray, size: tuple[int, int], mode: str) -> np.ndarray:
    return np.array(Image.fromarray(arr, mode=mode).resize(size, Image.Resampling.LANCZOS))


def upscale_cleaned_rgba(
    rgb_u8: np.ndarray,
    alpha_u8: np.ndarray,
    upscale: str,
    device: str,
    tile: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if upscale == "none":
        return rgb_u8, alpha_u8, {"enabled": False, "rgb_method": "none", "alpha_method": "none"}
    if upscale != "x4":
        raise ValueError(f"unsupported upscale mode: {upscale}")

    scale = 4.0
    up_rgb, method = esrgan_rgb_if_available(rgb_u8, scale=scale, device=device, tile=tile)
    fallback_warning = None
    if up_rgb is None:
        fallback_warning = f"WARNING: Real-ESRGAN unavailable; using Lanczos RGB fallback ({method})"
        print(f"[decontam_binarize] {fallback_warning}", file=sys.stderr)
        size = (rgb_u8.shape[1] * 4, rgb_u8.shape[0] * 4)
        up_rgb = resize_lanczos(rgb_u8, size, "RGB")
    out_size = (up_rgb.shape[1], up_rgb.shape[0])
    up_alpha = resize_lanczos(alpha_u8, out_size, "L")
    return up_rgb.astype(np.uint8), up_alpha.astype(np.uint8), {
        "enabled": True,
        "scale": 4,
        "rgb_method": method,
        "rgb_fallback_warning": fallback_warning,
        "alpha_method": "lanczos_clamped_u8",
        "out_size": [int(out_size[0]), int(out_size[1])],
    }


def threshold_and_erode(alpha_u8: np.ndarray, thresh: int, erode_px: int) -> tuple[np.ndarray, dict[str, Any]]:
    base = alpha_u8 >= thresh
    labels, n_labels = ndi.label(base, structure=np.ones((3, 3), dtype=bool))
    if erode_px > 0 and base.any():
        dist = ndi.distance_transform_edt(base)
        eroded = dist > float(erode_px)
        restored_components = 0
        for lbl in range(1, n_labels + 1):
            comp = labels == lbl
            if comp.any() and not eroded[comp].any():
                eroded |= comp
                restored_components += 1
        mask = eroded
    else:
        mask = base
        restored_components = 0
    return (mask.astype(np.uint8) * 255), {
        "alpha_thresh": int(thresh),
        "pre_erode_mask_px": int(base.sum()),
        "post_erode_mask_px": int(mask.sum()),
        "components_before_erode": int(n_labels),
        "restored_thin_components": int(restored_components),
    }


def softalpha_path(out_path: Path) -> Path:
    return out_path.with_name(f"{out_path.stem}-softalpha.png")


def default_metrics_path(out_path: Path) -> Path:
    return out_path.with_name(f"{out_path.stem}-metrics.json")


def process_rgba(
    rgba: np.ndarray,
    *,
    bg_rgb: np.ndarray | None = None,
    ppi: float | None = None,
    alpha_thresh: int = 128,
    erode: int = 0,
    upscale: str = "none",
    device: str = "cpu",
    tile: int = 512,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("input must be an RGBA image")
    src_alpha_u8 = rgba[..., 3]
    alpha = src_alpha_u8.astype(np.float32) / 255.0
    rgb_linear = srgb_to_linear(rgba[..., :3])
    bg_linear = srgb_to_linear(bg_rgb.reshape(1, 1, 3))[0, 0] if bg_rgb is not None else None

    core = alpha >= 0.98
    transition = (alpha > 0.02) & (alpha < 0.95)
    donor, donor_valid, donor_metrics = build_component_donor(rgb_linear, alpha, ppi)
    cleaned_linear, ridge_metrics = ridge_unmix(rgb_linear, alpha, donor, bg_linear)
    cleaned_linear, despill_metrics = despill_oklab(cleaned_linear, donor, rgb_linear, alpha, bg_linear)
    cleaned_u8 = np.clip(np.round(linear_to_srgb(cleaned_linear) * 255.0), 0, 255).astype(np.uint8)

    pre_mask = src_alpha_u8 >= alpha_thresh
    cleaned_u8, extension_metrics = extend_rgb_outside_mask(cleaned_u8, pre_mask, px=3)
    up_rgb, up_soft_alpha, upscale_metrics = upscale_cleaned_rgba(cleaned_u8, src_alpha_u8, upscale, device, tile)

    final_alpha, alpha_metrics = threshold_and_erode(up_soft_alpha, alpha_thresh, erode)
    final_mask = final_alpha > 0
    up_rgb, final_extension_metrics = extend_rgb_outside_mask(up_rgb, final_mask, px=3)
    out_rgba = np.dstack([up_rgb, final_alpha]).astype(np.uint8)

    metrics: dict[str, Any] = {
        "input_size": [int(rgba.shape[1]), int(rgba.shape[0])],
        "output_size": [int(out_rgba.shape[1]), int(out_rgba.shape[0])],
        "bg_color": None if bg_rgb is None else f"#{int(bg_rgb[0]):02X}{int(bg_rgb[1]):02X}{int(bg_rgb[2]):02X}",
        "ppi": ppi,
        "core_px": int(core.sum()),
        "transition_px": int(transition.sum()),
        "transparent_px": int((alpha <= 0.02).sum()),
        "donor_valid_px": int(donor_valid.sum()),
        "donor": donor_metrics,
        "ridge_unmix": ridge_metrics,
        "despill": despill_metrics,
        "pre_upscale_rgb_extension": extension_metrics,
        "upscale": upscale_metrics,
        "alpha": alpha_metrics,
        "final_rgb_extension": final_extension_metrics,
    }
    return out_rgba, up_soft_alpha, metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rgba", required=True, type=Path, help="straight-alpha RGBA PNG with retained soft alpha")
    ap.add_argument("--out", required=True, type=Path, help="print-ready RGBA PNG output")
    ap.add_argument("--bg-color", type=parse_hex_color, help="known/keyed background color as #RRGGBB")
    ap.add_argument("--ppi", type=float, help="source PPI for 0.15-0.35mm donor window; px fallback when omitted")
    ap.add_argument("--alpha-thresh", type=int, default=128, help="final alpha threshold, 0-255")
    ap.add_argument("--erode", type=int, choices=[0, 1, 2], default=0, help="signed-distance erode in final pixels")
    ap.add_argument("--upscale", choices=["none", "x4"], default="none", help="optional x4 RGB/alpha upscale hook")
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"], help="Real-ESRGAN device if locally available")
    ap.add_argument("--tile", type=int, default=512, help="Real-ESRGAN tile size if locally available")
    ap.add_argument("--metrics", type=Path, help="metrics JSON path; defaults to <out>-metrics.json")
    args = ap.parse_args()

    if not (0 <= args.alpha_thresh <= 255):
        ap.error("--alpha-thresh must be between 0 and 255")

    rgba = np.array(Image.open(args.rgba).convert("RGBA"))
    out, soft_alpha, metrics = process_rgba(
        rgba,
        bg_rgb=args.bg_color,
        ppi=args.ppi,
        alpha_thresh=args.alpha_thresh,
        erode=args.erode,
        upscale=args.upscale,
        device=args.device,
        tile=args.tile,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGBA").save(args.out)
    Image.fromarray(soft_alpha, "L").save(softalpha_path(args.out))
    metrics_path = args.metrics or default_metrics_path(args.out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
