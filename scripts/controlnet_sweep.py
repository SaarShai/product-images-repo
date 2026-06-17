#!/usr/bin/env python3
"""Sweep controlnet_conditioning_scale x preprocessor to maximize mean_iou.

For each (style, cond_scale) it generates with scripts/controlnet_gen.py, then
measures with scripts/svg_geometry_check.py against the exact SVG. Records a
metrics.json per cell and prints a ranked table. The winner's raw image is
copied to <task>/experiments/CN1-controlnet/raw.png.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def auto_bbox(path: Path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from geom_adherence_test import auto_bbox as ab
    return ab(path)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--base-model", default="Lykon/dreamshaper-8")
    ap.add_argument("--prompt-file", required=True, type=Path)
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--scales", default="0.8,1.0,1.2,1.5")
    ap.add_argument("--styles", default="lineart,canny",
                    help="comma list: lineart and/or canny")
    ap.add_argument("--seed", type=int, default=12345)
    a = ap.parse_args()

    prompt = a.prompt_file.read_text().strip()
    a.outdir.mkdir(parents=True, exist_ok=True)
    cn_for = {
        "lineart": "lllyasviel/control_v11p_sd15_lineart",
        "canny": "lllyasviel/sd-controlnet-canny",
    }

    # render maps once per style
    maps = {}
    for style in a.styles.split(","):
        mp = a.outdir / f"controlmap-{style}-{a.width}.png"
        run(["/usr/bin/python3", "scripts/svg_to_controlmap.py", str(a.svg),
             "--out", str(mp), "--width", str(a.width), "--style", style, "--stroke", "3"], cwd=ROOT)
        maps[style] = mp

    results = []
    for style in a.styles.split(","):
        for sc in [float(x) for x in a.scales.split(",")]:
            cell = f"{style}-cs{sc}"
            raw = a.outdir / f"{cell}.png"
            g = run(["/usr/bin/python3", "scripts/controlnet_gen.py",
                     "--control-map", str(maps[style]),
                     "--controlnet", cn_for[style],
                     "--base-model", a.base_model,
                     "--prompt", prompt,
                     "--cond-scale", str(sc), "--steps", str(a.steps),
                     "--width", str(a.width), "--seed", str(a.seed),
                     "--out", str(raw)], cwd=ROOT)
            if not raw.exists():
                print(f"{cell:18s} GEN FAILED\n{g.stderr[-400:]}")
                continue
            bbox = ",".join(str(v) for v in auto_bbox(raw))
            mj = a.outdir / f"{cell}.metrics.json"
            run(["/usr/bin/python3", "scripts/svg_geometry_check.py", str(raw),
                 "--svg", str(a.svg), "--bbox", bbox,
                 "--json-out", str(mj),
                 "--out-overlay", str(a.outdir / f"{cell}.overlay.png")], cwd=ROOT)
            m = json.loads(mj.read_text())
            maxpaint = max((h["painted_frac"] for h in m["holes"]), default=0.0)
            results.append((m["mean_iou"], cell, m["overall"], maxpaint, m["outside_frac"], raw, m))
            print(f"{cell:18s} mean_iou={m['mean_iou']:.3f} maxpaint={maxpaint:.3f} "
                  f"outside={m['outside_frac']:.1%} overall={m['overall']}")

    results.sort(reverse=True)
    print("\n=== RANKED ===")
    for r in results:
        print(f"{r[1]:18s} mean_iou={r[0]:.3f} maxpaint={r[3]:.3f} outside={r[4]:.1%} {r[2]}")
    if results:
        best = results[0]
        import shutil
        shutil.copy(best[5], a.outdir / "raw.png")
        shutil.copy(a.outdir / f"{best[1]}.metrics.json", a.outdir / "metrics.json")
        ov = a.outdir / f"{best[1]}.overlay.png"
        if ov.exists():
            shutil.copy(ov, a.outdir / "overlay.png")
        (a.outdir / "sweep.json").write_text(json.dumps(
            [{"cell": r[1], "mean_iou": r[0], "overall": r[2], "maxpaint": r[3],
              "outside_frac": r[4]} for r in results], indent=2))
        print(f"\nWINNER: {best[1]} mean_iou={best[0]:.3f} -> {a.outdir/'raw.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
