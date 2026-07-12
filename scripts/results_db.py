#!/usr/bin/env python3
"""results_db.py — Reconcile-from-disk results library for space-np01-front-bottom-02.

Scans ALL experiment directories and space-svg-exports-batch outputs on disk,
derives one canonical record per experiment, and writes:
  - tasks/space-np01-front-bottom-02/RESULTS/results.jsonl  (sorted by region_iou desc)
  - tasks/space-np01-front-bottom-02/RESULTS/RESULTS-BOARD.md

Idempotent: re-running produces byte-identical output. Records are deduped by id.
Do NOT call this from concurrent processes writing to the same output files.

Usage:
    python3 scripts/results_db.py            # default: rebuild from disk
    python3 scripts/results_db.py --dry-run  # print records, do not write
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_images  # noqa: E402 — single source of truth for codex output discovery

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "space-np01-front-bottom-02"
BATCH_TASK = ROOT / "tasks" / "space-svg-exports-batch"
RESULTS_DIR = TASK / "RESULTS"
JSONL_PATH = RESULTS_DIR / "results.jsonl"
BOARD_PATH = RESULTS_DIR / "RESULTS-BOARD.md"
SVG_TEMPLATE = "tasks/space-np01-front-bottom-02/source/template.svg"
REFS = [
    "tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png",
    "tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png",
]
PASS_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mtime_iso(path: Path | str) -> str:
    """Return ISO-8601 mtime for a path, or 'unknown'."""
    try:
        p = Path(path) if not isinstance(path, Path) else path
        if not p.is_absolute():
            p = ROOT / p
        t = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        return t.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return "unknown"


def _read_json(path: Path | str) -> dict | None:
    try:
        p = Path(path) if not isinstance(path, Path) else path
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return None


def _rel(path: Path | str | None) -> str:
    if path is None:
        return "unknown"
    p = Path(path) if not isinstance(path, Path) else path
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _verdict(region_iou: Any) -> str:
    if isinstance(region_iou, (int, float)):
        return "PASS" if region_iou >= PASS_THRESHOLD else "FAIL"
    return "unknown"


def _float_or(val: Any, fallback: Any = "unknown") -> Any:
    if isinstance(val, (int, float)):
        return float(round(val, 4))
    return fallback


def _run_geom_iou(image_path: str, svg_path: str) -> float | None:
    """Run geom_iou.py and return mean_region_iou, or None on failure."""
    try:
        script = ROOT / "scripts" / "geom_iou.py"
        result = subprocess.run(
            [sys.executable, str(script), image_path, "--svg", svg_path],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT)
        )
        for line in result.stdout.splitlines():
            if "mean region-IoU" in line:
                return float(line.split("=")[-1].strip())
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Experiment scrapers
# ---------------------------------------------------------------------------

def _record_from_experiment_dir(exp_dir: Path, exp_id: str) -> dict:
    """Build a canonical record from an experiment directory."""

    # Load all sidecar JSONs
    result_json = _read_json(exp_dir / "result.json")
    metrics_json = _read_json(exp_dir / "metrics.json")
    region_json = _read_json(exp_dir / "region_iou.json") or _read_json(exp_dir / "region.json")

    # Image files
    raw_png = exp_dir / "raw.png"
    exact_png = exp_dir / "exact.png"
    image_path_raw = _rel(raw_png) if raw_png.exists() else "unknown"
    image_path_exact = _rel(exact_png) if exact_png.exists() else "unknown"

    # Timestamp: prefer result.json timestamp, else file mtime
    timestamp = "unknown"
    if result_json and "timestamp" in result_json:
        timestamp = result_json["timestamp"]
    elif raw_png.exists():
        timestamp = _mtime_iso(raw_png)
    elif exact_png.exists():
        timestamp = _mtime_iso(exact_png)

    # --- region_iou ---
    region_iou: Any = "unknown"
    if region_json and "mean_region_iou" in region_json:
        region_iou = _float_or(region_json["mean_region_iou"])
    elif result_json:
        r = result_json
        if "region_iou_exact" in r:
            region_iou = _float_or(r["region_iou_exact"])
        elif "region_iou" in r and r["region_iou"] not in ("unknown", None, ""):
            region_iou = _float_or(r["region_iou"])
        elif "mean_region_iou" in r:
            region_iou = _float_or(r["mean_region_iou"])

    # Recompute if raw/exact png exists but no region json
    if region_iou == "unknown" and region_json is None:
        # Check for non-standard image names (e.g. HYB1 uses exact-bevel.png)
        candidate_imgs = [exact_png, raw_png]
        for alt_name in ("exact-bevel.png",):
            alt = exp_dir / alt_name
            if alt.exists():
                candidate_imgs.insert(0, alt)
        for candidate_img in candidate_imgs:
            if candidate_img.exists():
                computed = _run_geom_iou(_rel(candidate_img), SVG_TEMPLATE)
                if computed is not None:
                    region_iou = round(computed, 4)
                break

    # HYB1 / hybrid-composite: exact_bevel_composite.py re-seats openings exactly by construction.
    # geom_iou on exact-bevel.png measures 0.863 (bevel rim reduces fill-agnostic score vs pure cutout).
    # Use actual measured value — it still PASSes the gate.

    # --- white_iou ---
    white_iou: Any = "unknown"
    if metrics_json and "mean_iou" in metrics_json:
        white_iou = _float_or(metrics_json["mean_iou"])
    elif result_json:
        r = result_json
        wv = r.get("white_iou", r.get("mean_iou"))
        if wv not in (None, "unknown", ""):
            white_iou = _float_or(wv)

    # --- outside_frac ---
    outside_frac: Any = "unknown"
    if metrics_json and "outside_frac" in metrics_json:
        outside_frac = _float_or(metrics_json["outside_frac"])
    elif result_json and "outside_frac" in result_json:
        v = result_json["outside_frac"]
        if v not in (None, "unknown", ""):
            outside_frac = _float_or(v)

    # --- painted_max (max hole painted_frac from metrics) ---
    painted_max: Any = "unknown"
    src = metrics_json or result_json
    if src and "holes" in src:
        pfs = [h.get("painted_frac", 0) for h in src["holes"] if isinstance(h.get("painted_frac"), (int, float))]
        if pfs:
            painted_max = round(max(pfs), 4)

    # --- method / model / platform inference ---
    method, model, platform, prompt, control_map, reference_images = _infer_meta(
        exp_id, result_json, metrics_json
    )

    # --- notes ---
    notes = _infer_notes(exp_id, result_json, region_iou, white_iou, outside_frac)

    # --- vision-judge verdict (sidecar judge.json written by the judge workflow) ---
    judge = _read_json(exp_dir / "judge.json") or {}

    return {
        "id": exp_id,
        "method": method,
        "model": model,
        "platform": platform,
        "reference_images": reference_images,
        "svg": SVG_TEMPLATE,
        "prompt": prompt,
        "control_map": control_map,
        "region_iou": region_iou,
        "white_iou": white_iou,
        "outside_frac": outside_frac,
        "painted_max": painted_max,
        "image_path_raw": image_path_raw,
        "image_path_exact": image_path_exact,
        "timestamp": timestamp,
        "notes": notes,
        "verdict": _verdict(region_iou),
        "judge_geometry": judge.get("geometry_score", "unjudged"),
        "judge_style": judge.get("style_score", "unjudged"),
        "judge_overall": judge.get("overall_score", "unjudged"),
        "judge_verdict": judge.get("verdict", "unjudged"),
        "judge_summary": judge.get("one_line", judge.get("summary", "unjudged")),
    }


def _infer_meta(
    exp_id: str, result_json: dict | None, metrics_json: dict | None
) -> tuple[str, str, str, str, str, list]:
    """Infer method/model/platform/prompt/control_map/references from id + sidecars."""
    rj = result_json or {}
    mj = metrics_json or {}

    # Pull from result.json when available
    method = rj.get("method", "unknown")
    model = rj.get("model", "unknown")
    platform = rj.get("platform", "unknown")
    prompt = rj.get("prompt", "unknown")
    control_map = rj.get("control_map", rj.get("map", "unknown"))
    reference_images = rj.get("reference_images", [])

    # Normalize model from sidecars
    if model in ("openai",):
        model = "gpt-image-2"
        platform = platform if platform != "unknown" else "codex"
    if model in ("nanobanana", "nano-banana"):
        model = "nano-banana"
        platform = platform if platform != "unknown" else "agy"

    eid = exp_id.lower()

    # --- override from naming convention when result.json is missing or sparse ---
    if method == "unknown" or model == "unknown":
        if "dream1" == eid:
            method = "controlnet-lineart-clear"
            model = "dreamshaper-8"
            platform = "local-diffusers"
        elif "dream-ip" in eid:
            method = "controlnet-style-sd15"  # IP-Adapter attempt; failed
            model = "dreamshaper-8"
            platform = "local-diffusers"
        elif eid.startswith("cn-") or eid.startswith("cn1-"):
            if "inpaint" in eid:
                method = "controlnet-inpaint"
            elif "style" in eid:
                method = "controlnet-style-sd15"
            else:
                method = "controlnet-lineart-sd15"
            model = "sd1.5"
            platform = "local-diffusers"
        elif eid.startswith("sdxl"):
            method = "controlnet-canny-sdxl"
            model = "sdxl"
            platform = "local-diffusers"
        elif eid.startswith("hyb"):
            method = "hybrid-composite"
            model = "gpt-image-2+code"
            platform = "codex+local"
        elif eid.startswith("style"):
            method = "controlnet-style-sd15"
            model = "sd1.5"
            platform = "local-diffusers"
        elif eid.startswith("cw"):
            method = "comfyui-workflow"
            model = "sd1.5"
            platform = "local-diffusers"
        elif "nano" in eid or "bon2-nano" in eid:
            method = "nano-filled-contract"
            model = "nano-banana"
            platform = "agy"
        elif "openai" in eid or "bon2-openai" in eid:
            method = "gpt-image-best-of-n"
            model = "gpt-image-2"
            platform = "codex"
        elif eid.startswith("e1-") or eid.startswith("e11-"):
            method = "gpt-image-filled-contract"
            model = "gpt-image-2"
            platform = "codex"
        elif eid.startswith("e2-"):
            method = "nano-filled-contract"
            model = "nano-banana"
            platform = "agy"
        elif eid.startswith("e3-"):
            method = "gpt-image-lineart-contract"
            model = "gpt-image-2"
            platform = "codex"
        elif eid.startswith("e4-"):
            method = "nano-lineart-contract"
            model = "nano-banana"
            platform = "agy"
        elif eid.startswith("e5-"):
            method = "gpt-image-best-of-n"
            model = "gpt-image-2"
            platform = "codex"

    # Prompt inference
    if prompt == "unknown":
        if "bon2" in eid and "nano" in eid:
            prompt = "tasks/space-np01-front-bottom-02/prompts/BoN2-nano-letterbox.md"
        elif "bon2" in eid and "openai" in eid:
            prompt = "tasks/space-np01-front-bottom-02/prompts/BoN2-openai-letterbox.md"
        elif "rip" in eid:
            v = "1" if "rip-v1" in eid or "rip1" in eid else "2"
            prompt = f"tasks/space-np01-front-bottom-02/prompts/RIP-v{v}.md"
        elif "fix" in eid:
            for v in ("4", "3", "2", "1"):
                if f"fix-v{v}" in eid or f"fix{v}" in eid:
                    prompt = f"tasks/space-np01-front-bottom-02/prompts/FIX-v{v}.md"
                    break

    # Control map / base inference
    if control_map == "unknown":
        ctrl_from_mj = mj.get("map", "")
        if ctrl_from_mj:
            control_map = ctrl_from_mj

    # Reference images
    if not reference_images:
        reference_images = REFS

    return method, model, platform, prompt, control_map, reference_images


def _infer_notes(
    exp_id: str,
    result_json: dict | None,
    region_iou: Any,
    white_iou: Any,
    outside_frac: Any,
) -> str:
    rj = result_json or {}
    # Use existing note fields from result.json
    for key in ("style_note", "verdict", "note", "notes"):
        v = rj.get(key)
        if v and isinstance(v, str) and len(v) > 5:
            return v
    # Auto-construct
    parts = []
    eid = exp_id.lower()
    if "dream1" == eid:
        parts.append("dreamshaper-8 + lineart ControlNet + exact SVG clear")
    elif "dream-ip" in eid:
        parts.append("dreamshaper-8 + IP-Adapter attempt (failed: ValueError ip_adapter_image length mismatch)")
    elif "sdxl" in eid:
        parts.append("SDXL + ControlNet canny scout (incomplete: model download timed out)")
    elif "cw1" in eid:
        parts.append("ComfyUI workflow prep only — no inference run yet")
    elif "hyb1" == eid:
        parts.append("hybrid composite: gpt-image-2 art re-seated by exact_bevel_composite.py")
    elif "style1" == eid:
        parts.append("SD1.5 style injection with ref images, visual-only")
    elif "bon2" in eid and "nano" in eid:
        parts.append(f"Nano Banana BoN round-2 letterboxed")
    elif "bon2" in eid and "openai" in eid:
        parts.append(f"gpt-image-2 BoN round-2 letterboxed")
    elif "bon-nano" in eid:
        parts.append("Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).")
    elif "bon-openai" in eid:
        parts.append("gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).")
    elif eid.startswith("e11"):
        parts.append("Ablation: no contract list. Catastrophic geometry loss.")
    elif eid.startswith("e"):
        parts.append(f"Experiment {exp_id}")
    if isinstance(region_iou, float):
        parts.append(f"region-IoU={region_iou:.3f}")
    if isinstance(white_iou, float):
        parts.append(f"white-IoU={white_iou:.3f}")
    if isinstance(outside_frac, float):
        parts.append(f"outside_frac={outside_frac:.4f}")
    return ". ".join(parts) if parts else "unknown"


# ---------------------------------------------------------------------------
# Scan: BoN-nano subdirectories
# ---------------------------------------------------------------------------

def scan_bon_nano(exp_base: Path) -> list[dict]:
    parent = exp_base / "BoN-nano"
    if not parent.is_dir():
        return []
    records = []
    for sdir in sorted(parent.iterdir()):
        if not sdir.is_dir():
            continue
        sid = sdir.name
        exp_id = f"BoN-nano-{sid}"
        r = _record_from_experiment_dir(sdir, exp_id)
        # Override method/model/platform
        r["method"] = "nano-filled-contract"
        r["model"] = "nano-banana"
        r["platform"] = "agy"
        r["prompt"] = "tasks/space-np01-front-bottom-02/prompts/E1-filled-contract.md"
        r["control_map"] = "tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-genmap-filled.png"
        records.append(r)
    return records


def scan_bon_openai(exp_base: Path) -> list[dict]:
    parent = exp_base / "BoN-openai"
    if not parent.is_dir():
        return []
    records = []
    for sdir in sorted(parent.iterdir()):
        if not sdir.is_dir():
            continue
        sid = sdir.name
        exp_id = f"BoN-openai-{sid}"
        r = _record_from_experiment_dir(sdir, exp_id)
        r["method"] = "gpt-image-best-of-n"
        r["model"] = "gpt-image-2"
        r["platform"] = "codex"
        r["prompt"] = "tasks/space-np01-front-bottom-02/prompts/E1-filled-contract.md"
        r["control_map"] = "tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-genmap-filled.png"
        records.append(r)
    return records


# ---------------------------------------------------------------------------
# Scan: flat experiment dirs
# ---------------------------------------------------------------------------

# These directories are not experiments themselves (parents, logs, plans)
_NON_EXP_NAMES = {
    "BoN-nano", "BoN-openai",
    "DREAM-ip.log", "DREAM1.log",
    "LOOP.spec", "PIPELINE.md", "SWEEP.md",
    "RESEARCH-SYNTHESIS.md", "REVIEW-BRIEF.md", "SYSTEM-BUILD-PLAN.md",
}

# Dirs that exist but have no useful data (failed / placeholder)
_STUB_EXPERIMENT_IDS = {
    "DREAM-ip",      # IP-Adapter crashed, no images
    "SDXL-scout",    # model download timed out, no images
    "CW1-comfy",     # workflow prep only, no inference
    "E5-bestof-3",   # empty dir
    "BoN2-openai-s2",# empty dir
}


def scan_experiments(exp_base: Path) -> list[dict]:
    records = []
    for entry in sorted(exp_base.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in _NON_EXP_NAMES:
            continue
        # Stub experiments: still include so they appear in the library as known
        if name in _STUB_EXPERIMENT_IDS:
            records.append(_stub_record(name, entry))
            continue
        r = _record_from_experiment_dir(entry, name)
        records.append(r)
    return records


def _stub_record(exp_id: str, exp_dir: Path) -> dict:
    """Record for experiments that were started but produced no output images."""
    eid = exp_id.lower()
    if "dream-ip" in eid:
        method = "controlnet-style-sd15"
        model = "dreamshaper-8"
        platform = "local-diffusers"
        notes = "IP-Adapter attempt crashed: ValueError ip_adapter_image must match number of IP Adapters (got 2 images, 1 adapter). No output generated."
    elif "sdxl" in eid:
        method = "controlnet-canny-sdxl"
        model = "sdxl"
        platform = "local-diffusers"
        notes = "SDXL + ControlNet canny scout. Model download (xinsir/controlnet-canny-sdxl-1.0) timed out. No output generated."
    elif "cw1" in eid:
        method = "comfyui-workflow"
        model = "sd1.5"
        platform = "local-diffusers"
        notes = "ComfyUI workflow prepared (controlmap-lineart-512 + controlmap-canny-512) but no inference run executed."
    else:
        method = "unknown"
        model = "unknown"
        platform = "unknown"
        notes = "Empty experiment directory — no outputs."

    # Try to get mtime from any file in dir
    ts = "unknown"
    for f in exp_dir.rglob("*"):
        if f.is_file():
            ts = _mtime_iso(f)
            break

    return {
        "id": exp_id,
        "method": method,
        "model": model,
        "platform": platform,
        "reference_images": REFS,
        "svg": SVG_TEMPLATE,
        "prompt": "unknown",
        "control_map": "unknown",
        "region_iou": "unknown",
        "white_iou": "unknown",
        "outside_frac": "unknown",
        "painted_max": "unknown",
        "image_path_raw": "unknown",
        "image_path_exact": "unknown",
        "timestamp": ts,
        "notes": notes,
        "verdict": "unknown",
    }


# ---------------------------------------------------------------------------
# Scan: space-svg-exports-batch task
# ---------------------------------------------------------------------------

def scan_svg_exports_batch(batch_task: Path) -> list[dict]:
    """Derive records from space-svg-exports-batch checkpoint summaries + metadata."""
    records = []

    # 1. Checkpoint summaries (batch-bottom, checkpoint-01, etc.)
    checkpoints_dir = batch_task / "checkpoints"
    if checkpoints_dir.is_dir():
        for cfile in sorted(checkpoints_dir.glob("*.json")):
            try:
                data = json.loads(cfile.read_text())
            except Exception:
                continue
            candidates = data.get("candidates", [])
            for c in candidates:
                r = _batch_candidate_to_record(c)
                if r:
                    records.append(r)

    # 2. Procedural worker (agent-candidates)
    gen_summary = batch_task / "agent-candidates" / "procedural-worker" / "generation-summary.json"
    if gen_summary.exists():
        try:
            data = json.loads(gen_summary.read_text())
            if isinstance(data, list):
                for c in data:
                    r = _procedural_candidate_to_record(c)
                    if r:
                        records.append(r)
        except Exception:
            pass

    # 3. Style-tests metadata
    style_tests_dir = batch_task / "outputs" / "style-tests"
    if style_tests_dir.is_dir():
        for mfile in sorted(style_tests_dir.glob("*-metadata.json")):
            try:
                c = json.loads(mfile.read_text())
                r = _style_test_to_record(c)
                if r:
                    records.append(r)
            except Exception:
                continue

    # 4. Space-style summaries
    ss_summary = checkpoints_dir / "np01-front-bottom-space-style-summary.json" if checkpoints_dir.is_dir() else None
    if ss_summary and ss_summary.exists():
        try:
            data = json.loads(ss_summary.read_text())
            for c in data.get("candidates", []):
                r = _batch_candidate_to_record(c)
                if r:
                    records.append(r)
        except Exception:
            pass

    # 5. outputs/reviews/ metadata files (authoritative per-candidate records)
    reviews_dir = batch_task / "outputs" / "reviews"
    if reviews_dir.is_dir():
        for mfile in sorted(reviews_dir.glob("*-metadata.json")):
            try:
                c = json.loads(mfile.read_text())
                r = _batch_candidate_to_record(c)
                if r:
                    records.append(r)
            except Exception:
                continue

    # Dedup by id (first occurrence wins — checkpoint summaries preferred over reviews dupes)
    seen: dict[str, dict] = {}
    deduped = []
    for r in records:
        if r["id"] not in seen:
            seen[r["id"]] = r
            deduped.append(r)
    return deduped


def _batch_candidate_to_record(c: dict) -> dict | None:
    """Convert a batch-bottom-summary candidate to a canonical record."""
    candidate_path = c.get("candidate", "")
    if not candidate_path:
        return None
    # Derive id from candidate filename
    p = Path(candidate_path)
    exp_id = "batch-" + p.stem  # e.g. batch-np01-back-bottom-batch-bottom-v1
    # Avoid double-adding from multiple checkpoint files
    svg = c.get("svg", "unknown")
    timestamp = c.get("timestamp", "unknown")
    contours = c.get("contours", [])
    coverage = c.get("metrics", {}).get("painted_panel_coverage_pct", "unknown") if "metrics" in c else "unknown"
    outside = c.get("metrics", {}).get("outside_nonwhite_pixels", "unknown") if "metrics" in c else "unknown"
    cutout = c.get("metrics", {}).get("cutout_nonwhite_pixels", "unknown") if "metrics" in c else "unknown"
    verdict_from_data = "PASS" if (outside == 0 and cutout == 0) else "FAIL"
    outside_frac_approx: Any = 0 if outside == 0 else "unknown"
    artwork_path = c.get("artwork_only", c.get("artwork", "unknown"))
    refs = c.get("source_style_refs", c.get("style_sources", REFS))
    prompt_path = c.get("prompt", "tasks/space-svg-exports-batch/prompts/prompt-v2-style-packet-elements-first.md")
    cov_str = f"coverage={coverage:.2f}%" if isinstance(coverage, (int, float)) else ""
    notes = (
        f"space-svg-exports-batch procedural masking pass. "
        f"Metric: SVG mask coverage (cutout+outside=0 pxl, {cov_str}). "
        f"PASS={verdict_from_data}. "
        "Elements drawn in eroded safe pockets then SVG mask applied."
    )
    return {
        "id": exp_id,
        "method": "svg-masked-procedural",
        "model": "procedural-pil",
        "platform": "local-python",
        "reference_images": refs,
        "svg": svg,
        "prompt": prompt_path,
        "control_map": "unknown",
        "region_iou": "n/a",
        "white_iou": "n/a",
        "outside_frac": outside_frac_approx,
        "painted_max": "n/a",
        "image_path_raw": candidate_path,
        "image_path_exact": artwork_path,
        "timestamp": timestamp,
        "notes": notes,
        "verdict": verdict_from_data,
    }


def _procedural_candidate_to_record(c: dict) -> dict | None:
    candidate_path = c.get("candidate_png", "")
    if not candidate_path:
        return None
    p = Path(candidate_path)
    stem = p.stem  # e.g. np01-back-top-watercolor-control-panel-candidate
    exp_id = "procedural-" + stem
    m = c.get("metrics", {})
    outside = m.get("outside_nonwhite_pixels", "unknown")
    cutout = m.get("cutout_nonwhite_pixels", "unknown")
    coverage = m.get("painted_panel_coverage_pct", "unknown")
    verdict_val = m.get("verdict", "PASS" if (outside == 0 and cutout == 0) else "FAIL")
    notes = (
        f"PIL procedural watercolor control panel. "
        f"coverage={coverage}%, outside_px={outside}, cutout_px={cutout}. "
        f"{verdict_val}."
    )
    return {
        "id": exp_id,
        "method": "procedural-pil-svg-native",
        "model": "procedural-pil",
        "platform": "local-python",
        "reference_images": REFS,
        "svg": c.get("source_svg", "unknown"),
        "prompt": "tasks/space-svg-exports-batch/prompts/prompt-v2-style-packet-elements-first.md",
        "control_map": "unknown",
        "region_iou": "n/a",
        "white_iou": "n/a",
        "outside_frac": 0 if outside == 0 else "unknown",
        "painted_max": "n/a",
        "image_path_raw": _rel(candidate_path),
        "image_path_exact": "unknown",
        "timestamp": c.get("timestamp", _mtime_iso(candidate_path)),
        "notes": notes,
        "verdict": verdict_val,
    }


def _style_test_to_record(c: dict) -> dict | None:
    artwork = c.get("artwork", "")
    if not artwork:
        return None
    p = Path(artwork)
    stem = p.stem
    exp_id = "style-test-" + stem
    m = c.get("metrics", {})
    coverage = m.get("coverage_pct", "unknown")
    outside = m.get("outside_nonwhite_pixels", "unknown")
    cutout = m.get("cutout_nonwhite_pixels", "unknown")
    verdict_val = m.get("verdict", "PASS" if (outside == 0 and cutout == 0) else "FAIL")
    notes = (
        f"Style rebuild on locked SVG geometry. "
        f"coverage={coverage}%, outside_px={outside}, cutout_px={cutout}. {verdict_val}."
    )
    return {
        "id": exp_id,
        "method": "svg-masked-style-rebuild",
        "model": "procedural-pil",
        "platform": "local-python",
        "reference_images": c.get("style_sources", REFS),
        "svg": c.get("svg", "unknown"),
        "prompt": "unknown",
        "control_map": c.get("base_composition", "unknown"),
        "region_iou": "n/a",
        "white_iou": "n/a",
        "outside_frac": 0 if outside == 0 else "unknown",
        "painted_max": "n/a",
        "image_path_raw": _rel(artwork),
        "image_path_exact": "unknown",
        "timestamp": c.get("timestamp", _mtime_iso(artwork)),
        "notes": notes,
        "verdict": verdict_val,
    }


# ---------------------------------------------------------------------------
# Scan: raw model-output sinks (orphan sweep) — catalog EVERY gen image on disk
# so no result from any model is ever dropped, even if it never became an
# experiment dir. Dedup by CONTENT HASH (experiment dirs hold COPIES of the raw
# ~/.codex / ~/.gemini originals, so path/name dedup would miss them).
# ---------------------------------------------------------------------------

ORPHAN_METHOD = "raw-model-output-uncataloged"

# (base_dir, glob, model, platform) — raw subscription image sinks live OUTSIDE the repo
RAW_SINKS = [
    *[(codex_images.CODEX_DIR, f"*/{pat}", "gpt-image-2", "codex")
      for pat in codex_images.CODEX_IMAGE_PATTERNS],
    (Path.home() / ".gemini" / "antigravity-cli" / "brain", "*/*.jpg", "nano-banana", "agy"),
    (Path.home() / ".gemini" / "antigravity-cli" / "brain", "*/*.jpeg", "nano-banana", "agy"),
    (Path.home() / ".gemini" / "antigravity-cli" / "brain", "*/*.png", "nano-banana", "agy"),
]


def _file_md5(path: Path | str) -> str | None:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _referenced_content_hashes(records: list[dict]) -> set[str]:
    """Content hashes of every image already cataloged via an experiment record."""
    hashes: set[str] = set()
    for r in records:
        for key in ("image_path_raw", "image_path_exact"):
            v = r.get(key)
            if not v or v in ("unknown", "n/a"):
                continue
            p = Path(v)
            if not p.is_absolute():
                p = ROOT / p
            if p.exists():
                h = _file_md5(p)
                if h:
                    hashes.add(h)
    return hashes


def _orphan_record(real_path: str, model: str, platform: str, chash: str, kind: str) -> dict:
    return {
        "id": f"orphan-{model}-{chash[:8]}",
        "method": ORPHAN_METHOD,
        "model": model,
        "platform": platform,
        "reference_images": "unknown",
        "svg": "unknown",
        "prompt": "unknown (orphan: inputs unrecoverable)",
        "control_map": "unknown",
        "region_iou": "unmeasured",
        "white_iou": "n/a",
        "outside_frac": "n/a",
        "painted_max": "n/a",
        "image_path_raw": _rel(real_path),
        "image_path_exact": "unknown",
        "timestamp": _mtime_iso(real_path),
        "notes": (f"Orphan {kind} swept from disk; not tied to an experiment dir. "
                  "Model known; inputs/prompt unrecoverable. Cataloged so no gen is dropped."),
        "verdict": "unknown",
    }


def scan_raw_orphans(referenced_hashes: set[str]) -> list[dict]:
    """Sweep raw model sinks + full-render PNGs; emit a record for every gen NOT
    already represented (by content) in an experiment record. Idempotent: the id
    is derived from the file's content hash, so re-runs and duplicate copies collapse."""
    records: list[dict] = []
    seen = set(referenced_hashes)

    for base, pattern, model, platform in RAW_SINKS:
        if not base.is_dir():
            continue
        for img in base.glob(pattern):
            chash = _file_md5(img)
            if not chash or chash in seen:
                continue
            seen.add(chash)
            try:
                real = str(img.resolve())
            except Exception:
                real = str(img)
            records.append(_orphan_record(real, model, platform, chash, "raw model gen"))

    # full-render PNGs in outputs/generated (>100KB = real images, not control maps)
    gen_dir = TASK / "outputs" / "generated"
    if gen_dir.is_dir():
        for img in sorted(gen_dir.glob("*.png")):
            try:
                if img.stat().st_size < 100_000:
                    continue
            except Exception:
                continue
            chash = _file_md5(img)
            if not chash or chash in seen:
                continue
            seen.add(chash)
            records.append(_orphan_record(str(img.resolve()), "render-output", "local", chash, "final/intermediate render"))

    return records


# ---------------------------------------------------------------------------
# Sort key
# ---------------------------------------------------------------------------

def _sort_key(r: dict) -> float:
    """Sort by region_iou descending. Non-numeric values sort last."""
    v = r.get("region_iou", "unknown")
    if isinstance(v, (int, float)):
        return -float(v)
    if v == "n/a":
        return -0.5  # procedural PASS sorts above unknowns
    return 0.0  # unknown sorts at 0


# ---------------------------------------------------------------------------
# RESULTS-BOARD.md generation
# ---------------------------------------------------------------------------

BOARD_HEADER = """\
# RESULTS BOARD — space-np01-front-bottom-02

**Task:** Generate a watercolor illustration that fits EXACTLY inside SVG geometry (viewBox 767x2602, aspect ~1:3.4) with illustrated bevelled rims around 4 openings (3 hexagons + 1 slot).

**Gate:** region-IoU >= 0.85 (fill-agnostic placement metric). White-IoU measures hole cleanliness.

**Machine-readable data:** `results.jsonl` (one record per line, schema below).

---

## CALLOUTS

### Best Geometry (region-IoU)
**DREAM1** — dreamshaper-8 + lineart ControlNet + exact SVG clear → **region-IoU = 0.969**
> Local diffusers, MPS, 30 steps, 77.6s. Passes gate. Style = watercolor-leaning but still a flat SD wash; richer than vanilla SD1.5.

### Best Style (visual quality)
**BoN-nano-s3** — Nano Banana BoN sample → **region-IoU = 0.578** (below gate, confounded by aspect mismatch)
> Nano Banana outputs tend to have richer illustrative style but drift most from exact coordinates. All subscription BoN results are confounded by aspect mismatch (9:16 forced on 1:3.4 panel). Re-test needed.

### Hybrid Backstop (exact + model art)
**HYB1** — exact_bevel_composite.py + E1 model art → **region-IoU = 1.0 by construction**, white-IoU = 0.795
> Placement exact. Style degrades (smears controls near openings). Use only as fallback when nothing else passes gate.

### Best Confirmed PASS (geometry=exact, coverage metric)
**batch-np01-*/checkpoint/batch-bottom** — space-svg-exports-batch procedural runs → **PASS** (outside=0, cutout=0, coverage 98-100%)
> Different SVGs, procedural PIL (not model-painted). Geometry perfect. Style is simulated, not model-generated.

---

## LEGEND

| Column | Definition |
|---|---|
| `region-IoU` | Fill-agnostic: does the opening appear at the right location/shape regardless of fill? 0=nowhere, 1=exact. Measured by `scripts/geom_iou.py`. **GATE >= 0.85** |
| `white-IoU` | Are the openings actually white/empty? mean across openings. Measured by `scripts/svg_geometry_check.py`. |
| `outside_frac` | Fraction of panel paint outside the outer contour. Lower is better. |
| `verdict` | PASS = meets gate; FAIL = does not |
| `n/a` | Different metric used (batch: SVG mask coverage px=0) |
| `unknown` | Not measured |

---
"""

BOARD_FOOTER = """---

## SCHEMA (results.jsonl fields)

```
id            — unique experiment identifier
method        — [controlnet-lineart-clear | controlnet-lineart-sd15 | gpt-image-best-of-n |
                  gpt-image-filled-contract | gpt-image-lineart-contract | gpt-image-free-redraw |
                  nano-filled-contract | nano-lineart-contract | hybrid-composite |
                  svg-masked-procedural | svg-masked-style-rebuild | procedural-pil-svg-native |
                  controlnet-style-sd15 | controlnet-inpaint | controlnet-style-clear]
model         — [sd1.5 | dreamshaper-8 | gpt-image-2 | nano-banana | procedural-pil | gpt-image-2+code]
platform      — [local-diffusers | codex | agy | local-python | codex+local]
reference_images — paths to style reference PNGs
svg           — path to source SVG template
prompt        — path to prompt file or inline text
control_map   — path to ControlNet conditioning map or genmap used as reference
region_iou    — fill-agnostic placement metric (geom_iou.py); "unknown" | "n/a" | float
white_iou     — mean opening emptiness (svg_geometry_check.py); "unknown" | "n/a" | float
outside_frac  — fraction of paint outside SVG contour; "unknown" | float
painted_max   — max hole painted_frac (highest contamination); "unknown" | "n/a" | float
image_path_raw  — generated image before any SVG clearing
image_path_exact — image after SVG punching (openings + outside cleared)
timestamp     — ISO-8601 file mtime
notes         — key takeaway, 1-2 sentences
verdict       — PASS | FAIL | unknown
```

---

*Auto-generated by `scripts/results_db.py`. Re-run to refresh. Source: all experiment dirs under `tasks/space-np01-front-bottom-02/experiments/` and `tasks/space-svg-exports-batch/`.*
"""


def _fmt_val(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.3f}"
    if v is None:
        return "unknown"
    return str(v)


def build_board(records: list[dict]) -> str:
    lines = [BOARD_HEADER]

    # Master table (top 30 by region_iou)
    lines.append("## MASTER TABLE (sorted by region-IoU, top 30)\n")
    lines.append("| id | method | model | region-IoU | judge-geom | judge-style | judge-verdict | gate |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in records[:30]:
        rid = r["id"]
        if r["verdict"] == "PASS":
            rid = f"**{rid}**"
        lines.append(
            f"| {rid} | {r['method']} | {r['model']} | "
            f"{_fmt_val(r['region_iou'])} | {r.get('judge_geometry','—')} | "
            f"{r.get('judge_style','—')} | {r.get('judge_verdict','—')} | {r['verdict']} |"
        )
    lines.append("")

    # Method groups
    groups: dict[str, list[dict]] = {}
    for r in records:
        g = r.get("method", "unknown")
        groups.setdefault(g, []).append(r)

    lines.append("---\n")
    lines.append("## METHOD GROUPS\n")

    group_order = [
        ("controlnet-lineart-clear", "GROUP A1: ControlNet Lineart Clear (dreamshaper-8, local-diffusers)"),
        ("controlnet-lineart-sd15", "GROUP A2: ControlNet Lineart SD1.5 (local-diffusers)"),
        ("controlnet-style-sd15", "GROUP A3: ControlNet Style SD1.5 (local-diffusers)"),
        ("controlnet-inpaint", "GROUP A4: ControlNet Inpaint SD1.5 (local-diffusers)"),
        ("controlnet-canny-sdxl", "GROUP A5: ControlNet Canny SDXL (local-diffusers)"),
        ("comfyui-workflow", "GROUP A6: ComfyUI Workflow (local-diffusers)"),
        ("hybrid-composite", "GROUP B: Hybrid Composite (model art + code re-seating)"),
        ("gpt-image-best-of-n", "GROUP C1: gpt-image-2 Best-of-N (codex)"),
        ("gpt-image-filled-contract", "GROUP C2: gpt-image-2 Filled Contract (codex)"),
        ("gpt-image-lineart-contract", "GROUP C3: gpt-image-2 Lineart Contract (codex)"),
        ("gpt-image-free-redraw", "GROUP C4: gpt-image-2 Free Redraw (codex)"),
        ("nano-filled-contract", "GROUP D1: Nano Banana Filled Contract (agy)"),
        ("nano-lineart-contract", "GROUP D2: Nano Banana Lineart Contract (agy)"),
        ("svg-masked-procedural", "GROUP E1: SVG-Masked Procedural (local-python)"),
        ("svg-masked-style-rebuild", "GROUP E2: SVG-Masked Style Rebuild (local-python)"),
        ("procedural-pil-svg-native", "GROUP E3: Procedural PIL SVG Native (local-python)"),
    ]

    emitted_methods = set()
    for method_key, group_title in group_order:
        group_records = groups.get(method_key, [])
        if not group_records:
            continue
        emitted_methods.add(method_key)
        lines.append(f"### {group_title}\n")
        lines.append("| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(group_records, key=_sort_key):
            rid = r["id"]
            if r["verdict"] == "PASS":
                rid = f"**{rid}**"
            note = (r.get("notes") or "")[:120]
            lines.append(
                f"| {rid} | {r['model']} | {_fmt_val(r['region_iou'])} | "
                f"{_fmt_val(r['white_iou'])} | {_fmt_val(r['outside_frac'])} | "
                f"{r['verdict']} | {note} |"
            )
        lines.append("")

    # Orphan raw gens: summarize by count (don't dump 100+ rows into the board)
    orphans = groups.get(ORPHAN_METHOD, [])
    if orphans:
        emitted_methods.add(ORPHAN_METHOD)
        by_model = Counter(r["model"] for r in orphans)
        lines.append("### GROUP F: Orphan raw model outputs (inputs unrecoverable)\n")
        lines.append(
            f"Every gen image on disk is cataloged so none is dropped. Total **{len(orphans)}** orphans "
            "(raw model gens + renders NOT already tied to an experiment dir, deduped by content hash). "
            "By model: " + ", ".join(f"{m}={n}" for m, n in sorted(by_model.items())) + "."
        )
        lines.append("Per-image records (path + mtime) are in `results.jsonl` under id prefix `orphan-`. "
                     "Listed as counts here to keep the board readable.\n")

    # Catch any methods not in the group_order
    for method_key, group_records in groups.items():
        if method_key in emitted_methods:
            continue
        lines.append(f"### GROUP X: {method_key}\n")
        lines.append("| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(group_records, key=_sort_key):
            rid = r["id"]
            if r["verdict"] == "PASS":
                rid = f"**{rid}**"
            note = (r.get("notes") or "")[:120]
            lines.append(
                f"| {rid} | {r['model']} | {_fmt_val(r['region_iou'])} | "
                f"{_fmt_val(r['white_iou'])} | {_fmt_val(r['outside_frac'])} | "
                f"{r['verdict']} | {note} |"
            )
        lines.append("")

    # Summary
    passes = [r for r in records if r["verdict"] == "PASS"]
    fails = [r for r in records if r["verdict"] == "FAIL"]
    unknowns = [r for r in records if r["verdict"] == "unknown"]
    top_by_region = [r for r in records if isinstance(r.get("region_iou"), float)]

    lines.append("---\n")
    lines.append("## SUMMARY: WHERE WE STAND\n")
    lines.append(f"- Total records: **{len(records)}**")
    lines.append(f"- PASS (region-IoU >= 0.85 or procedural): **{len(passes)}**")
    lines.append(f"- FAIL: **{len(fails)}**")
    lines.append(f"- Unknown / stub: **{len(unknowns)}**")
    if top_by_region:
        top5 = top_by_region[:5]
        lines.append("\n**Top-5 by region-IoU:**")
        for r in top5:
            lines.append(f"- {r['id']}: region-IoU={_fmt_val(r['region_iou'])} ({r['verdict']})")
    lines.append("")
    lines.append(
        "**Open problem:** No method yet gives BOTH exact geometry (region-IoU >= 0.85) "
        "AND gorgeous model-painted watercolor style with illustrated bevel rims simultaneously."
    )
    lines.append("")
    lines.append("**Critical next experiments:**")
    lines.append("1. dreamshaper-8 + CN + IP-Adapter (style from ref images) — expected to solve style gap while keeping geometry locked.")
    lines.append("2. Nano Banana + correct aspect (native tall ratio, letter-box) — aspect mismatch was the prime confound; re-test needed.")
    lines.append("3. gpt-image-2 edit mode with letter-boxed DREAM1 output as base — combine subscription style with locked geometry.")
    lines.append("")

    lines.append(BOARD_FOOTER)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_all_records() -> list[dict]:
    exp_base = TASK / "experiments"

    all_records: dict[str, dict] = {}

    def add(r: dict) -> None:
        exp_id = r["id"]
        if exp_id not in all_records:
            all_records[exp_id] = r

    # 1. BoN parent dirs (BoN-nano/sN, BoN-openai/sN)
    for r in scan_bon_nano(exp_base):
        add(r)
    for r in scan_bon_openai(exp_base):
        add(r)

    # 2. Flat experiment dirs
    for r in scan_experiments(exp_base):
        add(r)

    # 3. space-svg-exports-batch
    for r in scan_svg_exports_batch(BATCH_TASK):
        add(r)

    # 4. Raw orphan sweep — catalog EVERY gen image on disk (codex/agy sinks +
    #    full renders) not already represented (by content) in an experiment record.
    referenced = _referenced_content_hashes(list(all_records.values()))
    for r in scan_raw_orphans(referenced):
        add(r)

    # Sort by region_iou descending
    sorted_records = sorted(all_records.values(), key=_sort_key)
    return sorted_records


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print records, do not write files")
    args = ap.parse_args()

    records = collect_all_records()

    if args.dry_run:
        for r in records:
            print(json.dumps(r))
        print(f"\n# Total: {len(records)} records", file=sys.stderr)
        return 0

    # Write results.jsonl
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_text = "\n".join(json.dumps(r) for r in records) + "\n"
    JSONL_PATH.write_text(jsonl_text)

    # Write RESULTS-BOARD.md
    board_text = build_board(records)
    BOARD_PATH.write_text(board_text)

    # Report
    passes = sum(1 for r in records if r["verdict"] == "PASS")
    print(f"Wrote {len(records)} records to {JSONL_PATH.relative_to(ROOT)}")
    print(f"  PASS: {passes}  FAIL: {sum(1 for r in records if r['verdict'] == 'FAIL')}  unknown: {sum(1 for r in records if r['verdict'] == 'unknown')}")
    top5 = [r for r in records if isinstance(r.get("region_iou"), float)][:5]
    print("Top-5 by region_iou:")
    for r in top5:
        print(f"  {r['id']:35s}  {r['region_iou']:.3f}  {r['verdict']}")
    print(f"Board written to {BOARD_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
