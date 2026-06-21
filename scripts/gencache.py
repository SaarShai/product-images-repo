#!/usr/bin/env python3
"""gencache.py — content-addressed cache for image-gen API calls.

Key = sha256 of all inputs that determine the output (image bytes, mask bytes, prompt,
engine/mode, seed, params). If a result for that key exists, reuse it for FREE instead of
paying for an identical call. Safe ONLY for deterministic calls — caller must pass a fixed
seed for stochastic engines (or opt-in knowingly).

Used as a library by falgen.py / automask.py (and any wrapper):
    from gencache import cache_key, cache_get, cache_put
    k = cache_key("falfill", img_bytes, mask_bytes, prompt, seed, ...)
    hit = cache_get(k)
    if hit: shutil.copy(hit, out); ...
    else: <run api>; cache_put(k, out)

CLI (inspect/stats):
    python3 scripts/gencache.py stats
"""
import hashlib
import shutil
import sys
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "gen"


def _to_bytes(p):
    if isinstance(p, bytes):
        return p
    if isinstance(p, Path):
        return p.read_bytes()
    if isinstance(p, str):
        # treat as a possible file path only if short enough to BE a path
        # (a long prompt string would raise OSError "File name too long")
        if len(p) < 250:
            try:
                fp = Path(p)
                if fp.exists() and fp.is_file():
                    return fp.read_bytes()
            except OSError:
                pass
        return p.encode()
    return repr(p).encode()


def cache_key(*parts):
    h = hashlib.sha256()
    for p in parts:
        b = _to_bytes(p)
        h.update(len(b).to_bytes(8, "big"))  # length-prefix to avoid boundary collisions
        h.update(b)
    return h.hexdigest()


def cache_get(key, ext="png"):
    f = CACHE_DIR / f"{key}.{ext}"
    return f if f.exists() else None


def cache_put(key, src, ext="png"):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dst = CACHE_DIR / f"{key}.{ext}"
    shutil.copy(src, dst)
    return dst


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        files = list(CACHE_DIR.glob("*")) if CACHE_DIR.exists() else []
        tot = sum(f.stat().st_size for f in files)
        print(f"[gencache] {CACHE_DIR}  entries={len(files)}  size={tot/1e6:.1f}MB")
    else:
        print(__doc__)
