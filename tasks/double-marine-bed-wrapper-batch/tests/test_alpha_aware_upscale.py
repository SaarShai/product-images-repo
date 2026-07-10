#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


MODULE_PATH = Path(__file__).resolve().parents[1] / "alpha_aware_upscale.py"
SPEC = importlib.util.spec_from_file_location("alpha_aware_upscale", MODULE_PATH)
assert SPEC and SPEC.loader
up = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = up
SPEC.loader.exec_module(up)


def synthetic_rgba(width: int = 24, height: int = 20) -> Image.Image:
    y, x = np.mgrid[:height, :width].astype(np.float32)
    rgb = np.stack(
        [
            35 + 180 * x / max(1, width - 1),
            45 + 160 * y / max(1, height - 1),
            220 - 120 * x / max(1, width - 1),
        ],
        axis=2,
    )
    radius = np.sqrt((x - width * 0.52) ** 2 + (y - height * 0.48) ** 2)
    alpha = np.clip((min(width, height) * 0.42 - radius) / 3.5, 0, 1)
    rgba = np.dstack([np.rint(rgb), np.rint(alpha * 255)]).astype(np.uint8)
    return Image.fromarray(rgba)


def fake_x4(image: Image.Image) -> Image.Image:
    return image.resize((image.width * 4, image.height * 4), Image.Resampling.LANCZOS)


def mae(a: Image.Image, b: Image.Image) -> float:
    aa = np.asarray(a, dtype=np.float32)
    bb = np.asarray(b, dtype=np.float32)
    return float(np.mean(np.abs(aa - bb)))


class AlphaAwareUpscaleTests(unittest.TestCase):
    def test_command_construction_stub(self) -> None:
        command = up.build_realesrgan_command(
            Path("/bin/realesrgan"),
            Path("/models"),
            Path("in.png"),
            Path("out.png"),
            tile=128,
        )
        self.assertEqual(
            command,
            [
                "/bin/realesrgan", "-i", "in.png", "-o", "out.png",
                "-n", "realesrgan-x4plus", "-m", "/models", "-s", "4",
                "-t", "128", "-f", "png",
            ],
        )

    def test_final_path_negative_fixture_trips(self) -> None:
        with self.assertRaisesRegex(up.AlphaUpscaleError, "refusing final"):
            up.reject_final_path(Path("/project/Images/finals/forbidden.png"))
        with self.assertRaisesRegex(up.AlphaUpscaleError, "refusing final"):
            up.reject_final_path(Path("/project/Images/final/forbidden.png"))

    def test_missing_ack_negative_fixture_trips(self) -> None:
        with self.assertRaisesRegex(up.AlphaUpscaleError, "not acknowledged"):
            up.validate_request(Path("missing.png"), Path("candidate.png"), acknowledged=False)

    def test_hidden_rgb_extension_preserves_visible_and_fills_zero_alpha(self) -> None:
        source = np.asarray(synthetic_rgba()).copy()
        source[source[:, :, 3] == 0, :3] = 255
        extended = up.extend_hidden_rgb(source[:, :, :3], source[:, :, 3])
        visible = source[:, :, 3] > 0
        self.assertTrue(np.array_equal(extended[visible], source[visible, :3]))
        self.assertFalse(np.any(np.all(extended[~visible] == 255, axis=1)))
        self.assertTrue(np.isfinite(extended).all())

    def test_split_is_exact_x8_soft_rgba_and_source_unchanged(self) -> None:
        source = synthetic_rgba()
        before = np.asarray(source).copy()
        result = up.upscale_split(source, fake_x4)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, (source.width * 8, source.height * 8))
        alpha = np.asarray(result.getchannel("A"))
        self.assertGreater(np.count_nonzero((alpha > 0) & (alpha < 255)), 0)
        self.assertTrue(np.array_equal(np.asarray(source), before))
        rgb = np.asarray(result.convert("RGB"))
        self.assertTrue(np.isfinite(rgb).all())
        self.assertGreaterEqual(int(rgb.min()), 0)
        self.assertLessEqual(int(rgb.max()), 255)
        reference = up.compare_alpha_to_split_reference(source, result)
        self.assertTrue(reference["exact_match"])
        self.assertEqual(reference["max_error_8bit"], 0)

    def test_direct_is_exact_x8_and_preserves_soft_alpha(self) -> None:
        source = synthetic_rgba()
        result = up.upscale_direct(source, fake_x4)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, (source.width * 8, source.height * 8))
        alpha = np.asarray(result.getchannel("A"))
        self.assertGreater(np.count_nonzero((alpha > 0) & (alpha < 255)), 0)

    def test_review_board_contains_four_backgrounds(self) -> None:
        source = synthetic_rgba(width=12, height=8)
        board = up.make_review_board(source, max_side=12)
        self.assertEqual(board.mode, "RGB")
        self.assertEqual(board.size, (24, 68))

    def test_two_plate_known_alpha_and_halo_metrics(self) -> None:
        source = synthetic_rgba()
        split = up.upscale_split(source, fake_x4)
        two_plate = up.upscale_two_plate(source, fake_x4, alpha_floor=0.02)
        self.assertEqual(two_plate.mode, "RGBA")
        self.assertEqual(two_plate.size, split.size)

        expected_alpha = np.asarray(split.getchannel("A"), dtype=np.float32)
        recovered_alpha = np.asarray(two_plate.getchannel("A"), dtype=np.float32)
        alpha_mae = float(np.mean(np.abs(expected_alpha - recovered_alpha))) / 255.0
        self.assertLess(alpha_mae, 3.0 / 255.0)

        for background in ((0, 0, 0), (255, 0, 255)):
            halo_mae = mae(up.composite_rgb(two_plate, background), up.composite_rgb(split, background))
            self.assertLess(halo_mae, 3.0)

    def test_two_plate_white_black_recomposition(self) -> None:
        source = synthetic_rgba()
        recovered = up.upscale_two_plate(source, fake_x4, alpha_floor=0.02)
        final_size = recovered.size
        for background in ((0, 0, 0), (255, 255, 255)):
            plate = fake_x4(up.composite_rgb(source, background)).resize(final_size, Image.Resampling.LANCZOS)
            recomposed = up.composite_rgb(recovered, background)
            self.assertLess(mae(plate, recomposed), 2.5)

    def test_low_alpha_recovery_has_no_division_blowup(self) -> None:
        height, width = 12, 17
        y, x = np.mgrid[:height, :width].astype(np.float32)
        alpha = np.clip((x + y) / 120.0, 0, 0.2)
        foreground = np.stack(
            [np.full_like(alpha, 0.8), np.full_like(alpha, 0.25), np.full_like(alpha, 0.55)],
            axis=2,
        )
        black = np.rint(foreground * alpha[:, :, None] * 255).astype(np.uint8)
        white = np.rint((foreground * alpha[:, :, None] + 1 - alpha[:, :, None]) * 255).astype(np.uint8)
        rgb, recovered_alpha = up.recover_two_plate(black, white, alpha_floor=0.05)
        self.assertTrue(np.isfinite(rgb).all())
        self.assertTrue(np.isfinite(recovered_alpha).all())
        self.assertGreaterEqual(int(rgb.min()), 0)
        self.assertLessEqual(int(rgb.max()), 255)


if __name__ == "__main__":
    unittest.main()
