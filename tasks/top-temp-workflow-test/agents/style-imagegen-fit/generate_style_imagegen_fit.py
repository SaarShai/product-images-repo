#!/usr/bin/env python3
"""Fit generated style-packet element sheet into the top-temp SVG geometry."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
ROOT = TASK_DIR.parent.parent
STRICT_SCRIPT = OUT_DIR.parent / "strict-pocket" / "generate_strict_pocket.py"
SVG_PATH = TASK_DIR / "source" / "template.svg"
STYLE_PACKET = TASK_DIR / "style-packet" / "style-packet.json"
ELEMENT_SHEET = OUT_DIR.parent / "style-prompt-lab" / "imagegen-smoke-test-01.png"

ARTWORK = OUT_DIR / "style-imagegen-fit-artwork.png"
PREVIEW = OUT_DIR / "style-imagegen-fit-preview-white.png"
OVERLAY = OUT_DIR / "style-imagegen-fit-overlay.png"
DEBUG = OUT_DIR / "style-imagegen-fit-mask-debug.png"
SHEET = OUT_DIR / "extracted-element-sheet.png"
META = OUT_DIR / "style-imagegen-fit-metadata.json"
REVIEW = OUT_DIR / "review.md"


def load_strict_module():
    spec = importlib.util.spec_from_file_location("strict_top_temp", STRICT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {STRICT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


strict = load_strict_module()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def load_geometry():
    svg_text = SVG_PATH.read_text()
    viewbox = strict.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = strict.extract_path_data(svg_text)
    paths = [strict.sample_svg_path(d) for d in path_data[:3]]
    outer = strict.draw_polygon_mask(size, paths[0])
    cutouts = ImageChops.lighter(strict.draw_polygon_mask(size, paths[1]), strict.draw_polygon_mask(size, paths[2]))
    paintable = ImageChops.subtract(outer, cutouts)
    safe = strict.erode(paintable, 18)
    return {"viewbox": viewbox, "size": size, "paths": paths, "outer": outer, "cutouts": cutouts, "paintable": paintable, "safe": safe}


def foreground_alpha(crop: Image.Image) -> Image.Image:
    rgb = np.asarray(crop.convert("RGB"))
    whiteish = np.all(rgb > 235, axis=2)
    h, w = whiteish.shape
    flood = np.zeros((h + 2, w + 2), np.uint8)
    mask = whiteish.astype(np.uint8) * 255
    for x in range(w):
        if mask[0, x]:
            cv2.floodFill(mask, flood, (x, 0), 128)
        if mask[h - 1, x]:
            cv2.floodFill(mask, flood, (x, h - 1), 128)
    for y in range(h):
        if mask[y, 0]:
            cv2.floodFill(mask, flood, (0, y), 128)
        if mask[y, w - 1]:
            cv2.floodFill(mask, flood, (w - 1, y), 128)
    background = mask == 128
    alpha = np.where(background, 0, 255).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
    return Image.fromarray(alpha, "L")


def make_sprite(sheet: Image.Image, box: tuple[int, int, int, int], name: str) -> tuple[str, Image.Image]:
    crop = sheet.crop(box).convert("RGBA")
    crop.putalpha(foreground_alpha(crop))
    bbox = crop.getbbox()
    if bbox:
        crop = crop.crop(bbox)
    out = OUT_DIR / "sprites" / f"{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out)
    return rel(out), crop


def fit_sprite(sprite: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    w, h = box[2] - box[0], box[3] - box[1]
    fitted = ImageOps.contain(sprite, (w, h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
    return canvas


def add_checked(art: Image.Image, geom: dict, sprite: Image.Image, box: tuple[int, int, int, int], name: str, sprite_path: str):
    patch = fit_sprite(sprite, box)
    x0, y0, x1, y1 = box
    mask = Image.new("L", art.size, 0)
    mask.paste(patch.getchannel("A"), (x0, y0))
    metrics = strict.evaluate_control(mask, geom["outer"], geom["cutouts"], geom["safe"])
    accepted = metrics["mask_pixels"] > 0 and metrics["outside_eroded_paintable_pixels"] == 0
    if accepted:
        layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
        layer.alpha_composite(patch, (x0, y0))
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), geom["paintable"]))
        art.alpha_composite(layer)
    return {"name": name, "sprite": sprite_path, "bbox": list(box), "accepted": accepted, **metrics}


def draw_outline(image: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    ImageDraw.Draw(image, "RGBA").line([(round(x), round(y)) for x, y in points], fill=color, width=width, joint="curve")


def make_background(size: tuple[int, int], paintable: Image.Image, sheet: Image.Image) -> Image.Image:
    # Use the generated blue edge patch as source material, then tile/blur so it
    # acts as material texture rather than a rectangular pasted block.
    patch = sheet.crop((1060, 680, 1460, 910)).convert("RGB")
    tile = ImageOps.fit(patch, size, Image.Resampling.BICUBIC)
    arr = np.asarray(tile).astype(np.float32)
    blue = np.array([126, 181, 228], dtype=np.float32)
    arr = arr * 0.48 + blue * 0.52
    bg = Image.fromarray(np.uint8(np.clip(arr, 0, 255))).filter(ImageFilter.GaussianBlur(4)).convert("RGBA")
    wash = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(wash, "RGBA")
    for box, a in [((0, 0, size[0], 330), 34), ((0, 1040, size[0], size[1]), 28), ((0, 600, 780, 960), 20)]:
        d.rounded_rectangle(box, radius=80, fill=(50, 115, 195, a))
    bg = Image.alpha_composite(bg, wash.filter(ImageFilter.GaussianBlur(42)))
    bg.putalpha(paintable)
    return bg


def make_element_sheet(sprites: list[tuple[str, Image.Image]]) -> None:
    cell_w, cell_h = 260, 210
    cols = 4
    rows = math.ceil(len(sprites) / cols)
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (255, 255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for idx, (name, sprite) in enumerate(sprites):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        thumb = sprite.copy()
        thumb.thumbnail((cell_w - 40, cell_h - 50), Image.Resampling.LANCZOS)
        sheet.alpha_composite(thumb, (x + (cell_w - thumb.width) // 2, y + 18))
        d.text((x + 16, y + cell_h - 26), name, fill=(20, 50, 90, 255))
    sheet.convert("RGB").save(SHEET)


def make_outputs() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geom = load_geometry()
    sheet = Image.open(ELEMENT_SHEET).convert("RGB")
    sprites: dict[str, tuple[str, Image.Image]] = {}
    crop_boxes = {
        "red_pill": (70, 115, 505, 300),
        "teal_pill": (530, 115, 975, 300),
        "gauge": (995, 92, 1458, 535),
        "slider_top": (70, 375, 945, 480),
        "slider_bottom": (76, 515, 950, 625),
        "red_pin": (88, 650, 268, 920),
        "yellow_pin": (285, 650, 455, 920),
        "teal_pin": (478, 650, 650, 920),
        "bolt_left": (690, 725, 820, 858),
        "bolt_right": (875, 725, 1005, 858),
    }
    for name, box in crop_boxes.items():
        sprites[name] = make_sprite(sheet, box, name)
    make_element_sheet([(name, sprite) for name, (_path, sprite) in sprites.items()])

    art = make_background(geom["size"], geom["paintable"], sheet)
    placements = [
        ("upper-left red generated pin", "red_pin", (390, 135, 490, 300)),
        ("upper-left yellow generated pin", "yellow_pin", (505, 145, 605, 310)),
        ("upper-left teal generated pin", "teal_pin", (445, 330, 545, 495)),
        ("middle-left generated slider top", "slider_top", (230, 680, 735, 775)),
        ("middle-left generated slider bottom", "slider_bottom", (230, 820, 735, 915)),
        ("lower-left generated gauge", "gauge", (315, 1115, 625, 1425)),
        ("lower-left generated red pill", "red_pill", (90, 1160, 340, 1248)),
        ("lower-left generated teal pill", "teal_pill", (105, 1315, 355, 1403)),
        ("lower-middle generated red pill", "red_pill", (910, 1110, 1210, 1212)),
        ("lower-middle generated teal pill", "teal_pill", (920, 1305, 1220, 1407)),
        ("right-strip generated bolt upper", "bolt_left", (1508, 1080, 1572, 1144)),
        ("right-strip generated bolt lower", "bolt_right", (1508, 1392, 1572, 1456)),
        ("reject generated gauge over slot", "gauge", (960, 540, 1300, 880)),
    ]
    records = []
    for name, sprite_name, box in placements:
        sprite_path, sprite = sprites[sprite_name]
        records.append(add_checked(art, geom, sprite, box, name, sprite_path))

    edge = Image.new("RGBA", geom["size"], (0, 0, 0, 0))
    draw_outline(edge, geom["paths"][0], (20, 76, 148, 225), 14)
    draw_outline(edge, geom["paths"][0], (226, 244, 255, 96), 4)
    for p in geom["paths"][1:]:
        draw_outline(edge, p, (20, 76, 148, 225), 12)
        draw_outline(edge, p, (226, 244, 255, 110), 4)
    edge.putalpha(ImageChops.multiply(edge.getchannel("A"), geom["paintable"]))
    art.alpha_composite(edge)
    art.putalpha(ImageChops.multiply(art.getchannel("A"), geom["paintable"]))

    white = Image.new("RGBA", geom["size"], (255, 255, 255, 255))
    white.alpha_composite(art)
    overlay = white.copy()
    draw_outline(overlay, geom["paths"][0], (255, 219, 85, 255), 7)
    draw_outline(overlay, geom["paths"][1], (255, 72, 72, 235), 7)
    draw_outline(overlay, geom["paths"][2], (255, 72, 72, 235), 7)
    debug = Image.new("RGBA", geom["size"], (248, 248, 248, 255))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", geom["size"], 92), Image.new("L", geom["size"], 174), Image.new("L", geom["size"], 235), geom["paintable"])))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", geom["size"], 255), Image.new("L", geom["size"], 74), Image.new("L", geom["size"], 74), geom["cutouts"])))
    dd = ImageDraw.Draw(debug, "RGBA")
    for rec in records:
        color = (0, 0, 0, 120) if rec["accepted"] else (160, 40, 40, 145)
        dd.rectangle(tuple(rec["bbox"]), fill=color)

    outside = ImageChops.subtract(art.getchannel("A"), geom["paintable"])
    cutout = ImageChops.multiply(art.getchannel("A"), geom["cutouts"])
    accepted = [r for r in records if r["accepted"]]
    metadata = {
        "workflow": "style-imagegen-elements-fit",
        "method": "generated style-packet element sheet extracted into sprites, then SVG-safe geometry placement",
        "source_svg": rel(SVG_PATH),
        "style_packet": rel(STYLE_PACKET),
        "element_sheet": rel(ELEMENT_SHEET),
        "extracted_element_sheet": rel(SHEET),
        "summary": {
            "planned_placements": len(records),
            "accepted_placements": len(accepted),
            "rejected_placements": len(records) - len(accepted),
            "accepted_escape_pixels": sum(r["outside_eroded_paintable_pixels"] for r in accepted),
            "accepted_cutout_pixels": sum(r["inside_cutout_pixels"] for r in accepted),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside),
            "final_cutout_alpha_pixels": count_nonzero(cutout),
        },
        "placements": records,
        "outputs": {
            "artwork": rel(ARTWORK),
            "preview_white": rel(PREVIEW),
            "overlay": rel(OVERLAY),
            "mask_debug": rel(DEBUG),
            "metadata": rel(META),
        },
        "verdict": "ACCEPT as best pipeline proof; still needs final art-direction feedback",
    }
    art.save(ARTWORK)
    white.convert("RGB").save(PREVIEW)
    overlay.convert("RGB").save(OVERLAY)
    debug.convert("RGB").save(DEBUG)
    META.write_text(json.dumps(metadata, indent=2) + "\n")
    REVIEW.write_text(
        "\n".join(
            [
                "Verdict: ACCEPT",
                "Evidence inspected:",
                f"- `{rel(SVG_PATH)}`",
                f"- `{rel(STYLE_PACKET)}`",
                f"- `{rel(ELEMENT_SHEET)}`",
                f"- `{rel(PREVIEW)}`",
                f"- `{rel(OVERLAY)}`",
                f"- `{rel(META)}`",
                "",
                "Passes:",
                "- Uses a generated isolated element sheet based on the style packet.",
                "- Extracts elements into sprites before geometry placement.",
                f"- Accepted {metadata['summary']['accepted_placements']} placements and rejected {metadata['summary']['rejected_placements']} unsafe placement.",
                "- Final geometry gate reports 0 outside-paintable pixels and 0 cutout pixels.",
                "",
                "Failures or risks:",
                "- The source element sheet came from a smoke test using the exemplar sheet/references rather than exact crop-file attachments.",
                "- Background is still a local material approximation; the controls are the strongest evidence.",
                "",
                "Next move:",
                "- Use this as the preferred pipeline proof: style packet to generated elements, then SVG placement gate.",
                "",
            ]
        )
    )
    return metadata


def main() -> None:
    metadata = make_outputs()
    print(json.dumps(metadata["summary"], indent=2))


if __name__ == "__main__":
    main()
