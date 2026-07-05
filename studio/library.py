"""Append-only content-addressed results library."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def add_result(lib_dir, src_image_path, meta):
    """Add an image result to the library and return its content id."""
    if not isinstance(meta, dict):
        raise TypeError("meta must be a dict")

    lib_path = Path(lib_dir)
    src_path = Path(src_image_path)
    sha256 = _sha256(src_path)
    result_id = sha256[:16]
    objects_dir = lib_path / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    existing = _existing_object(objects_dir, result_id, sha256)
    if existing is None:
        ext = src_path.suffix.lower() or ".bin"
        target = objects_dir / f"{result_id}{ext}"
        assert not target.exists(), f"refusing to overwrite existing object: {target}"
        shutil.copy2(src_path, target)

    record = {
        "id": result_id,
        "sha256": sha256,
        "orig_name": src_path.name,
        "meta": meta,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    # Same-content re-adds are object-store no-ops, but still append a JSONL row
    # so the results log remains an append-only audit trail of add_result calls.
    with (lib_path / "results.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    return result_id


def query(lib_dir, **filters):
    """Return result records whose meta dict matches all supplied filters."""
    results_path = Path(lib_dir) / "results.jsonl"
    if not results_path.exists():
        return []

    matches = []
    with results_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            meta = record.get("meta") or {}
            if all(meta.get(key) == value for key, value in filters.items()):
                matches.append(record)
    return matches


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _existing_object(objects_dir, result_id, sha256):
    matches = sorted(objects_dir.glob(f"{result_id}.*"))
    for path in matches:
        if _sha256(path) == sha256:
            return path
    if matches:
        raise AssertionError(f"refusing to overwrite existing object id: {result_id}")
    return None
