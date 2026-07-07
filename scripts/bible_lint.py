#!/usr/bin/env python3
"""Lint a versioned Screenery style bible YAML file."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "style-bible.schema.json"

STYLE_FIELDS = [
    "mood_words",
    "art_medium",
    "rendering_finish",
    "color_palette",
    "line_quality",
    "shape_language",
    "detail_density",
    "motif_vocabulary",
    "texture_rules",
    "anti_style",
    "reference_images",
    "reference_role_map",
    "per_surface_palette",
    "warm_cool_structure",
    "set_consistency",
    "review_gate",
    "signage_text_rule",
    "character_prop_proportions",
    "geometry_contract",
]

REQUIRED_FIELDS = ["bible_version", *STYLE_FIELDS]
REF_ROLES = [
    "architecture_anchor",
    "medium_anchor",
    "palette",
    "content_only",
    "anti_example",
]
OBJECT_FIELDS = {
    "mood_words",
    "art_medium",
    "rendering_finish",
    "color_palette",
    "line_quality",
    "shape_language",
    "detail_density",
    "motif_vocabulary",
    "texture_rules",
    "reference_images",
    "reference_role_map",
    "per_surface_palette",
    "warm_cool_structure",
    "set_consistency",
    "signage_text_rule",
    "character_prop_proportions",
    "geometry_contract",
}
BARE_SINGLE_WORD = re.compile(r"^[A-Za-z0-9_]+$")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass
class Check:
    status: str
    name: str
    detail: str


@dataclass
class LintResult:
    path: Path
    checks: list[Check] = field(default_factory=list)

    @property
    def errors(self) -> list[Check]:
        return [check for check in self.checks if check.status == "FAIL"]

    @property
    def warnings(self) -> list[Check]:
        return [check for check in self.checks if check.status == "WARN"]

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 2
        if self.warnings:
            return 1
        return 0

    def add(self, status: str, name: str, detail: str) -> None:
        self.checks.append(Check(status, name, detail))

    def format(self) -> str:
        lines = [f"Style bible lint: {self.path}"]
        lines.extend(
            f"{check.status} {check.name}: {check.detail}" for check in self.checks
        )
        return "\n".join(lines)


def lint_bible(bible_path: str | Path, repo_root: str | Path | None = None) -> LintResult:
    """Validate one bible YAML file and return a structured lint result."""
    path = Path(bible_path)
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    result = LintResult(path=path)

    try:
        data = _load_yaml(path)
    except Exception as exc:  # noqa: BLE001 - report parse errors as lint failures.
        result.add("FAIL", "load yaml", str(exc))
        return result

    result.add("PASS", "load yaml", "parsed YAML document")
    if not isinstance(data, dict):
        result.add("FAIL", "schema validation", "root document must be an object")
        return result

    _validate_schema(data, result)
    _check_refs(data, path, root, result)
    _check_style_specificity(data, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bible", help="Path to a style bible YAML file")
    args = parser.parse_args(argv)

    result = lint_bible(args.bible)
    print(result.format())
    return result.exit_code


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _validate_schema(data: dict[str, Any], result: LintResult) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    probe = subprocess.run(
        [sys.executable, "-c", "import jsonschema"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if probe.returncode == 0:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda item: list(item.path))
        if errors:
            for error in errors:
                location = "$"
                if error.path:
                    location += "." + ".".join(str(part) for part in error.path)
                result.add("FAIL", "schema validation", f"{location}: {error.message}")
        else:
            result.add("PASS", "schema validation", "jsonschema validator passed")
        return

    errors = _fallback_schema_errors(data)
    if errors:
        for error in errors:
            result.add("FAIL", "schema validation", error)
    else:
        result.add(
            "PASS",
            "schema validation",
            "fallback validator passed; jsonschema is not importable",
        )


def _fallback_schema_errors(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for field_name in REQUIRED_FIELDS:
        if field_name not in data:
            errors.append(f"missing required field: {field_name}")

    version = data.get("bible_version")
    if "bible_version" in data and (
        not isinstance(version, int) or isinstance(version, bool) or version < 1
    ):
        errors.append("bible_version must be an integer >= 1")

    if "refs_by_role" in data and "collection" not in data:
        errors.append("collection is required when refs_by_role is present")
    if "collection" in data and (
        not isinstance(data["collection"], str) or not data["collection"].strip()
    ):
        errors.append("collection must be a non-empty string")

    for field_name in OBJECT_FIELDS:
        if field_name in data and not isinstance(data[field_name], dict):
            errors.append(f"{field_name} must be an object")

    if "anti_style" in data and not _is_string_list(data["anti_style"]):
        errors.append("anti_style must be a list of strings")

    if "review_gate" in data and not isinstance(data["review_gate"], (str, dict)):
        errors.append("review_gate must be a string or legacy object")

    refs_by_role = data.get("refs_by_role")
    if refs_by_role is not None:
        if not isinstance(refs_by_role, dict):
            errors.append("refs_by_role must be an object")
        else:
            extra = sorted(set(refs_by_role) - set(REF_ROLES))
            if extra:
                errors.append(f"refs_by_role has unknown role keys: {', '.join(extra)}")
            for role in REF_ROLES:
                if role not in refs_by_role:
                    errors.append(f"refs_by_role missing required role: {role}")
                    continue
                if not _is_string_list(refs_by_role[role]):
                    errors.append(f"refs_by_role.{role} must be a list of strings")
            anti_examples = refs_by_role.get("anti_example")
            if isinstance(anti_examples, list) and not anti_examples:
                errors.append("refs_by_role.anti_example must not be empty")

    if "motif_sheet" in data and not isinstance(data["motif_sheet"], str):
        errors.append("motif_sheet must be a string path")

    if "forbidden_props" in data and not _is_string_list(data["forbidden_props"]):
        errors.append("forbidden_props must be a list of strings")

    color_script = data.get("color_script")
    if color_script is not None:
        if not isinstance(color_script, list):
            errors.append("color_script must be a list")
        else:
            for index, item in enumerate(color_script):
                prefix = f"color_script[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for key in ("surface", "hex", "note"):
                    if key not in item:
                        errors.append(f"{prefix}.{key} is required")
                    elif not isinstance(item[key], str) or not item[key].strip():
                        errors.append(f"{prefix}.{key} must be a non-empty string")
                if isinstance(item.get("hex"), str) and not HEX_COLOR.match(item["hex"]):
                    errors.append(f"{prefix}.hex must be #RRGGBB")

    return errors


def _check_refs(
    data: dict[str, Any], bible_path: Path, repo_root: Path, result: LintResult
) -> None:
    refs_by_role = data.get("refs_by_role")
    if refs_by_role is None:
        result.add("PASS", "refs_by_role paths", "not present; legacy spec mode")
        result.add("PASS", "refs_by_role uniqueness", "not present; legacy spec mode")
        result.add("PASS", "refs_by_role anti_example", "not present; legacy spec mode")
        return
    if not isinstance(refs_by_role, dict):
        result.add("FAIL", "refs_by_role paths", "refs_by_role is not an object")
        return

    total_refs = 0
    missing_refs: list[str] = []
    seen_by_path: dict[Path | str, tuple[str, str]] = {}
    duplicate_refs: list[str] = []

    for role, refs in refs_by_role.items():
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, str):
                continue
            total_refs += 1
            resolved = resolve_ref_path(ref, bible_path, repo_root)
            if resolved is None:
                missing_refs.append(f"{role}: {ref}")
                duplicate_key: Path | str = ref
            else:
                duplicate_key = resolved

            prior = seen_by_path.get(duplicate_key)
            if prior is not None and prior[0] != role:
                duplicate_refs.append(f"{ref} appears in {prior[0]} and {role}")
            else:
                seen_by_path[duplicate_key] = (role, ref)

    if missing_refs:
        for item in missing_refs:
            result.add("FAIL", "refs_by_role paths", f"missing ref file: {item}")
    else:
        result.add("PASS", "refs_by_role paths", f"{total_refs} refs exist")

    if duplicate_refs:
        for item in duplicate_refs:
            result.add("FAIL", "refs_by_role uniqueness", item)
    else:
        result.add("PASS", "refs_by_role uniqueness", "no ref path reused across roles")

    anti_examples = refs_by_role.get("anti_example")
    if isinstance(anti_examples, list) and anti_examples:
        result.add(
            "PASS",
            "refs_by_role anti_example",
            f"{len(anti_examples)} anti-example refs present",
        )
    elif isinstance(anti_examples, list):
        result.add("FAIL", "refs_by_role anti_example", "anti_example list is empty")


def _check_style_specificity(data: dict[str, Any], result: LintResult) -> None:
    warnings: list[str] = []
    for field_name in STYLE_FIELDS:
        if field_name not in data:
            continue
        for path, value in _iter_named_string_fields(data[field_name], [field_name]):
            if BARE_SINGLE_WORD.match(value.strip()):
                warnings.append(f"{'.'.join(path)} is a bare single word: {value!r}")

    if warnings:
        for warning in warnings:
            result.add("WARN", "style field specificity", warning)
    else:
        result.add(
            "PASS",
            "style field specificity",
            "no bare single-word named string fields in the 19 style fields",
        )


def _iter_named_string_fields(
    value: Any, path: list[str]
) -> Iterable[tuple[list[str], str]]:
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = [*path, str(key)]
            if isinstance(item, str):
                yield child_path, item
            elif isinstance(item, dict):
                yield from _iter_named_string_fields(item, child_path)
            elif isinstance(item, list):
                for index, child in enumerate(item):
                    if isinstance(child, dict):
                        yield from _iter_named_string_fields(
                            child, [*child_path, str(index)]
                        )


def resolve_ref_path(ref: str, bible_path: Path, repo_root: Path | None = None) -> Path | None:
    """Resolve a bible ref path against sensible repo and task-local conventions."""
    root = repo_root if repo_root is not None else REPO_ROOT
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


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


if __name__ == "__main__":
    raise SystemExit(main())
