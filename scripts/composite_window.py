#!/usr/bin/env python3
"""For panels that carry a FIXED embedded image (e.g. a window/door that must appear at EXACT
dimensions): register a free-form gen onto the SVG geometry (via register_to_svg), then composite
the EXACT embedded image back on top at its true SVG transform — so the gen supplies the integrated
surroundings (castle/walls/towers) while the window stays pixel-exact. Feathered paste blends it.

  composite_window.py --gen GEN.png --svg PANEL.svg --window WINDOW.png --out OUT.png [--width 1024]

WINDOW should be the background-removed cut (transparent outside the image), so only the real
window pixels land on the gen. The transform is parsed from the SVG's <image> element.
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent


def image_transform(svg_text):
    m = re.search(r'<image[^>]*?width="([\d.]+)"[^>]*?height="([\d.]+)"[^>]*?'
                  r'transform="translate\(([-\d.]+)[ ,]+([-\d.]+)\)\s*scale\(([-\d.]+)\)"', svg_text)
    if not m:
        return None
    w, h, tx, ty, s = (float(x) for x in m.groups())
    return w, h, tx, ty, s


def viewbox(svg_text):
    m = re.search(r'viewBox="([\d.\- ]+)"', svg_text)
    vx, vy, vw, vh = (float(x) for x in m.group(1).split())
    return vx, vy, vw, vh


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True, type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--window", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--feather", type=int, default=3)
    ap.add_argument("--no-register", action="store_true", help="gen already canvas-aligned; skip register")
    a = ap.parse_args()

    a.out.parent.mkdir(parents=True, exist_ok=True)
    reg = a.out.with_suffix(".registered.png")
    if a.no_register:
        reg = a.gen
    else:
        subprocess.run([sys.executable, str(ROOT / "scripts/register_to_svg.py"),
                        "--gen", str(a.gen), "--svg", str(a.svg), "--out", str(reg),
                        "--width", str(a.width)], check=True, capture_output=True)

    base = Image.open(reg).convert("RGBA")
    W, H = base.size
    svg_text = a.svg.read_text(errors="replace")
    vx, vy, vw, vh = viewbox(svg_text)
    tr = image_transform(svg_text)
    if not tr:
        print("no <image> transform found", file=sys.stderr); return 2
    iw, ih, tx, ty, s = tr
    sf = W / vw
    pw, ph = max(1, int(iw * s * sf)), max(1, int(ih * s * sf))
    px, py = int((tx - vx) * sf), int((ty - vy) * sf)

    win = Image.open(a.window).convert("RGBA").resize((pw, ph))
    if a.feather > 0:                      # soften the alpha edge so the paste blends
        alpha = win.split()[3].filter(ImageFilter.GaussianBlur(a.feather))
        win.putalpha(alpha)
    base.alpha_composite(win, (px, py))
    base.convert("RGB").save(a.out, quality=95)
    print(f"composited window {pw}x{ph} @({px},{py}) on {W}x{H} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
