#!/usr/bin/env python3
"""Stage-A candidate metrics (builder-lane measurement contract): for each of
the 4 scored gen.png (hard-composited Stage-A output), measure
outside-silhouette painted px, per-hole painted % (vs holes_mask, excl.
socket ref), socket (arch, Amendment 1) zone painted px/%, and coverage % of
the intended P1-equivalent paint region. Writes runs/metrics-stageA.json +
runs/RESULTS-stageA.md.

Run: /usr/bin/python3 tasks/geometry-adherence-solutions/experiment-1/scripts/measure_stage_a.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(HERE))
import build_assets as BA  # noqa: E402

RUNS = EXP / "runs"
INIT_FILL = BA.INIT_FILL
RUN_IDS = ["A-P1-s7", "A-P1-s21", "A-P2-s7", "A-P2-s21"]


def measure(run_id: str) -> dict:
    d = RUNS / run_id
    meta = json.loads((d / "meta.json").read_text())
    gen = Image.open(d / "gen.png").convert("RGB")
    W, H = gen.size
    silhouette, holes, st1_zone, socket_rect_px, socket_arch_mask, shapes, src_rect = BA.rasterize_geometry(W, H)

    sil_bool = np.asarray(silhouette) > 127
    hol_bool = np.asarray(holes) > 127
    sock_bool = np.asarray(socket_arch_mask) > 127

    arr = np.asarray(gen).astype(np.int16)
    white = np.array((255, 255, 255), dtype=np.int16)
    fill = np.array(INIT_FILL, dtype=np.int16)
    non_white = np.abs(arr - white).sum(axis=2) > 12
    non_neutral = np.abs(arr - fill).max(axis=2) > 10
    painted = non_white & non_neutral  # "actually painted" = neither clean white nor the neutral socket fill

    outside_painted_px = int((non_white & ~sil_bool).sum())

    hole_pct = []
    f, _, _ = BA.make_mapper(src_rect, W, H)
    for i, s in enumerate(s for s in shapes if s.role == "internal_cutout" and s.ref != BA.SOCKET_REF):
        m = Image.new("L", (W, H), 0)
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        ImageDraw.Draw(m).polygon(pts, fill=255)
        hb = np.asarray(m) > 127
        n = int(hb.sum())
        p = int((hb & non_white).sum())
        hole_pct.append({"ref": s.ref, "index": i, "area_px": n,
                          "painted_pct": round(100 * p / n, 3) if n else 0.0})

    socket_zone_px = int(sock_bool.sum())
    socket_zone_painted_px = int((sock_bool & painted).sum())
    socket_zone_painted_pct = round(100 * socket_zone_painted_px / socket_zone_px, 3) if socket_zone_px else 0.0

    paint_region = sil_bool & ~hol_bool & ~sock_bool  # P1-equivalent intended paint area (both arms should be fully painted here)
    region_px = int(paint_region.sum())
    coverage_px = int((paint_region & painted).sum())
    coverage_pct = round(100 * coverage_px / region_px, 3) if region_px else 0.0

    return {
        "run_id": run_id, "arm": meta["arm"], "seed": meta["seed"],
        "size": [W, H], "steps": meta["steps"], "gen_s": meta["gen_s"],
        "pipeline_load_s": meta["pipeline_load_s"], "nan_or_black": meta["nan_or_black"],
        "outside_silhouette_painted_px": outside_painted_px,
        "hole_paint_pct": hole_pct,
        "socket_zone_px": socket_zone_px,
        "socket_zone_painted_px": socket_zone_painted_px,
        "socket_zone_painted_pct": socket_zone_painted_pct,
        "paint_region_coverage_pct": coverage_pct,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-ids", nargs="+", default=RUN_IDS,
                     help="round-1 default: A-P1-s7 A-P1-s21 A-P2-s7 A-P2-s21")
    ap.add_argument("--metrics-out", type=Path, default=RUNS / "metrics-stageA.json")
    ap.add_argument("--results-out", type=Path, default=RUNS / "RESULTS-stageA.md")
    ap.add_argument("--title", default="# experiment-1 Stage-A results (4 scored gens)")
    a = ap.parse_args()

    results = [measure(r) for r in a.run_ids]
    a.metrics_out.write_text(json.dumps(results, indent=2) + "\n")

    lines = [a.title, "",
              "| run | arm | seed | size | wall_s (load+gen) | outside_painted_px | hole_paint_pct (avg) | "
              "socket_zone_painted_pct | coverage_pct | nan_or_black |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        avg_hole = (round(sum(h["painted_pct"] for h in r["hole_paint_pct"]) / len(r["hole_paint_pct"]), 2)
                    if r["hole_paint_pct"] else 0.0)
        wall = round(r["pipeline_load_s"] + r["gen_s"], 1)
        lines.append(f"| {r['run_id']} | {r['arm']} | {r['seed']} | {r['size'][0]}x{r['size'][1]} | "
                      f"{wall}s ({r['pipeline_load_s']}+{r['gen_s']}) | {r['outside_silhouette_painted_px']} | "
                      f"{avg_hole}% | {r['socket_zone_painted_pct']}% | {r['paint_region_coverage_pct']}% | "
                      f"{r['nan_or_black']} |")
    lines += ["", "Per-hole detail:", "", "| run | hole_ref | index | area_px | painted_pct |", "|---|---|---|---|---|"]
    for r in results:
        for h in r["hole_paint_pct"]:
            lines.append(f"| {r['run_id']} | {h['ref']} | {h['index']} | {h['area_px']} | {h['painted_pct']}% |")

    a.results_out.write_text("\n".join(lines) + "\n")
    print(f"wrote {a.metrics_out} + {a.results_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
