#!/usr/bin/env python3
"""_falcommon.py — shared secret-loading + image-encoding helpers for the fal/openai wrapper family.

Consolidates three helpers that were copy-pasted (and had drifted) across the wrappers:
  - load_fal_key()    : was duplicated in automask/falgen/qwen_edit/reupscale/falbatch/falref_apply
                        + inlined in bg_remove (a next() variant with no env check). falref_apply's
                        copy omitted the FAL_KEY env-var check entirely — fixed here (env first).
  - load_openai_key() : was duplicated in judge/openai_edit.
  - data_uri(img)     : PIL-Image -> base64 PNG data URI; was duplicated in automask/falgen/qwen_edit.
                        (judge.py has a DIFFERENT data_uri(path, maxside) that downsamples a FILE —
                        that one is intentionally NOT consolidated here.)

Keys are read from env first, then .secrets/<name>.env at the repo root; never printed. Both branches
.strip() the value (callers previously differed on this).
"""
import base64
import io
import os
from pathlib import Path

_SECRETS = Path(__file__).resolve().parent.parent / ".secrets"


def _load_key(var: str, env_file: str) -> str:
    k = os.environ.get(var)
    if k:
        return k.strip()
    env = _SECRETS / env_file
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(var + "="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"no {var} (set env or .secrets/{env_file})")


def load_fal_key() -> str:
    return _load_key("FAL_KEY", "fal.env")


def load_openai_key() -> str:
    return _load_key("OPENAI_API_KEY", "openai.env")


def data_uri(img) -> str:
    """PIL Image -> base64 PNG data URI."""
    b = io.BytesIO()
    img.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
