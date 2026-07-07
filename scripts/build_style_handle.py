#!/usr/bin/env python3
"""Build a per-collection reusable style-handle directory.

A style handle is a small, role-tagged directory of reference images plus a
validated manifest (`style-handle.yaml`) and a human contact sheet. It is the
reusable "pack" a style/geometry agent loads for one collection instead of
re-deriving references from scratch every round.

Manifest rows (YAML list): {file, role, provenance, notes, hold_out}
  - role is exactly one of ROLES (below); every file gets exactly one role
    EXCEPT feature_ref, where duplicate roles are allowed (multiple feature
    refs are normal).
  - hold_out is optional and only meaningful for style_ref / feature_ref rows:
    it names a target panel that ref may NOT be used for (see wiki lesson
    "hold-out ground-truth style ref").
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref_lint


ROOT = Path(__file__).resolve().parents[1]
ROLES = [
    "medium_ref",
    "palette_ref",
    "style_ref",
    "feature_ref",
    "geometry_ref",
    "layout_ref",
]
ROLES_ALLOWING_DUPLICATES = {"feature_ref"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class ManifestRow:
    file: str
    role: str
    provenance: str = ""
    notes: str = ""
    hold_out: str = ""
    resolved_path: Path = field(default=None, repr=False)


class ManifestError(ValueError):
    """Raised when a style-handle manifest fails validation."""


def load_manifest_rows(manifest_path: Path) -> list[dict[str, Any]]:
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return []
    # Accept both shapes:
    # 1. bare list (input manifests): [{ file, role, ... }, ...]
    # 2. emitted handle mapping: { created_at: ..., rows: [...] }
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "rows" in data:
        rows = data["rows"]
        if isinstance(rows, list):
            return rows
        raise ManifestError("manifest 'rows' key must be a list")
    raise ManifestError("manifest root must be a list of rows or a mapping with a 'rows' key")


def validate_manifest(rows: list[dict[str, Any]], manifest_dir: Path) -> list[ManifestRow]:
    """Validate manifest rows and resolve file paths. Raises ManifestError on failure."""
    errors: list[str] = []
    parsed: list[ManifestRow] = []
    seen_files_by_role: dict[str, set[str]] = {}

    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            errors.append(f"row {index}: must be a mapping, got {type(raw).__name__}")
            continue

        file_value = raw.get("file")
        role = raw.get("role")

        if not file_value:
            errors.append(f"row {index}: missing required field 'file'")
            continue
        if role not in ROLES:
            errors.append(
                f"row {index} ({file_value}): role {role!r} is not one of {ROLES}"
            )
            continue

        resolved = _resolve_ref_path(file_value, manifest_dir)
        if resolved is None:
            errors.append(f"row {index} ({file_value}): file does not exist")
            continue

        if role not in ROLES_ALLOWING_DUPLICATES:
            seen = seen_files_by_role.setdefault(role, set())
            if seen and file_value not in seen:
                errors.append(
                    f"row {index} ({file_value}): role {role!r} is already used by "
                    f"{sorted(seen)!r} (duplicate roles allowed only for feature_ref)"
                )
                continue
            seen.add(file_value)

        parsed.append(
            ManifestRow(
                file=str(file_value),
                role=role,
                provenance=str(raw.get("provenance", "")),
                notes=str(raw.get("notes", "")),
                hold_out=str(raw.get("hold_out", "")),
                resolved_path=resolved,
            )
        )

    # One-role-per-file rule: a given file must not appear under two different
    # roles (feature_ref duplicates of the SAME role are fine; this catches a
    # file reused across roles, e.g. style_ref AND palette_ref).
    role_by_file: dict[str, str] = {}
    for row in parsed:
        prior_role = role_by_file.get(row.file)
        if prior_role is not None and prior_role != row.role:
            errors.append(
                f"{row.file}: appears with role {prior_role!r} and role {row.role!r} "
                f"(exactly one role per file)"
            )
        else:
            role_by_file[row.file] = row.role

    if errors:
        raise ManifestError("\n".join(errors))

    return parsed


def _resolve_ref_path(file_value: str, manifest_dir: Path) -> Path | None:
    raw = Path(file_value)
    candidates = [raw] if raw.is_absolute() else [manifest_dir / raw, ROOT / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _role_prefix(index: int) -> str:
    return f"{index:02d}"


def lint_rows(rows: list[ManifestRow], skip_vlm_lint: bool) -> None:
    """Run ref_lint per manifest row; raise ManifestError naming file+reason on any rejection.

    Hold-out (path-pattern) check always runs. VLM checks (text/open-door) run unless
    skip_vlm_lint, in which case a loud WARNING is printed instead.
    """
    errors: list[str] = []

    if skip_vlm_lint:
        print(
            "WARNING: --skip-vlm-lint set — text/open-door VLM checks SKIPPED for all "
            "manifest rows. Dirty refs (readable text, open-door voids) will NOT be caught.",
            file=sys.stderr,
        )

    for row in rows:
        if row.hold_out and ref_lint.hold_out_violation(row.provenance, row.hold_out):
            errors.append(
                f"{row.file}: hold-out violation — provenance {row.provenance!r} looks like "
                f"a generated output for target panel {row.hold_out!r}"
            )
            continue

        if skip_vlm_lint:
            continue

        text_result = ref_lint.run_text_check(str(row.resolved_path), dry_run=False)
        if text_result.get("text_found"):
            errors.append(
                f"{row.file}: ref_lint text check rejected — readable text/logo found "
                f"({text_result.get('where', '')})"
            )
            continue

        door_result = ref_lint.run_door_check(str(row.resolved_path), dry_run=False)
        if door_result.get("open_door_found"):
            errors.append(
                f"{row.file}: ref_lint door check rejected — open door/void found "
                f"({door_result.get('where', '')})"
            )
            continue

    if errors:
        raise ManifestError("\n".join(errors))


def build_handle(rows: list[ManifestRow], handle_dir: Path, timestamp: str) -> dict[str, Any]:
    handle_dir.mkdir(parents=True, exist_ok=True)

    # Number files in manifest order, grouped so duplicate feature_ref rows
    # each get their own file without colliding.
    role_counts: dict[str, int] = {}
    manifest_out: list[dict[str, Any]] = []
    contact_items: list[tuple[str, Path]] = []

    for order, row in enumerate(rows, start=1):
        role_counts[row.role] = role_counts.get(row.role, 0) + 1
        suffix = row.resolved_path.suffix.lower() or ".png"
        if role_counts[row.role] > 1:
            dest_name = f"{_role_prefix(order)}-{row.role}-{role_counts[row.role]:02d}{suffix}"
        else:
            dest_name = f"{_role_prefix(order)}-{row.role}{suffix}"
        dest_path = handle_dir / dest_name
        shutil.copy2(row.resolved_path, dest_path)

        entry = {
            "file": dest_name,
            "role": row.role,
            "provenance": row.provenance,
            "notes": row.notes,
            "source_file": row.file,
        }
        if row.hold_out:
            entry["hold_out"] = row.hold_out
        manifest_out.append(entry)
        contact_items.append((dest_name, dest_path))

    manifest_doc = {
        "created_at": timestamp,
        "rows": manifest_out,
    }
    (handle_dir / "style-handle.yaml").write_text(
        yaml.safe_dump(manifest_doc, sort_keys=False), encoding="utf-8"
    )

    make_contact_sheet(contact_items, handle_dir / "contact-sheet.jpg")
    return manifest_doc


def make_contact_sheet(items: list[tuple[str, Path]], out_path: Path) -> None:
    """PIL grid contact sheet; labels sit in the gutter band BELOW each tile.

    This sheet is a human artifact for reviewing the handle at a glance. Model
    consumers must use the separate role-named files, not this sheet.
    """
    cols = 3
    cell_w, cell_h = 320, 260
    gutter_h = 40
    rows = max(1, -(-len(items) // cols))
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + gutter_h)), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except Exception:
        label_font = ImageFont.load_default()

    for index, (label, path) in enumerate(items):
        col = index % cols
        row = index // cols
        x0 = col * cell_w
        y0 = row * (cell_h + gutter_h)

        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((cell_w - 20, cell_h - 20), Image.Resampling.LANCZOS)
        tx = x0 + (cell_w - thumb.width) // 2
        ty = y0 + (cell_h - thumb.height) // 2
        sheet.paste(thumb, (tx, ty))

        gutter_y = y0 + cell_h
        draw.rectangle((x0, gutter_y, x0 + cell_w, gutter_y + gutter_h), fill=(238, 240, 242))
        draw.text((x0 + 10, gutter_y + 10), label[:40], fill=(40, 44, 52), font=label_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handle-dir", required=True, type=Path, help="Output style-handle directory")
    parser.add_argument("--manifest", required=True, type=Path, help="Input manifest YAML file")
    parser.add_argument("--timestamp", default=None, help="created_at value to stamp (defaults to now, UTC)")
    parser.add_argument(
        "--skip-vlm-lint",
        action="store_true",
        help="skip the ref_lint text/open-door VLM checks (hold-out check still runs); prints a WARNING",
    )
    args = parser.parse_args(argv)

    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.exists():
        raise SystemExit(f"Manifest does not exist: {manifest_path}")

    rows_raw = load_manifest_rows(manifest_path)
    try:
        rows = validate_manifest(rows_raw, manifest_path.parent)
        lint_rows(rows, skip_vlm_lint=args.skip_vlm_lint)
    except ManifestError as exc:
        print(f"Manifest validation failed:\n{exc}", file=sys.stderr)
        return 2

    timestamp = args.timestamp
    if timestamp is None:
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    handle_dir = args.handle_dir.expanduser().resolve()
    manifest_doc = build_handle(rows, handle_dir, timestamp)
    print(str(handle_dir))
    print(f"rows={len(manifest_doc['rows'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
