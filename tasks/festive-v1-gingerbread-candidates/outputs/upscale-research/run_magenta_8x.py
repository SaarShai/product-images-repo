#!/usr/bin/env python3
"""Full 8x cream pipeline for one magenta cutout:
  magenta→cream → downsample(~240 short) → clarity 4x → clarity 2x texture → cream final
No transparent keying.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import importlib.util

REPO = next(p for p in Path(__file__).resolve().parents if (p / "scripts" / "reupscale.py").exists())
VENV = REPO / ".venv-gen" / "bin" / "python"
REUPSCALE = REPO / "scripts" / "reupscale.py"
PIPE_PATH = Path(__file__).resolve().parent / "clarity_magenta_pipeline.py"

spec = importlib.util.spec_from_file_location("pipe", PIPE_PATH)
pipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipe)

PROMPT_4X = pipe.PROMPT
NEG = pipe.NEG
PROMPT_2X = (
    "gingerbread cookie cutout, thick white piped royal icing border, "
    "holly leaves with visible veins, glossy red berries, sugary candy ornaments "
    "with specular highlights, fine baked cookie crumb texture, crisp watercolor "
    "illustration detail, sharp clean edges, masterpiece, best quality"
)
NEG_2X = NEG + ", muddy, waxy"


def clarity(inp: Path, out: Path, factor: float, creativity: float, resemblance: float, prompt: str, steps: int) -> None:
    cmd = [
        str(VENV), str(REUPSCALE),
        "--image", str(inp), "--out", str(out),
        "--factor", str(factor),
        "--creativity", str(creativity),
        "--resemblance", str(resemblance),
        "--steps", str(steps),
        "--prompt", prompt,
        "--neg", NEG_2X if factor <= 2.5 else NEG,
    ]
    print("[8x]", " ".join(cmd[:8]), f"f={factor} c={creativity} r={resemblance}", flush=True)
    subprocess.check_call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--target-short", type=int, default=240)
    ap.add_argument("--copy", action="append", default=[])
    a = ap.parse_args()

    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    slug = a.slug

    cream = work / f"{slug}-cream.png"
    small = work / f"{slug}-cream-small.png"
    c4 = work / f"{slug}-clarity-4x.png"
    c8 = work / f"{slug}-clarity-8x.png"  # final cream RGB
    preview = work / f"{slug}-clarity-8x-preview.png"  # same as c8 for cream

    info = pipe.magenta_to_cream(Path(a.src), cream)
    ds = pipe.maybe_downsample(cream, small, a.target_short)
    print("cream", info["size"], "small", ds["size"], flush=True)

    clarity(small, c4, factor=4.0, creativity=0.25, resemblance=0.85, prompt=PROMPT_4X, steps=22)
    clarity(c4, c8, factor=2.0, creativity=0.4, resemblance=0.75, prompt=PROMPT_2X, steps=24)

    # preview is cream already
    shutil.copy2(c8, preview)

    from PIL import Image
    w, h = Image.open(c8).size
    print("DONE", slug, "8x", f"{w}x{h}", "final", c8, flush=True)

    for d in a.copy:
        dest = Path(d)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(c8, dest / c8.name)
        shutil.copy2(preview, dest / preview.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
