#!/usr/bin/env python3
"""Focused positive and negative checks for the image14 label builder."""

from __future__ import annotations

import unittest

import build_labels


class LabelBuilderTest(unittest.TestCase):
    def test_explicit_annotation_passes_validation(self) -> None:
        _, alpha, diagnostic, _ = build_labels.load_inputs()
        annotation, red_mask, blue_mask = build_labels.build_annotation()
        checks = build_labels.validate(
            annotation, red_mask, blue_mask, alpha, diagnostic
        )
        self.assertEqual(checks["red_pixels"], 3215)
        self.assertEqual(checks["blue_pixels"], 0)

    def test_unexpected_rgba_color_is_rejected(self) -> None:
        _, alpha, diagnostic, _ = build_labels.load_inputs()
        annotation, red_mask, blue_mask = build_labels.build_annotation()
        annotation.putpixel((0, 0), (0, 255, 0, 255))
        with self.assertRaisesRegex(RuntimeError, "Unexpected annotation colors"):
            build_labels.validate(
                annotation, red_mask, blue_mask, alpha, diagnostic
            )

    def test_red_blue_overlap_is_rejected(self) -> None:
        original_blue = build_labels.BLUE_STROKES
        try:
            build_labels.BLUE_STROKES = [build_labels.RED_STROKES[0]]
            with self.assertRaisesRegex(RuntimeError, "overlap"):
                build_labels.build_annotation()
        finally:
            build_labels.BLUE_STROKES = original_blue


if __name__ == "__main__":
    unittest.main()
