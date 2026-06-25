#!/usr/bin/env python3
"""Main-thread wave 2 candidate generators for the Berlin hotel base."""

from __future__ import annotations

from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path("tasks/berlin-hotel-base")
SRC = ROOT / "work/src.png"
BOX = (3162, 2582, 4082, 2845)
ZOOM = (3050, 2480, 4120, 2900)
TARGET_W = BOX[2] - BOX[0]
TARGET_H = BOX[3] - BOX[1]


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_candidate(method: str, name: str, patch: Image.Image, notes: str) -> None:
    outdir = ROOT / "wave2" / method
    ensure(outdir)
    src = Image.open(SRC).convert("RGB")
    patch = patch.convert("RGB").resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    patch = blend_edges(src, patch)
    out = src.copy()
    out.paste(patch, BOX[:2])
    full = outdir / f"{name}.png"
    zoom = outdir / f"{name}_zoom.png"
    out.save(full)
    out.crop(ZOOM).save(zoom)
    (outdir / "method_notes.md").write_text(notes + "\n", encoding="utf-8")


def blend_edges(src: Image.Image, patch: Image.Image) -> Image.Image:
    """Softly mix only the edge pixels with the original box to reduce hard seams."""
    original = src.crop(BOX).convert("RGB")
    alpha = Image.new("L", patch.size, 255)
    px = alpha.load()
    w, h = patch.size
    ramp_top = 24
    ramp_bottom = 14
    ramp_side = 8
    for y in range(h):
        for x in range(w):
            a = 255
            if y < ramp_top:
                a = min(a, int(255 * y / ramp_top))
            if h - 1 - y < ramp_bottom:
                a = min(a, int(255 * (h - 1 - y) / ramp_bottom))
            if x < ramp_side:
                a = min(a, int(255 * x / ramp_side))
            if w - 1 - x < ramp_side:
                a = min(a, int(255 * (w - 1 - x) / ramp_side))
            px[x, y] = max(0, min(255, a))
    return Image.composite(patch, original, alpha)


def color_match_to_art(patch: Image.Image) -> Image.Image:
    src = Image.open(SRC).convert("RGB")
    target = np.asarray(src.crop((3162, 2350, 4082, 2582))).astype(np.float32)
    arr = np.asarray(patch.convert("RGB")).astype(np.float32)
    t_mean = target.reshape(-1, 3).mean(axis=0)
    t_std = target.reshape(-1, 3).std(axis=0)
    a_mean = arr.reshape(-1, 3).mean(axis=0)
    a_std = arr.reshape(-1, 3).std(axis=0)
    arr = (arr - a_mean) / np.maximum(a_std, 1.0) * np.maximum(t_std * 0.92, 1.0) + t_mean
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def add_paper_wash(patch: Image.Image, strength: float = 0.08) -> Image.Image:
    arr = np.asarray(patch.convert("RGB")).astype(np.int16)
    rng = np.random.default_rng(22023)
    noise = rng.normal(0, 9, (patch.height, patch.width, 1))
    wash = np.clip(arr + noise * strength * 5, 0, 255).astype(np.uint8)
    return Image.fromarray(wash, "RGB").filter(ImageFilter.SMOOTH_MORE)


def plate_crop(path: Path, crop: tuple[int, int, int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    patch = im.crop(crop)
    patch = color_match_to_art(patch)
    patch = ImageEnhance.Contrast(patch).enhance(0.88)
    patch = ImageEnhance.Color(patch).enhance(0.68)
    return add_paper_wash(patch, 0.05)


def make_photo_stylized() -> Image.Image:
    ref = Image.open(ROOT / "refs/ritz_streetlevel.png").convert("RGB")
    # Upper podium band: avoids cars/people/canopy while keeping real facade rhythm.
    crop = ref.crop((62, 145, 610, 470))
    crop = crop.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    gray_edges = crop.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.7))
    edges = ImageOps.autocontrast(gray_edges)
    base = ImageEnhance.Color(crop).enhance(0.18)
    base = ImageEnhance.Contrast(base).enhance(0.55)
    base = color_match_to_art(base)
    ink = Image.new("RGB", base.size, (75, 83, 82))
    edge_mask = ImageOps.invert(edges).point(lambda v: 0 if v > 228 else 68)
    base = Image.composite(ink, base, edge_mask)
    base = add_paper_wash(base, 0.07)
    # Modest plinth so it meets the quay rather than floating.
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rectangle((0, TARGET_H - 34, TARGET_W, TARGET_H), fill=(188, 179, 154, 120))
    for y in range(TARGET_H - 30, TARGET_H, 9):
        draw.line((0, y, TARGET_W, y), fill=(105, 105, 95, 75), width=1)
    return base


def make_vector_paintover() -> Image.Image:
    src = Image.open(SRC).convert("RGB")
    facade = src.crop((3162, 2350, 4082, 2582)).resize((TARGET_W, TARGET_H), Image.Resampling.BICUBIC)
    base = ImageEnhance.Contrast(facade).enhance(0.72)
    base = ImageEnhance.Color(base).enhance(0.72)
    base = base.filter(ImageFilter.GaussianBlur(0.35))
    draw = ImageDraw.Draw(base, "RGBA")
    random.seed(22023)
    # Warm limestone wash.
    draw.rectangle((0, 0, TARGET_W, TARGET_H), fill=(224, 213, 184, 42))
    bay_w = 86
    start = 20
    for i, x in enumerate(range(start, TARGET_W - 30, bay_w)):
        pier_x = x + bay_w - 12
        shade = 54 if i % 3 else 40
        draw.rectangle((x - 6, 2, x + 5, TARGET_H - 28), fill=(158, 150, 126, 38))
        draw.rectangle((pier_x, 0, pier_x + 10, TARGET_H - 30), fill=(102, 105, 102, shade))
        for yy, h in ((20, 72), (112, 70)):
            wx = x + 17
            ww = 38
            draw.rectangle((wx - 5, yy - 8, wx + ww + 5, yy + h + 8), fill=(230, 218, 190, 96))
            draw.rectangle((wx, yy, wx + ww, yy + h), fill=(65, 91, 102, 128))
            draw.line((wx + ww // 2, yy + 3, wx + ww // 2, yy + h - 3), fill=(230, 224, 201, 95), width=2)
            draw.line((wx + 4, yy + h // 2, wx + ww - 4, yy + h // 2), fill=(49, 66, 72, 70), width=1)
    # Receding right face gets tighter lighter bays.
    for x in range(TARGET_W - 210, TARGET_W - 5, 34):
        draw.line((x, 8, x + 10, TARGET_H - 32), fill=(96, 101, 96, 65), width=2)
        draw.rectangle((x + 8, 42, x + 18, 100), fill=(58, 83, 93, 96))
        draw.rectangle((x + 18, 128, x + 28, 186), fill=(58, 83, 93, 78))
    # Cornice and plinth.
    draw.rectangle((0, 0, TARGET_W, 18), fill=(196, 184, 158, 105))
    draw.line((0, 19, TARGET_W, 19), fill=(88, 90, 86, 80), width=2)
    draw.rectangle((0, TARGET_H - 46, TARGET_W, TARGET_H), fill=(182, 173, 150, 135))
    for y in range(TARGET_H - 42, TARGET_H, 11):
        draw.line((0, y, TARGET_W, y), fill=(102, 102, 91, 74), width=1)
    for x in range(18, TARGET_W, 63):
        draw.line((x, TARGET_H - 44, x + random.randint(-2, 2), TARGET_H - 4), fill=(111, 105, 93, 48), width=1)
    return add_paper_wash(base, 0.05)


def make_plate_hybrid() -> Image.Image:
    seam_source = plate_crop(ROOT / "work/berlin_hotel_frontal_watercolor_elevation.png", (78, 1280, 920, 1514))
    base_source = plate_crop(ROOT / "work/building_recreate/cand_openai_p1.png", (90, 1320, 900, 1578))
    seam_source = seam_source.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    base_source = base_source.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    mask = Image.new("L", (TARGET_W, TARGET_H), 0)
    px = mask.load()
    for y in range(TARGET_H):
        if y < 110:
            a = 0
        elif y > 178:
            a = 255
        else:
            a = int(255 * (y - 110) / 68)
        for x in range(TARGET_W):
            px[x, y] = a
    hybrid = Image.composite(base_source, seam_source, mask)
    draw = ImageDraw.Draw(hybrid, "RGBA")
    draw.rectangle((0, TARGET_H - 34, TARGET_W, TARGET_H), fill=(174, 164, 142, 72))
    draw.line((0, TARGET_H - 36, TARGET_W, TARGET_H - 36), fill=(82, 86, 82, 70), width=2)
    return add_paper_wash(hybrid, 0.04)


def main() -> int:
    save_candidate(
        "w2_main_tower_plate",
        "frontal_elevation_base_registered",
        plate_crop(ROOT / "work/berlin_hotel_frontal_watercolor_elevation.png", (78, 1280, 920, 1514)),
        "# w2_main_tower_plate\n\nUsed existing generated full-tower frontal watercolor elevation and harvested the coherent lower base/plinth. Color-matched to the artwork facade and composited only inside the allowed edit box.",
    )
    save_candidate(
        "w2_main_design_plate",
        "openai_p1_lower_base_registered",
        plate_crop(ROOT / "work/building_recreate/cand_openai_p1.png", (90, 1320, 900, 1578)),
        "# w2_main_design_plate\n\nUsed unjudged `cand_openai_p1` lower tower/base as a standalone design plate. This tests whether a complete generated tower source gives a more coherent base than base-only inpainting.",
    )
    save_candidate(
        "w2_main_design_plate",
        "openai_p2_lower_base_registered",
        plate_crop(ROOT / "work/building_recreate/cand_openai_p2.png", (90, 1320, 900, 1578)),
        "# w2_main_design_plate\n\nUsed unjudged `cand_openai_p2` lower tower/base as a standalone design plate. p1/p2/p3 are similar but retained as a tiny tournament for registration/crop sensitivity.",
    )
    save_candidate(
        "w2_main_design_plate",
        "openai_p3_lower_base_registered",
        plate_crop(ROOT / "work/building_recreate/cand_openai_p3.png", (90, 1320, 900, 1578)),
        "# w2_main_design_plate\n\nUsed unjudged `cand_openai_p3` lower tower/base as a standalone design plate. p1/p2/p3 are similar but retained as a tiny tournament for registration/crop sensitivity.",
    )
    save_candidate(
        "w2_main_design_plate",
        "flux2_p1_lower_base_registered",
        plate_crop(ROOT / "work/building_recreate/cand_flux2_p1.png", (115, 1388, 985, 1676)),
        "# w2_main_design_plate\n\nUsed unjudged `cand_flux2_p1` lower tower/base as a standalone design plate. This tests a grittier, more perspectival source plate.",
    )
    save_candidate(
        "w2_main_design_plate",
        "flux2_p3_lower_base_registered",
        plate_crop(ROOT / "work/building_recreate/cand_flux2_p3.png", (130, 1360, 990, 1668)),
        "# w2_main_design_plate\n\nUsed unjudged `cand_flux2_p3` lower tower/base as a standalone design plate. This tests whether a perspectival source with more ground-floor character can survive registration.",
    )
    save_candidate(
        "w2_main_photo_stylized",
        "streetlevel_facade_artified",
        make_photo_stylized(),
        "# w2_main_photo_stylized\n\nUsed `refs/ritz_streetlevel.png` upper podium facade as real-architecture source, then desaturated, edge-extracted, color-matched, and added a modest plinth.",
    )
    save_candidate(
        "w2_main_vector_paintover",
        "vector_pier_window_base",
        make_vector_paintover(),
        "# w2_main_vector_paintover\n\nDrew a vector/paintover base from measured facade rhythm: piers, regular narrow windows, receding right face, cornice, and plinth. Uses artwork pixels as texture source.",
    )
    save_candidate(
        "w2_main_hybrid_plate",
        "tower_seam_openai_groundfloor_hybrid",
        make_plate_hybrid(),
        "# w2_main_hybrid_plate\n\nHybrid synthesis from early evidence: top/seam from the complete frontal tower elevation, lower ground-floor/plinth from `cand_openai_p1`. Tests whether full-tower coherence plus a distinct but quiet ground floor beats either alone.",
    )
    print("created main-thread candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
