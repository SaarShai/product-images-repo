#!/usr/bin/env python3
"""sync_results_images.py — HARD RULE enforcer.

Copy EVERY result image (raw.png / exact.png / region_overlay.png) from every
`tasks/space-*/experiments*/<id>/` dir into the single central library
`tasks/space-np01-front-bottom-02/RESULTS/Images/`, named `<task>__<id>__<kind>.png`.

Then VERIFY: every source result image has a copy in the library. Exits non-zero
and lists any missing, so a silent copy bug (e.g. a bad shell glob) is caught
instead of quietly dropping results.

`--task` selects which `tasks/` dir name/glob to sync (default: `space-*`, the
original hardcoded behavior — matches every `space-*` task into the central
`space-np01-front-bottom-02/RESULTS/Images` library). Any other value targets
that task's own `tasks/<task>/RESULTS/Images` library instead, so this script
is no longer a silent no-op outside the `space-*` family. If `--task` matches
NO directory under `tasks/`, this prints an explicit warning (not a silent
"OK") and exits non-zero.

Usage:
  python3 scripts/sync_results_images.py            # sync + verify (space-*)
  python3 scripts/sync_results_images.py --check     # verify only (no copy)
  python3 scripts/sync_results_images.py --task geometry-evidentiary-princess-n02
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "tasks/space-np01-front-bottom-02/RESULTS/Images"
KINDS = ("raw.png", "exact.png", "region_overlay.png")
DEFAULT_TASK = "space-*"


def task_dirs(task: str) -> list[Path]:
    return sorted((ROOT / "tasks").glob(task))


def task_label(tdir: Path) -> str:
    name = tdir.name
    return name[len("space-"):] if name.startswith("space-") else name


def images_dir_for(task: str) -> Path:
    if task == DEFAULT_TASK:
        return IMG  # legacy central library, unchanged for backward compat
    # a concrete (non-default) task pattern gets its own library, so unrelated
    # tasks never get silently mixed into (or silently missed from) the
    # space-np01 central library
    return ROOT / "tasks" / task / "RESULTS" / "Images"


def sources(task: str, img_dir: Path):
    for tdir in task_dirs(task):
        label = task_label(tdir)
        for exp in list(tdir.glob("experiments")) + list(tdir.glob("experiments-outset")):
            for cell in sorted(p for p in exp.iterdir() if p.is_dir()):
                for kind in KINDS:
                    f = cell / kind
                    if f.is_file():
                        dest = img_dir / f"{label}__{cell.name}__{kind[:-4]}.png"
                        yield f, dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, do not copy")
    ap.add_argument(
        "--task", default=DEFAULT_TASK,
        help="tasks/ dir name or glob to sync results for "
             f"(default: {DEFAULT_TASK!r}, the original hardcoded behavior)",
    )
    args = ap.parse_args()

    dirs = task_dirs(args.task)
    if not dirs:
        print(
            f"WARNING: no task directories matched '{args.task}' under "
            f"{ROOT / 'tasks'} — nothing to sync.", file=sys.stderr,
        )
        return 1

    img_dir = images_dir_for(args.task)
    img_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = []
    for src, dest in sources(args.task, img_dir):
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
        print(f"OK — every result image has a copy in {img_dir.relative_to(ROOT)}")
        return 0

    total = len(list(img_dir.glob('*.png')))
    print(f"synced: copied {copied} new; Images/ now holds {total} png")
    # post-copy verification
    still = [d.name for _, d in sources(args.task, img_dir) if not d.exists()]
    if still:
        print(f"WARNING: {len(still)} still missing after copy", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
