import importlib.util
from pathlib import Path

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

    result = gate.run_battery(path, None, None, "soft", tmp_path / "out")

    assert result["pass"] is False
    assert result["gates"]["D1_halo_gate"]["pass"] is False
    assert result["gates"]["D1_halo_gate"]["crop_paths"]


def test_five_enclosed_pockets_fail_d3(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "pockets.png"
    size = 180
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rectangle([35, 35, 145, 145], fill=(220, 150, 70, 255), outline=(35, 20, 10, 255), width=5)
    for x, y in [(65, 65), (95, 65), (125, 65), (80, 110), (115, 115)]:
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(0, 0, 0, 0))
    im.save(path)

    result = gate.run_battery(path, None, None, "soft", tmp_path / "out")

    assert result["pass"] is False
    assert result["gates"]["D3_pocket_gate"]["pass"] is False
    assert result["gates"]["D3_pocket_gate"]["metric_values"]["component_count"] == 5
    assert len(result["gates"]["D3_pocket_gate"]["crop_paths"]) == 5


def test_clean_binary_alpha_passes(tmp_path):
    gate = load_gate_battery()
    path = tmp_path / "clean.png"
    save_crisp_disc(path)

    result = gate.run_battery(path, None, None, "soft", tmp_path / "out")

    assert result["pass"] is True
    assert all(item["pass"] for item in result["gates"].values())
    assert (tmp_path / "out" / "battery.json").exists()
