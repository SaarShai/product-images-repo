#!/usr/bin/env python3
"""Deterministic tests for build_region_map.py. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOL = os.path.join(HERE, "build_region_map.py")
EXAMPLE_MANIFEST = os.path.join(
    REPO_ROOT, "skills", "region-map-guide", "examples", "wanderland-door.manifest.json"
)

PALETTE = {
    "pink": (0xE7, 0x00, 0x8A),
    "grey": (0x9E, 0x9E, 0x9E),
    "orange": (0xF5, 0x92, 0x1E),
    "blue": (0x00, 0x00, 0xEE),
    "green": (0x00, 0xC8, 0x00),
    "black": (0x11, 0x11, 0x11),
    "yellow": (0xF2, 0xD4, 0x00),
    "purple": (0x7B, 0x2F, 0xBE),
    "cyan": (0x00, 0xB8, 0xD4),
    "brown": (0x8B, 0x5A, 0x2B),
}


def run_tool(args):
    return subprocess.run(
        [sys.executable, TOOL] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


class HappyPathTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_png = os.path.join(self.tmpdir, "map.png")
        self.legend_txt = os.path.join(self.tmpdir, "legend.txt")
        with open(EXAMPLE_MANIFEST) as f:
            self.manifest = json.load(f)

    def test_build_example(self):
        result = run_tool(
            [
                "--manifest",
                EXAMPLE_MANIFEST,
                "--out",
                self.out_png,
                "--legend-out",
                self.legend_txt,
                "--expect-aspect",
                "1243:1776",
            ]
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # (a) output size == canvas
        img = Image.open(self.out_png).convert("RGB")
        canvas = self.manifest["canvas"]
        self.assertEqual(img.size, (canvas["width"], canvas["height"]))

        # (b) every palette color used appears in the output pixels
        used_colors = {self.manifest["silhouette"]["color"]}
        for region in self.manifest["regions"]:
            used_colors.add(region["color"])

        present = set()
        pixels = img.getdata()
        target_rgbs = {PALETTE[name]: name for name in used_colors}
        for px in pixels:
            if px in target_rgbs:
                present.add(target_rgbs[px])
            if present == used_colors:
                break
        self.assertEqual(present, used_colors, f"missing colors: {used_colors - present}")

        # (c) legend contains each region's color word and means text
        with open(self.legend_txt) as f:
            legend = f.read()
        for region in self.manifest["regions"]:
            self.assertIn(region["color"], legend)
            self.assertIn(region["means"], legend)


class LegendQualityTest(unittest.TestCase):
    """Regression coverage for the wanderland-door example legend:
    (1) same-means regions merge into one legend line (no duplicates),
    (2) the silhouette gets its own legend line,
    (3) the avoid:true door-knob region is phrased as a prohibition.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_png = os.path.join(self.tmpdir, "map.png")
        self.legend_txt = os.path.join(self.tmpdir, "legend.txt")
        with open(EXAMPLE_MANIFEST) as f:
            self.manifest = json.load(f)

    def test_legend_quality(self):
        result = run_tool(
            [
                "--manifest",
                EXAMPLE_MANIFEST,
                "--out",
                self.out_png,
                "--legend-out",
                self.legend_txt,
                "--expect-aspect",
                "1243:1776",
            ]
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        with open(self.legend_txt) as f:
            legend = f.read()

        # no duplicate legend lines (e.g. the two blue lamp regions share
        # the same means and must collapse to a single "blue = ..." line)
        body = legend.split("Regions: ", 1)[1]
        region_lines = [line.strip() for line in body.split(". ") if line.strip()]
        self.assertEqual(
            len(region_lines),
            len(set(region_lines)),
            f"duplicate legend lines found: {region_lines}",
        )
        self.assertEqual(
            legend.count("blue = a wall-mounted lamp fixture"),
            1,
            "blue lamp legend line should appear exactly once",
        )

        # silhouette line present, using its manifest "means"
        silhouette = self.manifest["silhouette"]
        self.assertIn(silhouette["color"], legend)
        self.assertIn(silhouette["means"], legend)

        # avoid:true door-knob region phrased as a prohibition
        knob_region = next(
            r for r in self.manifest["regions"] if r["name"] == "door-knobs"
        )
        self.assertTrue(knob_region.get("avoid"))
        self.assertIn("black dots", legend)
        self.assertIn("do NOT", legend)


class AvoidPhrasingTest(unittest.TestCase):
    """avoid:true region must be phrased as a prohibition ('do NOT')."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manifest_path = os.path.join(self.tmpdir, "manifest.json")
        self.out_png = os.path.join(self.tmpdir, "map.png")
        self.legend_txt = os.path.join(self.tmpdir, "legend.txt")
        manifest = {
            "canvas": {"width": 200, "height": 200, "background": "white"},
            "regions": [
                {
                    "name": "keep-clear",
                    "means": "any large motif",
                    "color": "purple",
                    "avoid": True,
                    "shape": {"type": "rect", "x": 10, "y": 10, "w": 50, "h": 50},
                }
            ],
        }
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f)

    def test_avoid_phrasing(self):
        result = run_tool(
            [
                "--manifest",
                self.manifest_path,
                "--out",
                self.out_png,
                "--legend-out",
                self.legend_txt,
            ]
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        with open(self.legend_txt) as f:
            legend = f.read()
        self.assertIn("do NOT", legend)
        self.assertIn("any large motif", legend)


class NegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_png = os.path.join(self.tmpdir, "map.png")
        self.legend_txt = os.path.join(self.tmpdir, "legend.txt")

    def _write(self, manifest):
        path = os.path.join(self.tmpdir, "manifest.json")
        with open(path, "w") as f:
            json.dump(manifest, f)
        return path

    def _run(self, manifest, extra_args=None):
        path = self._write(manifest)
        args = [
            "--manifest",
            path,
            "--out",
            self.out_png,
            "--legend-out",
            self.legend_txt,
        ]
        if extra_args:
            args += extra_args
        return run_tool(args)

    def test_aspect_mismatch(self):
        manifest = {
            "canvas": {"width": 200, "height": 100, "background": "white"},
            "regions": [],
        }
        result = self._run(manifest, ["--expect-aspect", "1:1"])
        self.assertEqual(result.returncode, 2)

    def test_duplicate_color(self):
        manifest = {
            "canvas": {"width": 200, "height": 200, "background": "white"},
            "regions": [
                {
                    "name": "a",
                    "means": "thing A",
                    "color": "blue",
                    "shape": {"type": "rect", "x": 0, "y": 0, "w": 10, "h": 10},
                },
                {
                    "name": "b",
                    "means": "thing B",
                    "color": "blue",
                    "shape": {"type": "rect", "x": 20, "y": 20, "w": 10, "h": 10},
                },
            ],
        }
        result = self._run(manifest)
        self.assertEqual(result.returncode, 2)

    def test_unknown_color(self):
        manifest = {
            "canvas": {"width": 200, "height": 200, "background": "white"},
            "regions": [
                {
                    "name": "a",
                    "means": "thing A",
                    "color": "magenta-ish",
                    "shape": {"type": "rect", "x": 0, "y": 0, "w": 10, "h": 10},
                }
            ],
        }
        result = self._run(manifest)
        self.assertEqual(result.returncode, 2)

    def test_band_missing_reference(self):
        manifest = {
            "canvas": {"width": 200, "height": 200, "background": "white"},
            "regions": [
                {
                    "name": "frame",
                    "means": "a frame",
                    "color": "orange",
                    "shape": {"type": "band", "around": "nonexistent", "thickness": 5},
                }
            ],
        }
        result = self._run(manifest)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
