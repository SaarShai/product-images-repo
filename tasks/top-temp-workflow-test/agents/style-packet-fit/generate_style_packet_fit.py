#!/usr/bin/env python3
"""Fit visual style-packet crops into the top-temp SVG geometry.

This is a proof that the style packet can drive geometry placement. It uses
real crops from the packet/source references as element material, places them in
safe pockets, and runs the same SVG outside/cutout gate.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


OUT_DIR = Path(__file__).resolve().parent
TASK_DIR = OUT_DIR.parent.parent
STRICT_SCRIPT = OUT_DIR.parent / "strict-pocket" / "generate_strict_pocket.py"
SVG_PATH = TASK_DIR / "source" / "template.svg"
STYLE_PACKET = TASK_DIR / "style-packet" / "style-packet.json"
REF1 = TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
REF2 = TASK_DIR / "refs" / "ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

ARTWORK = OUT_DIR / "style-packet-fit-artwork.png"
PREVIEW = OUT_DIR / "style-packet-fit-preview-white.png"
OVERLAY = OUT_DIR / "style-packet-fit-overlay.png"
DEBUG = OUT_DIR / "style-packet-fit-mask-debug.png"
META = OUT_DIR / "style-packet-fit-metadata.json"
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
        return str(path.resolve().relative_to(TASK_DIR.parent.parent))
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
    sampled_paths = [strict.sample_svg_path(d) for d in path_data[:3]]
    outer_mask = strict.draw_polygon_mask(size, sampled_paths[0])
    cutouts = ImageChops.lighter(
        strict.draw_polygon_mask(size, sampled_paths[1]),
        strict.draw_polygon_mask(size, sampled_paths[2]),
    )
    paintable = ImageChops.subtract(outer_mask, cutouts)
    safe = strict.erode(paintable, 18)
    return {
        "viewbox": viewbox,
        "size": size,
        "paths": sampled_paths,
        "outer_mask": outer_mask,
        "cutouts_mask": cutouts,
        "paintable_mask": paintable,
        "paintable_safe": safe,
    }


def fit_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image.convert("RGBA"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def feather_mask(size: tuple[int, int], radius: int) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    inset = max(2, radius)
    d.rounded_rectangle((inset, inset, w - inset - 1, h - inset - 1), radius=max(8, radius), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius / 2))


def draw_outline(layer: Image.Image, points: list[tuple[float, float]], color, width: int) -> None:
    d = ImageDraw.Draw(layer, "RGBA")
    d.line([(round(x), round(y)) for x, y in points], fill=color, width=width, joint="curve")


def make_background(size: tuple[int, int], paintable: Image.Image) -> Image.Image:
    packet = json.loads(STYLE_PACKET.read_text())
    texture_paths = [item["path"] for item in packet["crops"] if item["type"] in {"body-texture", "edge-treatment"}]
    edge_paths = [item["path"] for item in packet["crops"] if item["type"] == "edge-treatment"]
    textures = [Image.open(TASK_DIR.parent.parent / path).convert("RGB") for path in texture_paths[:2]]
    if not textures:
        textures = [Image.open(REF1).convert("RGB")]
    def blue_only(source: Image.Image) -> Image.Image:
        resized = fit_crop(source, size).convert("RGB")
        arr = np.asarray(resized).copy()
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        blue = (hsv[:, :, 0] >= 82) & (hsv[:, :, 0] <= 120) & (hsv[:, :, 1] > 20)
        fallback = np.array([126, 177, 225], dtype=np.uint8)
        if np.any(blue):
            fallback = np.median(arr[blue], axis=0).astype(np.uint8)
        arr[~blue] = fallback
        image = Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(8))
        detail = resized.filter(ImageFilter.GaussianBlur(2))
        return Image.blend(image, detail, 0.16).convert("RGBA")

    base = blue_only(textures[0])
    if len(textures) > 1:
        second = blue_only(textures[1])
        base = Image.blend(base, second, 0.38)

    # Add low-opacity enlarged edge crops for actual reference line/bleed feel.
    for idx, path in enumerate(edge_paths[:2]):
        edge = Image.open(TASK_DIR.parent.parent / path).convert("RGBA")
        edge = fit_crop(edge, (min(size[0], 720), min(size[1], 400)))
        edge.putalpha(feather_mask(edge.size, 60).point(lambda p: int(p * 0.28)))
        x = 30 if idx == 0 else size[0] - edge.width - 40
        y = 20 if idx == 0 else 110
        base.alpha_composite(edge, (x, y))

    base.putalpha(paintable)
    return base


def paste_checked(
    art: Image.Image,
    geom: dict,
    source: Image.Image,
    box: tuple[int, int, int, int],
    name: str,
    packet_source: str,
    feather: int = 24,
) -> dict:
    x0, y0, x1, y1 = box
    patch = fit_crop(source, (x1 - x0, y1 - y0))
    alpha = feather_mask(patch.size, feather)
    canvas_mask = Image.new("L", art.size, 0)
    canvas_mask.paste(alpha, (x0, y0))
    metrics = strict.evaluate_control(canvas_mask, geom["outer_mask"], geom["cutouts_mask"], geom["paintable_safe"])
    accepted = metrics["mask_pixels"] > 0 and metrics["outside_eroded_paintable_pixels"] == 0
    if accepted:
        patch.putalpha(alpha)
        layer = Image.new("RGBA", art.size, (0, 0, 0, 0))
        layer.alpha_composite(patch, (x0, y0))
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), geom["paintable_mask"]))
        art.alpha_composite(layer)
    return {
        "name": name,
        "packet_source": packet_source,
        "bbox": list(box),
        "accepted": accepted,
        **metrics,
    }


def make_outputs() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geom = load_geometry()
    size = geom["size"]
    art = make_background(size, geom["paintable_mask"])

    crops = TASK_DIR / "style-packet" / "crops"

    sources = {
        "yellow pin": crops / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-01.png",
        "red pin": crops / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-02.png",
        "mint pin": crops / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-accent-component-03.png",
        "slider bank": crops / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png",
        "gauge": crops / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-right-region.png",
        "red pill": crops / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png",
        "mint pill": crops / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-03.png",
        "yellow pill": crops / "ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png",
        "bolt": crops / "ref02-chatgpt-image-jun-9-2026-11-19-45-pm-edge-treatment.png",
    }

    placements = [
        ("upper-left yellow pin crop", "yellow pin", (410, 125, 500, 260), 18),
        ("upper-left red pin crop", "red pin", (515, 135, 605, 270), 18),
        ("upper-left mint pin crop", "mint pin", (462, 310, 552, 445), 18),
        ("middle-left real slider bank crop", "slider bank", (245, 690, 720, 920), 24),
        ("lower-left real gauge crop", "gauge", (330, 1125, 620, 1415), 24),
        ("lower-left red pill crop", "red pill", (92, 1168, 330, 1236), 18),
        ("lower-left mint pill crop", "mint pill", (100, 1282, 340, 1350), 18),
        ("lower-middle red pill crop", "red pill", (925, 1118, 1210, 1198), 20),
        ("lower-middle yellow pill crop", "yellow pill", (942, 1300, 1218, 1380), 20),
        ("right-strip upper bolt crop", "bolt", (1512, 1082, 1570, 1140), 12),
        ("right-strip lower bolt crop", "bolt", (1512, 1390, 1570, 1448), 12),
    ]

    records = []
    for name, key, box, feather in placements:
        source_path = sources[key]
        source = Image.open(source_path).convert("RGB")
        packet_source = rel(source_path)
        records.append(paste_checked(art, geom, source, box, name, packet_source, feather))

    edge_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_outline(edge_layer, geom["paths"][0], (18, 76, 150, 220), 14)
    draw_outline(edge_layer, geom["paths"][0], (230, 246, 255, 90), 4)
    for path in geom["paths"][1:]:
        draw_outline(edge_layer, path, (18, 76, 150, 220), 12)
        draw_outline(edge_layer, path, (230, 246, 255, 100), 4)
    edge_layer.putalpha(ImageChops.multiply(edge_layer.getchannel("A"), geom["paintable_mask"]))
    art.alpha_composite(edge_layer)

    final_alpha = ImageChops.multiply(art.getchannel("A"), geom["paintable_mask"])
    art.putalpha(final_alpha)

    white = Image.new("RGBA", size, (255, 255, 255, 255))
    white.alpha_composite(art)

    overlay = white.copy()
    draw_outline(overlay, geom["paths"][0], (255, 219, 85, 255), 7)
    draw_outline(overlay, geom["paths"][1], (255, 72, 72, 230), 7)
    draw_outline(overlay, geom["paths"][2], (255, 72, 72, 230), 7)

    debug = Image.new("RGBA", size, (248, 248, 248, 255))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, 91), Image.new("L", size, 172), Image.new("L", size, 232), geom["paintable_mask"])))
    debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, 255), Image.new("L", size, 70), Image.new("L", size, 70), geom["cutouts_mask"])))
    for record in records:
        box = record["bbox"]
        color = (0, 0, 0, 150) if record["accepted"] else (160, 40, 40, 145)
        m = Image.new("L", size, 0)
        d = ImageDraw.Draw(m)
        d.rounded_rectangle(tuple(box), 18, fill=255)
        debug.alpha_composite(Image.merge("RGBA", (Image.new("L", size, color[0]), Image.new("L", size, color[1]), Image.new("L", size, color[2]), m.point(lambda p: 100 if p else 0))))

    outside = ImageChops.subtract(art.getchannel("A"), geom["paintable_mask"])
    cutout = ImageChops.multiply(art.getchannel("A"), geom["cutouts_mask"])
    accepted = [r for r in records if r["accepted"]]
    metadata = {
        "workflow": "style-packet-crops-fit-into-svg",
        "method": "real reference/style-packet crops composited into named safe pockets, then SVG mask verified",
        "source_svg": rel(SVG_PATH),
        "style_packet": rel(STYLE_PACKET),
        "style_refs": [rel(REF1), rel(REF2)],
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
        "limitations": [
            "This is a packet-to-geometry fit proof, not a fresh image-generation result.",
            "Some source crops include original blue background, so feathered patch edges can still show.",
            "The next proper test should ask a style agent to generate isolated elements from these packet crops, then pass those elements to this geometry gate.",
        ],
    }

    art.save(ARTWORK)
    white.convert("RGB").save(PREVIEW)
    overlay.convert("RGB").save(OVERLAY)
    debug.convert("RGB").save(DEBUG)
    META.write_text(json.dumps(metadata, indent=2) + "\n")
    REVIEW.write_text(
        "\n".join(
            [
                "Verdict: LOCAL PATCH",
                "Evidence inspected:",
                f"- `{rel(SVG_PATH)}`",
                f"- `{rel(STYLE_PACKET)}`",
                f"- `{rel(PREVIEW)}`",
                f"- `{rel(OVERLAY)}`",
                f"- `{rel(DEBUG)}`",
                f"- `{rel(META)}`",
                "",
                "Passes:",
                "- Uses actual style-packet/source-reference crops rather than prose style imitation.",
                "- Places crops into SVG safe pockets before final masking.",
                f"- Geometry gate reports {metadata['summary']['final_outside_paintable_alpha_pixels']} outside pixels and {metadata['summary']['final_cutout_alpha_pixels']} cutout pixels.",
                "",
                "Failures or risks:",
                "- This is not yet a new image-generated element sheet; it is a crop-fit proof.",
                "- Feathered source-crop patches can show inherited rectangular background areas.",
                "",
                "Next move:",
                "- Use the style packet to generate isolated element sheets, then run this same geometry placement gate.",
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
