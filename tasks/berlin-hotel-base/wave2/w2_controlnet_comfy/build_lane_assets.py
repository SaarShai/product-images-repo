#!/usr/bin/env python3
"""Build lane-local control maps, guides, composites, and zooms.

This lane is intentionally self-contained: all outputs land beside this script.
The source image is read-only input; final composites replace only the shared
wave-2 allowed box.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[4]
LANE = Path(__file__).resolve().parent
SRC = ROOT / "tasks/berlin-hotel-base/work/src.png"

BOX = (3162, 2582, 4082, 2845)
ZOOM_BOX = (3060, 2480, 4120, 2900)
GEN_SIZE = (920, 264)


PROMPT = (
    "fine architectural watercolor and ink elevation of a pale limestone hotel "
    "facade base, strict flat near-frontal elevation, same vertical stone pier "
    "rhythm and same tall narrow windows continuing downward, quiet masonry "
    "ground floor, modest plain stone plinth meeting the quay, soft transparent "
    "watercolor wash, muted warm limestone, dark blue grey window recesses, "
    "delicate hand ink lines, no text"
)

NEGATIVE = (
    "glass hall, atrium, high ceiling lobby, canopy, marquee, porte-cochere, "
    "awning, storefront sign, logo, letters, words, people, cars, photorealistic, "
    "3d render, perspective view, rotated building, arched arcade, palace, "
    "neoclassical portico, heavy shadows, saturated colors"
)


def jitter(v: float, amount: float) -> float:
    return v + random.uniform(-amount, amount)


def rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, outline, width=1):
    draw.rounded_rectangle(xy, radius=radius, outline=outline, width=width)


def build_lineart() -> tuple[Image.Image, Image.Image]:
    """Return white-on-black control and pale color guide at GEN_SIZE."""

    random.seed(20260622)
    w, h = GEN_SIZE
    ctrl = Image.new("L", (w, h), 0)
    dc = ImageDraw.Draw(ctrl)

    guide = Image.new("RGB", (w, h), (230, 222, 203))
    dg = ImageDraw.Draw(guide, "RGBA")

    # Watercolor-paper variation and warm/cool stone modulation.
    noise = np.random.default_rng(2206).normal(0, 4.0, (h, w, 1))
    base = np.array(guide).astype(np.float32)
    wash_x = np.linspace(-8, 6, w, dtype=np.float32)[None, :, None]
    wash_y = np.linspace(4, -7, h, dtype=np.float32)[:, None, None]
    base += noise + wash_x + wash_y
    guide = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    dg = ImageDraw.Draw(guide, "RGBA")

    # Macro facade geometry. Front face ends around x=648; right side recedes.
    front_end = 648
    plinth_top = 236
    floor_lines = [2, 84, 171, plinth_top, 262]
    for y in floor_lines:
        dc.line([(0, y), (w, y)], fill=235, width=2 if y in (2, plinth_top, 262) else 1)
        dg.line([(0, y), (w, y)], fill=(86, 76, 62, 70), width=1)

    # Subtle masonry coursing: visible in color guide, faint in control.
    for y in range(24, plinth_top, 22):
        dc.line([(0, y), (front_end, y)], fill=72, width=1)
        dc.line([(front_end, y - 4), (w, y + 7)], fill=60, width=1)
        dg.line([(0, y), (front_end, y)], fill=(125, 106, 76, 34), width=1)
        dg.line([(front_end, y - 4), (w, y + 7)], fill=(125, 106, 76, 26), width=1)

    # Front-face bays, matching the clean tower rhythm above.
    front_bays = [(8, 86), (96, 181), (194, 280), (292, 378),
                  (390, 476), (488, 574), (586, 646)]
    pier_edges = [0, 92, 188, 286, 384, 482, 580, front_end]
    for x in pier_edges:
        dc.line([(x, 0), (x, plinth_top)], fill=255, width=2)
        dc.line([(x + 7, 0), (x + 7, plinth_top)], fill=112, width=1)
        dg.rectangle([x - 2, 0, x + 9, plinth_top], fill=(242, 234, 216, 55))
        dg.line([(x, 0), (x, plinth_top)], fill=(62, 58, 54, 70), width=1)

    # Center reveal before the receding side.
    for x in (648, 660, 674):
        dc.line([(x, 0), (x, plinth_top)], fill=230, width=2 if x == 648 else 1)
        dg.line([(x, 0), (x, plinth_top)], fill=(72, 62, 49, 70), width=1)

    # Right/receding side: compressed bays and lightly angled floor/coping lines.
    right_cols = [688, 720, 751, 781, 811, 839, 866, 891, 915]
    for x in right_cols:
        dc.line([(x, 0), (x, plinth_top)], fill=210, width=1)
        dg.line([(x, 0), (x, plinth_top)], fill=(68, 58, 49, 62), width=1)
    for y in [84, 171, plinth_top]:
        dc.line([(front_end, y), (w, y + 15)], fill=170, width=1)
        dg.line([(front_end, y), (w, y + 15)], fill=(90, 76, 58, 50), width=1)

    def draw_window_group(x0: int, x1: int, y0: int, y1: int, n: int = 3):
        if x1 - x0 < 14:
            return
        if x1 - x0 < 28:
            n = 1
        margin = max(8, int((x1 - x0) * 0.17))
        gap = 6
        avail = max(8, (x1 - x0) - 2 * margin - gap * (n - 1))
        ww = max(6, int(avail / n))
        start = x0 + margin
        for i in range(n):
            xx0 = start + i * (ww + gap)
            xx1 = max(xx0 + 3, min(x1 - margin, xx0 + ww))
            if xx1 > x1 - 2:
                continue
            rx = [jitter(xx0, 0.7), jitter(y0, 0.6), jitter(xx1, 0.7), jitter(y1, 0.8)]
            rounded_rect(dc, rx, radius=5, outline=255, width=2)
            dc.line([(rx[0] + 2, rx[1] + 2), (rx[0] + 2, rx[3] - 2)], fill=92, width=1)
            dg.rounded_rectangle(rx, radius=5, fill=(62, 82, 89, 170),
                                 outline=(32, 44, 49, 115), width=1)
            # Pale watercolor reflection inside the dark slit.
            dg.line([(rx[0] + 3, rx[1] + 3), (rx[0] + 3, rx[3] - 3)],
                    fill=(230, 234, 225, 55), width=1)

    floors = [(13, 70), (98, 154), (184, 229)]
    for bx0, bx1 in front_bays:
        for fy0, fy1 in floors:
            draw_window_group(bx0, bx1, fy0, fy1, n=3)

    # Right side: pairs/triads become tighter, echoing the angled wall.
    right_bays = list(zip(right_cols[:-1], right_cols[1:]))
    for idx, (bx0, bx1) in enumerate(right_bays):
        n = 2 if (bx1 - bx0) < 30 else 3
        for fy0, fy1 in floors:
            draw_window_group(bx0 + 2, bx1 - 2, fy0 + idx // 3, fy1 + idx // 3, n=n)

    # Quiet ground line/plinth with block joints: no canopy, no marquee silhouette.
    dg.rectangle([0, plinth_top, w, h], fill=(202, 194, 174, 105))
    for x in range(0, w, 44):
        dc.line([(x, plinth_top), (x, h)], fill=90, width=1)
        dg.line([(x, plinth_top), (x, h)], fill=(82, 72, 58, 38), width=1)
    dc.line([(0, plinth_top + 12), (w, plinth_top + 12)], fill=132, width=1)
    dc.line([(0, h - 5), (w, h - 5)], fill=215, width=2)
    dg.line([(0, h - 5), (w, h - 5)], fill=(75, 65, 53, 75), width=1)

    # Very faint tree/left-edge exclusion hint, not a facade feature.
    dg.rectangle([0, 0, 18, h], fill=(215, 218, 194, 35))

    ctrl = ctrl.filter(ImageFilter.GaussianBlur(0.25))
    ctrl_rgb = Image.merge("RGB", (ctrl, ctrl, ctrl))
    return ctrl_rgb, guide


def crop_to_box(img: Image.Image) -> Image.Image:
    x0, y0, x1, y1 = BOX
    return img.crop((x0, y0, x1, y1))


def make_mask() -> Image.Image:
    x0, y0, x1, y1 = BOX
    src = Image.open(SRC).convert("RGB")
    mask = Image.new("L", src.size, 0)
    ImageDraw.Draw(mask).rectangle([x0, y0, x1 - 1, y1 - 1], fill=255)
    return mask


def composite(raw_path: Path, out_stem: str) -> dict:
    src = Image.open(SRC).convert("RGB")
    x0, y0, x1, y1 = BOX
    bw, bh = x1 - x0, y1 - y0
    src_box = src.crop(BOX)

    raw = Image.open(raw_path).convert("RGB")
    patch = raw.resize((bw, bh), Image.Resampling.LANCZOS)

    guide = Image.open(LANE / "structure_color_guide.png").convert("RGB").resize((bw, bh), Image.Resampling.LANCZOS)
    # Harmonize: keep generated line/texture contrast, but pin palette to the
    # hand-built limestone guide and source-paper wash.
    raw_gray = np.asarray(patch.convert("L")).astype(np.float32)
    guide_arr = np.asarray(guide).astype(np.float32)
    src_arr = np.asarray(src_box).astype(np.float32)
    contrast = (raw_gray - raw_gray.mean()) / (raw_gray.std() + 1e-6)
    tone = np.clip(1.0 + 0.11 * contrast[:, :, None], 0.70, 1.22)
    harmonized = guide_arr * tone
    # Preserve local paper/noise and the already-good top/bottom scene contact.
    harmonized = 0.76 * harmonized + 0.24 * src_arr

    # Strengthen dark window slits from generated output, avoiding a glass hall.
    dark = np.clip((124 - raw_gray) / 80.0, 0, 1)[:, :, None]
    window_color = np.array([57, 76, 84], dtype=np.float32)
    harmonized = harmonized * (1 - 0.28 * dark) + window_color * (0.28 * dark)

    # Feather only inside the allowed box, so outside pixels remain byte-stable.
    alpha = np.ones((bh, bw, 1), dtype=np.float32)
    top_f, bot_f = 10, 18
    for i in range(top_f):
        alpha[i, :, 0] = (i + 1) / (top_f + 1)
    for i in range(bot_f):
        alpha[bh - bot_f + i, :, 0] = np.minimum(
            alpha[bh - bot_f + i, :, 0],
            (bot_f - i) / (bot_f + 1),
        )
    harmonized = src_arr * (1 - alpha) + harmonized * alpha
    patch_img = Image.fromarray(np.clip(harmonized, 0, 255).astype(np.uint8))

    out = src.copy()
    out.paste(patch_img, (x0, y0))
    comp = LANE / f"{out_stem}_composited.png"
    zoom = LANE / f"{out_stem}_zoom.png"
    patch_out = LANE / f"{out_stem}_patch.png"
    diff = LANE / f"{out_stem}_diff_inside_box.png"
    out.save(comp)
    out.crop(ZOOM_BOX).save(zoom)
    patch_img.save(patch_out)
    ImageChops.difference(src_box, patch_img).save(diff)
    return {"composite": str(comp), "zoom": str(zoom), "patch": str(patch_out), "diff": str(diff)}


def make_contact() -> None:
    entries = [
        ("source zoom", LANE / "source_zoom.png"),
        ("control", LANE / "control_lineart_strong.png"),
        ("guide", LANE / "structure_color_guide.png"),
        ("raw s220602", LANE / "raw_sd15_lineart_s220602.png"),
        ("candidate s220602", LANE / "candidate_sd15_lineart_s220602_zoom.png"),
        ("raw inverted s220603", LANE / "raw_sd15_lineart_inverted_s220603.png"),
        ("candidate inverted", LANE / "candidate_sd15_lineart_inverted_s220603_zoom.png"),
    ]
    thumbs = []
    tile_w, tile_h = 424, 190
    label_h = 28
    for label, path in entries:
        img = Image.open(path).convert("RGB")
        img.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h + label_h), (245, 242, 234))
        tile.paste(img, ((tile_w - img.width) // 2, label_h + (tile_h - img.height) // 2))
        d = ImageDraw.Draw(tile)
        d.text((8, 7), label, fill=(40, 38, 33))
        thumbs.append(tile)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h)), (232, 228, 218))
    for i, tile in enumerate(thumbs):
        x = (i % cols) * tile_w
        y = (i // cols) * (tile_h + label_h)
        sheet.paste(tile, (x, y))
    sheet.save(LANE / "contact_sheet.png")
    print(LANE / "contact_sheet.png")


def build_inputs() -> None:
    LANE.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    ctrl, guide = build_lineart()
    ctrl.save(LANE / "control_lineart_strong.png")
    # Inverted preview can be useful for lineart preprocessors expecting dark ink.
    ImageChops.invert(ctrl).save(LANE / "control_lineart_inverted_preview.png")
    guide.save(LANE / "structure_color_guide.png")
    src.crop(BOX).save(LANE / "source_allowed_box.png")
    src.crop(ZOOM_BOX).save(LANE / "source_zoom.png")
    make_mask().save(LANE / "mask_allowed_box_fullres.png")
    (LANE / "prompt.txt").write_text(PROMPT + "\n")
    (LANE / "negative.txt").write_text(NEGATIVE + "\n")
    metadata = {
        "source": str(SRC),
        "box": BOX,
        "zoom_box": ZOOM_BOX,
        "gen_size": GEN_SIZE,
        "prompt": PROMPT,
        "negative": NEGATIVE,
    }
    (LANE / "asset_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inputs")
    sub.add_parser("contact")
    cp = sub.add_parser("composite")
    cp.add_argument("--raw", required=True, type=Path)
    cp.add_argument("--stem", required=True)
    args = ap.parse_args()

    if args.cmd == "inputs":
        build_inputs()
    elif args.cmd == "contact":
        make_contact()
    elif args.cmd == "composite":
        print(json.dumps(composite(args.raw, args.stem), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
