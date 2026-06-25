#!/usr/bin/env python3
"""Assemble standalone lower-tower/base design plates for the Berlin hotel base.

All outputs are written next to this script. The only full-source composites
modify the allowed wave-2 edit box: x=3162..4082, y=2582..2845.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent
TASK = ROOT.parents[1]
SRC_PATH = TASK / "work" / "src.png"

BOX = (3162, 2582, 4082, 2845)
X0, Y0, X1, Y1 = BOX
W = X1 - X0
H = Y1 - Y0

PLATES = ROOT / "plates"
COMPOSITES = ROOT / "composites"
ZOOMS = ROOT / "zooms"
for out_dir in (PLATES, COMPOSITES, ZOOMS):
    out_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PlateSpec:
    name: str
    family: str
    path: Path
    verdict: str


def rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def to_array(im: Image.Image) -> np.ndarray:
    return np.asarray(im).astype(np.float32)


def from_array(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def watercolorize(im: Image.Image, color: float = 0.82, contrast: float = 0.92, brightness: float = 1.04) -> Image.Image:
    im = ImageEnhance.Color(im).enhance(color)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    im = ImageEnhance.Brightness(im).enhance(brightness)
    return Image.blend(im, im.filter(ImageFilter.GaussianBlur(0.55)), 0.26)


def color_match(im: Image.Image, ref: Image.Image, strength: float = 0.86) -> Image.Image:
    arr = to_array(im)
    ref_arr = to_array(ref.resize(im.size, Image.Resampling.BICUBIC))
    mean = arr.reshape(-1, 3).mean(axis=0)
    std = arr.reshape(-1, 3).std(axis=0) + 1.0
    ref_mean = ref_arr.reshape(-1, 3).mean(axis=0)
    ref_std = ref_arr.reshape(-1, 3).std(axis=0) + 1.0
    matched = (arr - mean) * (ref_std / std) + ref_mean
    out = arr * (1.0 - strength) + matched * strength
    return from_array(out)


def nonwhite_bbox(im: Image.Image) -> tuple[int, int, int, int]:
    arr = np.asarray(im.convert("RGB"))
    mask = (arr[:, :, 0] < 246) | (arr[:, :, 1] < 246) | (arr[:, :, 2] < 246)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    pad = 8
    return (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(im.width, int(xs.max()) + pad + 1),
        min(im.height, int(ys.max()) + pad + 1),
    )


def nonwhite_alpha(im: Image.Image) -> Image.Image:
    arr = np.asarray(im.convert("RGB"))
    mask = (arr[:, :, 0] < 235) | (arr[:, :, 1] < 235) | (arr[:, :, 2] < 235)
    alpha = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    return alpha.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(2.0))


def add_plinth(im: Image.Image, height: int, tone=(219, 213, 191), top_line=(112, 122, 116)) -> Image.Image:
    out = im.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    y0 = H - height
    draw.rectangle((0, y0, W, H), fill=(*tone, 220))
    for y in (y0 + 3, y0 + height // 2, H - 5):
        draw.line((0, y, W, y), fill=(*top_line, 74), width=1)
    for x in range(0, W, 58):
        draw.line((x, y0 + 2, x + 18, H - 2), fill=(112, 114, 100, 34), width=1)
    return out.filter(ImageFilter.GaussianBlur(0.18))


def add_ink_and_wash(im: Image.Image, seed: int, ink: float = 0.16) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = to_array(im)
    noise = rng.normal(0, 3.0, size=arr.shape[:2])
    arr[:, :, 0] += noise * 0.7
    arr[:, :, 1] += noise * 0.5
    arr[:, :, 2] += noise * 0.25
    im2 = from_array(arr)
    gray = ImageOps.grayscale(im2)
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.45))
    edge_arr = np.asarray(edges).astype(np.float32) / 255.0
    darken = 1.0 - edge_arr[:, :, None] * ink
    return from_array(to_array(im2) * darken)


def source_plate(src: Image.Image, crop_y: int, name: str, plinth: int, seed: int, warm: float = 0.0) -> PlateSpec:
    crop = src.crop((X0, crop_y, X1, crop_y + H)).resize((W, H), Image.Resampling.BICUBIC)
    arr = to_array(crop)
    if warm:
        arr[:, :, 0] += warm
        arr[:, :, 1] += warm * 0.45
        arr[:, :, 2] -= warm * 0.20
    plate = from_array(arr)
    plate = add_plinth(plate, plinth)
    plate = watercolorize(plate)
    plate = add_ink_and_wash(plate, seed)
    path = PLATES / f"{name}.png"
    plate.save(path)
    return PlateSpec(name, "source-continuation", path, "artwork-native facade rhythm; quiet but can read repetitive")


def extracted_plate(src: Image.Image, ref_path: Path, name: str, bottom_frac: float, height_frac: float, seed: int) -> PlateSpec:
    ref = rgb(ref_path)
    bbox = nonwhite_bbox(ref)
    building = ref.crop(bbox)
    y1 = building.height
    h = max(80, int(building.height * height_frac))
    y0 = max(0, int(building.height * (1.0 - bottom_frac)) - h // 4)
    crop = building.crop((0, y0, building.width, y1))
    crop = ImageOps.pad(crop, (W, H), method=Image.Resampling.BICUBIC, color=(246, 244, 238), centering=(0.5, 0.84))
    alpha = nonwhite_alpha(crop)
    ref_style = src.crop((X0, 2360, X1, 2580))
    crop = color_match(crop, ref_style, strength=0.68)
    crop = watercolorize(crop, color=0.72, contrast=0.82, brightness=1.08)
    crop = add_ink_and_wash(crop, seed, ink=0.11)
    fallback = src.crop((X0, 2350, X1, 2350 + H)).resize((W, H), Image.Resampling.BICUBIC)
    fallback = add_plinth(watercolorize(fallback), 22)
    fallback.paste(crop, (0, 0), alpha)
    crop = fallback
    path = PLATES / f"{name}.png"
    crop.save(path)
    return PlateSpec(name, "standalone-extract", path, f"lower band harvested from {ref_path.name}; more designed base but registration risk")


def streetlevel_plate(src: Image.Image, name: str) -> PlateSpec:
    ref = rgb(TASK / "refs" / "ritz_streetlevel.png")
    crop = ref.crop((40, 290, 610, 720))
    crop = ImageOps.fit(crop, (W, H), method=Image.Resampling.BICUBIC, centering=(0.53, 0.55))
    ref_style = src.crop((X0, 2360, X1, 2580))
    crop = color_match(crop, ref_style, strength=0.78)
    crop = watercolorize(crop, color=0.48, contrast=0.72, brightness=1.16)
    crop = add_ink_and_wash(crop, 54, ink=0.08)
    path = PLATES / f"{name}.png"
    crop.save(path)
    return PlateSpec(name, "streetlevel-reference", path, "real base reference, but still carries street-photo perspective")


def hybrid_plate(src: Image.Image, top_path: Path, bottom_path: Path, name: str, split: int, seed: int) -> PlateSpec:
    top = rgb(top_path).resize((W, H), Image.Resampling.BICUBIC)
    bottom = rgb(bottom_path).resize((W, H), Image.Resampling.BICUBIC)
    arr_top = to_array(top)
    arr_bottom = to_array(bottom)
    y = np.arange(H, dtype=np.float32)
    blend = np.clip((y - (split - 34)) / 68.0, 0.0, 1.0)[:, None, None]
    arr = arr_top * (1.0 - blend) + arr_bottom * blend
    out = from_array(arr)
    out = add_plinth(out, 24, tone=(218, 211, 190), top_line=(98, 111, 107))
    out = color_match(out, src.crop((X0, 2380, X1, 2600)), strength=0.35)
    out = watercolorize(out, color=0.84, contrast=0.90, brightness=1.02)
    out = add_ink_and_wash(out, seed, ink=0.13)
    path = PLATES / f"{name}.png"
    out.save(path)
    return PlateSpec(name, "hybrid", path, "source facade on top, designed standalone base below")


def foreground_tree_mask(src_region: Image.Image) -> Image.Image:
    arr = np.asarray(src_region.convert("RGB"))
    yy, xx = np.mgrid[:arr.shape[0], :arr.shape[1]]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    left = xx < 245
    yellow_green = (r > b + 24) & (g > b + 18) & (r > 92) & (g > 86) & (b < 145)
    twig = (r < 118) & (g < 112) & (b < 100) & (r > 38) & (g > 34) & (yy > 52)
    mask = left & (yellow_green | twig)
    alpha = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    alpha = alpha.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.3))
    return alpha


def composite_candidate(src: Image.Image, plate_path: Path, name: str, preserve_tree: bool = True) -> Path:
    cand = src.copy()
    plate = rgb(plate_path).resize((W, H), Image.Resampling.BICUBIC)
    cand.paste(plate, (X0, Y0))
    if preserve_tree:
        original_region = src.crop(BOX)
        mask = foreground_tree_mask(original_region)
        patched_region = cand.crop(BOX)
        patched_region.paste(original_region, (0, 0), mask)
        cand.paste(patched_region, (X0, Y0))
    out = COMPOSITES / f"{name}_composited.png"
    cand.save(out)
    return out


def save_zoom(src: Image.Image, cand_path: Path, name: str) -> Path:
    im = rgb(cand_path)
    zoom = im.crop((3050, 2470, 4140, 2915))
    out = ZOOMS / f"{name}_zoom.png"
    zoom.save(out)
    return out


def contact_sheet(specs: list[PlateSpec], out_path: Path) -> None:
    thumb_w, thumb_h = 300, 86
    pad = 18
    label_h = 48
    cols = 2
    rows = (len(specs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (thumb_h + label_h + pad) + pad), (248, 247, 242))
    draw = ImageDraw.Draw(sheet)
    for i, spec in enumerate(specs):
        im = rgb(spec.path)
        im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad + (i % cols) * (thumb_w + pad)
        y = pad + (i // cols) * (thumb_h + label_h + pad)
        sheet.paste(im, (x + (thumb_w - im.width) // 2, y))
        draw.text((x, y + thumb_h + 4), spec.name, fill=(28, 28, 28))
        draw.text((x, y + thumb_h + 20), spec.family, fill=(82, 82, 82))
    sheet.save(out_path)


def picks_sheet(picks: list[tuple[str, Path, Path]], out_path: Path) -> None:
    thumb_w, thumb_h = 520, 214
    pad = 18
    label_h = 34
    sheet = Image.new("RGB", (thumb_w + pad * 2, len(picks) * (thumb_h + label_h + pad) + pad), (248, 247, 242))
    draw = ImageDraw.Draw(sheet)
    for i, (name, _composite, zoom) in enumerate(picks):
        im = rgb(zoom)
        im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad
        y = pad + i * (thumb_h + label_h + pad)
        sheet.paste(im, (x + (thumb_w - im.width) // 2, y))
        draw.text((x, y + thumb_h + 5), name, fill=(28, 28, 28))
    sheet.save(out_path)


def main() -> None:
    src = rgb(SRC_PATH)
    specs: list[PlateSpec] = []

    specs.append(source_plate(src, 2319, "plate_01_source_continue_clean", 18, 10, warm=0))
    specs.append(source_plate(src, 2350, "plate_02_source_continue_lowerrow", 24, 11, warm=3))
    specs.append(source_plate(src, 2394, "plate_03_source_continue_grounded", 32, 12, warm=6))
    specs.append(source_plate(src, 2264, "plate_04_source_continue_tall", 20, 13, warm=1))

    extracted_sources = [
        ("plate_05_openai_p1_lowerbase", TASK / "work" / "building_recreate" / "cand_openai_p1.png", 0.22, 0.22, 21),
        ("plate_06_openai_p2_lowerbase", TASK / "work" / "building_recreate" / "cand_openai_p2.png", 0.22, 0.22, 22),
        ("plate_07_openai_p3_lowerbase", TASK / "work" / "building_recreate" / "cand_openai_p3.png", 0.22, 0.22, 23),
        ("plate_08_frontal_wc_lowerbase", TASK / "work" / "berlin_hotel_frontal_watercolor_elevation.png", 0.25, 0.24, 24),
        ("plate_09_flux2_p1_lowerbase", TASK / "work" / "building_recreate" / "cand_flux2_p1.png", 0.23, 0.24, 25),
        ("plate_10_flux2_p3_lowerbase", TASK / "work" / "building_recreate" / "cand_flux2_p3.png", 0.23, 0.24, 26),
    ]
    for args in extracted_sources:
        specs.append(extracted_plate(src, args[1], args[0], args[2], args[3], args[4]))

    specs.append(streetlevel_plate(src, "plate_11_streetlevel_watercolorized"))

    specs.append(hybrid_plate(src, specs[1].path, specs[4].path, "plate_12_hybrid_source_openai_p1", 150, 31))
    specs.append(hybrid_plate(src, specs[1].path, specs[5].path, "plate_13_hybrid_source_openai_p2", 150, 32))
    specs.append(hybrid_plate(src, specs[2].path, specs[7].path, "plate_14_hybrid_source_frontal_wc", 142, 33))
    specs.append(hybrid_plate(src, specs[2].path, specs[10].path, "plate_15_hybrid_source_streetlevel", 132, 34))

    contact_sheet(specs, ROOT / "plate_sheet.png")

    pick_names = [
        "plate_12_hybrid_source_openai_p1",
        "plate_14_hybrid_source_frontal_wc",
        "plate_03_source_continue_grounded",
    ]
    by_name = {spec.name: spec for spec in specs}
    picks: list[tuple[str, Path, Path]] = []
    for idx, pick in enumerate(pick_names, 1):
        comp_name = f"candidate_{idx}_{pick.removeprefix('plate_')}"
        comp = composite_candidate(src, by_name[pick].path, comp_name, preserve_tree=True)
        zoom = save_zoom(src, comp, comp_name)
        picks.append((comp_name, comp, zoom))
    picks_sheet(picks, ROOT / "candidate_zooms_sheet.png")

    manifest = ROOT / "manifest.tsv"
    with manifest.open("w", encoding="utf-8") as fh:
        fh.write("name\tfamily\tpath\tverdict\n")
        for spec in specs:
            fh.write(f"{spec.name}\t{spec.family}\t{spec.path.relative_to(ROOT)}\t{spec.verdict}\n")
        fh.write("\nselected_composite\tpath\tzoom\n")
        for name, comp, zoom in picks:
            fh.write(f"{name}\t{comp.relative_to(ROOT)}\t{zoom.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
