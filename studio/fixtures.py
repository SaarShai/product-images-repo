"""Historical fixture manifest loader."""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_MANIFEST = ".brainer/tenx/fixtures-manifest.json"
REQUIRED_FIXTURE_FIELDS = {"id", "kind", "paths", "expected", "source_task"}


def load_manifest(path=DEFAULT_MANIFEST):
    """Load and validate the historical fixture manifest."""
    manifest_path = _resolve_manifest_path(path)
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    _validate_manifest(manifest)
    return manifest


def iter_fixtures(kind=None):
    """Yield fixtures from the default manifest, optionally filtered by kind."""
    for fixture in load_manifest()["fixtures"]:
        if kind is None or fixture["kind"] == kind:
            yield fixture


def _resolve_manifest_path(path):
    manifest_path = Path(path)
    if manifest_path.exists() or manifest_path.is_absolute():
        return manifest_path

    repo_root_path = Path(__file__).resolve().parents[1] / manifest_path
    if repo_root_path.exists():
        return repo_root_path
    return manifest_path


def _validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("fixture manifest must be a JSON object")

    for field in ("fixtures", "missing"):
        if field not in manifest:
            raise ValueError(f"fixture manifest missing required top-level field: {field}")
        if not isinstance(manifest[field], list):
            raise ValueError(f"fixture manifest field must be a list: {field}")

    for index, fixture in enumerate(manifest["fixtures"]):
        if not isinstance(fixture, dict):
            raise ValueError(f"fixture at index {index} must be an object")

        missing = sorted(REQUIRED_FIXTURE_FIELDS - fixture.keys())
        if missing:
            raise ValueError(
                f"fixture at index {index} missing required field(s): {', '.join(missing)}"
            )
        if not isinstance(fixture["paths"], list):
            raise ValueError(f"fixture {fixture['id']} field must be a list: paths")
