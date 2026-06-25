---
nid: nwtke1
title: "Overlay geometry check (gate)"
type: step
x: 920
y: 300
icon: "📐"
summary: "scripts/skyline_panel.py check — overlay the real SVG and measure"
gate: "panels whole within boundaries; red zones contain only quiet/infrastructure"
status: draft
tags: [gate, geometry, skyline]
---
# Overlay geometry check (gate)

The Stage 2 hard gate for skyline. Overlay the real SVG onto each polished
candidate from [[polish|polish]] and measure with `scripts/skyline_panel.py check`
— overlay aspect, panel-edge x positions, separator y, red keep-clear rectangles,
and the adapted top contour all come from the SVG coordinate system, not a raster
preview crop.

Gate: **panels whole within boundaries; red zones contain only quiet /
infrastructure.** A landmark must read whole inside its physical panel (no cropped
base or entrance at a panel edge); red lanes may hold only blank sky, plain
wall/facade texture, water, rail, or solid train body — never a statue, sign, face,
text, or named landmark detail. A passing number is never acceptance on its own;
inspect the overlay (metrics lie → vision judge mandatory).

Candidates that pass advance to Stage 3 (select / gate). Geometry tool here:
`scripts/skyline_panel.py`. Workflow:
[[skyline-workflow|docs/skyline-template-illustration-workflow.md]].
