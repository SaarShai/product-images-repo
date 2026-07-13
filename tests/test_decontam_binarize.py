import importlib.util
from pathlib import Path

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
