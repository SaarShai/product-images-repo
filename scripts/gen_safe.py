#!/usr/bin/env python3
"""Race-safe image-generation wrappers for the subscription CLIs (codex / agy).

Why this exists
---------------
`geom_adherence_test.py` currently locates each generation's output file by
globbing the whole output tree and picking the newest by mtime. That is
RACE-UNSAFE: if two generations run against the SAME service concurrently, one
call can grab the other call's image. That forced best-of-N to serialize to
1-per-service.

This module resolves each call's output DETERMINISTICALLY so 4 concurrent gens
per service are safe. Resolution priority (per call):

  (a) Explicit path parsed from THIS call's own stdout/stderr, if the file
      exists. This is the strongest signal because it is emitted by the very
      process we launched.
        * codex prints `session id: <uuid>` on stderr; its image lands in
          `~/.codex/generated_images/<uuid>/` — a per-call unique dir
          (filename patterns live in scripts/codex_images.py).
        * agy prints the exact brain-dir source path in stdout (our prompt asks
          it to).
  (b) SET DIFFERENCE: files present AFTER the call minus files present BEFORE.
      If exactly one new file appeared, use it. (Under concurrency this is only
      trusted when the diff is unambiguous.)
  (c) Newest-after-timestamp — the legacy mtime behavior — as a last resort.

Both functions mirror the signatures/semantics of `geom_adherence_test.py`'s
`gen_codex` / `gen_agy` so they are drop-in replacements.

Empirical evidence captured 2026-06-17 (real runs on this machine):
  codex stderr: `session id: 019ed673-f927-7fe1-8407-840bf77b1641`
                -> an image in ~/.codex/generated_images/019ed673-.../  (existed)
  agy stdout:   `.../antigravity-cli/brain/3d6dba54-.../blue_circle_1781714453127.jpg`
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_images  # noqa: E402 — single source of truth for codex output discovery

AGY_BRAIN = os.path.expanduser("~/.gemini/antigravity-cli/brain")
AGY_EXTS = ("jpg", "jpeg", "png")

# codex prints `session id: <uuid>` on stderr (and again in the transcript).
_CODEX_SID_RE = re.compile(r"session id:\s*([0-9a-fA-F-]{16,})")
# agy prints the absolute brain-dir source path of the image it wrote.
_AGY_PATH_RE = re.compile(
    r"(/[^\s`\"']*antigravity-cli/brain/[^\s`\"']+\.(?:jpg|jpeg|png))"
)


# --------------------------------------------------------------------------- #
# generic helpers
# --------------------------------------------------------------------------- #
def _newest(files) -> str | None:
    files = [f for f in files if os.path.exists(f)]
    return max(files, key=os.path.getmtime) if files else None


# --------------------------------------------------------------------------- #
# codex (OpenAI gpt-image via `codex exec`)
# --------------------------------------------------------------------------- #
def _codex_image_for_session(sid: str) -> str | None:
    """The image written under the per-call session dir, if any."""
    return _newest(codex_images.session_images(codex_images.CODEX_DIR / sid))


def gen_codex_safe(prompt: str, images: list[Path], timeout: int) -> str | None:
    """Race-safe replacement for geom_adherence_test.gen_codex.

    Returns the absolute path of the image this exact invocation produced, or
    None. Safe to run concurrently against codex because resolution keys off
    the per-call session id printed to stderr.
    """
    before = set(codex_images.all_images())
    t0 = time.time() - 1  # epsilon so a same-second write isn't missed
    cmd = ["codex", "exec", "--skip-git-repo-check", "-",
           "-i", *[str(i) for i in images]]
    proc = subprocess.run(
        cmd, input=prompt, text=True, timeout=timeout, capture_output=True
    )
    out, err = proc.stdout or "", proc.stderr or ""

    # (a) explicit signal: the session id -> the per-call image dir.
    for m in _CODEX_SID_RE.finditer(err + "\n" + out):
        hit = _codex_image_for_session(m.group(1))
        if hit:
            return hit

    after = set(codex_images.all_images())

    # (b) set difference: exactly one new image file.
    new = after - before
    if len(new) == 1:
        return next(iter(new))
    if new:
        # multiple new files (concurrent peers) — pick the newest among the
        # ones that appeared during THIS call's window.
        return _newest(new)

    # (c) last resort: newest overall after our start (legacy behavior).
    fresh = [f for f in after if os.path.getmtime(f) >= t0]
    return _newest(fresh) or _newest(after)


# --------------------------------------------------------------------------- #
# agy (Google Nano Banana via `agy --print`)
# --------------------------------------------------------------------------- #
def _agy_glob() -> str:
    return os.path.join(AGY_BRAIN, "*", "*")


def _agy_snapshot() -> set[str]:
    return {
        f for ext in AGY_EXTS
        for f in glob.glob(os.path.join(AGY_BRAIN, "*", f"*.{ext}"))
    }


def gen_agy_safe(prompt: str, images: list[Path], out: Path,
                 timeout: int) -> str | None:
    """Race-safe replacement for geom_adherence_test.gen_agy.

    Mirrors gen_agy: forces the native generate_image tool, asks agy to copy
    the result to `out` AND print the exact brain-dir source path. Returns the
    authoritative brain-dir source path (or `out`/newest as fallback).
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
    before = _agy_snapshot()
    t0 = time.time() - 1
    cmd = ["agy", "--dangerously-skip-permissions", *add, "--print", full]
    proc = subprocess.run(cmd, text=True, timeout=timeout, capture_output=True)
    out_s, err_s = proc.stdout or "", proc.stderr or ""

    # (a) explicit signal: the brain-dir path agy printed.
    for m in _AGY_PATH_RE.finditer(out_s + "\n" + err_s):
        p = m.group(1)
        # Only trust it if it appeared during this call's window (guards against
        # agy echoing a stale path) and the file is actually present.
        if os.path.exists(p) and p not in before and os.path.getmtime(p) >= t0:
            return p

    after = _agy_snapshot()

    # (b) set difference: exactly one new brain-dir image.
    new = after - before
    if len(new) == 1:
        return next(iter(new))
    if new:
        return _newest(new)

    # (c) last resorts: the copied output, then newest brain image after t0.
    if out.exists():
        return str(out)
    fresh = [f for f in after if os.path.getmtime(f) >= t0]
    return _newest(fresh) or _newest(after)
