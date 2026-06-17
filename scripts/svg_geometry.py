#!/usr/bin/env python3
"""Robust, dependency-light SVG geometry reader shared across the workflow.

This is the single authoritative SVG -> geometry parser. It supersedes two
earlier parsers that both failed on real templates:

- ``svg_geometry_report.py`` hung (exit 124) on paths using smooth curves and
  leading-dot decimals (``v-.5s-.05...``) because its tokenizer dropped signs
  and left the command loop with no token to consume and no way to advance.
- ``export_svg_template_fit.parse_path_d`` raised ``Unsupported SVG path
  command`` on ``S``/``Q``/``T``/``A`` (it only handled ``M L H V C Z``).

This reader supports the full path grammar (M L H V C S Q T A Z, absolute and
relative), flattens curves and arcs to polylines, and is hard-guarded so a
malformed ``d`` raises a clear error instead of looping forever.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

Point = tuple[float, float]

# Matches one path command letter OR one number (with sign, leading/trailing
# dot, and scientific notation). This is the number regex that the *export*
# tool got right and the old report tool got wrong.
FLOAT = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
TOKEN_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|" + FLOAT)
CMD_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


@dataclass
class TemplateGeometry:
    viewbox: tuple[float, float, float, float]
    paths: list[list[Point]]
    polygons: list[list[Point]]


def is_command(token: str) -> bool:
    return len(token) == 1 and bool(CMD_RE.fullmatch(token))


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - t
    x = inv**3 * p0[0] + 3 * inv * inv * t * p1[0] + 3 * inv * t * t * p2[0] + t**3 * p3[0]
    y = inv**3 * p0[1] + 3 * inv * inv * t * p1[1] + 3 * inv * t * t * p2[1] + t**3 * p3[1]
    return (x, y)


def quad_point(p0: Point, p1: Point, p2: Point, t: float) -> Point:
    inv = 1.0 - t
    x = inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0]
    y = inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1]
    return (x, y)


def _arc_points(p0: Point, rx: float, ry: float, phi_deg: float, large: int, sweep: int, p1: Point, steps: int) -> list[Point]:
    """Flatten an elliptical arc to points (W3C SVG impl. notes F.6.5)."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi_deg % 360.0)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    dx = (p0[0] - p1[0]) / 2.0
    dy = (p0[1] - p1[1]) / 2.0
    x1p = cos_p * dx + sin_p * dy
    y1p = -sin_p * dx + cos_p * dy
    # Correct out-of-range radii.
    lam = (x1p**2) / (rx**2) + (y1p**2) / (ry**2)
    if lam > 1:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    denom = rx**2 * y1p**2 + ry**2 * x1p**2
    num = rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2
    coef = math.sqrt(max(0.0, num / denom)) if denom else 0.0
    if large == sweep:
        coef = -coef
    cxp = coef * rx * y1p / ry
    cyp = -coef * ry * x1p / rx
    cx = cos_p * cxp - sin_p * cyp + (p0[0] + p1[0]) / 2.0
    cy = sin_p * cxp + cos_p * cyp + (p0[1] + p1[1]) / 2.0

    def angle(ux: float, uy: float, vx: float, vy: float) -> float:
        dot = ux * vx + uy * vy
        n = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, dot / n))) if n else 0.0
        return -a if (ux * vy - uy * vx) < 0 else a

    theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi
    n_steps = max(2, int(steps * abs(dtheta) / (2 * math.pi)) + 1)
    pts: list[Point] = []
    for i in range(1, n_steps + 1):
        t = theta1 + dtheta * i / n_steps
        x = cos_p * rx * math.cos(t) - sin_p * ry * math.sin(t) + cx
        y = sin_p * rx * math.cos(t) + cos_p * ry * math.sin(t) + cy
        pts.append((x, y))
    return pts


def parse_path_d(data: str, curve_steps: int = 28) -> list[list[Point]]:
    """Parse an SVG path ``d`` string into flattened subpaths (>=3 points)."""
    tokens = TOKEN_RE.findall(data)
    i = 0
    n = len(tokens)
    command: str | None = None
    cur: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    prev_cubic_ctrl: Point | None = None
    prev_quad_ctrl: Point | None = None
    poly: list[Point] = []
    subpaths: list[list[Point]] = []

    def finish() -> None:
        nonlocal poly
        if len(poly) >= 3:
            subpaths.append(poly)
        poly = []

    def num() -> float:
        nonlocal i
        if i >= n or is_command(tokens[i]):
            raise ValueError(f"expected number near token {i} in path")
        v = float(tokens[i])
        i += 1
        return v

    def flag() -> int:
        """Read an arc flag (0/1); split a merged token like '0012' -> 0,0,1,2."""
        nonlocal i
        tok = tokens[i]
        if tok in ("0", "1"):
            i += 1
            return int(tok)
        if tok and tok[0] in ("0", "1"):
            tokens[i] = tok[1:]
            return int(tok[0])
        raise ValueError(f"expected arc flag near token {i}: {tok!r}")

    def more_numbers() -> bool:
        return i < n and not is_command(tokens[i])

    while i < n:
        guard = i
        if is_command(tokens[i]):
            command = tokens[i]
            i += 1
        if command is None:
            raise ValueError(f"path starts without a command: {data[:40]!r}")
        rel = command.islower()
        up = command.upper()

        if up == "M":
            x, y = num(), num()
            cur = (cur[0] + x, cur[1] + y) if rel else (x, y)
            finish()
            poly = [cur]
            start = cur
            command = "l" if rel else "L"
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif up == "L":
            x, y = num(), num()
            cur = (cur[0] + x, cur[1] + y) if rel else (x, y)
            poly.append(cur)
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif up == "H":
            x = num()
            cur = (cur[0] + x, cur[1]) if rel else (x, cur[1])
            poly.append(cur)
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif up == "V":
            y = num()
            cur = (cur[0], cur[1] + y) if rel else (cur[0], y)
            poly.append(cur)
            prev_cubic_ctrl = prev_quad_ctrl = None
        elif up == "C":
            c1 = (num(), num())
            c2 = (num(), num())
            end = (num(), num())
            p1 = (cur[0] + c1[0], cur[1] + c1[1]) if rel else c1
            p2 = (cur[0] + c2[0], cur[1] + c2[1]) if rel else c2
            p3 = (cur[0] + end[0], cur[1] + end[1]) if rel else end
            for s in range(1, curve_steps + 1):
                poly.append(cubic_point(cur, p1, p2, p3, s / curve_steps))
            cur, prev_cubic_ctrl, prev_quad_ctrl = p3, p2, None
        elif up == "S":
            c2 = (num(), num())
            end = (num(), num())
            p2 = (cur[0] + c2[0], cur[1] + c2[1]) if rel else c2
            p3 = (cur[0] + end[0], cur[1] + end[1]) if rel else end
            p1 = (2 * cur[0] - prev_cubic_ctrl[0], 2 * cur[1] - prev_cubic_ctrl[1]) if prev_cubic_ctrl else cur
            for s in range(1, curve_steps + 1):
                poly.append(cubic_point(cur, p1, p2, p3, s / curve_steps))
            cur, prev_cubic_ctrl, prev_quad_ctrl = p3, p2, None
        elif up == "Q":
            c1 = (num(), num())
            end = (num(), num())
            p1 = (cur[0] + c1[0], cur[1] + c1[1]) if rel else c1
            p2 = (cur[0] + end[0], cur[1] + end[1]) if rel else end
            for s in range(1, curve_steps + 1):
                poly.append(quad_point(cur, p1, p2, s / curve_steps))
            cur, prev_quad_ctrl, prev_cubic_ctrl = p2, p1, None
        elif up == "T":
            end = (num(), num())
            p2 = (cur[0] + end[0], cur[1] + end[1]) if rel else end
            p1 = (2 * cur[0] - prev_quad_ctrl[0], 2 * cur[1] - prev_quad_ctrl[1]) if prev_quad_ctrl else cur
            for s in range(1, curve_steps + 1):
                poly.append(quad_point(cur, p1, p2, s / curve_steps))
            cur, prev_quad_ctrl, prev_cubic_ctrl = p2, p1, None
        elif up == "A":
            rx, ry, rot = num(), num(), num()
            large, sweep = flag(), flag()
            end = (num(), num())
            p1 = (cur[0] + end[0], cur[1] + end[1]) if rel else end
            poly.extend(_arc_points(cur, rx, ry, rot, large, sweep, p1, curve_steps))
            cur, prev_cubic_ctrl, prev_quad_ctrl = p1, None, None
        elif up == "Z":
            if poly and poly[-1] != start:
                poly.append(start)
            cur = start
            finish()
            command = None
            prev_cubic_ctrl = prev_quad_ctrl = None
        else:
            raise ValueError(f"unsupported SVG path command {command!r}")

        # Hard guard: every iteration must make progress, or we bail loudly
        # instead of spinning forever (the old hang).
        if i == guard and not (up == "Z"):
            raise ValueError(f"path parser made no progress at token {i}: {tokens[max(0, i - 1):i + 2]}")

    finish()
    return subpaths


def parse_points(value: str) -> list[Point]:
    nums = [float(m) for m in re.findall(FLOAT, value)]
    if len(nums) % 2:
        nums = nums[:-1]
    return list(zip(nums[0::2], nums[1::2]))


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def read_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    vb = root.attrib.get("viewBox")
    if vb:
        parts = [float(p) for p in re.split(r"[\s,]+", vb.strip())]
        if len(parts) == 4:
            return tuple(parts)  # type: ignore[return-value]
    width = float(re.findall(FLOAT, root.attrib.get("width", "0"))[0]) if root.attrib.get("width") else 0.0
    height = float(re.findall(FLOAT, root.attrib.get("height", "0"))[0]) if root.attrib.get("height") else 0.0
    return (0.0, 0.0, width, height)


def read_template(svg_path: Path) -> TemplateGeometry:
    """Drop-in replacement for export_svg_template_fit.read_template."""
    root = ET.parse(svg_path).getroot()
    viewbox = read_viewbox(root)
    paths: list[list[Point]] = []
    polygons: list[list[Point]] = []
    for element in root.iter():
        name = tag_name(element)
        if name == "path" and element.attrib.get("d"):
            paths.extend(parse_path_d(element.attrib["d"]))
        elif name == "polygon" and element.attrib.get("points"):
            polygons.append(parse_points(element.attrib["points"]))
    if not paths and not polygons:
        raise ValueError(f"No path/polygon geometry found in {svg_path}")
    return TemplateGeometry(viewbox=viewbox, paths=paths, polygons=polygons)


if __name__ == "__main__":
    import sys

    geo = read_template(Path(sys.argv[1]))
    print(f"viewBox={geo.viewbox}")
    print(f"paths={len(geo.paths)} polygons={len(geo.polygons)}")
