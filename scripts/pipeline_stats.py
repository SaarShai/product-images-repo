#!/usr/bin/env python3
"""pipeline_stats.py — telemetry over the edit pipeline: scans provenance sidecars
(<out>.png.json from edit.py / <final>.batch.json from batch_edit.py) and the gencache,
and prints reliability + cost-saving metrics. Pure stdlib.

Run:  python3 scripts/pipeline_stats.py [--root .]
"""
import argparse, json
from pathlib import Path


def load_provenance(root):
    recs = []
    for p in root.rglob("*.json"):
        if ".venv" in p.parts or ".cache" in p.parts:
            continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        # single-edit provenance has 'op'+'result'; batch has a 'jobs'/'steps' list
        if isinstance(d, dict) and d.get("result") and d.get("op"):
            recs.append(("edit", p, d))
        elif isinstance(d, dict) and (d.get("jobs") or d.get("steps")):
            for s in (d.get("steps") or d.get("jobs") or []):
                if isinstance(s, dict) and s.get("result"):
                    recs.append(("batch-step", p, s))
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = Path(a.root).resolve()

    recs = load_provenance(root)
    n = len(recs)
    success = sum(1 for _, _, d in recs if d.get("result") == "SUCCESS")
    gate0 = sum(1 for _, _, d in recs if d.get("pixel_gate_ok"))
    leak_pass = sum(1 for _, _, d in recs
                    if isinstance(d.get("leak_metric"), dict) and d["leak_metric"].get("pass"))
    repairs = sum((d.get("repair_passes") or 0) for _, _, d in recs)
    ops = {}
    for _, _, d in recs:
        ops[d.get("op", "?")] = ops.get(d.get("op", "?"), 0) + 1

    cache = root / ".cache" / "gen"
    cfiles = list(cache.glob("*")) if cache.exists() else []
    csize = sum(f.stat().st_size for f in cfiles)

    def pct(x):
        return f"{100*x/n:.0f}%" if n else "n/a"

    print(f"[pipeline_stats] root={root}")
    print(f"  edits recorded       : {n}  (ops: {ops})")
    print(f"  RESULT=SUCCESS       : {success}/{n}  ({pct(success)})")
    print(f"  pixel gate clean     : {gate0}/{n}  ({pct(gate0)})")
    print(f"  perceptual leak PASS : {leak_pass}/{n}  ({pct(leak_pass)})")
    print(f"  auto-repair passes   : {repairs} total")
    print(f"  gencache             : {len(cfiles)} entries, {csize/1e6:.1f} MB "
          f"(each = a paid call NOT repeated)")


if __name__ == "__main__":
    main()
