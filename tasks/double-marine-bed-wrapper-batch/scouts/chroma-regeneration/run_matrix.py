#!/usr/bin/env python3
"""Run the frozen four-engine chroma matrix exactly once, in parallel."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

REPO = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parent
SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)
OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/chroma-regeneration/image14"
)
PRIOR = REPO / "tasks/double-marine-bed-wrapper-batch/regen-v12/14-regen-v12-attempt1-raw.png"
SOURCE_SHA = "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(text: str) -> str:
    text = re.sub(r"(?i)(authorization|FAL_KEY|api[_ -]?key|token)[=: ]+\S+", r"\1=[redacted]", text)
    text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[redacted-data-uri]", text)
    text = re.sub(r"https?://\S*(?:fal\.media|fal\.run)\S*", "[redacted-provider-url]", text)
    return text[-6000:]


def image_info(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {
            "path": str(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
        }


def run_command(record: dict[str, Any]) -> dict[str, Any]:
    candidate_dir = OUT / record["id"]
    candidate_dir.mkdir(parents=True, exist_ok=True)
    raw = candidate_dir / "raw.png"
    command = [part.replace("{RAW}", str(raw)) for part in record["command"]]
    environment = os.environ.copy()
    if record["id"] == "openai-a":
        environment["PATH"] = str(TASK / "bin") + os.pathsep + environment["PATH"]
    started = time.perf_counter()
    result = {**record, "status": "running", "started_at_utc": utc_now(), "command": command}
    process = subprocess.Popen(
        command,
        cwd=REPO,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=720)
        return_code = process.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        return_code = -1
        result["timeout"] = True
    result.update({
        "finished_at_utc": utc_now(),
        "duration_seconds": round(time.perf_counter() - started, 6),
        "return_code": return_code,
        "stdout_tail_redacted": redact(stdout or ""),
        "stderr_tail_redacted": redact(stderr or ""),
    })
    if return_code == 0 and raw.is_file():
        try:
            result["output"] = image_info(raw)
            result["status"] = "valid_output"
        except Exception as exc:
            result["status"] = "invalid_output"
            result["error"] = f"{type(exc).__name__}: {exc}"
    else:
        result["status"] = "failed"
    attempts = re.findall(r"OK attempt (\d+)|attempt (\d+)/", result["stderr_tail_redacted"])
    if attempts:
        result["subscription_attempt_markers"] = [next(value for value in pair if value) for pair in attempts]
    artifact = Path(str(raw) + ".artifact.json")
    if artifact.is_file():
        result["fal_artifact_path"] = str(artifact)
        result["fal_artifact_sha256"] = sha256(artifact)
    return result


def write_manifest(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / "matrix-attempt-lock.json"
    manifest_path = OUT / "manifest.json"
    if lock.exists() or manifest_path.exists():
        raise SystemExit(f"refusing second matrix run: {lock if lock.exists() else manifest_path} exists")
    if sha256(SOURCE) != SOURCE_SHA:
        raise SystemExit("source hash mismatch")

    prompt_a = TASK / "PROMPT-A.md"
    prompt_b = TASK / "PROMPT-B.md"
    common = {
        "reference_path": str(SOURCE),
        "reference_sha256": SOURCE_SHA,
        "target_key_hex": "#00FF00",
    }
    records = [
        {
            **common,
            "id": "openai-a",
            "provider": "OpenAI subscription",
            "endpoint_or_model": "Codex subscription image tool via gpt-5.4",
            "prompt_family": "A",
            "prompt_path": str(prompt_a),
            "prompt_sha256": sha256(prompt_a),
            "seed": None,
            "seed_note": "not exposed by subscription wrapper",
            "cost_class": "subscription; no metered API charge",
            "command": [
                "python3", "scripts/subgen.py", "--provider", "openai",
                "--prompt-file", str(prompt_a), "--out", "{RAW}",
                "-i", str(SOURCE), "--timeout", "600", "--retries", "2",
                "--model", "gpt-5.4",
            ],
        },
        {
            **common,
            "id": "nano-a",
            "provider": "Nano Banana subscription",
            "endpoint_or_model": "Antigravity built-in generate_image",
            "prompt_family": "A",
            "prompt_path": str(prompt_a),
            "prompt_sha256": sha256(prompt_a),
            "seed": None,
            "seed_note": "not exposed by subscription wrapper",
            "cost_class": "subscription; no metered API charge",
            "command": [
                "python3", "scripts/subgen.py", "--provider", "nano",
                "--prompt-file", str(prompt_a), "--out", "{RAW}",
                "-i", str(SOURCE), "--timeout", "600", "--retries", "2",
            ],
        },
        {
            **common,
            "id": "flux2-a",
            "provider": "fal",
            "endpoint_or_model": "fal-ai/flux-2-pro/edit",
            "prompt_family": "A",
            "prompt_path": str(prompt_a),
            "prompt_sha256": sha256(prompt_a),
            "seed": 1403,
            "cost_class": "metered; official rate USD 0.03 first output MP plus USD 0.015 extra input/output MP",
            "command": [
                "python3", "scripts/falgen.py", "--mode", "flux2edit",
                "--image", str(SOURCE), "--out", "{RAW}",
                "--prompt-file", str(prompt_a), "--maxside", "1024",
                "--seed", "1403",
            ],
        },
        {
            **common,
            "id": "kontext-b",
            "provider": "fal",
            "endpoint_or_model": "fal-ai/flux-pro/kontext/max",
            "prompt_family": "B",
            "prompt_path": str(prompt_b),
            "prompt_sha256": sha256(prompt_b),
            "seed": 1404,
            "cost_class": "metered; official rate USD 0.08 per image",
            "command": [
                "python3", "scripts/falgen.py", "--mode", "kontextmax",
                "--image", str(SOURCE), "--out", "{RAW}",
                "--prompt-file", str(prompt_b), "--seed", "1404",
            ],
        },
    ]
    lock_value = {
        "created_at_utc": utc_now(),
        "max_valid_candidates": 4,
        "request_records": [{k: v for k, v in record.items() if k != "command"} for record in records],
    }
    write_manifest(lock, lock_value)

    terminal = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_command, record): record["id"] for record in records}
        for future in as_completed(futures):
            try:
                terminal.append(future.result())
            except Exception as exc:
                record = next(item for item in records if item["id"] == futures[future])
                terminal.append({
                    **record,
                    "status": "failed",
                    "finished_at_utc": utc_now(),
                    "error": f"{type(exc).__name__}: {redact(str(exc))}",
                })
            partial = {
                "status": "running",
                "source": image_info(SOURCE),
                "target_key_hex_new_candidates": "#00FF00",
                "terminal_candidates": sorted(terminal, key=lambda item: item["id"]),
            }
            write_manifest(OUT / "manifest.partial.json", partial)

    baseline_dir = OUT / "prior-magenta"
    baseline_dir.mkdir(exist_ok=True)
    baseline_raw = baseline_dir / "raw.png"
    shutil.copy2(PRIOR, baseline_raw)
    baseline = {
        "id": "prior-magenta",
        "provider": "existing Cursor regeneration baseline",
        "endpoint_or_model": "OpenAI image tool, prior session",
        "prompt_family": "prior",
        "prompt_path": str(REPO / "tasks/double-marine-bed-wrapper-batch/regen-v12/PROMPT-regen-v12-runtime.md"),
        "reference_path": str(SOURCE),
        "reference_sha256": SOURCE_SHA,
        "target_key_hex": "#FF00FF",
        "seed": None,
        "cost_class": "sunk prior call; no new request",
        "status": "read_only_baseline",
        "output": image_info(baseline_raw),
        "source_copy_path": str(PRIOR),
        "source_copy_sha256": sha256(PRIOR),
    }
    manifest = {
        "status": "terminal",
        "started_at_utc": lock_value["created_at_utc"],
        "finished_at_utc": utc_now(),
        "source": image_info(SOURCE),
        "style_contract_path": str(TASK / "STYLE-CONTRACT.md"),
        "style_contract_sha256": sha256(TASK / "STYLE-CONTRACT.md"),
        "target_key_hex_new_candidates": "#00FF00",
        "valid_new_candidate_count": sum(item.get("status") == "valid_output" for item in terminal),
        "terminal_new_candidate_count": len(terminal),
        "new_candidates": sorted(terminal, key=lambda item: item["id"]),
        "baseline": baseline,
    }
    write_manifest(manifest_path, manifest)
    (OUT / "manifest.partial.json").unlink(missing_ok=True)
    print(
        f"MATRIX_TERMINAL terminal={manifest['terminal_new_candidate_count']} "
        f"valid={manifest['valid_new_candidate_count']}"
    )
    for item in manifest["new_candidates"]:
        print(
            f"{item['id']} status={item['status']} duration={item.get('duration_seconds')} "
            f"size={item.get('output', {}).get('width')}x{item.get('output', {}).get('height')}"
        )


if __name__ == "__main__":
    main()
