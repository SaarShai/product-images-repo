---
nid: nb8tyk
title: "Parse SVG"
type: step
x: 140
y: 300
icon: "📐"
summary: "Run svg_geometry_report.py → report of contour, cutouts, keep-clear"
gate: "outer contour + cutouts + keep-clear zones identified"
status: draft
tags: [svg, geometry, parse]
---
# Parse SVG

Read the geometry before prompting anything. The SVG is the **coordinate
authority** — nothing about layout is inferred from a raster.

```bash
scripts/svg_geometry_report.py <svg> --out svg-geometry-report.md
```

The report enumerates every geometric element so it can be classified:

- the **outer contour** / product body;
- **internal cutouts** — holes, slots, notches, center gaps, shared seams;
- **keep-clear zones** — dashed safe-area contours, red/yellow rectangles.

Watch the two Screenery export traps: a panel edge may be an open path plus a
sibling `<polyline>` (don't close it diagonally), and edge sockets/notches are
carved negative space whose paths can extend *past* the body bounds (don't
classify them as protrusions). If the report misses polygons, inspect the SVG
directly before moving on.

Gate: **outer contour + cutouts + keep-clear zones identified**. Tool detail:
[[svg-geometry-report-py|scripts/svg_geometry_report.py]]. Feeds
[[classify-roles|classify-roles]].
