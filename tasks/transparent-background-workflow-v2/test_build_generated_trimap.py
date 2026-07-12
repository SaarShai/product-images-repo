from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image


MODULE_PATH = Path(__file__).with_name("build_generated_trimap.py")
SPEC = importlib.util.spec_from_file_location("build_generated_trimap", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
trimap_builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = trimap_builder
SPEC.loader.exec_module(trimap_builder)


def white_canvas(size: int = 25) -> np.ndarray:
    return np.full((size, size, 3), 255, dtype=np.uint8)


def draw_closed_colored_contour(image: np.ndarray) -> None:
    color = (210, 60, 100)
    image[5, 5:20] = color
    image[19, 5:20] = color
    image[5:20, 5] = color
    image[5:20, 19] = color


def test_closed_colored_contour_preserves_interior_white_highlight_as_unknown():
    image = white_canvas()
    draw_closed_colored_contour(image)
    trimap, _ = trimap_builder.build_trimap_array(image)
    assert trimap[0, 0] == trimap_builder.SURE_BG
    assert trimap[5, 10] == trimap_builder.SURE_FG
    assert trimap[12, 12] == trimap_builder.UNKNOWN


def test_connected_white_gap_between_colored_branches_is_sure_background():
    image = white_canvas()
    image[3:22, 8:10] = (40, 150, 210)
    image[3:22, 15:17] = (220, 80, 130)
    trimap, _ = trimap_builder.build_trimap_array(image)
    assert trimap[12, 12] == trimap_builder.SURE_BG
    assert trimap[10, 8] == trimap_builder.SURE_FG
    assert trimap[10, 16] == trimap_builder.SURE_FG


def test_enclosed_key_colored_pocket_remains_unknown():
    image = white_canvas()
    draw_closed_colored_contour(image)
    trimap, _ = trimap_builder.build_trimap_array(image)
    assert trimap[10, 10] == trimap_builder.UNKNOWN


def test_pale_off_white_art_is_not_deleted_or_forced_foreground():
    image = white_canvas()
    image[8:17, 8:17] = (245, 242, 238)
    trimap, _ = trimap_builder.build_trimap_array(image)
    assert trimap[12, 12] == trimap_builder.UNKNOWN


def test_broken_contour_allows_connected_key_background_into_interior():
    image = white_canvas()
    draw_closed_colored_contour(image)
    image[5, 11:14] = 255
    trimap, _ = trimap_builder.build_trimap_array(image)
    assert trimap[12, 12] == trimap_builder.SURE_BG


def test_proposal_save_modes_are_exact_size_and_use_alpha_for_rgba(tmp_path: Path):
    image = white_canvas(11)
    image[5, 5] = (10, 80, 180)
    trimap, metrics = trimap_builder.build_trimap_array(image)
    grayscale_path = tmp_path / "proposal-l.png"
    rgba_path = tmp_path / "proposal-rgba.png"
    trimap_builder.save_proposal(grayscale_path, trimap, "L")
    trimap_builder.save_proposal(rgba_path, trimap, "RGBA")

    with Image.open(grayscale_path) as grayscale:
        assert grayscale.mode == "L"
        assert grayscale.size == (11, 11)
        np.testing.assert_array_equal(np.asarray(grayscale), trimap)
    with Image.open(rgba_path) as rgba:
        assert rgba.mode == "RGBA"
        assert rgba.size == (11, 11)
        np.testing.assert_array_equal(np.asarray(rgba)[:, :, 3], trimap)
    assert sum(metrics["counts"].values()) == 121
