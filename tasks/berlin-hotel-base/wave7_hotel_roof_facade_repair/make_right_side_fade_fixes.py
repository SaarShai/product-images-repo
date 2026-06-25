#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = Path("tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png")
V10 = RESULTS / "v10_precise_roof_cap_ledge_facade_restored.png"
CROP_BOX = (3500, 980, 3900, 1420)
STAIR_PROTECTED = (1720, 2200, 2600, 2940)

# Right-side roof/parapet area only. Keep the window/floor grid below out of all
# masks; the user selected v10 because its top floors are better preserved.
RIGHT_PARAPET = [
    (3685, 1122),
    (3812, 1142),
    (3862, 1204),
    (3840, 1288),
    (3732, 1272),
    (3678, 1228),
]
RIGHT_OUTER_FACE = [
    (3772, 1182),
    (3890, 1240),
    (3885, 1382),
    (3795, 1338),
    (3738, 1276),
]
RIGHT_EDGE_STRIP = [
    (3650, 1052),
    (3712, 1072),
    (3718, 1292),
    (3658, 1294),
]
FACADE_GUARD = [
    (3425, 1320),
    (3920, 1320),
    (3920, 1680),
    (3425, 1680),
]

RIGHT_REAR_FACE_SMALL = [
    (3705, 1088),
    (3818, 1150),
    (3860, 1210),
    (3838, 1288),
    (3755, 1268),
    (3690, 1198),
]
RIGHT_REAR_FACE_TINY = [
    (3728, 1098),
    (3810, 1156),
    (3848, 1208),
    (3828, 1266),
    (3768, 1248),
    (3712, 1190),
]
RIGHT_EDGE_WATERCOLOR = [
    (3825, 1198),
    (3866, 1222),
    (3850, 1342),
    (3814, 1326),
]


def load_donor(raw: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(raw).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def mask(size: tuple[int, int], polys: list[list[tuple[int, int]]], feather: int, opacity: float = 1.0) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for poly in polys:
        d.polygon(poly, fill=round(255 * opacity))
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    guard = Image.new("L", size, 0)
    gd = ImageDraw.Draw(guard)
    gd.polygon(FACADE_GUARD, fill=255)
    arr = np.asarray(m).copy()
    arr[np.asarray(guard) > 0] = 0
    return Image.fromarray(arr, "L")


def draw_linework(im: Image.Image, strength: int = 92) -> Image.Image:
    out = im.copy()
    d = ImageDraw.Draw(out, "RGBA")
    edge = (112, 104, 82, strength)
    pale = (238, 226, 188, strength)
    # Reassert the right roof side geometry and watercolor stone courses.
    d.line([(3690, 1126), (3818, 1148), (3862, 1208)], fill=edge, width=4)
    d.line([(3728, 1274), (3836, 1288)], fill=edge, width=3)
    d.line([(3860, 1208), (3840, 1368)], fill=edge, width=3)
    d.line([(3746, 1192), (3840, 1240)], fill=pale, width=3)
    d.line([(3750, 1234), (3840, 1280)], fill=(146, 132, 94, max(40, strength // 2)), width=2)
    for x in (3758, 3798, 3830):
        d.line([(x, 1168), (x - 4, 1290)], fill=(130, 120, 92, max(32, strength // 3)), width=1)
    return out


def diff_overlay(base_crop: Image.Image, crop: Image.Image, path: Path) -> None:
    diff = ImageChops.difference(base_crop, crop).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 5, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 120)
    Image.blend(base_crop, Image.fromarray(heat), 0.48).save(path)


def save_variant(name: str, im: Image.Image, base_for_diff: Image.Image) -> tuple[str, Path]:
    path = RESULTS / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    im.crop(CROP_BOX).save(RESULTS / f"{name}_right_top_crop.png")
    diff_overlay(base_for_diff.crop(CROP_BOX), im.crop(CROP_BOX), RESULTS / f"{name}_right_top_diff_overlay.png")
    return name, path


def fit_for_crop(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def make_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 430, 500
    cols = 2
    rows = (len(items) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items):
        im = fit_for_crop(path, Image.open(V10).size)
        crop = im.crop(CROP_BOX).resize((400, 440), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * tile_w
        y = 10 + (i // cols) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(RESULTS / "hotel_roof_facade_right_side_fade_fix_board.png")


def verify(variants: list[tuple[str, Path]]) -> None:
    v10 = np.asarray(Image.open(V10).convert("RGB"))
    base = np.asarray(Image.open(BASE).convert("RGB"))
    facade = np.zeros(v10.shape[:2], dtype=bool)
    facade[1320:1680, 3425:3920] = True
    stair = np.zeros(v10.shape[:2], dtype=bool)
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    stair[sy0:sy1, sx0:sx1] = True
    lines = []
    for label, path in variants:
        im = np.asarray(Image.open(path).convert("RGB"))
        diff_v10 = np.abs(im.astype(int) - v10.astype(int)).max(axis=2) > 2
        diff_base = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tchanged_vs_v10={int(diff_v10.sum())}"
            f"\tfacade_guard_changed_vs_v10={int((diff_v10 & facade).sum())}"
            f"\tfacade_guard_changed_vs_base={int((diff_base & facade).sum())}"
            f"\tstair_protected_changed_vs_v10={int((diff_v10 & stair).sum())}"
            f"\tpath={path.resolve()}"
        )
    (RESULTS / "hotel_roof_facade_right_side_fade_fix_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    v10 = Image.open(V10).convert("RGB")
    base = Image.open(BASE).convert("RGB")
    precise = load_donor(RAW / "reference_guided_top_precise_raw.png", v10.size)
    loose = load_donor(RAW / "reference_guided_top_loose_raw.png", v10.size)

    m_precise = mask(v10.size, [RIGHT_PARAPET, RIGHT_OUTER_FACE], feather=3, opacity=0.96)
    v11 = Image.composite(precise, v10, m_precise)

    m_precise_edge = mask(v10.size, [RIGHT_PARAPET, RIGHT_OUTER_FACE, RIGHT_EDGE_STRIP], feather=2, opacity=1.0)
    v12 = draw_linework(Image.composite(precise, v10, m_precise_edge), strength=58)

    # The loose donor has a warmer/watercolor side face; use it in a smaller patch.
    m_loose = mask(v10.size, [RIGHT_OUTER_FACE], feather=5, opacity=0.72)
    v13 = draw_linework(Image.composite(loose, v10, m_loose), strength=70)

    # Conservative manual-only candidate if donor pixels introduce too much new geometry.
    v14 = draw_linework(v10, strength=92)

    m_small = mask(v10.size, [RIGHT_REAR_FACE_SMALL], feather=2, opacity=0.86)
    v15 = Image.composite(precise, v10, m_small)

    m_tiny = mask(v10.size, [RIGHT_REAR_FACE_TINY], feather=1, opacity=0.94)
    v16 = Image.composite(precise, v10, m_tiny)

    m_edge = mask(v10.size, [RIGHT_EDGE_WATERCOLOR], feather=3, opacity=0.72)
    v17 = Image.composite(precise, v10, m_edge)

    m_combo = ImageChops.lighter(m_tiny, m_edge)
    v18 = Image.composite(precise, v10, m_combo)

    variants = [
        save_variant("v11_right_parapet_precise_reinforced", v11, v10),
        save_variant("v12_right_parapet_precise_plus_edge_lines", v12, v10),
        save_variant("v13_right_face_warm_donor_plus_lines", v13, v10),
        save_variant("v14_right_face_linework_only", v14, v10),
        save_variant("v15_right_rear_face_small_precise", v15, v10),
        save_variant("v16_right_rear_face_tiny_precise", v16, v10),
        save_variant("v17_right_outer_edge_soft_precise", v17, v10),
        save_variant("v18_right_face_tiny_plus_edge", v18, v10),
    ]
    board_items = [
        ("v10 selected baseline", V10),
        ("precise donor context", RAW / "reference_guided_top_precise_raw.png"),
        *variants[:1],
        *variants[4:],
    ]
    make_board(board_items)
    verify(variants)


if __name__ == "__main__":
    main()
