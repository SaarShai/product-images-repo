#!/usr/bin/env python3
"""forbidden_gate.py — salient-feature check inside forbidden zones (ADVISORY).

The master template's red-dashed stripes sit over the CENTER stabilizer slots:
no significant features may live there (user rule, turn 54). This gate proxies
"salient feature" with local edge density + color variance inside the forbidden
region, compared against the panel body baseline. It is ADVISORY (exit 0 with
verdict in JSON + overlay for the human/VLM) because paint texture legitimately
crosses the stripes — only OBJECTS are forbidden, and that final call is visual.

CLI: python3 scripts/forbidden_gate.py --cand <img> --forbidden <p>-forbidden.png \
        --mask <p>-mask.png [--overlay <out.png>] [--ratio-warn 1.35]
Verdict: OK if forbidden-zone edge density <= ratio-warn x body baseline
(and variance ratio too), else WARN with the numbers.
"""
from __future__ import annotations

import argparse, json
import numpy as np
from PIL import Image


def _edges(gray):
    gx = np.abs(np.diff(gray.astype(float), axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray.astype(float), axis=0, prepend=gray[:1, :]))
    return gx + gy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--forbidden", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--overlay", default=None)
    ap.add_argument("--ratio-warn", type=float, default=1.35)
    ap.add_argument("--exclude-edges", default=None,
                    help="control map PNG: cut edges the model legitimately paints "
                         "(the slot outline INSIDE the stripe); a dilated band "
                         "around them is excluded from both zones")
    ap.add_argument("--exclude-dilate", type=int, default=8)
    a = ap.parse_args()

    cand = Image.open(a.cand).convert("RGB")
    forb = np.array(Image.open(a.forbidden).convert("L").resize(cand.size, Image.NEAREST)) > 127
    body = np.array(Image.open(a.mask).convert("L").resize(cand.size, Image.NEAREST)) > 127
    rgb = np.array(cand)
    gray = np.array(cand.convert("L"))

    if not forb.any():
        print(json.dumps({"verdict": "OK", "note": "no forbidden region"})); return

    if a.exclude_edges:
        ce = np.array(Image.open(a.exclude_edges).convert("L").resize(cand.size, Image.NEAREST)) > 127
        for _ in range(a.exclude_dilate):
            ce = ce | np.roll(ce, 1, 0) | np.roll(ce, -1, 0) | np.roll(ce, 1, 1) | np.roll(ce, -1, 1)
        forb = forb & ~ce
        body = body & ~ce

    edges = _edges(gray)
    base_zone = body & ~forb
    ed_forb = float(edges[forb & body].mean())
    ed_base = float(edges[base_zone].mean())
    var_forb = float(rgb[forb & body].std())
    var_base = float(rgb[base_zone].std())
    ed_ratio = ed_forb / max(ed_base, 1e-6)
    var_ratio = var_forb / max(var_base, 1e-6)
    verdict = "OK" if (ed_ratio <= a.ratio_warn and var_ratio <= a.ratio_warn) else "WARN"

    if a.overlay:
        ov = rgb.copy()
        ov[forb] = (0.45 * ov[forb] + 0.55 * np.array([255, 40, 40])).astype("uint8")
        Image.fromarray(ov).save(a.overlay)

    print(json.dumps({
        "verdict": verdict, "advisory": True,
        "edge_density": {"forbidden": round(ed_forb, 2), "body": round(ed_base, 2),
                         "ratio": round(ed_ratio, 3)},
        "color_variance": {"forbidden": round(var_forb, 2), "body": round(var_base, 2),
                           "ratio": round(var_ratio, 3)},
        "ratio_warn": a.ratio_warn,
        "overlay": a.overlay,
    }, indent=1))


if __name__ == "__main__":
    main()
