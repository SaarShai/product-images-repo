#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


MODULE_PATH = Path(__file__).with_name("white_key.py")
SPEC = importlib.util.spec_from_file_location("white_key", MODULE_PATH)
assert SPEC and SPEC.loader
white_key = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(white_key)


def antialiased_fixture(draw_callback, size: tuple[int, int] = (128, 128), scale: int = 4) -> np.ndarray:
    large = Image.new("RGB", (size[0] * scale, size[1] * scale), (254, 254, 254))
    draw_callback(ImageDraw.Draw(large), scale)
    return np.asarray(large.resize(size, Image.Resampling.LANCZOS), dtype=np.uint8)


def circle_fixture_with_true_alpha(
    foreground: tuple[int, int, int],
    size: int = 128,
    scale: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    large_rgb = Image.new("RGB", (size * scale, size * scale), (254, 254, 254))
    ImageDraw.Draw(large_rgb).ellipse(
        (22 * scale, 22 * scale, 106 * scale, 106 * scale), fill=foreground
    )
    large_alpha = Image.new("L", large_rgb.size, 0)
    ImageDraw.Draw(large_alpha).ellipse(
        (22 * scale, 22 * scale, 106 * scale, 106 * scale), fill=255
    )
    rgb = np.asarray(large_rgb.resize((size, size), Image.Resampling.LANCZOS), dtype=np.uint8)
    alpha = np.asarray(large_alpha.resize((size, size), Image.Resampling.LANCZOS), dtype=np.uint8)
    return rgb, alpha


class WhiteKeyTests(unittest.TestCase):
    def test_clean_colored_contour_produces_real_alpha(self) -> None:
        def draw(d: ImageDraw.ImageDraw, s: int) -> None:
            d.ellipse((25*s, 25*s, 103*s, 103*s), fill=(235, 145, 170), outline=(165, 68, 105), width=5*s)

        rgba, metrics = white_key.key_array(antialiased_fixture(draw))
        self.assertEqual(0, int(rgba[0, 0, 3]))
        self.assertEqual(255, int(rgba[64, 64, 3]))
        self.assertGreater(metrics["alpha"]["unique"], 2)
        self.assertTrue(metrics["gates"]["machine_pass"])

    def test_enclosed_pure_white_is_removed_globally(self) -> None:
        def draw(d: ImageDraw.ImageDraw, s: int) -> None:
            d.ellipse((20*s, 20*s, 108*s, 108*s), fill=(205, 85, 125))
            d.ellipse((45*s, 45*s, 83*s, 83*s), fill=(254, 254, 254))

        rgba, metrics = white_key.key_array(antialiased_fixture(draw))
        self.assertEqual(0, int(rgba[64, 64, 3]))
        self.assertGreater(metrics["topology"]["enclosed_transparent_pixel_count"], 500)

    def test_tinted_pale_offwhite_foreground_survives(self) -> None:
        def draw(d: ImageDraw.ImageDraw, s: int) -> None:
            d.rounded_rectangle((22*s, 22*s, 106*s, 106*s), radius=12*s,
                                fill=(250, 248, 245), outline=(128, 87, 77), width=4*s)

        rgba, _ = white_key.key_array(antialiased_fixture(draw))
        self.assertGreaterEqual(int(rgba[64, 64, 3]), 250)
        self.assertGreaterEqual(int(rgba[30:98, 30:98, 3].min()), 250)

    def test_regularized_unmix_removes_white_fringe_without_green_despill(self) -> None:
        foreground = np.asarray((210, 70, 95), dtype=np.float64)
        source, true_alpha = circle_fixture_with_true_alpha(tuple(foreground.astype(int)))
        rgba, metrics = white_key.key_array(source)
        true_alpha_f = true_alpha.astype(np.float64) / 255.0
        expected_on_black = np.round(foreground[None, None, :] * true_alpha_f[..., None])
        actual_on_black = white_key.composite(rgba, (0, 0, 0)).astype(np.float64)
        visible_edge = (true_alpha > 5) & (true_alpha < 250)
        edge_error = np.abs(actual_on_black[visible_edge] - expected_on_black[visible_edge])
        alpha_error = np.abs(rgba[..., 3].astype(np.float64) / 255.0 - true_alpha_f)
        self.assertGreater(int(((rgba[..., 3] > 0) & (rgba[..., 3] < 255)).sum()), 10)
        self.assertLess(float(edge_error.mean()), 10.0)
        self.assertLess(float(np.percentile(edge_error, 95)), 20.0)
        self.assertLess(float(np.percentile(alpha_error[visible_edge], 95)), 0.10)
        self.assertFalse(metrics["unmix"]["hue_specific_despill"])
        self.assertLess(metrics["reconstruction_on_sampled_key"]["mae"], 1.5)

    def test_cli_writes_rgba_json_and_four_background_board(self) -> None:
        def draw(d: ImageDraw.ImageDraw, s: int) -> None:
            d.rectangle((30*s, 30*s, 98*s, 98*s), fill=(80, 140, 200))

        rgb = antialiased_fixture(draw)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / "source.png", root / "out.png"
            report, board = root / "metrics.json", root / "board.png"
            Image.fromarray(rgb, "RGB").save(source)
            metrics = white_key.process(source, output, report, board)
            with Image.open(output) as output_image:
                self.assertEqual("RGBA", output_image.mode)
            with Image.open(board) as board_image:
                self.assertEqual((256, 324), board_image.size)
            self.assertTrue(report.is_file())
            self.assertTrue(metrics["gates"]["machine_pass"])

    def test_negative_all_white_trips_rgba_profile_gate(self) -> None:
        rgb = np.full((96, 96, 3), 254, dtype=np.uint8)
        _, metrics = white_key.key_array(rgb)
        self.assertFalse(metrics["gates"]["rgba_profile_valid"])
        self.assertFalse(metrics["gates"]["machine_pass"])

    def test_negative_nonwhite_border_rejects_background_model(self) -> None:
        rgb = np.full((96, 96, 3), (0, 255, 0), dtype=np.uint8)
        with self.assertRaises(white_key.BackgroundModelError):
            white_key.key_array(rgb)

    def test_negative_variable_border_rejects_background_model(self) -> None:
        rgb = np.full((96, 96, 3), 254, dtype=np.uint8)
        rgb[:4, ::2] = 241
        rgb[-4:, 1::2] = 241
        rgb[::2, :4] = 241
        rgb[1::2, -4:] = 241
        with self.assertRaises(white_key.BackgroundModelError):
            white_key.key_array(rgb)


if __name__ == "__main__":
    unittest.main(verbosity=2)
