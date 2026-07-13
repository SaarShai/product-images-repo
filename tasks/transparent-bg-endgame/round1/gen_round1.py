#!/usr/bin/env python3
"""Round-1 transparent-background experiment generator.

Build-only contract: dry-run and compile do not touch the network. A normal run
expects OPENAI_API_KEY via scripts/_falcommon.py::load_openai_key().
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
ROUND_DIR = Path(__file__).resolve().parent
RAW_DIR = ROUND_DIR / "raws"
PROMPT_DIR = ROUND_DIR / "prompts"
MANIFEST_PATH = ROUND_DIR / "MANIFEST.json"

sys.path.insert(0, str(REPO / "scripts"))
from _falcommon import load_openai_key  # noqa: E402


SIZE = "1024x1536"
QUALITY = "high"
SUBJECT = "H"
MAX_API_CALLS = 12
MAX_RETRIES = 1

IMAGES_ENDPOINT = "https://api.openai.com/v1/images/generations"
RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"

EDGE_CONTOUR_BLOCK = (
    "Every painted shape has a continuous, fully closed contour with no gaps "
    "or fade-outs, using a slightly darker or more saturated version of the "
    "adjacent local fill - never black and never white. Only the background may "
    "be pure #FFFFFF; every white-looking subject detail or highlight is a "
    "visibly tinted pastel off-white, fully enclosed by its contour."
)

EXCLUSIONS_BLOCK = (
    "No text, border, cut line, sticker rim, checkerboard, "
    "transparency-preview pattern, extra objects, or ground shadow."
)

KEYABLE_FINE_BLOCK = (
    "Fine detail is essential and must remain keyable: all thin fronds and "
    "antennae use full pigment strength, non-white mid-tones; every thinnest "
    "element has a closed contour; the minimum stroke is about a thick pencil "
    "line relative to the canvas; filaments are grouped into connected fans "
    "sharing one silhouette; no isolated strands over open background."
)

DEVIATION_AUTHORIZATION = (
    "Keyability overrides naturalism and reference fidelity for thin features "
    "only: thin fronds and antennae may be slightly sturdier, rounder, and "
    "grouped while keeping their intended color, position, and role."
)

ANTI_AURA_TAIL = (
    "isolated cutout on true transparency; transparent pixels begin immediately\n"
    "outside the outermost painted or inked subject contour; all pigment and\n"
    "paper-grain texture remain inside the subject silhouette only; no surrounding\n"
    "watercolor wash, color bloom, glow, aura, halo, rim light, backlight, mist,\n"
    "vignette, drop shadow, ambient color spill, or diffuse silhouette expansion;\n"
    "flat ambient lighting; preserve soft watercolor texture inside the forms, but\n"
    "no pigment outside them; only a 1-2 pixel antialiased transition at the\n"
    "actual art edge."
)

HARD_EDGE_BLOCK = (
    "the outer silhouette boundary is a crisp hard step; nothing feathers, "
    "fades, or blends outside the contour; no semi-transparent outer transition "
    "band; no anti-aliasing at the outermost edge; background color meets art "
    "color abruptly"
)

GREEN_BACKGROUND_CLAUSE = (
    "solid flat uniform background exactly #00FF00, every background pixel\n"
    "identical, no gradient, no vignette, no texture, no shadow, no glow; nothing\n"
    "cropped at the edges"
)

WHITE_BACKGROUND_CLAUSE = (
    "background: perfectly uniform solid pure #FFFFFF, flat, no texture, "
    "no gradient, no shadow"
)


@dataclass(frozen=True)
class Route:
    id: str
    model: str
    endpoint: str
    background: str | None
    native_alpha: bool


ROUTES = (
    Route("O1", "gpt-image-1", "/v1/images/generations", "transparent", True),
    Route("O2", "chatgpt-image-latest", "/v1/images/generations", "transparent", True),
    Route("C", "gpt-image-2", "/v1/responses", None, False),
    Route("W", "gpt-image-1", "/v1/images/generations", "opaque", False),
)


def build_base_prompt(prompt_level: str) -> str:
    parts = [
        "[SUBJECT H]",
        (
            "Create a single watercolor coral cluster with closed ink contours. "
            "The cluster must contain ALL of these visible elements: one "
            "legitimate green seaweed sprig, pale tinted off-white barnacle "
            "details, several deliberately thin fronds or antennae, and "
            "intentional negative-space gaps between branches. Nothing touches "
            "the canvas edges; keep a clear margin on all four sides."
        ),
        "",
        "[STYLE]",
        (
            "Soft professional children's-book watercolor: airy pastel color, "
            "translucent washes, gentle pigment variation and granulation, "
            "rounded organic coral forms, delicate ink-line detail, and soft "
            "ambient light."
        ),
        "",
        "[EDGE CONTOUR]",
        EDGE_CONTOUR_BLOCK,
        "",
        "[KEYABLE-FINE]",
        KEYABLE_FINE_BLOCK,
        DEVIATION_AUTHORIZATION,
        "",
        "[EXCLUSIONS]",
        EXCLUSIONS_BLOCK,
        "",
        "[ANTI-AURA]",
        ANTI_AURA_TAIL,
    ]
    if prompt_level == "HARD":
        parts.extend(["", "[FACTUAL HARD EDGE]", HARD_EDGE_BLOCK])
    return "\n".join(parts)


def prompt_key(route_id: str, prompt_level: str) -> str:
    if route_id in ("O1", "O2"):
        family = "native"
    elif route_id == "C":
        family = "green"
    elif route_id == "W":
        family = "white"
    else:
        raise ValueError(f"unknown route {route_id}")
    return f"{family}_{prompt_level}"


def build_prompt(route_id: str, prompt_level: str) -> str:
    prompt = build_base_prompt(prompt_level)
    if route_id == "C":
        prompt += "\n\n[ROUTE C-GREEN BACKGROUND]\n" + GREEN_BACKGROUND_CLAUSE
    elif route_id == "W":
        prompt += "\n\n[ROUTE W WHITE BACKGROUND]\n" + WHITE_BACKGROUND_CLAUSE
    return prompt


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def output_path(route_id: str, prompt_level: str) -> Path:
    return RAW_DIR / f"H_{route_id}_{prompt_level}_r1.png"


def attempt_path(route_id: str, prompt_level: str, attempt: int) -> Path:
    return RAW_DIR / f"H_{route_id}_{prompt_level}_r1_attempt{attempt}.png"


def prompt_path(route_id: str, prompt_level: str) -> Path:
    return PROMPT_DIR / f"{prompt_key(route_id, prompt_level)}.txt"


def alpha_stats(path: Path) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as img:
        if "A" not in img.getbands():
            return {
                "present": False,
                "mode": img.mode,
                "min": None,
                "max": None,
                "unique": 0,
                "zero_pct": 0.0,
                "soft_pct": 0.0,
                "opaque_pct": 0.0,
                "histogram": None,
            }
        alpha = img.getchannel("A")
        hist = alpha.histogram()
        total = sum(hist)
        nonzero_bins = [i for i, count in enumerate(hist) if count]
        zero = hist[0]
        opaque = hist[255]
        soft = total - zero - opaque
        return {
            "present": True,
            "mode": img.mode,
            "min": min(nonzero_bins),
            "max": max(nonzero_bins),
            "unique": len(nonzero_bins),
            "zero_pct": round(100.0 * zero / total, 4),
            "soft_pct": round(100.0 * soft / total, 4),
            "opaque_pct": round(100.0 * opaque / total, 4),
            "histogram": hist,
        }


def alpha_ok(stats: dict[str, Any]) -> bool:
    return (
        bool(stats.get("present"))
        and stats.get("min") == 0
        and stats.get("max") == 255
        and int(stats.get("unique") or 0) > 2
        and float(stats.get("zero_pct") or 0.0) > 0.0
    )


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {
            "experiment": "transparent-bg-endgame-round1",
            "subject": SUBJECT,
            "size": SIZE,
            "quality": QUALITY,
            "api_call_cap": MAX_API_CALLS,
            "entries": [],
        }
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def upsert_entry(manifest: dict[str, Any], entry: dict[str, Any]) -> None:
    entries = [e for e in manifest.get("entries", []) if e.get("id") != entry["id"]]
    entries.append(entry)
    manifest["entries"] = sorted(entries, key=lambda e: e["id"])
    manifest["updated_at_unix"] = round(time.time(), 3)
    save_manifest(manifest)


def ensure_prompt_files() -> dict[str, Path]:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    seen: dict[str, Path] = {}
    for route in ROUTES:
        for prompt_level in ("AA", "HARD"):
            key = prompt_key(route.id, prompt_level)
            if key in seen:
                continue
            path = prompt_path(route.id, prompt_level)
            path.write_text(build_prompt(route.id, prompt_level) + "\n")
            seen[key] = path
    return seen


def make_entry(route: Route, prompt_level: str, status: str) -> dict[str, Any]:
    prompt = build_prompt(route.id, prompt_level)
    return {
        "id": f"H-{route.id}-{prompt_level}-r1",
        "route": route.id,
        "prompt_level": prompt_level,
        "subject": SUBJECT,
        "model": route.model,
        "endpoint": route.endpoint,
        "params": route_params(route),
        "prompt_sha256": sha256_text(prompt),
        "prompt_file": rel(prompt_path(route.id, prompt_level)),
        "file": rel(output_path(route.id, prompt_level)),
        "alpha_stats": None,
        "wall_secs": 0.0,
        "usage": None,
        "status": status,
        "attempts": [],
    }


def route_params(route: Route) -> dict[str, Any]:
    if route.id == "C":
        return {
            "responses_model": "gpt-5",
            "tool": {
                "type": "image_generation",
                "model": route.model,
                "quality": QUALITY,
                "size": SIZE,
            },
            "background": True,
        }
    return {
        "model": route.model,
        "n": 1,
        "size": SIZE,
        "quality": QUALITY,
        "background": route.background,
    }


def post_images_generation(key: str, route: Route, prompt: str) -> dict[str, Any]:
    import requests

    payload = {
        "model": route.model,
        "prompt": prompt,
        "n": 1,
        "size": SIZE,
        "quality": QUALITY,
        "background": route.background,
    }
    response = requests.post(
        IMAGES_ENDPOINT,
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=180,
    )
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def submit_responses_job(key: str, prompt: str) -> str:
    import requests

    payload = {
        "model": "gpt-5",
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "tools": [
            {
                "type": "image_generation",
                "model": "gpt-image-2",
                "quality": QUALITY,
                "size": SIZE,
            }
        ],
        "background": True,
    }
    response = requests.post(
        RESPONSES_ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"submit failed HTTP {response.status_code}: {response.text[:500]}")
    return response.json()["id"]


def poll_responses_job(key: str, response_id: str, timeout_s: int = 600) -> dict[str, Any]:
    import requests

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        response = requests.get(
            f"{RESPONSES_ENDPOINT}/{response_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        job = response.json()
        status = job.get("status")
        if status in ("completed", "failed", "cancelled", "incomplete"):
            return job
        time.sleep(5)
    raise TimeoutError(f"job {response_id} did not complete within {timeout_s}s")


def extract_responses_image_b64(job: dict[str, Any]) -> str | None:
    for item in job.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    return None


def write_image_from_generation_json(response_json: dict[str, Any], path: Path) -> None:
    data = response_json.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise RuntimeError("no data[0].b64_json in image generation response")
    path.write_bytes(base64.b64decode(data[0]["b64_json"]))


def generate_once(
    key: str,
    route: Route,
    prompt_level: str,
    attempt: int,
) -> tuple[Path, dict[str, Any], dict[str, Any] | None, str | None]:
    prompt = build_prompt(route.id, prompt_level)
    out = attempt_path(route.id, prompt_level, attempt)
    if route.id == "C":
        response_id = submit_responses_job(key, prompt)
        job = poll_responses_job(key, response_id)
        b64_image = extract_responses_image_b64(job)
        if not b64_image:
            raise RuntimeError(f"no image_generation_call result: {job.get('error') or job.get('status')}")
        out.write_bytes(base64.b64decode(b64_image))
        return out, job, job.get("usage"), response_id

    response_json = post_images_generation(key, route, prompt)
    write_image_from_generation_json(response_json, out)
    return out, response_json, response_json.get("usage"), None


def run_cell(
    key: str,
    manifest: dict[str, Any],
    route: Route,
    prompt_level: str,
    api_calls_used: int,
) -> int:
    final_path = output_path(route.id, prompt_level)
    entry = make_entry(route, prompt_level, "pending")

    if final_path.exists():
        entry["status"] = "skipped_existing"
        if route.native_alpha:
            entry["alpha_stats"] = alpha_stats(final_path)
        upsert_entry(manifest, entry)
        print(f"SKIP existing {entry['id']} -> {rel(final_path)}")
        return api_calls_used

    for attempt in range(1, MAX_RETRIES + 2):
        if api_calls_used >= MAX_API_CALLS:
            entry["status"] = "api_cap_exhausted"
            upsert_entry(manifest, entry)
            print(f"CAP  {entry['id']} (api call cap {MAX_API_CALLS} reached)")
            return api_calls_used

        api_calls_used += 1
        attempt_record: dict[str, Any] = {"attempt": attempt, "api_call_number": api_calls_used}
        t0 = time.time()
        try:
            attempt_file, response_json, usage, response_id = generate_once(key, route, prompt_level, attempt)
            wall_secs = round(time.time() - t0, 3)
            stats = alpha_stats(attempt_file) if route.native_alpha else None
            attempt_record.update(
                {
                    "status": "generated",
                    "file": rel(attempt_file),
                    "wall_secs": wall_secs,
                    "usage": usage,
                    "response_id": response_id,
                    "alpha_stats": stats,
                }
            )
            entry["attempts"].append(attempt_record)
            entry["wall_secs"] = round(float(entry["wall_secs"]) + wall_secs, 3)
            entry["usage"] = usage
            entry["alpha_stats"] = stats

            if route.native_alpha and not alpha_ok(stats or {}):
                entry["status"] = "alpha_failed"
                upsert_entry(manifest, entry)
                print(f"RETRY alpha failed {entry['id']} attempt {attempt}")
                continue

            attempt_file.replace(final_path)
            entry["file"] = rel(final_path)
            entry["status"] = "ok"
            upsert_entry(manifest, entry)
            print(f"OK   {entry['id']} -> {rel(final_path)}")
            return api_calls_used

        except Exception as exc:  # noqa: BLE001 - keep one bad route from aborting the matrix.
            wall_secs = round(time.time() - t0, 3)
            attempt_record.update(
                {
                    "status": "error",
                    "wall_secs": wall_secs,
                    "error": str(exc),
                }
            )
            entry["attempts"].append(attempt_record)
            entry["wall_secs"] = round(float(entry["wall_secs"]) + wall_secs, 3)
            entry["status"] = "error"
            upsert_entry(manifest, entry)
            print(f"ERR  {entry['id']} attempt {attempt}: {exc}", file=sys.stderr)

    return api_calls_used


def plan_rows() -> list[dict[str, Any]]:
    rows = []
    for route in ROUTES:
        for prompt_level in ("AA", "HARD"):
            rows.append(
                {
                    "id": f"H-{route.id}-{prompt_level}-r1",
                    "route": route.id,
                    "prompt_level": prompt_level,
                    "model": route.model,
                    "endpoint": route.endpoint,
                    "params": route_params(route),
                    "prompt_file": rel(prompt_path(route.id, prompt_level)),
                    "prompt_sha256": sha256_text(build_prompt(route.id, prompt_level)),
                    "file": rel(output_path(route.id, prompt_level)),
                }
            )
    return rows


def dry_run() -> None:
    print(
        json.dumps(
            {
                "mode": "dry-run",
                "network_calls": 0,
                "api_call_cap": MAX_API_CALLS,
                "round_dir": rel(ROUND_DIR),
                "manifest": rel(MANIFEST_PATH),
                "prompt_files_unique": sorted({row["prompt_file"] for row in plan_rows()}),
                "generations": plan_rows(),
            },
            indent=2,
            sort_keys=True,
        )
    )


def run() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ensure_prompt_files()
    manifest = load_manifest()
    manifest["planned_generations"] = plan_rows()
    manifest["prompt_files_unique"] = sorted({row["prompt_file"] for row in plan_rows()})
    save_manifest(manifest)

    key = load_openai_key()
    api_calls_used = 0
    for route in ROUTES:
        for prompt_level in ("AA", "HARD"):
            api_calls_used = run_cell(key, manifest, route, prompt_level, api_calls_used)
    manifest["api_calls_used_this_run"] = api_calls_used
    save_manifest(manifest)
    print(f"done: api_calls_used={api_calls_used}, manifest={rel(MANIFEST_PATH)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the generation plan; make no API calls")
    args = parser.parse_args()
    if args.dry_run:
        dry_run()
    else:
        run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
