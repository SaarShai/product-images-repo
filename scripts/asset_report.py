#!/usr/bin/env python3
"""Report image/template asset status for this repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [
    ROOT / "assets",
    ROOT / "tasks",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def svg_info(path: Path) -> dict[str, object]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"valid_xml": False, "error": str(exc)}

    info: dict[str, object] = {"valid_xml": True}
    info["width"] = root.attrib.get("width")
    info["height"] = root.attrib.get("height")
    info["viewBox"] = root.attrib.get("viewBox")

    ids: list[str] = []
    labels: list[str] = []
    for node in root.iter():
        node_id = node.attrib.get("id")
        label = node.attrib.get("{http://www.inkscape.org/namespaces/inkscape}label")
        if node_id:
            ids.append(node_id)
        if label:
            labels.append(label)

    info["ids"] = ids[:100]
    info["labels"] = labels[:100]
    return info


def inspect_file(path: Path) -> dict[str, object]:
    rel = path.relative_to(ROOT)
    item: dict[str, object] = {
        "path": str(rel),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    suffix = path.suffix.lower()
    if suffix == ".png":
        size = png_size(path)
        item["type"] = "png"
        item["dimensions"] = size
    elif suffix == ".svg":
        item["type"] = "svg"
        item.update(svg_info(path))
    else:
        item["type"] = suffix.lstrip(".") or "unknown"
    return item


def iter_assets(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for base in paths:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__"}]
            for filename in filenames:
                path = Path(dirpath) / filename
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                    found.append(path)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()

    assets = [inspect_file(path) for path in iter_assets(args.paths)]
    expected_svg = ROOT / "assets" / "templates" / "two-panel-template.svg"
    report = {
        "root": str(ROOT),
        "asset_count": len(assets),
        "svg_expected": str(expected_svg.relative_to(ROOT)),
        "svg_present": expected_svg.exists(),
        "assets": assets,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"root: {report['root']}")
    print(f"assets: {report['asset_count']}")
    print(f"svg: {'present' if report['svg_present'] else 'missing'} ({report['svg_expected']})")
    for asset in assets:
        dims = asset.get("dimensions")
        extra = f" {dims[0]}x{dims[1]}" if isinstance(dims, tuple) else ""
        print(f"- {asset['path']} [{asset['type']}]{extra} {asset['bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
