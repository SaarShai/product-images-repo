#!/usr/bin/env python3
"""Summarize simple SVG geometry and write a markdown report."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]|-?\d+(?:\.\d+)?")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def is_command(token: str) -> bool:
    return bool(re.fullmatch(r"[AaCcHhLlMmQqSsTtVvZz]", token))


def parse_numbers(value: str | None) -> list[float]:
    if not value:
        return []
    return [float(match.group(0)) for match in TOKEN_RE.finditer(value) if not is_command(match.group(0))]


def path_coords(d: str | None) -> list[tuple[float, float]]:
    if not d:
        return []

    tokens = TOKEN_RE.findall(d)
    coords: list[tuple[float, float]] = []
    x = y = start_x = start_y = 0.0
    index = 0
    command = ""

    def has_number(offset: int = 0) -> bool:
        return index + offset < len(tokens) and not is_command(tokens[index + offset])

    def has_numbers(count: int) -> bool:
        return all(has_number(offset) for offset in range(count))

    def number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        if is_command(tokens[index]):
            command = tokens[index]
            index += 1
        if not command:
            break

        relative = command.islower()
        cmd = command.upper()

        if cmd == "M":
            first = True
            while has_numbers(2):
                nx = number()
                ny = number()
                if relative:
                    nx += x
                    ny += y
                x, y = nx, ny
                coords.append((x, y))
                if first:
                    start_x, start_y = x, y
                    first = False
                command = "l" if relative else "L"
        elif cmd == "L":
            while has_numbers(2):
                nx = number()
                ny = number()
                if relative:
                    nx += x
                    ny += y
                x, y = nx, ny
                coords.append((x, y))
        elif cmd == "H":
            while has_number():
                nx = number()
                if relative:
                    nx += x
                x = nx
                coords.append((x, y))
        elif cmd == "V":
            while has_number():
                ny = number()
                if relative:
                    ny += y
                y = ny
                coords.append((x, y))
        elif cmd == "C":
            while has_numbers(6):
                values = [number() for _ in range(6)]
                points = [(values[0], values[1]), (values[2], values[3]), (values[4], values[5])]
                if relative:
                    points = [(px + x, py + y) for px, py in points]
                coords.extend(points)
                x, y = points[-1]
        elif cmd == "S":
            while has_numbers(4):
                values = [number() for _ in range(4)]
                points = [(values[0], values[1]), (values[2], values[3])]
                if relative:
                    points = [(px + x, py + y) for px, py in points]
                coords.extend(points)
                x, y = points[-1]
        elif cmd == "Q":
            while has_numbers(4):
                values = [number() for _ in range(4)]
                points = [(values[0], values[1]), (values[2], values[3])]
                if relative:
                    points = [(px + x, py + y) for px, py in points]
                coords.extend(points)
                x, y = points[-1]
        elif cmd == "T":
            while has_numbers(2):
                nx = number()
                ny = number()
                if relative:
                    nx += x
                    ny += y
                x, y = nx, ny
                coords.append((x, y))
        elif cmd == "A":
            while has_numbers(7):
                values = [number() for _ in range(7)]
                nx, ny = values[5], values[6]
                if relative:
                    nx += x
                    ny += y
                x, y = nx, ny
                coords.append((x, y))
        elif cmd == "Z":
            x, y = start_x, start_y
            coords.append((x, y))
        else:
            break

    return coords


def element_coords(node: ET.Element) -> list[tuple[float, float]]:
    tag = local_name(node.tag)
    if tag == "rect":
        x = float(node.attrib.get("x", 0))
        y = float(node.attrib.get("y", 0))
        w = float(node.attrib.get("width", 0))
        h = float(node.attrib.get("height", 0))
        return [(x, y), (x + w, y + h)]
    if tag == "line":
        return [
            (float(node.attrib.get("x1", 0)), float(node.attrib.get("y1", 0))),
            (float(node.attrib.get("x2", 0)), float(node.attrib.get("y2", 0))),
        ]
    if tag == "path":
        return path_coords(node.attrib.get("d"))
    if tag in {"polygon", "polyline"}:
        values = parse_numbers(node.attrib.get("points"))
        if len(values) < 4:
            return []
        return list(zip(values[0::2], values[1::2]))
    if tag == "circle":
        cx = float(node.attrib.get("cx", 0))
        cy = float(node.attrib.get("cy", 0))
        r = float(node.attrib.get("r", 0))
        return [(cx - r, cy - r), (cx + r, cy + r)]
    if tag == "ellipse":
        cx = float(node.attrib.get("cx", 0))
        cy = float(node.attrib.get("cy", 0))
        rx = float(node.attrib.get("rx", 0))
        ry = float(node.attrib.get("ry", 0))
        return [(cx - rx, cy - ry), (cx + rx, cy + ry)]
    return []


def bbox(coords: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
    if not coords:
        return None
    xs = [coord[0] for coord in coords]
    ys = [coord[1] for coord in coords]
    return min(xs), min(ys), max(xs), max(ys)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", type=Path, default=ROOT / "assets/templates/two-panel-template.svg", nargs="?")
    parser.add_argument("--out", type=Path, default=ROOT / "tasks/castle-panels/svg-geometry-report.md")
    args = parser.parse_args()

    svg = args.svg if args.svg.is_absolute() else ROOT / args.svg
    tree = ET.parse(svg)
    root = tree.getroot()
    rows: list[tuple[str, str, tuple[float, float, float, float]]] = []
    all_coords: list[tuple[float, float]] = []

    for node in root.iter():
        coords = element_coords(node)
        node_bbox = bbox(coords)
        if node_bbox is None:
            continue
        all_coords.extend(coords)
        rows.append((
            local_name(node.tag),
            node.attrib.get("id") or node.attrib.get("class") or "(unnamed)",
            node_bbox,
        ))

    active_bbox = bbox(all_coords)
    lines = [
        "# SVG Geometry Report",
        "",
        f"Source: `{svg.relative_to(ROOT)}`",
        f"ViewBox: `{root.attrib.get('viewBox', '')}`",
        "",
    ]
    if active_bbox:
        x0, y0, x1, y1 = active_bbox
        lines.extend([
            "## Active Geometry Bounds",
            "",
            f"- x: `{x0:.2f}` to `{x1:.2f}`",
            f"- y: `{y0:.2f}` to `{y1:.2f}`",
            f"- width: `{x1 - x0:.2f}`",
            f"- height: `{y1 - y0:.2f}`",
            "",
        ])

    lines.extend([
        "## Elements",
        "",
        "| Type | ID/Class | Bounds |",
        "|---|---|---|",
    ])
    for tag, name, item_bbox in rows:
        x0, y0, x1, y1 = item_bbox
        lines.append(f"| `{tag}` | `{name}` | `{x0:.2f},{y0:.2f}` -> `{x1:.2f},{y1:.2f}` |")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
