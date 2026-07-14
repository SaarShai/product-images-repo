import importlib.util
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "chroma_key_upscale.py"


def load_module():
    spec = importlib.util.spec_from_file_location("chroma_key_upscale", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binary_alpha_disc(size=64, radius=20):
    """A hard-edged (non-AA) binary alpha disc, matching print-profile
    chroma-key/green-purge outputs."""
    yy, xx = np.mgrid[0:size, 0:size]
    c = size // 2
    disc = (yy - c) ** 2 + (xx - c) ** 2 <= radius ** 2
    return np.where(disc, 255, 0).astype(np.uint8)


def test_binary_alpha_flag_thresholds_lanczos_output_to_hard_binary():
    mod = load_module()
    alpha = binary_alpha_disc()

    up_soft = mod.resize_alpha(alpha, alpha.shape[1] * 4, alpha.shape[0] * 4, binary=False)
    up_binary = mod.resize_alpha(alpha, alpha.shape[1] * 4, alpha.shape[0] * 4, binary=True)

    # default (soft) behavior reintroduces intermediate alpha values on a
    # binary input (the bug this flag fixes)
    assert len(np.unique(up_soft)) > 2

    # --binary-alpha thresholds strictly back to {0, 255}
    assert set(np.unique(up_binary).tolist()) <= {0, 255}
    assert up_binary.shape == (alpha.shape[0] * 4, alpha.shape[1] * 4)


def test_upscale_rgba_binary_alpha_true_produces_only_hard_alpha_values():
    mod = load_module()
    alpha = binary_alpha_disc()
    rgb = np.full((*alpha.shape, 3), [40, 120, 60], dtype=np.uint8)
    rgba = np.dstack([rgb, alpha])

    def fake_esrgan_rgb(rgb_u8, scale, device, tile):
        h, w = rgb_u8.shape[:2]
        s = int(scale)
        return np.repeat(np.repeat(rgb_u8, s, axis=0), s, axis=1)

    mod.esrgan_rgb = fake_esrgan_rgb

    out, metrics = mod.upscale_rgba(rgba, scale=4, device="cpu", tile=512, binary_alpha=True)

    out_alpha = out[..., 3]
    assert set(np.unique(out_alpha).tolist()) <= {0, 255}
    assert "binary_threshold" in metrics["alpha_method"]


def test_upscale_rgba_default_binary_alpha_false_preserves_existing_behavior():
    mod = load_module()
    alpha = binary_alpha_disc()
    rgb = np.full((*alpha.shape, 3), [40, 120, 60], dtype=np.uint8)
    rgba = np.dstack([rgb, alpha])

    def fake_esrgan_rgb(rgb_u8, scale, device, tile):
        h, w = rgb_u8.shape[:2]
        s = int(scale)
        return np.repeat(np.repeat(rgb_u8, s, axis=0), s, axis=1)

    mod.esrgan_rgb = fake_esrgan_rgb

    out, metrics = mod.upscale_rgba(rgba, scale=4, device="cpu", tile=512)

    out_alpha = out[..., 3]
    assert len(np.unique(out_alpha)) > 2
    assert metrics["alpha_method"] == "lanczos_independent_resize"
