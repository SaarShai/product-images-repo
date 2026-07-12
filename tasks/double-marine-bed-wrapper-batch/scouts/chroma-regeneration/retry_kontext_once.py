#!/usr/bin/env python3
"""Use the brief's single transient no-image retry for Kontext, then lock."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[4]
OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/chroma-regeneration/image14"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(text: str) -> str:
    text = re.sub(r"(?i)(authorization|FAL_KEY|api[_ -]?key|token)[=: ]+\S+", r"\1=[redacted]", text)
    text = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[redacted-data-uri]", text)
    text = re.sub(r"https?://\S*(?:fal\.media|fal\.run)\S*", "[redacted-provider-url]", text)
    return text[-6000:]


def image_info(path: Path) -> dict:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return {
            "path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
            "width": image.width, "height": image.height, "mode": image.mode, "format": image.format,
        }


def main() -> None:
    lock = OUT / "kontext-transient-retry-lock.json"
    manifest_path = OUT / "manifest.json"
    if lock.exists():
        raise SystemExit(f"refusing additional Kontext retry: {lock} exists")
    manifest = json.loads(manifest_path.read_text())
    records = manifest["new_candidates"]
    record = next(item for item in records if item["id"] == "kontext-b")
    diagnostic = record.get("stderr_tail_redacted", "")
    if record.get("status") != "failed" or "RemoteDisconnected" not in diagnostic:
        raise SystemExit("Kontext record is not the authorized transient RemoteDisconnected/no-image case")
    raw = Path(record["command"][record["command"].index("--out") + 1])
    if raw.exists():
        raise SystemExit("unexpected existing Kontext output; refusing retry")

    first_attempt = {
        "status": record.get("status"),
        "started_at_utc": record.get("started_at_utc"),
        "finished_at_utc": record.get("finished_at_utc"),
        "duration_seconds": record.get("duration_seconds"),
        "return_code": record.get("return_code"),
        "stderr_tail_redacted": diagnostic,
        "charge_status": "unknown because transport closed without HTTP response",
    }
    lock.write_text(json.dumps({
        "created_at_utc": utc_now(),
        "authorized_retry_count": 1,
        "reason": "top-level brief permits one transient no-image retry; first attempt RemoteDisconnected with no output",
        "same_command": record["command"],
        "same_prompt_sha256": record["prompt_sha256"],
        "same_reference_sha256": record["reference_sha256"],
        "same_seed": record["seed"],
    }, indent=2) + "\n")

    started_at = utc_now()
    started = time.perf_counter()
    result = subprocess.run(
        record["command"], cwd=REPO, env=os.environ.copy(), capture_output=True, text=True, timeout=360,
    )
    retry = {
        "status": "failed",
        "started_at_utc": started_at,
        "finished_at_utc": utc_now(),
        "duration_seconds": round(time.perf_counter() - started, 6),
        "return_code": result.returncode,
        "stdout_tail_redacted": redact(result.stdout or ""),
        "stderr_tail_redacted": redact(result.stderr or ""),
    }
    if result.returncode == 0 and raw.is_file():
        retry["status"] = "valid_output"
        retry["output"] = image_info(raw)
    artifact = Path(str(raw) + ".artifact.json")
    if artifact.is_file():
        retry["fal_artifact_path"] = str(artifact)
        retry["fal_artifact_sha256"] = sha256(artifact)

    record["attempt_history"] = [first_attempt, retry]
    record["transient_retry_used"] = True
    record["transient_retry_count"] = 1
    record["status"] = retry["status"]
    for field in (
        "started_at_utc", "finished_at_utc", "duration_seconds", "return_code",
        "stdout_tail_redacted", "stderr_tail_redacted", "output",
        "fal_artifact_path", "fal_artifact_sha256",
    ):
        if field in retry:
            record[field] = retry[field]
        else:
            record.pop(field, None)
    manifest["valid_new_candidate_count"] = sum(item.get("status") == "valid_output" for item in records)
    manifest["kontext_transient_retry_used"] = True
    manifest["kontext_first_attempt_charge_status"] = first_attempt["charge_status"]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        f"KONTEXT_RETRY_TERMINAL status={retry['status']} duration={retry['duration_seconds']} "
        f"size={retry.get('output', {}).get('width')}x{retry.get('output', {}).get('height')}"
    )


if __name__ == "__main__":
    main()
