#!/usr/bin/env python3
"""Concurrency self-test for scripts/gen_safe.py.

Launches 2 CONCURRENT codex calls AND 2 concurrent agy calls, each with a
DISTINCT trivial prompt, then asserts every call resolved a DISTINCT, correct
file (no cross-assignment).

How "correct attribution" is proven per service:
  * codex — resolution keys off the per-call `session id` printed on stderr,
    and the image lives in `~/.codex/generated_images/<session_id>/`. We assert
    (i) the two codex calls resolved files in DIFFERENT session dirs, and
    (ii) each resolved path is the only ig_*.png in its own session dir. The
    session id is minted by codex per invocation, so a swap is structurally
    impossible — this is a stronger check than model-rendered colour (gpt-image
    does not reliably honour "make it solid red" for trivial swatch prompts).
  * agy — resolution keys off the exact brain-dir path agy PRINTS for the image
    it just wrote. agy honours flat-colour prompts, so we additionally verify
    each resolved image's dominant colour matches what THAT call asked for.

Trivial prompts, cheap generations; all temp inputs/outputs cleaned up.

Run:  python3 scripts/test_gen_safe.py
Exit: 0 = all distinct & correctly attributed, 1 = failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_safe import gen_agy_safe, gen_codex_safe  # noqa: E402

TIMEOUT = 360
# (label, RGB, human colour name) — distinct, easy to discriminate.
CODEX_JOBS = [("codexRED", (220, 30, 30), "pure bright RED"),
              ("codexBLUE", (30, 30, 220), "pure bright BLUE")]
AGY_JOBS = [("agyGREEN", (30, 200, 30), "pure bright GREEN"),
            ("agyYELLOW", (230, 220, 30), "pure bright YELLOW")]


def dominant_rgb(path: str) -> tuple[int, int, int]:
    arr = np.asarray(Image.open(path).convert("RGB")).reshape(-1, 3)
    return tuple(int(v) for v in arr.mean(axis=0))


def closest(rgb, palette):
    return min(palette, key=lambda c: sum((a - b) ** 2 for a, b in zip(rgb, c[1])))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gen_safe_test_"))
    # one trivial neutral input image (codex requires -i; agy uses a base too)
    seed = tmp / "seed.png"
    Image.new("RGB", (64, 64), (128, 128, 128)).save(seed)

    results: dict[str, str | None] = {}

    def run_codex(job):
        label, _rgb, name = job
        prompt = (f"Generate ONE tiny solid {name} 64x64 PNG image, "
                  f"a single flat fill of that colour. Just produce one image.")
        return label, gen_codex_safe(prompt, [seed], TIMEOUT)

    def run_agy(job):
        label, _rgb, name = job
        out = tmp / f"{label}.png"
        prompt = (f"Generate ONE tiny simple image that is a solid flat fill of "
                  f"{name}, nothing else.")
        return label, gen_agy_safe(prompt, [seed], out, TIMEOUT)

    print("Launching 2 concurrent codex + 2 concurrent agy generations...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = ([ex.submit(run_codex, j) for j in CODEX_JOBS]
                + [ex.submit(run_agy, j) for j in AGY_JOBS])
        for f in futs:
            label, path = f.result()
            results[label] = path
            print(f"  {label:12s} -> {path}")

    ok = True

    # 1) every call resolved an existing path
    for label, path in results.items():
        if not path or not Path(path).exists():
            print(f"FAIL: {label} resolved no existing file ({path})")
            ok = False

    # 2) all four paths distinct (no sharing)
    paths = [p for p in results.values() if p]
    if len(set(paths)) != len(paths):
        print(f"FAIL: duplicate path assignment -> {paths}")
        ok = False
    else:
        print("PASS: all resolved paths are distinct")

    # 3a) codex — structural attribution via unique per-call session dir.
    codex_paths = [results[l] for l, *_ in CODEX_JOBS if results.get(l)]
    sess_dirs = [Path(p).parent for p in codex_paths]
    if len(set(map(str, sess_dirs))) == len(sess_dirs) == len(CODEX_JOBS):
        print(f"PASS: codex calls landed in distinct session dirs "
              f"{[d.name for d in sess_dirs]}")
    else:
        print(f"FAIL: codex session dirs not distinct -> {sess_dirs}")
        ok = False
    for label in (l for l, *_ in CODEX_JOBS):
        p = results.get(label)
        if not p:
            continue
        siblings = list(Path(p).parent.glob("ig_*.png"))
        if siblings != [Path(p)]:
            print(f"FAIL: {label} session dir holds {len(siblings)} images, "
                  f"resolution ambiguous -> {siblings}")
            ok = False
        else:
            print(f"  codex {label:12s} sole image in dir {Path(p).parent.name} [OK]")

    # 3b) agy — content attribution (agy honours flat-colour prompts).
    palette = AGY_JOBS
    by_label = {l: (rgb, name) for l, rgb, name in AGY_JOBS}
    for label in (l for l, *_ in AGY_JOBS):
        path = results.get(label)
        if not path or not Path(path).exists():
            continue
        rgb = dominant_rgb(path)
        match = closest(rgb, palette)
        want_rgb = by_label[label][0]
        got_label = match[0]
        verdict = "OK" if got_label == label else "MISMATCH"
        if got_label != label:
            ok = False
        print(f"  agy   {label:12s} dom={rgb} nearest={got_label:12s} "
              f"want~{want_rgb} [{verdict}]")

    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT:", "PASS — no cross-assignment" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
