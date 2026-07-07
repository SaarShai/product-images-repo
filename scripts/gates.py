#!/usr/bin/env python3
"""Run all deterministic panel gates and emit one bundle.

Inputs are the vector_spec.py geometry products for one panel:
  <panel>-spec.json, <panel>-mask.png, <panel>-control.png,
  <panel>-forbidden.png, <panel>-holes.png.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PY = sys.executable or "python3"

ASPECT_TOL = 0.01
HOLE_LUMINANCE_MIN = 245.0
DUAL_GEOMETRY_DISAGREEMENT_MAX = 0.15


def _abs(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _gate_path(geom: Path, panel: str, suffix: str) -> Path:
    return geom / f"{panel}-{suffix}"


def _run_json(cmd: list[str]) -> tuple[int, str, str, dict[str, Any] | None]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = None
    return proc.returncode, proc.stdout, proc.stderr, payload


def _command_for_bundle(cmd: list[str]) -> list[str]:
    return cmd


def _missing_result(name: str, path: Path) -> dict[str, Any]:
    return {
        "gate": name,
        "verdict": "FAIL",
        "error": f"required file not found: {path}",
    }


def run_geom_gate(cand: Path, mask: Path) -> dict[str, Any]:
    if not mask.exists():
        return _missing_result("geom", mask)
    cmd = [PY, str(SCRIPTS / "geom_gate.py"), "--cand", str(cand), "--mask", str(mask)]
    rc, stdout, stderr, payload = _run_json(cmd)
    if payload is None:
        return {
            "gate": "geom",
            "verdict": "FAIL",
            "returncode": rc,
            "command": _command_for_bundle(cmd),
            "stdout": stdout,
            "stderr": stderr,
            "error": "geom_gate.py did not emit parseable JSON",
        }

    raw_fails = list(payload.get("fails") or [])
    raw_warnings = list(payload.get("warnings") or [])
    fill_fails = [f for f in raw_fails if "fill_inside_contour" in str(f)]
    non_fill_fails = [f for f in raw_fails if f not in fill_fails]

    if non_fill_fails:
        verdict = "FAIL"
    elif fill_fails:
        verdict = "WARN"
    elif raw_warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "gate": "geom",
        "verdict": verdict,
        "raw_verdict": payload.get("verdict"),
        "returncode": rc,
        "command": _command_for_bundle(cmd),
        "fill_inside_contour": payload.get("fill_inside_contour"),
        "overflow_outside_contour": payload.get("overflow_outside_contour"),
        "edge_iou": payload.get("edge_iou"),
        "candidate_size": payload.get("candidate_size"),
        "thresh": payload.get("thresh"),
        "fails": raw_fails,
        "warnings": raw_warnings,
        "downgraded_failures": fill_fails,
        "downgrade_rule": (
            "fill_inside_contour failures are WARN because geom_gate.py's "
            "fill detector false-fails legitimately white or sparse panels"
        ),
        "raw": payload,
    }


def run_forbidden_gate(cand: Path, forbidden: Path, mask: Path, control: Path) -> dict[str, Any]:
    for name, path in (("forbidden", forbidden), ("mask", mask), ("control", control)):
        if not path.exists():
            return _missing_result("forbidden", path)

    cmd = [
        PY,
        str(SCRIPTS / "forbidden_gate.py"),
        "--cand",
        str(cand),
        "--forbidden",
        str(forbidden),
        "--mask",
        str(mask),
        "--exclude-edges",
        str(control),
    ]
    rc, stdout, stderr, payload = _run_json(cmd)
    if payload is None:
        return {
            "gate": "forbidden",
            "verdict": "FAIL",
            "returncode": rc,
            "command": _command_for_bundle(cmd),
            "stdout": stdout,
            "stderr": stderr,
            "error": "forbidden_gate.py did not emit parseable JSON",
        }

    raw = payload.get("verdict")
    verdict = "PASS" if raw == "OK" else "WARN" if raw == "WARN" else "FAIL"
    return {
        "gate": "forbidden",
        "verdict": verdict,
        "raw_verdict": raw,
        "returncode": rc,
        "command": _command_for_bundle(cmd),
        "advisory": payload.get("advisory", True),
        "edge_density": payload.get("edge_density"),
        "color_variance": payload.get("color_variance"),
        "ratio_warn": payload.get("ratio_warn"),
        "note": payload.get("note"),
        "raw": payload,
    }


def _resolve_svg(geom: Path, panel: str, explicit: Path | None) -> Path:
    if explicit is not None:
        return _abs(explicit)
    direct = geom / f"{panel}.svg"
    if direct.exists():
        return direct
    return geom / f"{panel}-panel.svg"


def run_dual_geometry(cand: Path, svg: Path, outdir: Path, output_stem: str) -> dict[str, Any]:
    """Two independent geometry metrics + a grader-disagreement flag.

    geom_iou.py's mean_region_iou is FILL-AGNOSTIC (placement/shape only, any
    fill color scores high); svg_geometry_check.py's mean_iou is WHITE-based
    (only an empty/white opening scores high). They measure different things on
    purpose, so a big gap between them is itself a signal — e.g. a cutout that is
    correctly placed but painted-over scores high region-IoU / low white-IoU.
    Flag disagreement > DUAL_GEOMETRY_DISAGREEMENT_MAX rather than silently
    averaging it away (lesson: a single blended number hides exactly this case).
    """
    if not svg.exists():
        return {"available": False, "note": f"no SVG supplied/found: {svg}"}

    region_json = outdir / f"{output_stem}-region-iou.json"
    white_json = outdir / f"{output_stem}-white-iou.json"

    region_cmd = [PY, str(SCRIPTS / "geom_iou.py"), str(cand), "--svg", str(svg), "--json-out", str(region_json)]
    region_proc = subprocess.run(region_cmd, capture_output=True, text=True)
    region_payload = _json_load(region_json) if region_json.exists() else None

    white_cmd = [PY, str(SCRIPTS / "svg_geometry_check.py"), str(cand), "--svg", str(svg), "--json-out", str(white_json)]
    white_proc = subprocess.run(white_cmd, capture_output=True, text=True)
    white_payload = _json_load(white_json) if white_json.exists() else None

    region_iou = region_payload.get("mean_region_iou") if region_payload else None
    white_iou = white_payload.get("mean_iou") if white_payload else None

    disagreement = None
    flagged = False
    if region_iou is not None and white_iou is not None:
        disagreement = round(abs(region_iou - white_iou), 4)
        flagged = disagreement > DUAL_GEOMETRY_DISAGREEMENT_MAX

    return {
        "available": True,
        "svg": str(svg),
        "region_iou": {
            "metric": "mean_region_iou",
            "value": region_iou,
            "command": _command_for_bundle(region_cmd),
            "returncode": region_proc.returncode,
            "json_path": str(region_json) if region_json.exists() else None,
            "openings": region_payload.get("openings") if region_payload else None,
            "error": None if region_payload is not None else (region_proc.stderr.strip() or region_proc.stdout.strip()),
        },
        "white_iou": {
            "metric": "mean_iou",
            "value": white_iou,
            "command": _command_for_bundle(white_cmd),
            "returncode": white_proc.returncode,
            "json_path": str(white_json) if white_json.exists() else None,
            "holes": white_payload.get("holes") if white_payload else None,
            "error": None if white_payload is not None else (white_proc.stderr.strip() or white_proc.stdout.strip()),
        },
        "disagreement": disagreement,
        "disagreement_max": DUAL_GEOMETRY_DISAGREEMENT_MAX,
        "flagged": flagged,
        "flag_reason": (
            f"|region_iou - white_iou| = {disagreement} > {DUAL_GEOMETRY_DISAGREEMENT_MAX}"
            " -- the two geometry metrics disagree (grader-disagreement lesson): "
            "review which is right before trusting either alone."
        ) if flagged else None,
    }


def _components(mask: np.ndarray) -> list[np.ndarray]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out: list[np.ndarray] = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        comp = np.zeros_like(mask, dtype=bool)
        seen[y0, x0] = True
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        while queue:
            y, x = queue.popleft()
            comp[y, x] = True
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        out.append(comp)
    out.sort(key=lambda c: int(c.sum()), reverse=True)
    return out


def _bbox(comp: np.ndarray) -> list[int]:
    ys, xs = np.where(comp)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def holes_gate(cand: Path, holes: Path, threshold: float = HOLE_LUMINANCE_MIN) -> dict[str, Any]:
    if not holes.exists():
        return _missing_result("holes", holes)

    image = Image.open(cand).convert("RGB")
    holes_mask = Image.open(holes).convert("L").resize(image.size, Image.Resampling.NEAREST)
    holes_arr = np.asarray(holes_mask) > 127
    rgb = np.asarray(image).astype(np.float32)
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

    rows = []
    for i, comp in enumerate(_components(holes_arr), 1):
        area = int(comp.sum())
        if area == 0:
            continue
        # Measure the hole CORE, not the full disc: the finish chain paints a
        # bevel rim (navy shadow + lit lip) inside the hole edge by design, so a
        # full-disc mean fails legitimately-beveled holes (calibrated on r16d door
        # — known-good post-bevel, rim pulled mean to ~200-228). The core (mask
        # eroded ~30% of the hole's own radius) stays paper-white after punching.
        core = comp
        radius = max(1, int(round(np.sqrt(area / np.pi) * 0.3)))
        for _ in range(radius):
            nxt = core.copy()
            nxt[1:, :] &= core[:-1, :]; nxt[:-1, :] &= core[1:, :]
            nxt[:, 1:] &= core[:, :-1]; nxt[:, :-1] &= core[:, 1:]
            if nxt.sum() < 0.25 * area:
                break  # thin shapes (slots) erode fast — keep a meaningful core
            core = nxt
        mean_luma = float(luminance[core].mean())
        rows.append(
            {
                "i": i,
                "area_px": area,
                "core_px": int(core.sum()),
                "bbox": _bbox(comp),
                "mean_luminance": round(mean_luma, 3),
                "threshold_min": threshold,
                "verdict": "PASS" if mean_luma > threshold else "FAIL",
            }
        )

    verdict = "FAIL" if any(r["verdict"] == "FAIL" for r in rows) else "PASS"
    return {
        "gate": "holes",
        "verdict": verdict,
        "threshold_min": threshold,
        "holes_found": len(rows),
        "holes": rows,
    }


def dimensions_gate(cand: Path, spec: Path) -> dict[str, Any]:
    if not spec.exists():
        return _missing_result("dimensions", spec)

    image = Image.open(cand)
    actual = [image.width, image.height]
    try:
        payload = _json_load(spec)
        expected = payload["size_px"]
        if not (
            isinstance(expected, list)
            and len(expected) == 2
            and all(isinstance(v, int) for v in expected)
            and expected[0] > 0
            and expected[1] > 0
        ):
            raise ValueError("spec size_px must be a positive [width, height] list")
    except Exception as exc:
        return {
            "gate": "dimensions",
            "verdict": "FAIL",
            "candidate_size_px": actual,
            "spec": str(spec),
            "error": str(exc),
        }

    actual_aspect = actual[0] / actual[1]
    expected_aspect = expected[0] / expected[1]
    aspect_diff = abs(actual_aspect - expected_aspect)
    exact = actual == expected
    if exact:
        verdict = "PASS"
    elif aspect_diff <= ASPECT_TOL:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "gate": "dimensions",
        "verdict": verdict,
        "candidate_size_px": actual,
        "expected_size_px": expected,
        "exact_match": exact,
        "candidate_aspect": round(actual_aspect, 6),
        "expected_aspect": round(expected_aspect, 6),
        "aspect_abs_diff": round(aspect_diff, 6),
        "aspect_tolerance": ASPECT_TOL,
    }


def _binary_mask(path: Path, size: tuple[int, int]) -> Image.Image:
    return Image.open(path).convert("L").resize(size, Image.Resampling.NEAREST).point(
        lambda p: 255 if p > 127 else 0
    )


def _mask_layer(size: tuple[int, int], mask: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    transparent = Image.new("RGBA", size, (0, 0, 0, 0))
    colored = Image.new("RGBA", size, color)
    return Image.composite(colored, transparent, mask)


def write_overlay(cand: Path, control: Path, forbidden: Path, holes: Path, out: Path) -> dict[str, Any]:
    base = Image.open(cand).convert("RGBA")
    size = base.size

    if forbidden.exists():
        forb = _binary_mask(forbidden, size)
        base.alpha_composite(_mask_layer(size, forb, (255, 0, 0, 64)))

    if control.exists():
        ctrl = _binary_mask(control, size)
        base.alpha_composite(_mask_layer(size, ctrl, (255, 0, 0, 102)))

    hole_count = 0
    if holes.exists():
        hole_mask = _binary_mask(holes, size)
        edge_mask = hole_mask.filter(ImageFilter.FIND_EDGES).point(lambda p: 255 if p > 0 else 0)
        base.alpha_composite(_mask_layer(size, edge_mask, (255, 220, 0, 210)))

        hole_arr = np.asarray(hole_mask) > 127
        draw = ImageDraw.Draw(base, "RGBA")
        width = max(2, min(size) // 220)
        pad = max(2, width * 2)
        for comp in _components(hole_arr):
            hole_count += 1
            x0, y0, x1, y1 = _bbox(comp)
            span_w = x1 - x0
            span_h = y1 - y0
            thin_full_frame = (
                (span_w > size[0] * 0.85 or span_h > size[1] * 0.85)
                and int(comp.sum()) < size[0] * size[1] * 0.02
            )
            if thin_full_frame:
                continue
            draw.ellipse(
                [x0 - pad, y0 - pad, x1 + pad, y1 + pad],
                outline=(255, 220, 0, 235),
                width=width,
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out)
    return {
        "path": str(out),
        "control_edges": control.exists(),
        "forbidden_bands": forbidden.exists(),
        "hole_regions": hole_count,
    }


def overall_verdict(gates: dict[str, dict[str, Any]]) -> str:
    verdicts = [g.get("verdict") for g in gates.values()]
    if "FAIL" in verdicts:
        return "FAIL"
    if "WARN" in verdicts:
        return "WARN"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cand", required=True, type=Path)
    parser.add_argument("--geom", required=True, type=Path)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--stage", choices=("init", "restyle", "finish"), default="finish")
    parser.add_argument(
        "--svg",
        type=Path,
        help="panel SVG (for the dual region-IoU/white-IoU geometry metrics); "
        "default: <geom>/<panel>.svg if present, else <geom>/<panel>-panel.svg",
    )
    parser.add_argument(
        "--output-stem",
        default=None,
        help="filename stem for output bundle/overlay/metric JSON files (default: <panel>-<stage>)",
    )
    args = parser.parse_args()

    cand = _abs(args.cand)
    geom = _abs(args.geom)
    outdir = _abs(args.outdir)
    panel = args.panel
    stage = args.stage
    output_stem = args.output_stem or f"{panel}-{stage}"
    svg = _resolve_svg(geom, panel, args.svg)

    if not cand.exists():
        print(json.dumps({"overall_verdict": "FAIL", "error": f"candidate not found: {cand}"}, indent=2))
        return 2

    spec = _gate_path(geom, panel, "spec.json")
    mask = _gate_path(geom, panel, "mask.png")
    control = _gate_path(geom, panel, "control.png")
    forbidden = _gate_path(geom, panel, "forbidden.png")
    holes = _gate_path(geom, panel, "holes.png")
    overlay_path = outdir / f"{output_stem}-overlay.png"
    bundle_path = outdir / f"{output_stem}-bundle.json"

    outdir.mkdir(parents=True, exist_ok=True)
    overlay_info = write_overlay(cand, control, forbidden, holes, overlay_path)
    dual_geometry = run_dual_geometry(cand, svg, outdir, output_stem)

    gates = {
        "geom": run_geom_gate(cand, mask),
        "forbidden": run_forbidden_gate(cand, forbidden, mask, control),
        "holes": holes_gate(cand, holes),
        "dimensions": dimensions_gate(cand, spec),
    }
    verdict = overall_verdict(gates)
    # a dual-geometry disagreement never hard-fails the bundle (it's a flag for
    # human/VLM review, not a deterministic pass/fail on its own) but WARN-downgrades
    # an otherwise-clean PASS so it doesn't slip past unnoticed.
    if dual_geometry.get("flagged") and verdict == "PASS":
        verdict = "WARN"

    bundle = {
        "panel": panel,
        "stage": stage,
        "candidate_path": str(cand),
        "candidate_sha256": _sha256(cand),
        "geometry_dir": str(geom),
        "overlay_path": str(overlay_path),
        "overlay": overlay_info,
        "dual_geometry": dual_geometry,
        "bundle_path": str(bundle_path),
        "gates": gates,
        "overall_verdict": verdict,
    }

    bundle_path.write_text(json.dumps(bundle, indent=2) + "\n")
    print(json.dumps(bundle, indent=2))
    return 2 if verdict == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
