#!/usr/bin/env python3
"""Local fallback probes for top-temp checkpoint 2.

These are intentionally procedural simulations. The point is to test workflow
shape when remote agents are slow: keep the strict SVG mask gate, then compare
style/complexity approaches without touching other agents' folders.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
STRICT_SCRIPT = OUT_DIR.parent / "strict-pocket" / "generate_strict_pocket.py"
SVG_PATH = TASK_DIR / "source" / "template.svg"
MANIFEST_PATH = TASK_DIR / "template-manifest.json"

REFS = [
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
    TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
]


def load_strict_module():
    spec = importlib.util.spec_from_file_location("strict_top_temp", STRICT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {STRICT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


strict = load_strict_module()


def count_nonzero(mask: Image.Image) -> int:
    return int(np.count_nonzero(np.asarray(mask)))


def load_geometry():
    svg_text = SVG_PATH.read_text()
    manifest = json.loads(MANIFEST_PATH.read_text())
    viewbox = strict.parse_viewbox(svg_text)
    _, _, vb_width, vb_height = viewbox
    size = (math.ceil(vb_width), math.ceil(vb_height))
    path_data = strict.extract_path_data(svg_text)
    sampled_paths = [strict.sample_svg_path(d) for d in path_data[:3]]
    outer_mask = strict.draw_polygon_mask(size, sampled_paths[0])
    cutout_masks = [strict.draw_polygon_mask(size, points) for points in sampled_paths[1:3]]
    cutouts_mask = ImageChops.lighter(cutout_masks[0], cutout_masks[1])
    paintable_mask = ImageChops.subtract(outer_mask, cutouts_mask)
    paintable_safe = strict.erode(paintable_mask, 18)
    return {
        "manifest": manifest,
        "viewbox": viewbox,
        "size": size,
        "paths": sampled_paths,
        "outer_mask": outer_mask,
        "cutouts_mask": cutouts_mask,
        "paintable_mask": paintable_mask,
        "paintable_safe": paintable_safe,
    }


def soft_noise(size: tuple[int, int], seed: int, scale: int, blur: int) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(seed)
    small = rng.normal(0, 1, (math.ceil(height / scale), math.ceil(width / scale)))
    small = (small - small.min()) / (small.max() - small.min())
    return Image.fromarray(np.uint8(small * 255)).resize(size, Image.Resampling.BICUBIC).filter(
        ImageFilter.GaussianBlur(blur)
    )


def watercolor_body(size: tuple[int, int], paintable: Image.Image, seed: int) -> Image.Image:
    width, height = size
    rng = np.random.default_rng(seed)
    n1 = np.asarray(soft_noise(size, seed, 28, 6)).astype(np.float32) / 255.0
    n2 = np.asarray(soft_noise(size, seed + 11, 90, 18)).astype(np.float32) / 255.0
    mix = np.clip(0.68 * n1 + 0.32 * n2, 0, 1)
    light = np.array([174, 219, 249], dtype=np.float32)
    mid = np.array([96, 166, 224], dtype=np.float32)
    deep = np.array([36, 102, 179], dtype=np.float32)
    rgb = light * (1 - mix[..., None]) + mid * mix[..., None]
    rgb = rgb * 0.92 + deep * (np.maximum(mix - 0.68, 0)[..., None] * 0.35)
    rgb += rng.normal(0, 4.5, rgb.shape)
    image = Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).convert("RGBA")

    washes = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(washes, "RGBA")
    for _ in range(58):
        cx = int(rng.integers(40, width - 40))
        cy = int(rng.integers(40, height - 40))
        rx = int(rng.integers(80, 300))
        ry = int(rng.integers(45, 180))
        color = rng.choice(
            [
                (25, 83, 165, int(rng.integers(14, 32))),
                (214, 238, 255, int(rng.integers(18, 42))),
                (70, 145, 214, int(rng.integers(12, 28))),
            ]
        )
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=tuple(int(v) for v in color))
    washes = washes.filter(ImageFilter.GaussianBlur(22))
    image = Image.alpha_composite(image, washes)

    paper = Image.new("RGBA", size, (255, 255, 255, 0))
    pd = ImageDraw.Draw(paper, "RGBA")
    for _ in range(1800):
        x = int(rng.integers(0, width))
        y = int(rng.integers(0, height))
        a = int(rng.integers(3, 12))
        pd.point((x, y), fill=(255, 255, 255, a))
    image = Image.alpha_composite(image, paper)
    image.putalpha(paintable)
    return image


def draw_path_outline(layer: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    d = ImageDraw.Draw(layer, "RGBA")
    coords = [(round(x), round(y)) for x, y in points]
    d.line(coords, fill=color, width=width, joint="curve")


def add_template_edges(art: Image.Image, geom: dict) -> None:
    paintable = geom["paintable_mask"]
    layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
    draw_path_outline(layer, geom["paths"][0], (10, 61, 137, 215), 24)
    draw_path_outline(layer, geom["paths"][0], (25, 91, 173, 210), 14)
    draw_path_outline(layer, geom["paths"][0], (231, 246, 255, 90), 5)
    for path in geom["paths"][1:3]:
        draw_path_outline(layer, path, (14, 68, 145, 225), 19)
        draw_path_outline(layer, path, (232, 246, 255, 110), 5)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), paintable))
    art.alpha_composite(layer)


def rounded_wash(d: ImageDraw.ImageDraw, box, radius: int, fill, outline=(18, 69, 143, 235), width: int = 5):
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0, y0 + 10, x1, y1 + 18), radius, fill=(9, 47, 108, 70))
    d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), radius + 2, fill=(13, 63, 139, 225))
    d.rounded_rectangle((x0 + 5, y0 + 4, x1 - 5, y1 - 5), max(2, radius - 4), fill=fill)
    d.rounded_rectangle((x0 + 17, y0 + 10, x1 - 22, y0 + 26), 12, fill=(255, 255, 255, 80))
    d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), radius + 2, outline=outline, width=width)


def draw_lamps(layer: Image.Image, mask_mode: bool, positions=None) -> None:
    d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
    positions = positions or [
        (504, 160, (255, 103, 94, 250)),
        (582, 232, (252, 194, 61, 250)),
        (462, 270, (91, 203, 181, 250)),
    ]
    for x, y, color in positions:
        if mask_mode:
            d.ellipse((x - 36, y - 34, x + 36, y + 40), fill=255)
            continue
        d.ellipse((x - 35, y - 25, x + 35, y + 42), fill=(12, 50, 111, 80))
        d.ellipse((x - 31, y - 31, x + 31, y + 31), fill=(13, 65, 143, 230))
        d.ellipse((x - 23, y - 26, x + 23, y + 20), fill=color)
        d.ellipse((x - 15, y - 22, x + 3, y - 8), fill=(255, 255, 255, 132))
        d.arc((x - 21, y - 23, x + 22, y + 21), 220, 60, fill=(255, 255, 255, 45), width=5)


def draw_sliders(layer: Image.Image, mask_mode: bool, y_values=None, knob_xs=None, x0=250, x1=725) -> None:
    d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
    y_values = y_values or [716, 790, 866, 938]
    knob_xs = knob_xs or [310, 462, 595, 690]
    knob_colors = [(255, 103, 94, 250), (252, 194, 61, 250), (91, 203, 181, 250)]
    for idx, y in enumerate(y_values):
        k = knob_xs[idx]
        if mask_mode:
            d.line((x0, y, x1, y), fill=255, width=24)
            d.rounded_rectangle((k - 25, y - 24, k + 25, y + 24), 9, fill=255)
            continue
        d.line((x0, y + 7, x1, y + 7), fill=(9, 48, 111, 80), width=18)
        d.line((x0, y, x1, y), fill=(23, 85, 162, 225), width=15)
        d.line((x0 + 16, y - 5, x1 - 18, y - 5), fill=(228, 246, 255, 130), width=5)
        rounded_wash(d, (k - 21, y - 21, k + 21, y + 19), 8, knob_colors[idx % len(knob_colors)], width=3)


def draw_gauge(layer: Image.Image, mask_mode: bool, cx=470, cy=1278, r=118) -> None:
    d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
    if mask_mode:
        d.ellipse((cx - r - 12, cy - r - 8, cx + r + 12, cy + r + 24), fill=255)
        return
    d.ellipse((cx - r - 10, cy - r + 10, cx + r + 10, cy + r + 27), fill=(9, 45, 105, 80))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(16, 73, 154, 238))
    d.ellipse((cx - r + 20, cy - r + 20, cx + r - 20, cy + r - 20), fill=(219, 241, 255, 238))
    d.pieslice((cx - r + 27, cy - r + 27, cx + r - 27, cy + r - 27), 205, 340, fill=(191, 226, 250, 125))
    d.arc((cx - r + 35, cy - r + 35, cx + r - 35, cy + r - 35), 205, 338, fill=(41, 102, 178, 245), width=10)
    for angle in range(-120, 121, 30):
        rad = math.radians(angle)
        x0 = cx + math.cos(rad) * (r - 42)
        y0 = cy + math.sin(rad) * (r - 42)
        x1 = cx + math.cos(rad) * (r - 22)
        y1 = cy + math.sin(rad) * (r - 22)
        d.line((x0, y0, x1, y1), fill=(15, 71, 142, 220), width=5)
    needle = math.radians(38)
    d.line((cx, cy, cx + math.cos(needle) * 66, cy + math.sin(needle) * 66), fill=(18, 60, 127, 250), width=8)
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(252, 194, 61, 250))
    d.ellipse((cx - 82, cy - 88, cx - 18, cy - 58), fill=(255, 255, 255, 105))


def draw_pills(layer: Image.Image, mask_mode: bool, boxes=None) -> None:
    d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
    boxes = boxes or [
        ((108, 1180, 290, 1224), (255, 103, 94, 250)),
        ((116, 1260, 336, 1306), (252, 194, 61, 250)),
        ((122, 1342, 310, 1388), (91, 203, 181, 250)),
    ]
    for box, color in boxes:
        if mask_mode:
            d.rounded_rectangle(box, 19, fill=255)
            continue
        rounded_wash(d, box, 19, color, width=4)


def draw_bolts(layer: Image.Image, mask_mode: bool, positions=None) -> None:
    d = ImageDraw.Draw(layer, "RGBA" if layer.mode == "RGBA" else None)
    positions = positions or [(1544, 1105), (1546, 1402)]
    for cx, cy in positions:
        if mask_mode:
            d.ellipse((cx - 27, cy - 27, cx + 27, cy + 27), fill=255)
            continue
        d.ellipse((cx - 24, cy - 20, cx + 24, cy + 29), fill=(9, 45, 101, 90))
        d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(25, 82, 160, 238))
        d.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=(223, 242, 255, 245))
        d.line((cx - 11, cy + 8, cx + 11, cy - 8), fill=(68, 125, 194, 245), width=5)


ControlFn = Callable[[Image.Image, bool], None]


def add_checked_control(art: Image.Image, geom: dict, name: str, pocket: str, role: str, draw_fn: ControlFn):
    mask = Image.new("L", art.size, 0)
    draw_fn(mask, True)
    metrics = strict.evaluate_control(mask, geom["outer_mask"], geom["cutouts_mask"], geom["paintable_safe"])
    accepted = metrics["mask_pixels"] > 0 and metrics["outside_eroded_paintable_pixels"] == 0
    if accepted:
        layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
        draw_fn(layer, False)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), geom["paintable_mask"]))
        layer = layer.filter(ImageFilter.GaussianBlur(0.08))
        art.alpha_composite(layer)
    return {"name": name, "pocket": pocket, "role": role, "accepted": accepted, **metrics}


def make_debug(size: tuple[int, int], geom: dict, controls: list[dict], masks: list[Image.Image], title: str) -> Image.Image:
    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 92),
                Image.new("L", size, 174),
                Image.new("L", size, 235),
                geom["paintable_mask"],
            ),
        )
    )
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (
                Image.new("L", size, 255),
                Image.new("L", size, 75),
                Image.new("L", size, 75),
                geom["cutouts_mask"],
            ),
        )
    )
    safe_alpha = geom["paintable_safe"].point(lambda p: 72 if p else 0)
    debug.alpha_composite(
        Image.merge(
            "RGBA",
            (Image.new("L", size, 51), Image.new("L", size, 210), Image.new("L", size, 119), safe_alpha),
        )
    )
    for control, mask in zip(controls, masks):
        alpha = mask.point(lambda p: 150 if p else 0)
        if control["accepted"]:
            color = (0, 0, 0)
        else:
            color = (150, 45, 45)
        debug.alpha_composite(
            Image.merge(
                "RGBA",
                (Image.new("L", size, color[0]), Image.new("L", size, color[1]), Image.new("L", size, color[2]), alpha),
            )
        )
    ImageDraw.Draw(debug, "RGBA").text((24, 22), title, fill=(0, 0, 0, 220))
    return debug


def make_overlay(art: Image.Image, geom: dict) -> Image.Image:
    overlay = Image.new("RGBA", art.size, (255, 255, 255, 255))
    overlay.alpha_composite(art)
    draw_path_outline(overlay, geom["paths"][0], (255, 219, 85, 255), 7)
    draw_path_outline(overlay, geom["paths"][1], (255, 78, 78, 235), 7)
    draw_path_outline(overlay, geom["paths"][2], (255, 78, 78, 235), 7)
    return overlay


def render_candidate(slug: str, title: str, seed: int, control_specs: list[tuple[str, str, str, ControlFn]], note: str):
    geom = load_geometry()
    size = geom["size"]
    art = watercolor_body(size, geom["paintable_mask"], seed)
    add_template_edges(art, geom)

    controls = []
    masks = []
    for name, pocket, role, draw_fn in control_specs:
        mask = Image.new("L", size, 0)
        draw_fn(mask, True)
        masks.append(mask)
        controls.append(add_checked_control(art, geom, name, pocket, role, draw_fn))

    final_alpha = ImageChops.multiply(art.getchannel("A"), geom["paintable_mask"])
    art.putalpha(final_alpha)
    overlay = make_overlay(art, geom)
    debug = make_debug(size, geom, controls, masks, title)
    outside = ImageChops.subtract(art.getchannel("A"), geom["paintable_mask"])
    in_cutouts = ImageChops.multiply(art.getchannel("A"), geom["cutouts_mask"])

    accepted = [c for c in controls if c["accepted"]]
    metadata = {
        "workflow": f"main-fallback-{slug}",
        "title": title,
        "source_svg": "tasks/top-temp-workflow-test/source/template.svg",
        "template_manifest": "tasks/top-temp-workflow-test/template-manifest.json",
        "style_refs": [str(p.relative_to(TASK_DIR.parent.parent)) for p in REFS],
        "method_note": note,
        "summary": {
            "planned_controls": len(controls),
            "accepted_controls": len(accepted),
            "rejected_controls": len(controls) - len(accepted),
            "accepted_control_escape_pixels": sum(c["outside_eroded_paintable_pixels"] for c in accepted),
            "accepted_control_cutout_pixels": sum(c["inside_cutout_pixels"] for c in accepted),
            "final_outside_paintable_alpha_pixels": count_nonzero(outside),
            "final_cutout_alpha_pixels": count_nonzero(in_cutouts),
        },
        "decorative_controls": controls,
    }

    art_path = OUT_DIR / f"{slug}-artwork.png"
    overlay_path = OUT_DIR / f"{slug}-overlay.png"
    debug_path = OUT_DIR / f"{slug}-mask-debug.png"
    meta_path = OUT_DIR / f"{slug}-metadata.json"
    art.save(art_path)
    overlay.save(overlay_path)
    debug.save(debug_path)
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def component_sheet() -> None:
    sheet = Image.new("RGBA", (1050, 560), (255, 255, 255, 255))
    d = ImageDraw.Draw(sheet, "RGBA")
    d.text((34, 28), "Component-library style probe", fill=(20, 58, 115, 255))
    samples = [
        ("gauge", lambda layer, mode: draw_gauge(layer, mode, 170, 280, 92)),
        (
            "capsules",
            lambda layer, mode: draw_pills(
                layer,
                mode,
                [
                    ((350, 170, 600, 230), (255, 103, 94, 250)),
                    ((350, 260, 620, 325), (91, 203, 181, 250)),
                    ((350, 355, 590, 418), (252, 194, 61, 250)),
                ],
            ),
        ),
        (
            "sliders",
            lambda layer, mode: draw_sliders(layer, mode, [190, 260, 330], [785, 850, 915], 720, 970),
        ),
        (
            "lamps",
            lambda layer, mode: draw_lamps(
                layer,
                mode,
                [(765, 430, (255, 103, 94, 250)), (850, 430, (252, 194, 61, 250)), (935, 430, (91, 203, 181, 250))],
            ),
        ),
    ]
    for label, fn in samples:
        layer = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
        fn(layer, False)
        sheet.alpha_composite(layer)
        d.text((40, 510), "reusable rounded watercolor controls; place only after SVG-safe bbox/mask check", fill=(20, 58, 115, 220))
    sheet.save(OUT_DIR / "component-library-sheet.png")


def write_review(metas: list[dict]) -> None:
    lines = [
        "# Main Fallback Checkpoint 2 Review",
        "",
        "Verdict: LOCAL PATCH",
        "",
        "Evidence inspected:",
        "- `tasks/top-temp-workflow-test/source/template.svg`",
        "- `tasks/top-temp-workflow-test/template-manifest.json`",
        "- `tasks/top-temp-workflow-test/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`",
        "- `tasks/top-temp-workflow-test/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`",
        "- `tasks/top-temp-workflow-test/agents/main-fallback/*-artwork.png`",
        "- `tasks/top-temp-workflow-test/agents/main-fallback/*-overlay.png`",
        "- `tasks/top-temp-workflow-test/agents/main-fallback/*-mask-debug.png`",
        "",
        "Passes:",
    ]
    for meta in metas:
        s = meta["summary"]
        lines.append(
            f"- `{meta['workflow']}`: accepted {s['accepted_controls']}/{s['planned_controls']} controls; "
            f"outside={s['final_outside_paintable_alpha_pixels']}; cutout={s['final_cutout_alpha_pixels']}."
        )
    lines += [
        "",
        "Failures or risks:",
        "- These are procedural fallback probes, so style is still an approximation of the references rather than a true generative watercolor pass.",
        "- The strict-style and component-library approaches improve object vocabulary while keeping the old geometry gate, but they still need human visual selection.",
        "- The micro-pocket probe proves style more cleanly only because it deliberately avoids making a complete panel.",
        "",
        "Next move:",
        "- Use checkpoint 2 to choose whether to continue with strict-style polish/component-library, or simplify the production task into pocket-level style proofs before another full-template generation.",
        "",
    ]
    (OUT_DIR / "review.md").write_text("\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metas = []
    metas.append(
        render_candidate(
            "main-strict-style",
            "strict geometry, richer watercolor hardware",
            4101,
            [
                ("upper-left lamp cluster", "upper-left tall bay", "reference-style colored lamps", draw_lamps),
                ("middle-left slider bank", "middle-left field", "watercolor slider rails", draw_sliders),
                ("lower-left gauge", "lower-left base bay", "large blue-white gauge", draw_gauge),
                ("lower-left pill bars", "lower-left base bay", "colored capsule buttons", draw_pills),
                ("right-strip bolts", "right vertical strip", "small screw heads", draw_bolts),
            ],
            "Rescue the accepted strict-pocket geometry with richer watercolor rendering.",
        )
    )
    metas.append(
        render_candidate(
            "main-micro-pocket-style",
            "single-pocket style proof",
            4117,
            [
                (
                    "upper-left large gauge",
                    "upper-left tall bay",
                    "single-pocket watercolor gauge",
                    lambda layer, mode: draw_gauge(layer, mode, 505, 210, 82),
                ),
                (
                    "upper-left lamps",
                    "upper-left tall bay",
                    "small colored bulbs only in one pocket",
                    lambda layer, mode: draw_lamps(
                        layer,
                        mode,
                        [
                            (450, 340, (255, 103, 94, 250)),
                            (525, 360, (252, 194, 61, 250)),
                            (595, 345, (91, 203, 181, 250)),
                        ],
                    ),
                ),
            ],
            "Reduce the task to one safe pocket to separate style learning from full-template geometry.",
        )
    )
    component_sheet()
    metas.append(
        render_candidate(
            "main-component-library",
            "component library placed into pockets",
            4129,
            [
                ("component lamps", "upper-left tall bay", "library bulb sprite", draw_lamps),
                ("component sliders", "middle-left field", "library slider sprite", draw_sliders),
                ("component gauge", "lower-left base bay", "library gauge sprite", draw_gauge),
                ("component bolts", "right vertical strip", "library screw sprite", draw_bolts),
            ],
            "Create reference-style parts first, then place only checked components into safe pockets.",
        )
    )
    metas.append(
        render_candidate(
            "main-simple-full-panel",
            "sparse full-panel composition",
            4159,
            [
                ("large lower-left gauge", "lower-left base bay", "dominant gauge motif", draw_gauge),
                (
                    "short slider bank",
                    "middle-left field",
                    "three sparse sliders",
                    lambda layer, mode: draw_sliders(layer, mode, [735, 835, 935], [350, 515, 650], 250, 700),
                ),
                (
                    "two capsule buttons",
                    "lower-left base bay",
                    "minimal colored controls",
                    lambda layer, mode: draw_pills(
                        layer,
                        mode,
                        [
                            ((105, 1190, 310, 1238), (255, 103, 94, 250)),
                            ((125, 1300, 340, 1350), (91, 203, 181, 250)),
                        ],
                    ),
                ),
            ],
            "Keep the full template but lower motif density so geometry is less overloaded.",
        )
    )
    write_review(metas)
    print(json.dumps({m["workflow"]: m["summary"] for m in metas}, indent=2))


if __name__ == "__main__":
    main()
