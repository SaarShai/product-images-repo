#!/usr/bin/env python3
"""Verify outputs from object_recovery_image14.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image

from object_recovery_image14 import BASELINE_CANDIDATE, OUT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify object-aware recovery candidates for image14."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=OUT_ROOT / "manifest.json",
        help="Path to manifest JSON from object_recovery_image14.py",
    )
    return parser.parse_args()


def resolve_path(entry_path: Any, fallback: Path) -> Path | None:
    if not isinstance(entry_path, str) or not entry_path:
        return None
    p = Path(entry_path)
    if p.is_absolute():
        return p
    return (fallback / p).resolve()


def load_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def alpha_is_binary(alpha: np.ndarray) -> tuple[bool, int]:
    arr = alpha.ravel()
    semi = int(((arr > 0) & (arr < 255)).sum())
    return semi == 0, semi


def normalize_candidates(manifest: Any) -> list[Mapping[str, Any]]:
    if isinstance(manifest, Mapping):
        value = manifest.get("candidates", manifest.get("items", manifest.get("entries", [])))
        if isinstance(value, list):
            return [entry for entry in value if isinstance(entry, Mapping)]
        return []
    if isinstance(manifest, list):
        return [entry for entry in manifest if isinstance(entry, Mapping)]
    return []


def get_expected_size(manifest: Mapping[str, Any], fallback: Path) -> tuple[int, int] | None:
    if manifest.get("baseline_alpha", {}).get("size"):
        width, height = manifest["baseline_alpha"]["size"]
        try:
            return int(width), int(height)
        except Exception:
            pass
    if isinstance(manifest.get("baseline"), str):
        base = Path(manifest["baseline"])
        if not base.is_absolute():
            base = (fallback / base).resolve()
        try:
            with Image.open(base) as im:
                return im.size
        except OSError:
            return None
    return None


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.exists():
        print(f"FAIL: manifest missing: {manifest_path}")
        return 1

    manifest_root = manifest_path.parent
    manifest = load_manifest(manifest_path)
    if not isinstance(manifest, (dict, list)):
        print("FAIL: manifest format unsupported")
        return 1

    entries = normalize_candidates(manifest)
    if not entries:
        print("FAIL: manifest contains no candidate entries")
        return 1

    expected_size = get_expected_size(manifest, manifest_root) if isinstance(manifest, dict) else None
    if expected_size is None:
        expected_size = (None, None)

    ok = True
    nonempty = 0
    for idx, entry in enumerate(entries, start=1):
        candidate_path = resolve_path(entry.get("candidate_rgba"), manifest_root)
        if candidate_path is None:
            candidate_path = resolve_path(entry.get("candidate"), manifest_root)
        if candidate_path is None:
            candidate_path = resolve_path(entry.get("path"), manifest_root)
        if candidate_path is None:
            print(f"FAIL[{idx}]: missing candidate path in manifest")
            ok = False
            continue
        if not candidate_path.exists():
            print(f"FAIL[{idx}]: candidate missing: {candidate_path}")
            ok = False
            continue

        try:
            with Image.open(candidate_path) as im:
                if im.mode != "RGBA":
                    print(f"FAIL[{idx}]: candidate not RGBA: {candidate_path} mode={im.mode}")
                    ok = False
                    continue
                if expected_size[0] is not None and im.size != expected_size:
                    print(
                        f"FAIL[{idx}]: size mismatch for {candidate_path}: "
                        f"got={im.size} expected={expected_size}"
                    )
                    ok = False
                    continue
                alpha = np.asarray(im.getchannel("A"))
                binary, semi_px = alpha_is_binary(alpha)
                if not binary:
                    print(
                        f"FAIL[{idx}]: non-binary alpha for {candidate_path}: semi_alpha_px={semi_px}"
                    )
                    ok = False
                if int(alpha.sum()) <= 0:
                    print(f"FAIL[{idx}]: empty alpha for {candidate_path}")
                    ok = False
                else:
                    nonempty += 1
        except OSError as exc:
            print(f"FAIL[{idx}]: cannot read {candidate_path}: {exc}")
            ok = False

    if nonempty == 0:
        print("FAIL: no non-empty candidates")
        ok = False

    print(f"manifest: {manifest_path}")
    print(f"candidates-checked: {len(entries)}")
    print(f"candidates-nonempty: {nonempty}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
