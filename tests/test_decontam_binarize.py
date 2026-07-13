import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000, rgb2lab


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "decontam_binarize.py"


def load_module():
    spec = importlib.util.spec_from_file_location("decontam_binarize", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def alpha_disc(size=96, radius=28, blur=2.2):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    c = size // 2
    draw.ellipse([c - radius, c - radius, c + radius, c + radius], fill=255)
    return np.array(mask.filter(ImageFilter.GaussianBlur(blur)), dtype=np.uint8)


def test_known_white_matte_decontamination_reduces_edge_deltae_to_true_fg():
    mod = load_module()
    alpha_u8 = alpha_disc()
    alpha = alpha_u8.astype(np.float32) / 255.0
    true_fg = np.array([205, 45, 70], dtype=np.float32)
    white = np.array([255, 255, 255], dtype=np.float32)
    observed = np.round(alpha[..., None] * true_fg + (1.0 - alpha[..., None]) * white).astype(np.uint8)
    rgba = np.dstack([observed, alpha_u8]).astype(np.uint8)

    out, _soft, metrics = mod.process_rgba(rgba, bg_rgb=np.array([255, 255, 255], dtype=np.uint8))
    edge = (alpha > 0.08) & (alpha < 0.92)
    true_rgb = np.zeros_like(observed)
    true_rgb[:] = true_fg.astype(np.uint8)
    before_de = deltaE_ciede2000(rgb2lab(observed / 255.0), rgb2lab(true_rgb / 255.0))[edge].mean()
    after_de = deltaE_ciede2000(rgb2lab(out[..., :3] / 255.0), rgb2lab(true_rgb / 255.0))[edge].mean()

    assert metrics["ridge_unmix"]["transition_px"] > 0
    assert after_de < before_de * 0.55


def test_final_alpha_is_strictly_binary():
    mod = load_module()
    alpha_u8 = alpha_disc()
    rgb = np.full((*alpha_u8.shape, 3), [40, 120, 210], dtype=np.uint8)
    rgba = np.dstack([rgb, alpha_u8])

    out, soft, _metrics = mod.process_rgba(rgba)

    assert set(np.unique(out[..., 3])).issubset({0, 255})
    assert len(np.unique(soft)) > 2


def test_thin_two_pixel_stroke_survives_erode_without_component_loss():
    mod = load_module()
    size = 64
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[31:33, 8:56, :3] = [25, 25, 25]
    rgba[31:33, 8:56, 3] = 255

    out, _soft, metrics = mod.process_rgba(rgba, erode=1)
    labels_before, n_before = ndi.label(rgba[..., 3] >= 128, structure=np.ones((3, 3), dtype=bool))
    labels_after, n_after = ndi.label(out[..., 3] == 255, structure=np.ones((3, 3), dtype=bool))

    assert n_before == 1
    assert n_after == 1
    assert out[..., 3].sum() > 0
    assert metrics["alpha"]["restored_thin_components"] == 1


def test_ncnn_realesrgan_subprocess_route_returns_x4_rgb(tmp_path, monkeypatch):
    mod = load_module()
    binary = tmp_path / "realesrgan-ncnn-vulkan"
    models = tmp_path / "models"
    binary.write_text("#!/bin/sh\n")
    models.mkdir()
    monkeypatch.setattr(mod, "DEFAULT_REALESRGAN_BIN", binary)
    monkeypatch.setattr(mod, "DEFAULT_REALESRGAN_MODELS", models)

    def fake_run(command, capture_output, text, check):
        input_path = Path(command[command.index("-i") + 1])
        output_path = Path(command[command.index("-o") + 1])
        image = Image.open(input_path).convert("RGB")
        image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST).save(output_path)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rgb = np.full((3, 5, 3), [80, 40, 20], dtype=np.uint8)

    out, method = mod.ncnn_realesrgan_rgb_if_available(rgb, tile=128)

    assert method == "realesrgan_ncnn_x4plus"
    assert out.shape == (12, 20, 3)


def test_venv_realesrgan_subprocess_route_returns_x4_rgb(tmp_path, monkeypatch):
    mod = load_module()
    python = tmp_path / "python"
    model = tmp_path / "RealESRGAN_x4plus.pth"
    python.write_text("#!/bin/sh\n")
    model.write_text("model")
    monkeypatch.setattr(mod, "DEFAULT_VENV_GEN_PYTHON", python)
    monkeypatch.setattr(mod, "ESRGAN_UPSCALE_SCRIPT", tmp_path / "esrgan_upscale.py")
    monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
    mod.ESRGAN_UPSCALE_SCRIPT.write_text("#!/usr/bin/env python\n")
    (tmp_path / "models-gen/esrgan").mkdir(parents=True)
    model.rename(tmp_path / "models-gen/esrgan/RealESRGAN_x4plus.pth")

    def fake_run(command, cwd, capture_output, text, check):
        input_path = Path(command[command.index("--image") + 1])
        output_path = Path(command[command.index("--out") + 1])
        image = Image.open(input_path).convert("RGB")
        image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST).save(output_path)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rgb = np.full((2, 4, 3), [80, 40, 20], dtype=np.uint8)

    out, method = mod.venv_realesrgan_rgb_if_available(rgb, scale=4.0, device="cpu", tile=128)

    assert method == "realesrgan_x4plus_venv_gen"
    assert out.shape == (8, 16, 3)


def test_lanczos_fallback_is_loud_in_metrics_and_stderr(capsys, monkeypatch):
    mod = load_module()

    def fake_esrgan(_rgb_u8, scale, device, tile):
        return None, "lanczos_fallback_import_error:ModuleNotFoundError"

    monkeypatch.setattr(mod, "esrgan_rgb_if_available", fake_esrgan)
    rgb = np.full((4, 4, 3), [10, 20, 30], dtype=np.uint8)
    alpha = np.full((4, 4), 255, dtype=np.uint8)

    up_rgb, up_alpha, metrics = mod.upscale_cleaned_rgba(rgb, alpha, "x4", "cpu", 128)
    err = capsys.readouterr().err

    assert up_rgb.shape == (16, 16, 3)
    assert up_alpha.shape == (16, 16)
    assert metrics["rgb_method"] == "lanczos_fallback_import_error:ModuleNotFoundError"
    assert metrics["rgb_fallback_warning"]
    assert "WARNING: Real-ESRGAN unavailable; using Lanczos RGB fallback" in err
