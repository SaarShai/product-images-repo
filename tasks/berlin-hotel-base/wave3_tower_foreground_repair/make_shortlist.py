#!/usr/bin/env python3
"""Compose shortlist candidates from the strongest wave3 repair lanes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from generate_local_variants import FOREGROUND_ZOOM, SPHERE_ZOOM


ROOT = Path(__file__).resolve().parent
BASELINE = (ROOT / "../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png").resolve()
OUT = ROOT / "shortlist"
ZOOM = OUT / "zooms"


def load(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def overlay_donor_changes(original_base: Image.Image, current: Image.Image, donor: Image.Image) -> Image.Image:
    base_arr = np.asarray(original_base.convert("RGB"))
    current_arr = np.asarray(current.convert("RGB"))
    donor_arr = np.asarray(donor.convert("RGB"))
    changed = np.any(base_arr != donor_arr, axis=2)
    out = current_arr.copy()
    out[changed] = donor_arr[changed]
    return Image.fromarray(out, "RGB")


def compose(name: str, donors: list[Path], note: str) -> str:
    base = load(BASELINE)
    img = base.copy()
    for donor in donors:
        img = overlay_donor_changes(base, img, load(donor))
    OUT.mkdir(parents=True, exist_ok=True)
    ZOOM.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.png")
    img.crop(SPHERE_ZOOM).save(ZOOM / f"{name}_sphere.png")
    img.crop(FOREGROUND_ZOOM).save(ZOOM / f"{name}_foreground.png")
    return f"- `{name}.png` — {note}"


def main() -> None:
    refined = ROOT / "refined_variants"
    sphere = ROOT / "agents/sphere_clean"
    foreground = ROOT / "agents/foreground_clean"
    external = ROOT / "agents/external_edit_probe"

    combos: list[tuple[str, list[Path], str]] = [
        (
            "s01_refined_combo_sphere_poles_soft",
            [refined / "r07_combo_sphere_poles_soft.png"],
            "Main-thread conservative combo: refined sphere sky patch plus softened white foreground wipes.",
        ),
        (
            "s02_refined_combo_neighbor_clone",
            [refined / "r08_combo_sphere_neighbor_clone.png"],
            "Main-thread refined sphere plus narrow neighbor-clone foreground cleanup.",
        ),
        (
            "s03_refined_balanced_subtle_haze",
            [refined / "r09_combo_balanced_subtle_haze.png"],
            "Main-thread refined sphere plus restrained haze tint and wipe softening.",
        ),
        (
            "s04_worker_watercolor_plus_conservative_fg",
            [
                sphere / "sphere_clean_v03_watercolor_haze_blend.png",
                foreground / "foreground_clean_05_conservative_blend.png",
            ],
            "Sphere worker watercolor blend plus foreground worker conservative blend.",
        ),
        (
            "s05_worker_watercolor_plus_sampled_fg",
            [
                sphere / "sphere_clean_v03_watercolor_haze_blend.png",
                foreground / "foreground_clean_01_sampled_texture_patch.png",
            ],
            "Sphere worker watercolor blend plus foreground worker strongest sampled texture cleanup.",
        ),
        (
            "s06_worker_strong_sphere_plus_conservative_fg",
            [
                sphere / "sphere_clean_v05_strong_sky_haze_patch.png",
                foreground / "foreground_clean_05_conservative_blend.png",
            ],
            "Stronger sphere removal plus conservative foreground cleanup.",
        ),
        (
            "s07_worker_watercolor_plus_softwash_fg",
            [
                sphere / "sphere_clean_v03_watercolor_haze_blend.png",
                foreground / "foreground_clean_03_soft_watercolor_wash.png",
            ],
            "Painterly sphere reduction plus soft watercolor foreground wash.",
        ),
        (
            "s08_refined_sphere_plus_foreground_conservative",
            [
                refined / "r01_sphere_sky_patch_refined.png",
                foreground / "foreground_clean_05_conservative_blend.png",
            ],
            "Refined sphere sky patch plus safest foreground worker cleanup.",
        ),
        (
            "s09_openai_bounded_external",
            [external / "openai_bounded_candidate.png"],
            "External OpenAI bounded composite; strongest redesign, included for method comparison.",
        ),
    ]

    notes = [compose(name, donors, note) for name, donors, note in combos]
    (OUT / "notes.md").write_text("# Wave3 Shortlist\n\n" + "\n".join(notes) + "\n")
    print(f"wrote {len(notes)} shortlist candidates to {OUT}")


if __name__ == "__main__":
    main()
