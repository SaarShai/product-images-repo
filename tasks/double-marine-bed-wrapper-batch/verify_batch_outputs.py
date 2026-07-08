#!/usr/bin/env python3
"""Lightweight verifier for double Marine Bed Wrapper batch outputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify double Marine Bed Wrapper batch final PNGs against source manifest."
    )
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest JSON")
    parser.add_argument(
        "--source-dir", required=True, type=Path, help="Directory containing source images"
    )
    parser.add_argument(
        "--final-dir", required=True, type=Path, help="Directory containing final PNG outputs"
    )
    return parser.parse_args()


def load_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_file(base: Path, value: Any) -> Path | None:
    if not value or not isinstance(value, str):
        return None
    p = Path(value)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def normalize_entries(manifest: Any) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    meta: Mapping[str, Any]
    if isinstance(manifest, list):
        return manifest, {}
    if isinstance(manifest, dict):
        for key in ("entries", "rows", "files", "items"):
            if isinstance(manifest.get(key), list):
                return manifest[key], manifest
        raise ValueError("Manifest must contain an entries/rows/files/items array.")
    raise TypeError("Manifest must be a JSON object or array.")


def _entry_source_path(
    entry: Mapping[str, Any], source_dir: Path, manifest_dir: Path
) -> Path | None:
    for key in ("source", "source_path", "source_file", "src", "input", "input_path"):
        value = entry.get(key)
        if not value or not isinstance(value, str):
            continue
        resolved = resolve_file(source_dir, value)
        if resolved is not None:
            return resolved
        resolved = resolve_file(manifest_dir, value)
        if resolved is not None:
            return resolved
    return None


def _entry_final_path(entry: Mapping[str, Any], final_dir: Path, manifest_dir: Path) -> Path | None:
    for key in ("final", "final_path", "final_file", "output", "output_path"):
        value = entry.get(key)
        if not value or not isinstance(value, str):
            continue
        resolved = resolve_file(final_dir, value)
        if resolved is not None:
            return resolved
        resolved = resolve_file(manifest_dir, value)
        if resolved is not None:
            return resolved
    return None


@dataclass
class CheckResult:
    source: Path
    final: Path
    ok: bool
    details: list[str]


def _entry_allow_alpha_exception(entry: Mapping[str, Any], manifest_root: Mapping[str, Any]) -> bool:
    keys = (
        "allow_semi_transparent_alpha",
        "allow_semi_transparent",
        "allow_partial_alpha",
        "allow_non_binary_alpha",
    )
    for key in keys:
        if key in entry and isinstance(entry.get(key), bool):
            return bool(entry.get(key))
        if key in manifest_root and isinstance(manifest_root.get(key), bool):
            return bool(manifest_root.get(key))
    return False


def _entry_eligible(entry: Mapping[str, Any]) -> bool:
    if "eligible" in entry:
        return bool(entry.get("eligible", True))
    if "skip" in entry:
        return not bool(entry.get("skip"))
    return True


def check_pair(
    source: Path, final: Path, allow_semi_alpha: bool
) -> list[str]:
    failures: list[str] = []

    if not source.exists():
        failures.append(f"source missing: {source}")
        return failures
    if not final.exists():
        failures.append(f"final missing: {final}")
        return failures

    try:
        with Image.open(source) as src_img, Image.open(final) as final_img:
            if final_img.width != src_img.width * 8 or final_img.height != src_img.height * 8:
                failures.append(
                    f"size mismatch: source=({src_img.width}x{src_img.height}) final=({final_img.width}x{final_img.height})"
                )

            final_bands = final_img.getbands()
            if "A" not in final_bands:
                failures.append(f"final lacks alpha channel: mode={final_img.mode}")
                return failures

            alpha = final_img.getchannel("A")
            if not allow_semi_alpha:
                alpha_hist = alpha.histogram()
                if sum(alpha_hist[1:255]) > 0:
                    failures.append("final has semi-transparent alpha pixels (non-binary alpha)")

            if alpha.getbbox() is None:
                failures.append("final nontransparent bbox is empty")
    except OSError as err:
        failures.append(f"image read error: {err}")
    return failures


def verify_manifest(
    manifest_path: Path,
    source_dir: Path,
    final_dir: Path,
) -> list[CheckResult]:
    manifest = load_manifest(manifest_path)
    entries, root = normalize_entries(manifest)
    manifest_dir = manifest_path.parent
    final_dir = final_dir.resolve()

    results: list[CheckResult] = []
    for index, raw_entry in enumerate(entries, start=1):
        if not isinstance(raw_entry, Mapping):
            continue
        if not _entry_eligible(raw_entry):
            continue

        source = _entry_source_path(raw_entry, source_dir, manifest_dir)
        final = _entry_final_path(raw_entry, final_dir, manifest_dir)

        if source is None:
            results.append(
                CheckResult(
                    source=Path(f"<entry-{index}>"),
                    final=Path("<missing>"),
                    ok=False,
                    details=["missing source field"],
                )
            )
            continue
        if final is None:
            results.append(
                CheckResult(
                    source=source,
                    final=Path("<missing>"),
                    ok=False,
                    details=["missing final field"],
                )
            )
            continue

        source = source if source.is_absolute() else source.resolve()
        final = final if final.is_absolute() else final.resolve()
        if not source.is_relative_to(source_dir):
            results.append(
                CheckResult(
                    source=source,
                    final=Path(f"<missing>"),
                    ok=False,
                    details=["source path not under source-dir"],
                )
            )
            continue

        details = check_pair(source, final, _entry_allow_alpha_exception(raw_entry, root))
        in_final_dir = final.is_relative_to(final_dir)
        if not in_final_dir:
            details.append(f"final path outside final-dir: {final} not under {final_dir}")

        results.append(CheckResult(source=source, final=final, ok=not details, details=details))

    return results


def main() -> int:
    args = parse_args()
    manifest = args.manifest.expanduser().resolve()
    source_dir = args.source_dir.expanduser().resolve()
    final_dir = args.final_dir.expanduser().resolve()

    if not manifest.exists():
        print(f"FAIL: manifest not found: {manifest}")
        return 1
    if not source_dir.is_dir():
        print(f"FAIL: source-dir invalid: {source_dir}")
        return 1
    if not final_dir.is_dir():
        print(f"FAIL: final-dir invalid: {final_dir}")
        return 1

    results = verify_manifest(manifest, source_dir, final_dir)
    if not results:
        print("FAIL: manifest has no eligible entries to verify")
        return 1

    total = len(results)
    passed = sum(1 for r in results if r.ok)
    failed = total - passed

    for item in results:
        if item.ok:
            continue
        print(f"FAIL: {item.source} -> {item.final}")
        for detail in item.details:
            print(f"  - {detail}")

    status = "PASS" if failed == 0 else "FAIL"
    print(f"{status}: {passed}/{total} entries passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
