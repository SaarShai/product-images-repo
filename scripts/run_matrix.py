#!/usr/bin/env python3
"""run_matrix.py — experiment orchestrator that REPLACES hardcoded run_*.sh
fan-out scripts with an auditable, data-driven route matrix.

Instead of a bespoke shell script per experiment (run_fan_o1.sh, run_winin.sh,
...), describe the whole fan-out as ONE JSON matrix and run it through the
single supported generator core (scripts/subgen.py). Provenance is recorded in
a results catalog so a later judge/audit knows exactly what was generated, from
which prompt (and prompt version), with which references.

Concurrency policy (matches the house rule "agy serial, codex concurrent"):
  * openai (codex) routes may run CONCURRENTLY.
  * nano   (agy)   routes MUST run ONE-AT-A-TIME (serial) — agy is not safe to
    run in parallel.
nano routes are run serially BEFORE the openai pool is launched, so a nano
route never overlaps an openai route either.

Matrix JSON: a list of route objects, e.g.
  [
    {
      "label": "o1-complete",
      "provider": "openai",
      "prompt_file": "tasks/whole-panel-build/B4-princess-window/prompt-W-complete.md",
      "refs": ["tasks/.../guide-clean2.png", "tasks/.../style-ref.png"],
      "out": "tasks/whole-panel-build/sub/o1-complete.png",
      "timeout": 520,        # optional, default 300
      "retries": 2,          # optional, default 3
      "model": "gpt-image-1" # optional, openai only
    },
    ...
  ]
Relative paths are resolved against the repo root (this file's parent's parent).

Catalog JSON (default M.catalog.json next to the matrix): per route
  {label, provider, prompt_file, refs, out, exists, dims, prompt_version, status}
where prompt_version is read from a "version:" tag in the prompt file if present
(else null), exists/dims describe the produced output, and status is one of
planned | ok | fail | skipped(dry-run).

CLI:
  python3 scripts/run_matrix.py --matrix M.json [--dry-run] [--catalog OUT.json]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# repo root = .../<repo>/scripts/run_matrix.py -> parents[1]
REPO_ROOT = Path(__file__).resolve().parents[1]

# "version:" tag anywhere in a prompt file, e.g. "version: v6" or "# version: 2025-06".
# Captures the rest of the line (trimmed). Markdown bullet / heading markers are stripped.
_VERSION_RE = re.compile(r"^\s*(?:[#>*\-]\s*)*version\s*:\s*(.+?)\s*$", re.I | re.M)

DEFAULT_TIMEOUT = 300
DEFAULT_RETRIES = 3


def _resolve(p):
    """Resolve a possibly-relative path against the repo root."""
    pp = Path(p)
    return pp if pp.is_absolute() else (REPO_ROOT / pp)


def read_prompt_version(prompt_file):
    """Return the value of a 'version:' tag in the prompt file, or None."""
    fp = _resolve(prompt_file)
    try:
        text = fp.read_text()
    except Exception:
        return None
    m = _VERSION_RE.search(text)
    return m.group(1).strip() if m else None


def _image_dims(path):
    """Return [w, h] for an existing image, or None."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return list(im.size)
    except Exception:
        return None


def catalog_entry(route, status):
    """Build a provenance/results catalog entry for a route at a given status."""
    out = _resolve(route["out"])
    exists = out.exists()
    return {
        "label": route.get("label"),
        "provider": route.get("provider"),
        "prompt_file": route.get("prompt_file"),
        "refs": list(route.get("refs", [])),
        "out": str(route.get("out")),
        "exists": exists,
        "dims": _image_dims(out) if exists else None,
        "prompt_version": read_prompt_version(route.get("prompt_file")),
        "status": status,
    }


def load_matrix(matrix_path):
    """Load + validate the route matrix. Returns a list of route dicts."""
    data = json.loads(Path(matrix_path).read_text())
    # Allow either a bare list or {"routes": [...]} for convenience.
    if isinstance(data, dict) and "routes" in data:
        data = data["routes"]
    if not isinstance(data, list):
        raise ValueError("matrix must be a JSON list of route objects (or {routes: [...]})")
    seen_labels = set()
    for i, r in enumerate(data):
        if not isinstance(r, dict):
            raise ValueError("route #%d is not an object" % i)
        for key in ("label", "provider", "prompt_file", "out"):
            if not r.get(key):
                raise ValueError("route #%d missing required field %r" % (i, key))
        if r["provider"] not in ("openai", "nano"):
            raise ValueError("route %r: provider must be openai|nano, got %r"
                             % (r["label"], r["provider"]))
        if r["label"] in seen_labels:
            raise ValueError("duplicate route label %r" % r["label"])
        seen_labels.add(r["label"])
        r.setdefault("refs", [])
        if not isinstance(r["refs"], list):
            raise ValueError("route %r: refs must be a list" % r["label"])
    return data


def run_route(route):
    """Run ONE route via subgen.generate(). Returns (status, error_or_None)."""
    # Import lazily so --dry-run never needs subgen's runtime deps.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import subgen  # noqa: E402
    refs = [str(_resolve(p)) for p in route.get("refs", [])]
    out = _resolve(route["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        subgen.generate(
            route["provider"],
            _resolve(route["prompt_file"]).read_text(),
            refs,
            out,
            timeout=int(route.get("timeout", DEFAULT_TIMEOUT)),
            retries=int(route.get("retries", DEFAULT_RETRIES)),
            model=route.get("model"),
        )
        return ("ok", None)
    except Exception as ex:  # noqa: BLE001 — record failure, keep matrix going
        return ("fail", str(ex))


def main():
    ap = argparse.ArgumentParser(description="route-matrix experiment orchestrator")
    ap.add_argument("--matrix", required=True, type=Path,
                    help="path to the route-matrix JSON")
    ap.add_argument("--dry-run", action="store_true",
                    help="print planned routes + catalog, run NO gens")
    ap.add_argument("--catalog", type=Path, default=None,
                    help="where to write the results catalog JSON "
                         "(default: <matrix>.catalog.json)")
    ap.add_argument("--max-openai", type=int, default=4,
                    help="max concurrent openai routes (default 4)")
    a = ap.parse_args()

    try:
        routes = load_matrix(a.matrix)
    except Exception as ex:  # noqa: BLE001
        print("ERROR loading matrix: %s" % ex, file=sys.stderr)
        return 2

    catalog_out = a.catalog or a.matrix.with_suffix(a.matrix.suffix + ".catalog.json")

    nano_routes = [r for r in routes if r["provider"] == "nano"]
    openai_routes = [r for r in routes if r["provider"] == "openai"]

    print("[run_matrix] %d route(s): %d openai (concurrent), %d nano (serial)"
          % (len(routes), len(openai_routes), len(nano_routes)), file=sys.stderr)
    for r in routes:
        print("  - %-18s %-7s prompt=%s refs=%d -> %s"
              % (r["label"], r["provider"], r["prompt_file"],
                 len(r.get("refs", [])), r["out"]), file=sys.stderr)

    if a.dry_run:
        catalog = [catalog_entry(r, "skipped(dry-run)") for r in routes]
        out_text = json.dumps(catalog, indent=2)
        catalog_out.parent.mkdir(parents=True, exist_ok=True)
        catalog_out.write_text(out_text)
        print("[run_matrix] DRY-RUN — no gens executed. Catalog -> %s" % catalog_out,
              file=sys.stderr)
        print(out_text)
        return 0

    results = {}  # label -> (status, error)

    # 1) nano serially FIRST (never overlaps openai either).
    for r in nano_routes:
        print("[run_matrix] nano (serial): %s" % r["label"], file=sys.stderr)
        results[r["label"]] = run_route(r)

    # 2) openai concurrently.
    if openai_routes:
        workers = max(1, min(a.max_openai, len(openai_routes)))
        with ThreadPoolExecutor(max_workers=workers) as ex_pool:
            futs = {ex_pool.submit(run_route, r): r for r in openai_routes}
            for fut in as_completed(futs):
                r = futs[fut]
                results[r["label"]] = fut.result()
                print("[run_matrix] openai done: %s -> %s"
                      % (r["label"], results[r["label"]][0]), file=sys.stderr)

    catalog = []
    n_ok = n_fail = 0
    for r in routes:
        status, err = results.get(r["label"], ("planned", None))
        if status == "ok":
            n_ok += 1
        elif status == "fail":
            n_fail += 1
            print("[run_matrix] FAIL %s: %s" % (r["label"], err), file=sys.stderr)
        entry = catalog_entry(r, status)
        if err:
            entry["error"] = err
        catalog.append(entry)

    out_text = json.dumps(catalog, indent=2)
    catalog_out.parent.mkdir(parents=True, exist_ok=True)
    catalog_out.write_text(out_text)
    print("[run_matrix] %d ok, %d fail. Catalog -> %s" % (n_ok, n_fail, catalog_out),
          file=sys.stderr)
    print(out_text)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
