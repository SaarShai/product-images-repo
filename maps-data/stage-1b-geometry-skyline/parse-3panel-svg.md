---
nid: nm2ayh
title: "Parse 3-panel SVG"
type: step
x: 140
y: 300
icon: "📐"
summary: "skyline_panel.py spec → per-panel .spec.json (widths/aspects from SVG viewBox)"
gate: "panel widths/aspects derived from SVG viewBox"
status: draft
tags: [svg, geometry, skyline]
---
# Parse 3-panel SVG

Run [[skyline-panel-py|scripts/skyline_panel.py]] in spec mode to emit one
per-panel `.spec.json` for the three physical panels. Panel widths and aspects
are read from the **SVG viewBox** and visible coordinate bounds — one central
door panel plus two narrow side panels — not from a square raster preview, which
lies about aspect.

The `.spec.json` is the single source of geometry that both the generation guide
and the judge consume downstream; agents never hand-author a guide. This is the
realization of "SVG is the coordinate authority".

Gate: **panel widths/aspects derived from SVG viewBox**. Next: assign the
landmark roster at [[allocate-landmarks|allocate-landmarks]].
