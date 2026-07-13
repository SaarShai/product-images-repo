import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw


REPO = Path(__file__).resolve().parents[1]
GATE_PATH = REPO / "scripts" / "gates" / "gate_battery.py"


def load_gate_battery():
    spec = importlib.util.spec_from_file_location("gate_battery", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_crisp_disc(path: Path, size: int = 160) -> None:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    r = size // 3
    cx = cy = size // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 150, 70, 255))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(35, 20, 10, 255), width=5)
    im.save(path)


def save_soft_edge_disc(path: Path, edge_rgb: tuple[int, int, int], size: int = 180) -> None:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    cx = cy = size // 2
    r = size // 3
    fill_rgb = (240, 70, 210)
    for offset, alpha in [(5, 48), (4, 80), (3, 112), (2, 144), (1, 190)]:
        draw.ellipse(
            [cx - r - offset, cy - r - offset, cx + r + offset, cy + r + offset],
            fill=(*edge_rgb, alpha),
        )
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*fill_rgb, 255))
    im.save(path)


def test_white_halo_ring_fails_d1(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "white-halo.png"
    size = 160
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    cx = cy = size // 2
    r = size // 3
    draw.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(255, 255, 255, 96))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 150, 70, 255))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(35, 20, 10, 255), width=5)
    im.save(path)

    result = gate.run_battery(path, None, None, None, "soft", tmp_path / "out", ppi=254)

    assert result["pass"] is False
    assert result["verdict"] == "FAIL"
    assert result["gates"]["D1_halo_gate"]["pass"] is False
    assert result["gates"]["D1_halo_gate"]["verdict"] == "FAIL"
    assert result["gates"]["D1_halo_gate"]["crop_paths"]


def test_bright_colored_soft_aa_edge_passes_donor_referenced_d1(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "bright-aa.png"
    save_soft_edge_disc(path, edge_rgb=(240, 70, 210))

    result = gate.run_battery(path, None, None, None, "soft", tmp_path / "out", ppi=254)

    assert result["gates"]["D1_halo_gate"]["verdict"] == "PASS"
    assert result["gates"]["D1_halo_gate"]["metric_values"]["H_L"] <= 2.0


def test_white_contaminated_soft_edge_fails_donor_referenced_d1(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "white-contaminated-aa.png"
    save_soft_edge_disc(path, edge_rgb=(255, 255, 255))

    result = gate.run_battery(path, None, None, None, "soft", tmp_path / "out", ppi=254)

    assert result["gates"]["D1_halo_gate"]["verdict"] == "FAIL"
    assert result["gates"]["D1_halo_gate"]["metric_values"]["H_area_mm2"] >= 0.10


def test_many_enclosed_alpha_pockets_are_d3a_review_only(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "pockets.png"
    size = 260
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([20, 20, 240, 240], fill=(220, 150, 70, 255), outline=(35, 20, 10, 255), width=5)
    for y in range(35, 225, 12):
        for x in range(35, 225, 12):
            draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(0, 0, 0, 0))
    im.save(path)

    result = gate.run_battery(path, None, None, None, "soft", tmp_path / "out")

    assert result["pass"] is False
    assert result["verdict"] == "REVIEW"
    assert result["gates"]["D3a_alpha_pockets"]["pass"] is False
    assert result["gates"]["D3a_alpha_pockets"]["verdict"] == "REVIEW"
    assert result["gates"]["D3a_alpha_pockets"]["advisory"] is True
    assert result["gates"]["D3a_alpha_pockets"]["metric_values"]["component_count"] > 100
    assert len(result["gates"]["D3a_alpha_pockets"]["crop_paths"]) == 5


def test_retained_background_fails_d3b_when_bg_color_supplied(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "retained-bg.png"
    im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([30, 30, 150, 150], fill=(220, 150, 70, 255), outline=(35, 20, 10, 255), width=5)
    draw.rectangle([75, 75, 105, 105], fill=(255, 255, 255, 255))
    im.save(path)

    result = gate.run_battery(path, None, None, (255, 255, 255), "soft", tmp_path / "out")

    assert result["verdict"] == "FAIL"
    assert result["gates"]["D3b_retained_background"]["verdict"] == "FAIL"
    assert result["gates"]["D3b_retained_background"]["metric_values"]["component_count"] == 1
    assert result["gates"]["D3b_retained_background"]["crop_paths"]


def test_clean_binary_alpha_passes(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "clean.png"
    save_crisp_disc(path)

    result = gate.run_battery(path, None, None, None, "soft", tmp_path / "out")

    assert result["pass"] is True
    assert result["verdict"] == "PASS"
    assert all(item["pass"] for item in result["gates"].values())
    assert (tmp_path / "out" / "battery.json").exists()


def run_cli(
    path: Path,
    out_dir: Path,
    profile: str,
    extra_args=None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = "/tmp/pyc"
    cmd = [
        sys.executable,
        str(GATE_PATH),
        "--rgba",
        str(path),
        "--profile",
        profile,
        "--out-dir",
        str(out_dir),
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_exit_contract_pass_fail_review_profiles(tmp_path):
    clean = tmp_path / "clean.png"
    review_only = tmp_path / "review-soft-alpha.png"
    fail = tmp_path / "fail-retained-bg.png"
    save_crisp_disc(clean)
    save_soft_edge_disc(review_only, edge_rgb=(240, 70, 210))

    im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([35, 35, 145, 145], fill=(220, 150, 70, 255), outline=(35, 20, 10, 255), width=5)
    draw.rectangle([75, 75, 105, 105], fill=(255, 255, 255, 255))
    im.save(fail)

    clean_run = run_cli(clean, tmp_path / "clean-out", "soft")
    review_run = run_cli(review_only, tmp_path / "review-out", "soft")
    print_fail_run = run_cli(review_only, tmp_path / "print-out", "print")
    hard_fail_run = run_cli(fail, tmp_path / "fail-out", "soft", ["--bg-color", "#FFFFFF"])

    assert clean_run.returncode == 0, clean_run.stderr
    assert json.loads(clean_run.stdout)["verdict"] == "PASS"
    assert review_run.returncode == 3, review_run.stdout
    assert json.loads(review_run.stdout)["verdict"] == "REVIEW"
    assert print_fail_run.returncode == 2, print_fail_run.stdout
    assert json.loads(print_fail_run.stdout)["verdict"] == "FAIL"
    assert hard_fail_run.returncode == 2, hard_fail_run.stdout
    assert json.loads(hard_fail_run.stdout)["verdict"] == "FAIL"


def test_border_policy_auto_reviews_and_forbid_fails(tmp_path):
    path = tmp_path / "edge-touching.png"
    im = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 20, 50, 60], fill=(220, 150, 70, 255))
    im.save(path)

    auto_run = run_cli(path, tmp_path / "auto-out", "soft")
    forbid_run = run_cli(path, tmp_path / "forbid-out", "soft", ["--border-policy", "forbid"])

    assert auto_run.returncode == 3, auto_run.stdout
    assert json.loads(auto_run.stdout)["verdict"] == "REVIEW"
    assert forbid_run.returncode == 2, forbid_run.stdout
    assert json.loads(forbid_run.stdout)["verdict"] == "FAIL"


def test_user_approved_marine_soft_profile_never_hard_fails(tmp_path):
    marine = REPO / "REVIEW" / "marine-bed-transparent" / "chroma-lane" / "final-candidate" / "marine_green_P1_keyed_x4.png"

    run = run_cli(marine, tmp_path / "marine-out", "soft")
    result = json.loads(run.stdout)

    assert run.returncode in {0, 3}, run.stdout
    assert result["verdict"] in {"PASS", "REVIEW"}
