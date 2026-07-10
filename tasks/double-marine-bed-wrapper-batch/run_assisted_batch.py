#!/usr/bin/env python3
"""Run explicit assisted-background-removal cases as resumable candidates only."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from PIL import Image


SCHEMA = "assisted-bg-batch-spec/v1"
REPORT_SCHEMA = "assisted-bg-batch-report/v1"
STATE_SCHEMA = "assisted-bg-batch-case/v1"
CASE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
FINAL_PATH_PARTS = {"final", "finals"}
CANDIDATE_PATH_PARTS = {"candidate", "candidates"}
CASE_FILENAMES = {
    "native_proposal": "native-proposal.png",
    "candidate": "candidate-rgba.png",
    "metrics": "metrics.json",
    "core_manifest": "core-manifest.json",
    "review_board": "review-board.png",
    "state": "batch-manifest.json",
}


class BatchError(ValueError):
    """A deterministic, user-correctable batch-spec or resume error."""


def _canonical_hash(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(path, data)


def _resolve_path(value: Any, base_dir: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise BatchError(f"{label} must be a non-empty path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _validate_keys(
    payload: Any,
    *,
    required: set[str],
    optional: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BatchError(f"{label} must be an object")
    keys = set(payload)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)
    if missing:
        raise BatchError(f"{label} is missing required keys: {missing}")
    if unknown:
        raise BatchError(f"{label} has unknown keys: {unknown}")
    return payload


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise BatchError(f"{label} must be a 64-character SHA-256 hex digest")
    return value.casefold()


def _validate_size(value: Any, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value)
    ):
        raise BatchError(f"{label} must be [positive_width, positive_height]")
    return value[0], value[1]


def _reject_final_path(path: Path, label: str) -> None:
    forbidden = FINAL_PATH_PARTS & {part.casefold() for part in path.parts}
    if forbidden:
        raise BatchError(f"{label} refuses final-path promotion ({sorted(forbidden)}): {path}")


def _require_candidate_path(path: Path, label: str) -> None:
    _reject_final_path(path, label)
    if not (CANDIDATE_PATH_PARTS & {part.casefold() for part in path.parts}):
        raise BatchError(f"{label} must be inside a candidate/ or candidates/ directory: {path}")


def _case_paths(output_dir: Path) -> dict[str, Path]:
    return {name: output_dir / filename for name, filename in CASE_FILENAMES.items()}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BatchError(f"cannot read {label} {path}: {error}") from error
    if not isinstance(payload, dict):
        raise BatchError(f"{label} must contain a JSON object: {path}")
    return payload


def _load_spec(path: Path) -> dict[str, Any]:
    payload = _read_json(path, "batch spec")
    _validate_keys(payload, required={"schema", "cases"}, optional=set(), label="batch spec")
    if payload["schema"] != SCHEMA:
        raise BatchError(f"unsupported batch schema {payload['schema']!r}; expected {SCHEMA!r}")
    if not isinstance(payload["cases"], list) or not payload["cases"]:
        raise BatchError("batch spec cases must be a non-empty list")
    return payload


def _case_declarations(
    spec: dict[str, Any], spec_dir: Path
) -> list[tuple[dict[str, Any], dict[str, Path]]]:
    declarations: list[tuple[dict[str, Any], dict[str, Path]]] = []
    seen_ids: set[str] = set()
    seen_paths: dict[Path, str] = {}
    seen_outputs: dict[Path, str] = {}
    for index, raw_case in enumerate(spec["cases"]):
        case = _validate_keys(
            raw_case,
            required={"id", "source", "output_dir"},
            optional={"proposal", "legacy_rgba_proposal", "corrections"},
            label=f"cases[{index}]",
        )
        case_id = case["id"]
        if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
            raise BatchError(
                f"cases[{index}].id must match {CASE_ID_RE.pattern!r}, got {case_id!r}"
            )
        if case_id in seen_ids:
            raise BatchError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        source = _validate_keys(
            case["source"],
            required={"path", "sha256", "size_wh"},
            optional=set(),
            label=f"case {case_id} source",
        )
        proposal_fields = [key for key in ("proposal", "legacy_rgba_proposal") if key in case]
        if len(proposal_fields) != 1:
            raise BatchError(
                f"case {case_id} must declare exactly one of proposal or legacy_rgba_proposal"
            )
        proposal_field = proposal_fields[0]
        proposal_required = {"path", "resample"} if proposal_field == "legacy_rgba_proposal" else {"path"}
        proposal = _validate_keys(
            case[proposal_field],
            required=proposal_required,
            optional={"sha256", "size_wh"},
            label=f"case {case_id} {proposal_field}",
        )
        if proposal_field == "legacy_rgba_proposal" and proposal["resample"] != "lanczos":
            raise BatchError(f"case {case_id} legacy resample must explicitly be 'lanczos'")
        corrections = None
        if "corrections" in case:
            corrections = _validate_keys(
                case["corrections"],
                required={"path"},
                optional={"sha256", "size_wh"},
                label=f"case {case_id} corrections",
            )

        paths = {
            "source": _resolve_path(source["path"], spec_dir, f"case {case_id} source.path"),
            "proposal": _resolve_path(
                proposal["path"], spec_dir, f"case {case_id} {proposal_field}.path"
            ),
            "output_dir": _resolve_path(
                case["output_dir"], spec_dir, f"case {case_id} output_dir"
            ),
        }
        if corrections is not None:
            paths["corrections"] = _resolve_path(
                corrections["path"], spec_dir, f"case {case_id} corrections.path"
            )
        _require_candidate_path(paths["output_dir"], f"case {case_id} output_dir")
        if paths["output_dir"] in seen_outputs:
            raise BatchError(
                f"duplicate output directory for cases {seen_outputs[paths['output_dir']]} and {case_id}: "
                f"{paths['output_dir']}"
            )
        seen_outputs[paths["output_dir"]] = case_id
        for role in ("source", "proposal", "corrections"):
            if role not in paths:
                continue
            path = paths[role]
            label = f"case {case_id} {role}"
            if path in seen_paths:
                raise BatchError(f"duplicate input path for {seen_paths[path]} and {label}: {path}")
            seen_paths[path] = label
        declarations.append((case, paths))

    input_paths = set(seen_paths)
    for case, paths in declarations:
        for role, output_path in _case_paths(paths["output_dir"]).items():
            if output_path in input_paths:
                raise BatchError(
                    f"case {case['id']} generated {role} path would overwrite an input: {output_path}"
                )
    return declarations


def _verify_optional_expectations(
    declaration: dict[str, Any], actual_sha: str, actual_size: tuple[int, int], label: str
) -> None:
    if "sha256" in declaration:
        expected_sha = _validate_sha256(declaration["sha256"], f"{label}.sha256")
        if actual_sha != expected_sha:
            raise BatchError(f"{label} SHA-256 mismatch: expected {expected_sha}, got {actual_sha}")
    if "size_wh" in declaration:
        expected_size = _validate_size(declaration["size_wh"], f"{label}.size_wh")
        if actual_size != expected_size:
            raise BatchError(f"{label} dimensions mismatch: expected {expected_size}, got {actual_size}")


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=9, optimize=False)
    return buffer.getvalue()


def _prepare_case(
    case: dict[str, Any],
    paths: dict[str, Path],
    *,
    core_path: Path,
    backend: str,
    device: str,
    unlock_radius: int,
) -> dict[str, Any]:
    case_id = case["id"]
    source_path = paths["source"]
    proposal_path = paths["proposal"]
    for label, path in (("source", source_path), ("proposal", proposal_path)):
        if not path.is_file():
            raise BatchError(f"case {case_id} {label} is not a file: {path}")
    if "corrections" in paths and not paths["corrections"].is_file():
        raise BatchError(f"case {case_id} corrections is not a file: {paths['corrections']}")

    source_sha = _sha256_file(source_path)
    expected_source_sha = _validate_sha256(case["source"]["sha256"], f"case {case_id} source.sha256")
    expected_source_size = _validate_size(
        case["source"]["size_wh"], f"case {case_id} source.size_wh"
    )
    if source_sha != expected_source_sha:
        raise BatchError(
            f"case {case_id} source SHA-256 mismatch: expected {expected_source_sha}, got {source_sha}"
        )
    with Image.open(source_path) as source_image:
        source_size = source_image.size
        source_mode = source_image.mode
    if source_mode != "RGB":
        raise BatchError(f"case {case_id} source must be native RGB, got {source_mode}")
    if source_size != expected_source_size:
        raise BatchError(
            f"case {case_id} source dimensions mismatch: expected {expected_source_size}, got {source_size}"
        )

    proposal_field = "proposal" if "proposal" in case else "legacy_rgba_proposal"
    proposal_declaration = case[proposal_field]
    proposal_sha = _sha256_file(proposal_path)
    with Image.open(proposal_path) as proposal_image:
        proposal_size = proposal_image.size
        proposal_mode = proposal_image.mode
        _verify_optional_expectations(
            proposal_declaration,
            proposal_sha,
            proposal_size,
            f"case {case_id} {proposal_field}",
        )
        if proposal_field == "legacy_rgba_proposal":
            if proposal_mode != "RGBA":
                raise BatchError(
                    f"case {case_id} legacy proposal must be genuine RGBA, got {proposal_mode}"
                )
            if (
                proposal_size[0] <= source_size[0]
                or proposal_size[1] <= source_size[1]
                or proposal_size[0] * source_size[1] != proposal_size[1] * source_size[0]
            ):
                raise BatchError(
                    f"case {case_id} legacy proposal must be a larger, proportional RGBA image; "
                    f"source={source_size}, proposal={proposal_size}"
                )
            native_proposal = proposal_image.getchannel("A").resize(
                source_size, Image.Resampling.LANCZOS, reducing_gap=3.0
            )
            transform = {
                "kind": "legacy-rgba-alpha-downsample",
                "from_size_wh": list(proposal_size),
                "to_size_wh": list(source_size),
                "resample": "lanczos",
            }
        else:
            if proposal_size != source_size:
                raise BatchError(
                    f"case {case_id} native proposal dimensions must match source {source_size}, "
                    f"got {proposal_size}"
                )
            if proposal_mode in {"L", "1"}:
                native_proposal = proposal_image.convert("L")
            elif proposal_mode == "RGBA":
                native_proposal = proposal_image.getchannel("A")
            elif proposal_mode == "RGB":
                channels = proposal_image.split()
                raw_channels = [channel.tobytes() for channel in channels]
                if raw_channels[0] != raw_channels[1] or raw_channels[1] != raw_channels[2]:
                    raise BatchError(f"case {case_id} RGB native proposal must be grayscale")
                native_proposal = channels[0]
            else:
                raise BatchError(
                    f"case {case_id} native proposal mode must be L, 1, grayscale RGB, or RGBA; "
                    f"got {proposal_mode}"
                )
            transform = {
                "kind": "native-to-l",
                "from_size_wh": list(proposal_size),
                "to_size_wh": list(source_size),
                "source_mode": proposal_mode,
            }
        native_bytes = _png_bytes(native_proposal)

    correction_payload = None
    if "corrections" in paths:
        correction_path = paths["corrections"]
        correction_sha = _sha256_file(correction_path)
        with Image.open(correction_path) as correction_image:
            correction_size = correction_image.size
            correction_mode = correction_image.mode
        _verify_optional_expectations(
            case["corrections"],
            correction_sha,
            correction_size,
            f"case {case_id} corrections",
        )
        if correction_mode != "RGBA":
            raise BatchError(
                f"case {case_id} corrections must be genuine RGBA, got {correction_mode}"
            )
        if correction_size != source_size:
            raise BatchError(
                f"case {case_id} corrections dimensions must exactly match source {source_size}, "
                f"got {correction_size}"
            )
        correction_payload = {
            "path": str(correction_path),
            "sha256": correction_sha,
            "size_wh": list(correction_size),
            "mode": correction_mode,
        }

    if not core_path.is_file():
        raise BatchError(f"assisted core is not a file: {core_path}")
    output_paths = _case_paths(paths["output_dir"])
    input_payload = {
        "source": {
            "path": str(source_path),
            "sha256": source_sha,
            "size_wh": list(source_size),
            "mode": source_mode,
        },
        "proposal_original": {
            "path": str(proposal_path),
            "sha256": proposal_sha,
            "size_wh": list(proposal_size),
            "mode": proposal_mode,
            "field": proposal_field,
        },
        "proposal_native": {
            "path": str(output_paths["native_proposal"]),
            "sha256": _sha256_bytes(native_bytes),
            "size_wh": list(source_size),
            "mode": "L",
            "transform": transform,
        },
        "corrections": correction_payload,
    }
    config_payload = {
        "backend": backend,
        "device": device,
        "correction_unlock_radius": unlock_radius,
        "core": {"path": str(core_path), "sha256": _sha256_file(core_path)},
        "python_executable": sys.executable,
        "runner": {"path": str(Path(__file__).resolve()), "sha256": _sha256_file(Path(__file__).resolve())},
    }
    input_hash = _canonical_hash(input_payload)
    config_hash = _canonical_hash(config_payload)
    fingerprint = _canonical_hash(
        {"schema": STATE_SCHEMA, "case_id": case_id, "input_hash": input_hash, "config_hash": config_hash}
    )
    command = [
        sys.executable,
        str(core_path),
        "--source",
        str(source_path),
        "--proposal",
        str(output_paths["native_proposal"]),
    ]
    if correction_payload is not None:
        command.extend(["--corrections", correction_payload["path"]])
    command.extend(
        [
            "--output",
            str(output_paths["candidate"]),
            "--metrics",
            str(output_paths["metrics"]),
            "--manifest",
            str(output_paths["core_manifest"]),
            "--review-board",
            str(output_paths["review_board"]),
            "--backend",
            backend,
            "--device",
            device,
            "--correction-unlock-radius",
            str(unlock_radius),
        ]
    )
    return {
        "case_id": case_id,
        "output_dir": paths["output_dir"],
        "paths": output_paths,
        "native_bytes": native_bytes,
        "inputs": input_payload,
        "config": config_payload,
        "input_hash": input_hash,
        "config_hash": config_hash,
        "fingerprint": fingerprint,
        "command": command,
        "source_sha": source_sha,
        "source_size": source_size,
    }


def _verified_outputs(prepared: dict[str, Any]) -> dict[str, Any]:
    paths = prepared["paths"]
    required = ("candidate", "metrics", "core_manifest", "review_board")
    for name in required:
        if not paths[name].is_file():
            raise BatchError(f"core reported success but did not write {name}: {paths[name]}")
    with Image.open(paths["candidate"]) as candidate:
        if candidate.mode != "RGBA" or candidate.size != prepared["source_size"]:
            raise BatchError(
                f"candidate must be native-size RGBA {prepared['source_size']}, "
                f"got mode={candidate.mode} size={candidate.size}"
            )
    _read_json(paths["metrics"], "core metrics")
    core_manifest = _read_json(paths["core_manifest"], "core manifest")
    if core_manifest.get("status") != "candidate-unapproved" or core_manifest.get("production_ready") is not False:
        raise BatchError("core manifest does not preserve candidate-unapproved / production_ready=false")
    return {
        name: {"path": str(paths[name]), "sha256": _sha256_file(paths[name])}
        for name in required
    }


def _resume_state(prepared: dict[str, Any]) -> Optional[dict[str, Any]]:
    state_path = prepared["paths"]["state"]
    if not state_path.exists():
        return None
    state = _read_json(state_path, "case batch manifest")
    if state.get("schema") != STATE_SCHEMA:
        raise BatchError(f"resume mismatch: unsupported case state schema in {state_path}")
    for key in ("fingerprint", "input_hash", "config_hash"):
        if state.get(key) != prepared[key]:
            raise BatchError(
                f"resume mismatch: {key} changed for case {prepared['case_id']}; pass --overwrite"
            )
    native_path = prepared["paths"]["native_proposal"]
    expected_native_sha = prepared["inputs"]["proposal_native"]["sha256"]
    if not native_path.is_file() or _sha256_file(native_path) != expected_native_sha:
        raise BatchError(
            f"resume mismatch: normalized proposal missing or changed for case {prepared['case_id']}; "
            "pass --overwrite"
        )
    outputs = state.get("outputs")
    if not isinstance(outputs, dict):
        raise BatchError(f"resume mismatch: output hashes missing for case {prepared['case_id']}")
    for name in ("candidate", "metrics", "core_manifest", "review_board"):
        record = outputs.get(name)
        path = prepared["paths"][name]
        if (
            not isinstance(record, dict)
            or record.get("path") != str(path)
            or not path.is_file()
            or record.get("sha256") != _sha256_file(path)
        ):
            raise BatchError(
                f"resume mismatch: {name} missing or changed for case {prepared['case_id']}; "
                "pass --overwrite"
            )
    return state


def _default_command_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _command_result(result: Any) -> tuple[int, str, str]:
    if isinstance(result, int):
        return result, "", ""
    return (
        int(getattr(result, "returncode")),
        str(getattr(result, "stdout", "") or ""),
        str(getattr(result, "stderr", "") or ""),
    )


def _nonempty_owned_outputs(prepared: dict[str, Any]) -> list[Path]:
    output_dir = prepared["output_dir"]
    if not output_dir.exists():
        return []
    return sorted((path for path in output_dir.iterdir()), key=lambda path: path.name)


def _run_prepared_case(
    prepared: dict[str, Any],
    *,
    dry_run: bool,
    overwrite: bool,
    command_runner: Callable[[list[str]], Any],
) -> dict[str, Any]:
    state = None
    if not overwrite:
        state = _resume_state(prepared)
        if state is None:
            existing = _nonempty_owned_outputs(prepared)
            if existing:
                raise BatchError(
                    f"case {prepared['case_id']} candidate directory is not empty and has no resumable "
                    f"state: {[str(path) for path in existing]}; pass --overwrite"
                )
    action = "run" if state is None or overwrite else "resume"
    command = list(prepared["command"])
    if overwrite and action == "run":
        command.append("--overwrite")
    if dry_run:
        return {
            "id": prepared["case_id"],
            "status": "planned",
            "action": action,
            "command": command,
            "fingerprint": prepared["fingerprint"],
            "native_proposal": prepared["inputs"]["proposal_native"],
            "production_ready": False,
            "promotion_performed": False,
        }
    if action == "resume":
        return {
            "id": prepared["case_id"],
            "status": "success",
            "action": "resumed",
            "command": command,
            "fingerprint": prepared["fingerprint"],
            "outputs": state["outputs"],
            "production_ready": False,
            "promotion_performed": False,
        }

    _atomic_write_bytes(prepared["paths"]["native_proposal"], prepared["native_bytes"])
    result = command_runner(command)
    returncode, _stdout, stderr = _command_result(result)
    if returncode != 0:
        detail = stderr.strip() or "no stderr"
        raise BatchError(f"assisted core failed with exit {returncode}: {detail}")
    after_sha = _sha256_file(Path(prepared["inputs"]["source"]["path"]))
    if after_sha != prepared["source_sha"]:
        raise BatchError(
            f"source changed while processing case {prepared['case_id']}: "
            f"{prepared['source_sha']} -> {after_sha}"
        )
    outputs = _verified_outputs(prepared)
    state_payload = {
        "schema": STATE_SCHEMA,
        "status": "candidate-unapproved",
        "production_ready": False,
        "promotion_performed": False,
        "case_id": prepared["case_id"],
        "fingerprint": prepared["fingerprint"],
        "input_hash": prepared["input_hash"],
        "config_hash": prepared["config_hash"],
        "inputs": prepared["inputs"],
        "config": prepared["config"],
        "command": command,
        "outputs": outputs,
        "source_unchanged_proof": {
            "before_sha256": prepared["source_sha"],
            "after_sha256": after_sha,
            "unchanged": True,
        },
    }
    _atomic_write_json(prepared["paths"]["state"], state_payload)
    return {
        "id": prepared["case_id"],
        "status": "success",
        "action": "ran",
        "command": command,
        "fingerprint": prepared["fingerprint"],
        "outputs": outputs,
        "production_ready": False,
        "promotion_performed": False,
    }


def _best_effort_source_hash(case: dict[str, Any], spec_dir: Path) -> Optional[str]:
    try:
        source = case.get("source")
        if not isinstance(source, dict):
            return None
        path = _resolve_path(source.get("path"), spec_dir, "source.path")
        return _sha256_file(path) if path.is_file() else None
    except (BatchError, OSError):
        return None


def execute_batch(
    spec_path: Path,
    aggregate_path: Path,
    *,
    core_path: Path,
    backend: str,
    device: str,
    correction_unlock_radius: int,
    case_filter: Optional[Sequence[str]] = None,
    dry_run: bool = False,
    overwrite: bool = False,
    command_runner: Callable[[list[str]], Any] = _default_command_runner,
) -> dict[str, Any]:
    spec_path = spec_path.expanduser().resolve()
    aggregate_path = aggregate_path.expanduser().resolve()
    core_path = core_path.expanduser().resolve()
    _reject_final_path(aggregate_path, "aggregate report")
    if correction_unlock_radius < 0:
        raise BatchError("correction unlock radius must be non-negative")
    spec = _load_spec(spec_path)
    declarations = _case_declarations(spec, spec_path.parent)
    reserved_paths = {spec_path, core_path}
    for _case, paths in declarations:
        reserved_paths.update(paths[role] for role in ("source", "proposal", "corrections") if role in paths)
        reserved_paths.update(_case_paths(paths["output_dir"]).values())
    if aggregate_path in reserved_paths:
        raise BatchError(f"aggregate report path collides with an input or case artifact: {aggregate_path}")
    all_ids = [case["id"] for case, _paths in declarations]
    selected_ids = list(case_filter) if case_filter else all_ids
    if len(selected_ids) != len(set(selected_ids)):
        raise BatchError("--case values must be unique")
    unknown = sorted(set(selected_ids) - set(all_ids))
    if unknown:
        raise BatchError(f"--case requested unknown case ids: {unknown}")
    selected = [(case, paths) for case, paths in declarations if case["id"] in set(selected_ids)]
    selected.sort(key=lambda item: selected_ids.index(item[0]["id"]))

    config_summary = {
        "backend": backend,
        "device": device,
        "correction_unlock_radius": correction_unlock_radius,
        "core": {"path": str(core_path), "sha256": _sha256_file(core_path) if core_path.is_file() else None},
        "python_executable": sys.executable,
    }
    spec_payload = {"path": str(spec_path), "sha256": _sha256_file(spec_path)}
    config_summary_hash = _canonical_hash(config_summary)
    if aggregate_path.exists() and not dry_run and not overwrite:
        previous = _read_json(aggregate_path, "existing aggregate report")
        compatible = (
            previous.get("schema") == REPORT_SCHEMA
            and previous.get("spec", {}).get("sha256") == spec_payload["sha256"]
            and previous.get("config_hash") == config_summary_hash
        )
        if not compatible:
            raise BatchError(
                f"aggregate report exists with different spec/config; pass --overwrite: {aggregate_path}"
            )
    results: list[dict[str, Any]] = []
    for case, paths in selected:
        source_before = _best_effort_source_hash(case, spec_path.parent)
        try:
            prepared = _prepare_case(
                case,
                paths,
                core_path=core_path,
                backend=backend,
                device=device,
                unlock_radius=correction_unlock_radius,
            )
            result = _run_prepared_case(
                prepared,
                dry_run=dry_run,
                overwrite=overwrite,
                command_runner=command_runner,
            )
        except (BatchError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            result = {
                "id": case["id"],
                "status": "failure",
                "error": str(error),
                "production_ready": False,
                "promotion_performed": False,
            }
        source_after = _best_effort_source_hash(case, spec_path.parent)
        result["source_unchanged_proof"] = {
            "before_sha256": source_before,
            "after_sha256": source_after,
            "unchanged": source_before is not None and source_before == source_after,
            "available": source_before is not None and source_after is not None,
        }
        if result["source_unchanged_proof"]["available"] and not result["source_unchanged_proof"]["unchanged"]:
            result["status"] = "failure"
            result["error"] = "source changed during batch case execution"
        results.append(result)

    failures = sum(result["status"] == "failure" for result in results)
    successes = sum(result["status"] == "success" for result in results)
    planned = sum(result["status"] == "planned" for result in results)
    report = {
        "schema": REPORT_SCHEMA,
        "status": "planned" if dry_run and not failures else ("success" if not failures else "partial-failure"),
        "dry_run": dry_run,
        "production_ready": False,
        "promotion_performed": False,
        "spec": spec_payload,
        "aggregate_path": str(aggregate_path),
        "case_filter": selected_ids,
        "config": config_summary,
        "config_hash": config_summary_hash,
        "counts": {
            "selected": len(results),
            "success": successes,
            "planned": planned,
            "failure": failures,
        },
        "cases": results,
    }
    if not dry_run:
        _atomic_write_json(aggregate_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="explicit assisted-bg-batch-spec/v1 JSON")
    parser.add_argument("--aggregate", type=Path, required=True, help="aggregate candidate report JSON")
    parser.add_argument(
        "--core",
        type=Path,
        default=Path(__file__).resolve().with_name("assisted_bg_remove.py"),
        help="assisted_bg_remove.py path (default: adjacent core)",
    )
    parser.add_argument("--backend", choices=("vitmatte", "closed_form"), required=True)
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), required=True)
    parser.add_argument("--correction-unlock-radius", type=int, required=True)
    parser.add_argument(
        "--case",
        action="append",
        help="run one exact case id; repeat for a bounded ordered subset (no globs/discovery)",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate and print deterministic commands; write nothing")
    parser.add_argument("--overwrite", action="store_true", help="rerun mismatched/existing candidate state explicitly")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = execute_batch(
            args.spec,
            args.aggregate,
            core_path=args.core,
            backend=args.backend,
            device=args.device,
            correction_unlock_radius=args.correction_unlock_radius,
            case_filter=args.case,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except (BatchError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["counts"]["failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
