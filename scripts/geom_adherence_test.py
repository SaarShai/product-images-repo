#!/usr/bin/env python3
"""Run ONE geometry-adherence experiment row: generate -> auto-register -> measure -> record.

Measures the MODEL'S OWN output (no compositing) so methods are compared on how
well the model itself adhered to the geometry. Auto-detects the panel bounding
box from the non-white region, so it works regardless of the output size/placement.

Usage:
  geom_adherence_test.py --id E2-magenta --model openai \
     --map MAP.png --prompt PROMPT.md --refs R1.png R2.png \
     --svg template.svg --outdir tasks/<task>/experiments [--bbox L,T,R,B] [--timeout 300]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_images  # noqa: E402 — single source of truth for codex output discovery


def newest_codex_image() -> str | None:
    return codex_images.newest_image()


def _killpg_quiet(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except OSError:
        pass  # group gone, or zombie/reparented member we can't re-signal


def _run_group(cmd: list[str], timeout: int, input_text: str | None = None) -> None:
    """Run `cmd` in its OWN process group and tear the WHOLE group down on exit.

    Why not plain subprocess.run(..., timeout=...): on TimeoutExpired the run helper
    SIGKILLs only the direct child. The codex/agy CLIs are node wrappers that fork a
    native binary (codex's vendor bin); that grandchild gets reparented to PID 1 and
    keeps running. A surviving codex would then race a retry's fresh `codex exec` and
    corrupt/misattribute generated images (the image picker is not concurrency-safe).

    start_new_session=True makes the child a session+group leader, so its PGID == its
    PID and every descendant inherits that PGID. We always killpg the group (TERM then
    KILL) in `finally`, so nothing in the group can outlive this call — on timeout OR
    on a clean return that still left a stray child behind.
    """
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    pgid = proc.pid  # == process-group id because start_new_session called setsid()
    try:
        proc.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # whole group already gone (clean exit) — skip escalation
        except OSError:
            _killpg_quiet(pgid, signal.SIGKILL)  # e.g. EPERM on a zombie member
        else:
            time.sleep(0.3)
            _killpg_quiet(pgid, signal.SIGKILL)
        try:
            proc.communicate(timeout=5)  # reap the leader
        except (subprocess.TimeoutExpired, ValueError):
            proc.kill()


def gen_codex(prompt: str, images: list[Path], timeout: int) -> str | None:
    before = newest_codex_image()
    cmd = ["codex", "exec", "--skip-git-repo-check", "-", "-i", *[str(i) for i in images]]
    _run_group(cmd, timeout, input_text=prompt)
    after = newest_codex_image()
    return after if (after and after != before) else None


def newest_agy_image(after_ts: float) -> str | None:
    """agy's native generate_image tool writes to ~/.gemini/antigravity-cli/brain/<uuid>/<slug>_<ts>.jpg
    (always JPEG, regardless of requested extension). Find the newest one created after `after_ts`."""
    base = os.path.expanduser("~/.gemini/antigravity-cli/brain")
    files = [
        f for ext in ("jpg", "jpeg", "png")
        for f in glob.glob(os.path.join(base, "*", f"*.{ext}"))
        if os.path.getmtime(f) >= after_ts
    ]
    return max(files, key=os.path.getmtime) if files else None


def gen_agy(prompt: str, images: list[Path], out: Path, timeout: int) -> str | None:
    """Generate via agy's NATIVE generate_image tool (Nano Banana / Gemini image).

    IMPORTANT: agy is a coding agent. If the prompt invites it, it will fall back to
    writing Pillow/matplotlib code instead of calling the real image model. We therefore
    explicitly force the generate_image tool and forbid code. The native tool writes a
    JPEG into ~/.gemini/antigravity-cli/brain/<uuid>/; agy then copies it to `out`, but we
    also locate the brain-dir source as the authoritative fallback.
    """
    dirs = {str(Path(i).resolve().parent) for i in images} | {str(out.parent.resolve())}
    add: list[str] = []
    for d in dirs:
        add += ["--add-dir", d]
    full = (
        "You are an image-generation operator. Use ONLY your built-in generate_image tool "
        "(the Nano Banana / Gemini image model) to synthesize ONE high-resolution image. "
        "Request the highest resolution / 2K quality available and reason explicitly about "
        "the layout before generating. Do NOT write Python, Pillow, matplotlib, or any code, "
        "and do NOT just composite the inputs — actually generate a new illustration.\n\n"
        + prompt
        + f"\n\nComposition base image (the layout CONTRACT) — pass this as the primary "
        f"base/input image to generate_image: {images[0].resolve()}\n"
        + "Style reference images to also pass to generate_image: "
        + ", ".join(str(i.resolve()) for i in images[1:])
        + "\n\nThe attached layout is a tall, narrow portrait panel — call generate_image "
        "with AspectRatio='9:16' (the tallest option the tool supports) so the panel "
        "proportions and opening spacing match the base; do not squash it to a squarer frame."
        + f"\n\nAfter generate_image returns, copy the produced file to {out.resolve()} "
        "and print the exact source path the tool wrote it to."
    )
    t0 = time.time() - 1  # small epsilon so a same-second write isn't missed
    cmd = ["agy", "--dangerously-skip-permissions", *add, "--print", full]
    _run_group(cmd, timeout)
    # Authoritative: the native tool's brain-dir JPEG written during this run.
    brain = newest_agy_image(t0)
    if brain:
        return brain
    if out.exists():
        return str(out)
    # last resort: newest image agy left in the output dir
    cand = sorted(
        (p for ext in ("png", "jpg", "jpeg") for p in out.parent.glob(f"*.{ext}")),
        key=os.path.getmtime, reverse=True,
    )
    return str(cand[0]) if cand else None


def auto_bbox(path: Path) -> tuple[int, int, int, int]:
    arr = np.asarray(Image.open(path).convert("RGB"))
    nonwhite = np.any(arr < 240, axis=2)
    ys, xs = np.where(nonwhite)
    if len(xs) == 0:
        h, w = arr.shape[:2]
        return (0, 0, w, h)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--model", choices=["openai", "nanobanana"], default="openai")
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--prompt", required=True, type=Path)
    ap.add_argument("--refs", nargs="*", type=Path, default=[])
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--bbox", help="L,T,R,B in the gen image; default = auto-detect panel")
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    if not a.refs:
        raise SystemExit("style.ref_images must contain at least one path")

    exp = (a.outdir if a.outdir.is_absolute() else ROOT / a.outdir) / a.id
    exp.mkdir(parents=True, exist_ok=True)
    prompt = (a.prompt if a.prompt.is_absolute() else ROOT / a.prompt).read_text()
    images = [a.map, *a.refs]
    t0 = time.time()

    # Single, verified, always-working subscription gen path (subgen.py):
    # own process group + killpg on timeout (no orphans), deterministic per-call
    # output discovery (no picker races), forced-image + retry, validated output.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from subgen import gen_openai, gen_nano
    try:
        if a.model == "openai":
            produced = str(gen_openai(prompt, images, exp / "raw.png", a.timeout, retries=3))
        else:
            produced = str(gen_nano(prompt, images, exp / "raw.png", a.timeout, retries=3))
    except Exception as ex:  # noqa: BLE001
        print(f"{a.id}: subgen failed: {ex}", file=sys.stderr)
        produced = None

    if not produced:
        rec = {"id": a.id, "model": a.model, "error": "no image produced"}
        (exp / "result.json").write_text(json.dumps(rec, indent=2))
        print(f"{a.id:26s} model={a.model:11s} ERROR no image")
        return 1

    raw = exp / "raw.png"
    if Path(produced).resolve() != raw.resolve():
        shutil.copy(produced, raw)
    bbox = a.bbox or ",".join(str(v) for v in auto_bbox(raw))

    check = subprocess.run(
        [sys.executable, "scripts/svg_geometry_check.py", str(raw), "--svg", str(a.svg),
         "--bbox", bbox, "--out-overlay", str(exp / "overlay.png"), "--json-out", str(exp / "metrics.json")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if check.returncode != 0:
        # Surface the guard message instead of letting it be swallowed by
        # capture_output — a bare crash here previously masked itself as a
        # downstream FileNotFoundError when metrics.json was never written
        # (geometry-evidentiary-princess-n02 Finding A).
        raise SystemExit(
            f"{a.id}: svg_geometry_check.py failed (exit {check.returncode}):\n{check.stderr}"
        )
    m = json.loads((exp / "metrics.json").read_text())
    m.update({"id": a.id, "model": a.model, "bbox": bbox, "secs": round(time.time() - t0, 1),
              "map": str(a.map), "prompt": str(a.prompt)})
    (exp / "result.json").write_text(json.dumps(m, indent=2))
    maxpaint = max((h["painted_frac"] for h in m["holes"]), default=0.0)
    print(f"{a.id:26s} model={a.model:11s} mean_iou={m['mean_iou']:.3f} maxpaint={maxpaint:.3f} "
          f"outside={m['outside_frac']:.1%} overall={m['overall']} {m['secs']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
