#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "tasks/berlin-hotel-base/wave13_regenerate_bridge_crop"
BASE_IMAGE = TASK / "inputs/bridge_piers_work_crop.png"
REF_IMAGE = TASK / "inputs/left_pier_reference_crop.png"


def parse_ids(value: str) -> list[int]:
    ids: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = [int(x) for x in part.split("-", 1)]
            ids.extend(range(lo, hi + 1))
        else:
            ids.append(int(part))
    return ids


def image_size(path: Path) -> list[int] | None:
    try:
        with Image.open(path) as img:
            return [img.width, img.height]
    except Exception:
        return None


def run_one(provider: str, round_id: str, idx: int, timeout: int, retries: int) -> dict:
    prompt = TASK / f"prompts/{round_id}/{provider}/{round_id.replace('round', 'r')}_t{idx:02d}_{provider}.md"
    out = TASK / f"{round_id}/{provider}/{round_id.replace('round', 'r')}_t{idx:02d}_{provider}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        "scripts/subgen.py",
        "--provider",
        provider,
        "--prompt-file",
        str(prompt),
        "--out",
        str(out),
        "-i",
        str(BASE_IMAGE),
        str(REF_IMAGE),
        "--timeout",
        str(timeout),
        "--retries",
        str(retries),
    ]
    started = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    elapsed = round(time.time() - started, 2)
    size = image_size(out)
    return {
        "round": round_id,
        "provider": provider,
        "template_id": idx,
        "prompt_file": str(prompt),
        "output": str(out),
        "status": "ok" if proc.returncode == 0 and size else "failed",
        "returncode": proc.returncode,
        "size": size,
        "elapsed_s": elapsed,
        "stdout_tail": (proc.stdout or "")[-1000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["openai", "nano"], required=True)
    parser.add_argument("--round", dest="round_id", choices=["round1", "round2"], required=True)
    parser.add_argument("--ids", required=True)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    ids = parse_ids(args.ids)
    with args.manifest.open("a") as fh:
        for idx in ids:
            row = run_one(args.provider, args.round_id, idx, args.timeout, args.retries)
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            fh.flush()
            print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
