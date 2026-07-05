"""Panel Packet schema and validation helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


PANEL_TYPES = ("door", "narrow", "generic", "skyline", "edge-socket")
DEFAULT_GEOM_IOU_MIN = 0.85
DEFAULT_N_CANDIDATES = 6
DEFAULT_PROVIDERS = ["openai", "nano"]


@dataclass
class PanelPacket:
    svg_path: str
    panel_type: str
    style: dict
    output: dict
    gates: dict = field(default_factory=lambda: {"geom_iou_min": DEFAULT_GEOM_IOU_MIN})
    n_candidates: int = DEFAULT_N_CANDIDATES
    providers: list = field(default_factory=lambda: list(DEFAULT_PROVIDERS))


def load_packet(path):
    """Load a JSON packet, apply validation defaults, raise on invalid.

    Loading is the hard boundary: no run may start from an invalid packet.
    """
    packet_path = Path(path)
    data = json.loads(packet_path.read_text())
    errors = validate_packet(data)
    if errors:
        raise ValueError(f"invalid packet {packet_path}: " + "; ".join(errors))
    return data


def validate_packet(d):
    """Validate and normalize a packet dict.

    Returns a list of error strings. Defaults are applied in place. This function
    is deliberately defensive and never raises for malformed packet data.
    """
    errors = []
    try:
        if not isinstance(d, dict):
            return ["packet must be an object"]

        _validate_svg_path(d, errors)
        _validate_panel_type(d, errors)
        _validate_style(d, errors)
        _validate_gates(d, errors)
        _validate_n_candidates(d, errors)
        _validate_providers(d, errors)
        _validate_output(d, errors)
    except Exception as exc:
        errors.append(f"validation failed: {exc}")
    return errors


def _validate_svg_path(d, errors):
    svg_path = d.get("svg_path")
    if not svg_path:
        errors.append("missing svg_path")
        return
    if not isinstance(svg_path, (str, Path)):
        errors.append("svg_path must be a path string")
        return
    if not Path(svg_path).exists():
        errors.append(f"svg_path does not exist: {svg_path}")


def _validate_panel_type(d, errors):
    panel_type = d.get("panel_type")
    if not panel_type:
        errors.append("missing panel_type")
        return
    if panel_type not in PANEL_TYPES:
        allowed = ", ".join(PANEL_TYPES)
        errors.append(f"panel_type must be one of: {allowed}")


def _validate_style(d, errors):
    style = d.get("style")
    if not isinstance(style, dict):
        errors.append("style must be an object")
        return

    ref_images = style.get("ref_images")
    if not ref_images:
        errors.append("style.ref_images must contain at least one path")
        return
    if not isinstance(ref_images, list):
        errors.append("style.ref_images must be a list")
        return

    for ref_path in ref_images:
        if not isinstance(ref_path, (str, Path)):
            errors.append("style.ref_images entries must be path strings")
            continue
        if not Path(ref_path).exists():
            errors.append(f"style.ref_images path does not exist: {ref_path}")

    for optional_id in ("packet_id", "lora_id"):
        if optional_id in style and not isinstance(style[optional_id], str):
            errors.append(f"style.{optional_id} must be a string")


def _validate_gates(d, errors):
    gates = d.get("gates")
    if gates is None:
        gates = {}
        d["gates"] = gates
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
        return
    gates.setdefault("geom_iou_min", DEFAULT_GEOM_IOU_MIN)
    geom_iou_min = gates.get("geom_iou_min")
    if isinstance(geom_iou_min, bool) or not isinstance(geom_iou_min, (int, float)):
        errors.append("gates.geom_iou_min must be a float")


def _validate_n_candidates(d, errors):
    if "n_candidates" not in d:
        d["n_candidates"] = DEFAULT_N_CANDIDATES
    n_candidates = d.get("n_candidates")
    if isinstance(n_candidates, bool) or not isinstance(n_candidates, int):
        errors.append("n_candidates must be an int")
        return
    if n_candidates < 1:
        errors.append("n_candidates must be at least 1")


def _validate_providers(d, errors):
    if "providers" not in d:
        d["providers"] = list(DEFAULT_PROVIDERS)
    providers = d.get("providers")
    if not isinstance(providers, list):
        errors.append("providers must be a list")
        return
    if not providers:
        errors.append("providers must contain at least one provider")
        return
    for provider in providers:
        if not isinstance(provider, str) or not provider:
            errors.append("providers entries must be non-empty strings")


def _validate_output(d, errors):
    output = d.get("output")
    if not isinstance(output, dict):
        errors.append("output must be an object")
        return
    for key in ("production_images_dir", "task_dir"):
        value = output.get(key)
        if not value:
            errors.append(f"missing output.{key}")
        elif not isinstance(value, (str, Path)):
            errors.append(f"output.{key} must be a path string")
