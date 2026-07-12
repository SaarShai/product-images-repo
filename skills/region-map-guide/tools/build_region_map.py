#!/usr/bin/env python3
"""Build a flat-color REGION MAP guide image + generation-ready legend prompt
from a JSON manifest describing named color-coded zones on a canvas.

CLI:
    build_region_map.py --manifest <json> --out <map.png> --legend-out <legend.txt>
                         [--expect-aspect W:H] [--scale F]

See skills/region-map-guide/SKILL.md for the manifest schema.
"""
import argparse
import json
import sys

from PIL import Image, ImageDraw

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


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def resolve_color(name):
    if name not in PALETTE:
        die(
            f"unknown color name '{name}'; must be one of "
            f"{', '.join(sorted(PALETTE))}"
        )
    return PALETTE[name]


def check_bbox(name, x0, y0, x1, y1, width, height):
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        die(
            f"region '{name}' bbox ({x0},{y0})-({x1},{y1}) is outside "
            f"canvas {width}x{height}"
        )


def shape_bbox(shape, regions_by_name, width, height):
    """Return (x0,y0,x1,y1) bounding box for a shape dict."""
    t = shape["type"]
    if t == "rect" or t == "arch":
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        return x, y, x + w, y + h
    if t == "circle":
        cx, cy, r = shape["cx"], shape["cy"], shape["r"]
        return cx - r, cy - r, cx + r, cy + r
    if t == "dots":
        r = shape["r"]
        xs = [p[0] for p in shape["points"]]
        ys = [p[1] for p in shape["points"]]
        return min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r
    if t == "polygon":
        xs = [p[0] for p in shape["points"]]
        ys = [p[1] for p in shape["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    if t == "band":
        around = shape["around"]
        thickness = shape["thickness"]
        if around not in regions_by_name:
            die(f"band references unknown region '{around}'")
        inner_shape = regions_by_name[around]["shape"]
        if inner_shape["type"] not in ("arch", "rect", "circle"):
            die(
                f"band around '{around}' requires an arch/rect/circle "
                f"shape, got '{inner_shape['type']}'"
            )
        return enlarged_shape_bbox(inner_shape, thickness)
    die(f"unknown shape type '{t}'")


def enlarged_shape_bbox(shape, thickness):
    t = shape["type"]
    if t == "circle":
        cx, cy, r = shape["cx"], shape["cy"], shape["r"]
        r2 = r + thickness
        return cx - r2, cy - r2, cx + r2, cy + r2
    if t == "arch":
        # arch bands surround the top and sides only, like a doorframe;
        # the bottom edge stays flush with the inner shape's bottom
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        return x - thickness, y - thickness, x + w + thickness, y + h
    # rect: enlarge on all sides
    x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
    return x - thickness, y - thickness, x + w + thickness, y + h + thickness


def enlarge_shape(shape, thickness):
    """Return a new shape dict of the same type, enlarged by thickness."""
    t = shape["type"]
    if t == "circle":
        return {
            "type": "circle",
            "cx": shape["cx"],
            "cy": shape["cy"],
            "r": shape["r"] + thickness,
        }
    if t == "arch":
        # surrounds top and sides only; bottom stays flush (doorframe-style)
        return {
            "type": t,
            "x": shape["x"] - thickness,
            "y": shape["y"] - thickness,
            "w": shape["w"] + 2 * thickness,
            "h": shape["h"] + thickness,
        }
    # rect
    return {
        "type": t,
        "x": shape["x"] - thickness,
        "y": shape["y"] - thickness,
        "w": shape["w"] + 2 * thickness,
        "h": shape["h"] + 2 * thickness,
    }


def draw_shape(draw, shape, color):
    t = shape["type"]
    if t == "rect":
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        draw.rectangle([x, y, x + w, y + h], fill=color)
    elif t == "circle":
        cx, cy, r = shape["cx"], shape["cy"], shape["r"]
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    elif t == "arch":
        x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
        radius = w / 2.0
        arc_cy = y + radius
        # semicircular top
        draw.ellipse([x, y, x + w, y + 2 * radius], fill=color)
        # rectangular body beneath the arc's center line
        body_top = arc_cy
        body_bottom = y + h
        if body_bottom > body_top:
            draw.rectangle([x, body_top, x + w, body_bottom], fill=color)
    elif t == "dots":
        r = shape["r"]
        for px, py in shape["points"]:
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color)
    elif t == "polygon":
        draw.polygon([tuple(p) for p in shape["points"]], fill=color)
    elif t == "band":
        pass  # handled separately via enlarge_shape at call site
    else:
        die(f"unknown shape type '{t}'")


def build_map(manifest, scale):
    canvas = manifest["canvas"]
    width = int(canvas["width"] * scale)
    height = int(canvas["height"] * scale)

    img = Image.new("RGB", (width, height), (255, 255, 255))

    # --- silhouette ---
    silhouette = manifest.get("silhouette")
    if silhouette:
        src_path = silhouette["source"]
        sil_color_name = silhouette["color"]
        sil_color = resolve_color(sil_color_name)
        Image.MAX_IMAGE_PIXELS = None
        src = Image.open(src_path).convert("RGB").resize(
            (width, height), Image.LANCZOS
        )
        px = src.load()
        out = img.load()
        for yy in range(height):
            for xx in range(width):
                r, g, b = px[xx, yy]
                if not (r >= 250 and g >= 250 and b >= 250):
                    out[xx, yy] = sil_color

    draw = ImageDraw.Draw(img)

    regions = manifest["regions"]
    regions_by_name = {r["name"]: r for r in regions}

    # --- validate colors: one color == one meaning ---
    color_owner = {}
    if silhouette:
        color_owner[silhouette["color"]] = ("<silhouette>", "<silhouette>")

    def claim_color(owner_name, color_name, means):
        resolve_color(color_name)  # validates existence
        owner_key = means  # one color = one MEANING; same means may repeat
        if color_name in color_owner and color_owner[color_name][0] != owner_key:
            prev_name = color_owner[color_name][1]
            die(
                f"color '{color_name}' is used by both region "
                f"'{prev_name}' and '{owner_name}' with different "
                "meanings (one color must map to one meaning)"
            )
        color_owner[color_name] = (owner_key, owner_name)

    for region in regions:
        claim_color(region["name"], region["color"], region["means"])
        if region["shape"]["type"] == "band":
            around = region["shape"]["around"]
            if around not in regions_by_name:
                die(f"band '{region['name']}' references unknown region '{around}'")
            inner_color = regions_by_name[around]["color"]
            if inner_color == region["color"]:
                die(
                    f"band '{region['name']}' may not reuse its inner "
                    f"region's color '{inner_color}'"
                )

    # --- validate bboxes ---
    for region in regions:
        shape = region["shape"]
        if shape["type"] == "dots":
            # bbox check already covers all points
            pass
        x0, y0, x1, y1 = shape_bbox(shape, regions_by_name, canvas["width"], canvas["height"])
        check_bbox(region["name"], x0, y0, x1, y1, canvas["width"], canvas["height"])

    # --- draw order: bands first (drawn under their referenced region),
    # then non-band/non-dot regions in manifest order, dots last ---
    band_regions = [r for r in regions if r["shape"]["type"] == "band"]
    plain_regions = [
        r for r in regions if r["shape"]["type"] not in ("band", "dots")
    ]
    dots_regions = [r for r in regions if r["shape"]["type"] == "dots"]

    for region in band_regions:
        shape = region["shape"]
        color = resolve_color(region["color"])
        around = shape["around"]
        inner_shape = regions_by_name[around]["shape"]
        enlarged = enlarge_shape(inner_shape, shape["thickness"])
        drawn_shape = scale_shape(enlarged, scale)
        draw_shape(draw, drawn_shape, color)

    for region in plain_regions:
        color = resolve_color(region["color"])
        drawn_shape = scale_shape(region["shape"], scale)
        draw_shape(draw, drawn_shape, color)

    for region in dots_regions:
        color = resolve_color(region["color"])
        drawn_shape = scale_shape(region["shape"], scale)
        draw_shape(draw, drawn_shape, color)

    return img


def scale_shape(shape, scale):
    if scale == 1.0:
        return shape
    t = shape["type"]
    if t in ("rect", "arch"):
        return {
            "type": t,
            "x": shape["x"] * scale,
            "y": shape["y"] * scale,
            "w": shape["w"] * scale,
            "h": shape["h"] * scale,
        }
    if t == "circle":
        return {
            "type": t,
            "cx": shape["cx"] * scale,
            "cy": shape["cy"] * scale,
            "r": shape["r"] * scale,
        }
    if t == "dots":
        return {
            "type": t,
            "points": [[p[0] * scale, p[1] * scale] for p in shape["points"]],
            "r": shape["r"] * scale,
        }
    if t == "polygon":
        return {
            "type": t,
            "points": [[p[0] * scale, p[1] * scale] for p in shape["points"]],
        }
    return shape


def build_legend(manifest):
    regions = manifest["regions"]
    lines = []
    seen = set()

    def add_line(line):
        if line not in seen:
            seen.add(line)
            lines.append(line)

    silhouette = manifest.get("silhouette")
    if silhouette:
        sil_color = silhouette["color"]
        sil_means = silhouette.get("means", "the panel body/facade")
        add_line(f"{sil_color} = {sil_means}.")

    for region in regions:
        color = region["color"]
        means = region["means"]
        avoid = region.get("avoid", False)
        dots = region["shape"]["type"] == "dots"
        color_label = f"{color} dots" if dots else color
        if avoid:
            if "do not" in means.lower():
                # means already phrases the prohibition itself
                line = f"{color_label} = {means}."
            else:
                # keep means as a label, never embed it mid-sentence — arbitrary
                # means text garbles a "do NOT place <means> in that area" template
                line = (f"{color_label} mark a keep-clear zone ({means}); "
                        f"do NOT paint any element in that area.")
        else:
            line = f"{color_label} = {means}."
        add_line(line)

    header = (
        "This image is a REGION MAP, not artwork. Each flat color marks "
        "where one element must be painted. Strictly follow the areas and "
        "generate a proportional image in the same style as the attached "
        "style reference. Do not draw the map's colors or any outlines. "
        "White background."
    )
    body = "Regions: " + " ".join(lines)
    return header + "\n" + body + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--legend-out", required=True)
    parser.add_argument("--expect-aspect", default=None)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    canvas = manifest.get("canvas")
    if not canvas or "width" not in canvas or "height" not in canvas:
        die("manifest missing canvas.width/canvas.height")

    if args.expect_aspect:
        try:
            ew, eh = (float(v) for v in args.expect_aspect.split(":"))
        except ValueError:
            die(f"invalid --expect-aspect '{args.expect_aspect}', expected W:H")
        actual = canvas["width"] / canvas["height"]
        expected = ew / eh
        if abs(actual / expected - 1) > 0.01:
            die(
                f"canvas aspect {canvas['width']}:{canvas['height']} "
                f"({actual:.4f}) does not match --expect-aspect "
                f"{args.expect_aspect} ({expected:.4f})"
            )

    img = build_map(manifest, args.scale)
    img.save(args.out)

    legend = build_legend(manifest)
    with open(args.legend_out, "w") as f:
        f.write(legend)

    print(f"wrote {args.out} ({img.size[0]}x{img.size[1]})")
    print(f"wrote {args.legend_out}")


if __name__ == "__main__":
    main()
