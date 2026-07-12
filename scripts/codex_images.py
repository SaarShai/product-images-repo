#!/usr/bin/env python3
"""Single source of truth for locating codex CLI generated-image files.

`codex exec` writes each generation into a per-call session dir under
~/.codex/generated_images/<session-id>/. The FILENAME prefix is a codex
implementation detail that has already changed once (~2026-07) and silently
broke every script that carried its own hardcoded glob. All discovery
therefore goes through this module: when the CLI renames again, extend
CODEX_IMAGE_PATTERNS here and every consumer follows.

scripts/test_codex_images.py fails if any script under scripts/ reintroduces
a hardcoded codex image filename glob instead of using this helper.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

CODEX_DIR = Path.home() / ".codex" / "generated_images"

# Every filename pattern the codex CLI has used for generated images,
# oldest first ("ig_" prefix historically, "exec-" since ~2026-07).
CODEX_IMAGE_PATTERNS = ("ig_*.png", "exec-*.png")


def session_images(session_dir: Path | str) -> list[str]:
    """All generated images inside ONE per-call session dir (unsorted)."""
    d = Path(session_dir)
    return [str(p) for pat in CODEX_IMAGE_PATTERNS for p in d.glob(pat)]


def all_images(base: Path | str = CODEX_DIR) -> list[str]:
    """All generated images across every session dir under `base`."""
    return [f for pat in CODEX_IMAGE_PATTERNS
            for f in glob.glob(str(Path(base) / "*" / pat))]


def newest_image(base: Path | str = CODEX_DIR) -> str | None:
    """Most recently written generated image under `base`, if any."""
    files = all_images(base)
    return max(files, key=os.path.getmtime) if files else None
