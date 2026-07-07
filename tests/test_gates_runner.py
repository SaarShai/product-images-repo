import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
GATES = REPO / "scripts" / "gates.py"


def _write_geometry(tmp_path):
    geom = tmp_path / "geom"
    geom.mkdir()
    panel = "toy"
    w, h = 80, 120

    holes = Image.new("L", (w, h), 0)
    ImageDraw.Draw(holes).ellipse([34, 52, 46, 64], fill=255)

    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rectangle([8, 8, 72, 112], fill=255)
    d.ellipse([34, 52, 46, 64], fill=0)

    control = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(control)
    d.rectangle([8, 8, 72, 112], outline=255, width=2)
    d.ellipse([34, 52, 46, 64], outline=255, width=2)

    forbidden = Image.new("L", (w, h), 0)
    ImageDraw.Draw(forbidden).rectangle([28, 20, 32, 100], fill=255)

    mask.save(geom / f"{panel}-mask.png")
    control.convert("RGB").save(geom / f"{panel}-control.png")
    forbidden.save(geom / f"{panel}-forbidden.png")
    holes.save(geom / f"{panel}-holes.png")
    (geom / f"{panel}-spec.json").write_text(
        json.dumps(
            {
                "panel": panel,
                "source": "test",
                "size_px": [w, h],
                "aspect": round(w / h, 4),
                "body_frac": 0.8,
                "holes_n": 1,
                "forbidden_bands_frac": [[0.35, 0.4]],
            },
            indent=2,
        )
        + "\n"
    )
    return geom, panel


def _candidate(path, geom, panel, fill=True, hole_color=None):
    mask = np.array(Image.open(geom / f"{panel}-mask.png").convert("L")) > 127
    holes = np.array(Image.open(geom / f"{panel}-holes.png").convert("L")) > 127
    arr = np.full((120, 80, 3), 255, dtype=np.uint8)
    if fill:
        arr[mask] = (130, 92, 62)
    if hole_color is not None:
        arr[holes] = hole_color
    Image.fromarray(arr).save(path)
    return path


def _run(cand, geom, panel, outdir, stage="init"):
    return subprocess.run(
        [
            sys.executable,
            str(GATES),
            "--cand",
            str(cand),
            "--geom",
            str(geom),
            "--panel",
            panel,
            "--outdir",
            str(outdir),
            "--stage",
            stage,
        ],
        capture_output=True,
        text=True,
    )


def test_gates_runner_passes_good_candidate_and_writes_bundle(tmp_path):
    geom, panel = _write_geometry(tmp_path)
    cand = _candidate(tmp_path / "good.png", geom, panel)
    outdir = tmp_path / "out"

    result = _run(cand, geom, panel, outdir)

    assert result.returncode == 0, result.stdout + result.stderr
    bundle = json.loads(result.stdout)
    assert bundle["overall_verdict"] == "PASS"
    assert bundle["gates"]["holes"]["verdict"] == "PASS"
    assert bundle["gates"]["dimensions"]["verdict"] == "PASS"
    assert Path(bundle["overlay_path"]).exists()
    assert (outdir / f"{panel}-init-bundle.json").exists()


def test_gates_runner_fails_when_hole_region_is_painted(tmp_path):
    geom, panel = _write_geometry(tmp_path)
    cand = _candidate(tmp_path / "bad-hole.png", geom, panel, hole_color=(30, 20, 10))
    outdir = tmp_path / "out"

    result = _run(cand, geom, panel, outdir)

    assert result.returncode == 2
    bundle = json.loads(result.stdout)
    assert bundle["overall_verdict"] == "FAIL"
    assert bundle["gates"]["holes"]["verdict"] == "FAIL"
    assert bundle["gates"]["holes"]["holes"][0]["mean_luminance"] < 245
    assert Path(bundle["overlay_path"]).exists()


def test_gates_runner_downgrades_fill_only_geom_failure_to_warn(tmp_path):
    geom, panel = _write_geometry(tmp_path)
    cand = _candidate(tmp_path / "sparse.png", geom, panel, fill=False)
    outdir = tmp_path / "out"

    result = _run(cand, geom, panel, outdir)

    assert result.returncode == 0, result.stdout + result.stderr
    bundle = json.loads(result.stdout)
    assert bundle["overall_verdict"] == "WARN"
    assert bundle["gates"]["geom"]["verdict"] == "WARN"
    assert bundle["gates"]["geom"]["raw_verdict"] == "FAIL"
    assert bundle["gates"]["geom"]["downgraded_failures"]
