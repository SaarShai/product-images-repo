#!/usr/bin/env python3
"""Write generation render-trace JSON records for style-bible renders."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def build_render_trace(
    bible_path: str | Path,
    prompt_text: str,
    refs: Iterable[dict[str, str] | tuple[str, str]],
    engine: str,
    params: dict[str, Any],
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a render trace dict without writing it."""
    bible = Path(bible_path)
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    bible_data = _load_bible(bible)
    bible_version = bible_data.get("bible_version")
    if not isinstance(bible_version, int):
        raise ValueError(f"{bible} does not contain an integer bible_version")

    normalized_refs = []
    for ref in refs:
        role, ref_path = _normalize_ref(ref)
        resolved = resolve_ref_path(ref_path, bible, root)
        if resolved is None:
            raise FileNotFoundError(f"ref file not found for role {role}: {ref_path}")
        normalized_refs.append(
            {
                "path": ref_path,
                "sha256": sha256_file(resolved),
                "role": role,
            }
        )

    return {
        "bible_version": bible_version,
        "bible_sha256": sha256_file(bible),
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "prompt_text": prompt_text,
        "refs": normalized_refs,
        "engine": engine,
        "params": params,
    }


def write_render_trace(
    bible_path: str | Path,
    prompt_text: str,
    refs: Iterable[dict[str, str] | tuple[str, str]],
    engine: str,
    params: dict[str, Any],
    out_path: str | Path,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build and write a render trace JSON file, returning the written payload."""
    trace = build_render_trace(
        bible_path=bible_path,
        prompt_text=prompt_text,
        refs=refs,
        engine=engine,
        params=params,
        repo_root=repo_root,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bible", help="Path to bible YAML")
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt-text", help="Rendered prompt text")
    prompt.add_argument("--prompt-file", help="File containing rendered prompt text")
    parser.add_argument(
        "--ref",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="Attached reference path with role; may be repeated",
    )
    parser.add_argument(
        "--refs-json",
        help='JSON list of {"role": "...", "path": "..."} refs',
    )
    parser.add_argument("--engine", required=True, help="Generation engine name")
    parser.add_argument(
        "--params",
        default="{}",
        help="Extra render params as a JSON object",
    )
    parser.add_argument("--out", required=True, help="Output trace JSON path")
    args = parser.parse_args(argv)

    prompt_text = (
        Path(args.prompt_file).read_text(encoding="utf-8")
        if args.prompt_file
        else args.prompt_text
    )
    params = json.loads(args.params)
    if not isinstance(params, dict):
        raise ValueError("--params must decode to a JSON object")

    refs = _parse_cli_refs(args.ref, args.refs_json)
    write_render_trace(
        bible_path=args.bible,
        prompt_text=prompt_text,
        refs=refs,
        engine=args.engine,
        params=params,
        out_path=args.out,
    )
    return 0


def sha256_file(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_ref_path(
    ref: str, bible_path: Path, repo_root: str | Path | None = None
) -> Path | None:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    raw = Path(ref)
    candidates = [raw] if raw.is_absolute() else []
    if not raw.is_absolute():
        candidates.extend(
            [
                bible_path.parent / raw,
                bible_path.parent.parent / raw,
                root / raw,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _load_bible(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return data


def _parse_cli_refs(ref_args: list[str], refs_json: str | None) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for raw in ref_args:
        if "=" not in raw:
            raise ValueError(f"--ref must be ROLE=PATH, got {raw!r}")
        role, path = raw.split("=", 1)
        refs.append({"role": role, "path": path})

    if refs_json:
        decoded = json.loads(refs_json)
        if not isinstance(decoded, list):
            raise ValueError("--refs-json must decode to a list")
        for item in decoded:
            if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not isinstance(item.get("path"), str):
                raise ValueError("--refs-json items must contain string role and path")
            refs.append({"role": item["role"], "path": item["path"]})

    return refs


def _normalize_ref(ref: dict[str, str] | tuple[str, str]) -> tuple[str, str]:
    if isinstance(ref, dict):
        role = ref.get("role")
        path = ref.get("path")
    else:
        role, path = ref
    if not isinstance(role, str) or not role:
        raise ValueError(f"ref has invalid role: {ref!r}")
    if not isinstance(path, str) or not path:
        raise ValueError(f"ref has invalid path: {ref!r}")
    return role, path


if __name__ == "__main__":
    raise SystemExit(main())
