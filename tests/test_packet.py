import json

from studio.packet import validate_packet, load_packet


def make_packet(tmp_path):
    svg = tmp_path / "panel.svg"
    svg.write_text("<svg></svg>")
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"image")
    return {
        "svg_path": str(svg),
        "panel_type": "door",
        "style": {"ref_images": [str(ref)]},
        "gates": {"geom_iou_min": 0.9},
        "n_candidates": 6,
        "providers": ["openai", "nano"],
        "output": {
            "production_images_dir": str(tmp_path / "Images"),
            "task_dir": str(tmp_path / "task"),
        },
    }


def test_valid_packet_passes(tmp_path):
    packet = make_packet(tmp_path)

    assert validate_packet(packet) == []


def test_missing_svg_fails(tmp_path):
    packet = make_packet(tmp_path)
    del packet["svg_path"]

    errors = validate_packet(packet)

    assert any("svg_path" in error for error in errors)


def test_empty_ref_images_fails(tmp_path):
    packet = make_packet(tmp_path)
    packet["style"]["ref_images"] = []

    errors = validate_packet(packet)

    assert any("ref_images" in error for error in errors)


def test_bad_panel_type_fails(tmp_path):
    packet = make_packet(tmp_path)
    packet["panel_type"] = "wall"

    errors = validate_packet(packet)

    assert any("panel_type" in error for error in errors)


def test_defaults_are_applied(tmp_path):
    packet = make_packet(tmp_path)
    del packet["gates"]
    del packet["n_candidates"]
    del packet["providers"]

    assert validate_packet(packet) == []
    assert packet["gates"]["geom_iou_min"] == 0.85
    assert packet["n_candidates"] == 6
    assert packet["providers"] == ["openai", "nano"]


def test_load_packet_rejects_invalid(tmp_path):
    packet = make_packet(tmp_path)
    packet["style"]["ref_images"] = []
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet))

    try:
        load_packet(packet_path)
    except ValueError as exc:
        assert "ref_images" in str(exc)
    else:
        raise AssertionError("load_packet accepted an invalid packet")


def test_load_packet_applies_defaults(tmp_path):
    packet = make_packet(tmp_path)
    del packet["gates"]
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet))

    loaded = load_packet(packet_path)

    assert loaded["gates"]["geom_iou_min"] == 0.85
    assert validate_packet(loaded) == []
