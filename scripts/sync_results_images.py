#!/usr/bin/env python3
"""sync_results_images.py — HARD RULE enforcer.

Copy EVERY result image (raw.png / exact.png / region_overlay.png) from every
`tasks/space-*/experiments*/<id>/` dir into the single central library
`tasks/space-np01-front-bottom-02/RESULTS/Images/`, named `<task>__<id>__<kind>.png`.

Then VERIFY: every source result image has a copy in the library. Exits non-zero
and lists any missing, so a silent copy bug (e.g. a bad shell glob) is caught
instead of quietly dropping results.

Usage:
  python3 scripts/sync_results_images.py            # sync + verify
  python3 scripts/sync_results_images.py --check     # verify only (no copy)
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "tasks/space-np01-front-bottom-02/RESULTS/Images"
KINDS = ("raw.png", "exact.png", "region_overlay.png")


def sources():
    for tdir in sorted((ROOT / "tasks").glob("space-*")):
        task = tdir.name[len("space-"):]
        for exp in list(tdir.glob("experiments")) + list(tdir.glob("experiments-outset")):
            for cell in sorted(p for p in exp.iterdir() if p.is_dir()):
                for kind in KINDS:
                    f = cell / kind
                    if f.is_file():
                        dest = IMG / f"{task}__{cell.name}__{kind[:-4]}.png"
                        yield f, dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, do not copy")
    args = ap.parse_args()
    IMG.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = []
    for src, dest in sources():
        if dest.exists():
            continue
        if args.check:
            missing.append(dest.name)
        else:
            shutil.copy2(src, dest)
            copied += 1

    if args.check:
        if missing:
            print(f"MISSING {len(missing)} result image(s) in Images/:")
            for m in missing:
                print(f"  {m}")
            return 1
        print(f"OK — every result image has a copy in {IMG.relative_to(ROOT)}")
        return 0

    total = len(list(IMG.glob('*.png')))
    print(f"synced: copied {copied} new; Images/ now holds {total} png")
    # post-copy verification
    still = [d.name for _, d in sources() if not d.exists()]
    if still:
        print(f"WARNING: {len(still)} still missing after copy", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
