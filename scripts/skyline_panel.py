#!/usr/bin/env python3
"""Skyline 3-panel geometry: build a GEOMETRY GUIDE to feed image gen, and CHECK a
candidate against the real SVG geometry (overlay).

Panels (city-skyline template): door (center, outer_contour), left + right (narrow,
paintable_region, aspect ~0.389).

  guide : grey body silhouette (paint here) + keep-clear zones (red) + the internal
          cut features (door flaps / saloon arch / knobs) as outlines, cropped to the
          panel. Feed this as a reference input so the gen FITS the panel + aligns the
          gateway to the arch + avoids keep-clear. (Do NOT ask the model to draw the
          lines — prompt: paint artwork to fill the grey, gateway in the arch.)
  check : fit a candidate into the panel bbox on a white panel-size canvas, then draw
          the real SVG role outlines on top (contour=lime, cutout=magenta,
          keep-clear=red, body just filled). Reveals mis-fit (gateway off the arch,
          art outside contour, focal content in keep-clear, cropping).
"""
import argparse, sys, json, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402

PANELS = {
    "door":  {"role": "outer_contour", "xrange": (1500, 4800)},
    "left":  {"role": "paintable_region", "xrange": (0, 1700), "aspect": 0.389},
    "right": {"role": "paintable_region", "xrange": (4700, 6399), "aspect": 0.389},
}


def load(svg):
    vb, shapes = C.extract_shapes(Path(svg))
    return vb, C.classify(shapes)


def panel_bbox(cl, panel):
    spec = PANELS[panel]
    lo, hi = spec["xrange"]
    cands = [s for s in cl if s.polygon is not None and s.role == spec["role"]
             and lo <= (s.bounds[0] + s.bounds[2]) / 2 <= hi
             and (s.bounds[2] - s.bounds[0]) > 300 and (s.bounds[3] - s.bounds[1]) > 300]
    if not cands:
        raise SystemExit(f"no {spec['role']} body found for panel {panel}")
    # the largest matching body
    s = max(cands, key=lambda s: (s.bounds[2] - s.bounds[0]) * (s.bounds[3] - s.bounds[1]))
    return s.bounds, s.polygon


def to_img(px, py, bbox, W, H):
    x0, y0, x1, y1 = bbox
    return ((px - x0) / (x1 - x0) * W, (py - y0) / (y1 - y0) * H)


def draw_poly(d, poly, bbox, W, H, **kw):
    pts = [to_img(x, y, bbox, W, H) for x, y in poly.exterior.coords]
    d.polygon(pts, **kw)


def in_panel(s, bbox, frac=0.6):
    x0, y0, x1, y1 = bbox
    cx, cy = (s.bounds[0] + s.bounds[2]) / 2, (s.bounds[1] + s.bounds[3]) / 2
    return x0 <= cx <= x1 and y0 <= cy <= y1


def panel_spec(svg, panel, vb, cl):
    """The single geometry CONTRACT for a panel, derived from the SVG. Consumed by
    BOTH the gen-guide and the judge so neither uses a generic prior or a wrong guide."""
    bbox, body = panel_bbox(cl, panel)
    x0, y0, x1, y1 = bbox
    pw, ph = (x1 - x0), (y1 - y0)
    sha = hashlib.sha256(Path(svg).read_bytes()).hexdigest()[:16]
    def frac_box(s):
        bx0, by0, bx1, by1 = s.bounds
        return {"x0": round((bx0 - x0) / pw, 3), "y0": round((by0 - y0) / ph, 3),
                "x1": round((bx1 - x0) / pw, 3), "y1": round((by1 - y0) / ph, 3)}
    keep_clear, arch_cands = [], []
    for s in cl:
        if s.polygon is None or not in_panel(s, bbox):
            continue
        if s.role == "no_focal_motif_zone":
            keep_clear.append(frac_box(s))
        elif s.role == "internal_cutout" and (s.bounds[3] - s.bounds[1]) / ph <= 0.45:
            fb = frac_box(s)
            xc = (fb["x0"] + fb["x1"]) / 2
            yc = (fb["y0"] + fb["y1"]) / 2
            # the saloon arch = a wide cutout, horizontally CENTRED, in the upper-mid band
            if (fb["x1"] - fb["x0"]) > 0.2 and 0.35 <= xc <= 0.65 and 0.2 < yc < 0.6:
                arch_cands.append(fb)
    # widest central candidate wins
    arch = max(arch_cands, key=lambda b: b["x1"] - b["x0"]) if arch_cands else None
    return {
        "panel": panel,
        "svg": str(svg),
        "svg_sha256_16": sha,
        "viewbox": [round(v, 2) for v in vb] if vb else None,
        "bbox_svg": [round(v, 1) for v in bbox],
        "aspect": round(pw / ph, 4),
        "aspect_tol": 0.02,
        "contour": "domed rectangle: vertical sides, domed top; fill artwork edge-to-edge to the outer contour",
        "saloon_arch_frac": arch,
        "keep_clear_lanes_frac": keep_clear,
        "must_not": [
            "taper / pinch / trapezoid (narrow bottom or hourglass waist)",
            "leave outer corners or mid-height sides as background",
            "crop a landmark base or focal feature at a seam",
            "place a focal/iconic feature in a keep_clear lane",
        ],
        "gateway": "align the main gateway/portal to saloon_arch_frac" if arch else None,
    }


def cmd_spec(a, vb, cl):
    spec = panel_spec(a.svg, a.panel, vb, cl)
    txt = json.dumps(spec, indent=2)
    if a.out:
        Path(a.out).write_text(txt)
        print(f"spec -> {a.out}  panel={a.panel} aspect={spec['aspect']} sha={spec['svg_sha256_16']}")
    else:
        print(txt)


def cmd_guide(a, vb, cl):
    bbox, body = panel_bbox(cl, a.panel)
    x0, y0, x1, y1 = bbox
    W = a.width
    H = int(round(W * (y1 - y0) / (x1 - x0)))
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")
    draw_poly(d, body, bbox, W, H, fill=(200, 200, 200, 255))  # grey body = paint here
    # Bold OUTER contour = "fill artwork edge-to-edge to HERE". Must dominate any
    # interior line, else the model traces an interior cut edge as the silhouette.
    draw_poly(d, body, bbox, W, H, outline=(45, 45, 45, 255), width=max(3, W // 110))
    ph = (y1 - y0)
    for s in cl:
        if s.polygon is None or not in_panel(s, bbox):
            continue
        if s.role == "no_focal_motif_zone":
            draw_poly(d, s.polygon, bbox, W, H, fill=(255, 80, 80, 90))  # keep-clear
        elif s.role == "internal_cutout":
            # The two saloon-door FLAP polygons splay diagonally toward the bottom
            # corners; drawn bold, the model reads them as the building's OUTER edge
            # and tapers it into a trapezoid (bottom-corner triangles left as bg).
            # They're already implied by the body silhouette → SKIP the large ones;
            # keep only small central hints (saloon arch / knobs), drawn FAINT so they
            # read as interior detail, not a silhouette edge.
            hfrac = (s.bounds[3] - s.bounds[1]) / ph
            if hfrac > 0.45:
                continue
            draw_poly(d, s.polygon, bbox, W, H, outline=(120, 90, 40, 95), width=max(1, W // 500))
    img.save(a.out)
    # PROVENANCE sidecar: stamps which SVG/panel/bbox/aspect this guide came from, so
    # a gen records the exact guide it used and a verify step can assert it's correct
    # (prevents feeding a stale / hand-authored / wrong-panel guide).
    spec = panel_spec(a.svg, a.panel, vb, cl)
    spec["guide_png"] = str(a.out)
    spec["guide_size"] = [W, H]
    sidecar = str(Path(a.out).with_suffix(".spec.json"))
    Path(sidecar).write_text(json.dumps(spec, indent=2))
    print(f"guide -> {a.out}  panel={a.panel} bbox={tuple(round(v) for v in bbox)} size={W}x{H} aspect={(x1-x0)/(y1-y0):.3f}")
    print(f"spec  -> {sidecar}  aspect={spec['aspect']} sha={spec['svg_sha256_16']}")


def cmd_check(a, vb, cl):
    bbox, body = panel_bbox(cl, a.panel)
    x0, y0, x1, y1 = bbox
    W = a.width
    H = int(round(W * (y1 - y0) / (x1 - x0)))
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    cand = Image.open(a.cand).convert("RGB")
    # fit candidate to FILL the panel (scale to cover, center-crop) — matches how a
    # tall artwork would be placed into the panel.
    cw, ch = cand.size
    scale = max(W / cw, H / ch)
    nw, nh = int(round(cw * scale)), int(round(ch * scale))
    cand = cand.resize((nw, nh), Image.LANCZOS)
    canvas.paste(cand, ((W - nw) // 2, (H - nh) // 2))
    arr = np.asarray(canvas)
    def _white_frac(x0c, y0c, x1c, y1c):
        reg = arr[y0c:y1c, x0c:x1c]
        return float((reg > 235).all(axis=2).mean())
    if a.panel == "door":
        # SIDE-FILL / taper GATE (door only): the door is a full-bleed scene that must
        # fill the rectangular contour. A trapezoid (narrow bottom) or hourglass pinch
        # leaves near-white bg in the bottom OUTER corners / mid-height sides. Top
        # corners skipped — the dome legitimately curves inward. Clean separation on
        # real data (good 0.24/0.39 vs bad 0.88+) so this GATES.
        bw, bh = int(0.16 * W), int(0.16 * H)
        sw = int(0.10 * W)
        probes = {
            "bot-left":  _white_frac(0, H - bh, bw, H),
            "bot-right": _white_frac(W - bw, H - bh, W, H),
            "mid-left":  _white_frac(0, int(0.42 * H), sw, int(0.66 * H)),
            "mid-right": _white_frac(W - sw, int(0.42 * H), W, int(0.66 * H)),
        }
        taper = max(probes.values()) > 0.4
        detail = " ".join(f"{k}={v:.2f}" for k, v in probes.items())
        print(f"side-fill: {detail} -> "
              f"{'TAPER/UNDERFILL (FAIL)' if taper else 'fills contour (ok)'}")
    else:
        # NARROWS are sky-aware: a tower with WHITE SKY at the sides is correct, so the
        # door edge-fill rule false-fails good narrows (proven: good geoW2 and bad
        # too-narrow gens overlap at cov 0.71-0.79 — NOT separable). So narrows are
        # ADVISORY: report content coverage + center keep-clear lane fill; route the
        # "too narrow / margin" (#8) and "feature/head in the center lane" (#5) calls to
        # the spec-anchored VLM judge + human, NOT a fragile pixel gate.
        nonwhite = ~(arr > 235).all(axis=2)
        band = nonwhite[int(0.40 * H):int(0.75 * H)]
        covs = [(np.where(r)[0][-1] - np.where(r)[0][0]) / W for r in band if r.any()]
        cov = float(np.median(covs)) if covs else 0.0
        lanes = [s for s in cl if s.role == "no_focal_motif_zone" and in_panel(s, bbox)]
        lane_txt = ""
        if lanes:
            lx0 = min((s.bounds[0] - x0) / (x1 - x0) for s in lanes)
            lx1 = max((s.bounds[2] - x0) / (x1 - x0) for s in lanes)
            lane_fill = _white_frac(int(lx0 * W), int(0.25 * H), int(lx1 * W), H)
            lane_txt = f" center-lane[{lx0:.2f}-{lx1:.2f}]_painted={1 - lane_fill:.2f}"
            # PANEL-RELATIVE lane crop so a judge/human can SEE whether a recognizable
            # feature (face/head/sign) sits in or is cropped at the lane (#5 horse-head).
            pad = int(0.10 * W)
            lane_crop = canvas.crop((max(0, int(lx0 * W) - pad), 0,
                                     min(W, int(lx1 * W) + pad), H))
            lane_path = str(Path(a.out).with_suffix(".lane.png"))
            lane_crop.save(lane_path)
            lane_txt += f" lane_crop={lane_path}"
        print(f"narrow (ADVISORY): content_coverage={cov:.2f}{lane_txt} "
              f"-> judge: tower fills panel? feature/head in center keep-clear lane?")
    d = ImageDraw.Draw(canvas, "RGBA")
    # body contour (lime), keep-clear (red), internal cutouts (magenta)
    lw = max(2, W // 300)
    draw_poly(d, body, bbox, W, H, outline=(0, 230, 0, 255), width=lw + 1)
    for s in cl:
        if s.polygon is None or not in_panel(s, bbox):
            continue
        if s.role == "no_focal_motif_zone":
            draw_poly(d, s.polygon, bbox, W, H, outline=(255, 0, 0, 255), width=lw)
        elif s.role == "internal_cutout":
            draw_poly(d, s.polygon, bbox, W, H, outline=(255, 0, 200, 255), width=lw)
    canvas.save(a.out)
    print(f"check -> {a.out}  panel={a.panel} size={W}x{H} cand={cw}x{ch} cand_aspect={cw/ch:.3f} panel_aspect={(x1-x0)/(y1-y0):.3f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--svg", required=True)
    p.add_argument("--panel", required=True, choices=list(PANELS))
    p.add_argument("--mode", required=True, choices=["guide", "check", "spec"])
    p.add_argument("--out")  # required for guide/check; optional for spec (prints to stdout)
    p.add_argument("--cand")
    p.add_argument("--width", type=int, default=820)
    a = p.parse_args()
    vb, cl = load(a.svg)
    if a.mode == "spec":
        cmd_spec(a, vb, cl)
    elif a.mode == "guide":
        if not a.out:
            raise SystemExit("--out required for guide")
        cmd_guide(a, vb, cl)
    else:
        if not a.out:
            raise SystemExit("--out required for check")
        if not a.cand:
            raise SystemExit("--cand required for check")
        cmd_check(a, vb, cl)


if __name__ == "__main__":
    main()
