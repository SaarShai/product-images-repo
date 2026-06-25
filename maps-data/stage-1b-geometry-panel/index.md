---
nid: m8s3b4
title: "Stage 1b — Geometry (SVG die-cut panel)"
type: map
kind: process
status: draft
nodes:
  - parse-svg
  - classify-roles
  - build-guide
  - outset-needed
  - outset-cutouts
  - verify-coords
  - svg-geometry-report-py
  - svg-template-workflow
edges:
  - {from: parse-svg, to: classify-roles, label: ""}
  - {from: classify-roles, to: build-guide, label: ""}
  - {from: build-guide, to: outset-needed, label: ""}
  - {from: outset-needed, to: outset-cutouts, label: "Yes"}
  - {from: outset-cutouts, to: verify-coords, label: ""}
  - {from: outset-needed, to: verify-coords, label: "No"}
  - {from: parse-svg, to: svg-geometry-report-py, label: "", route: smoothstep}
  - {from: build-guide, to: svg-template-workflow, label: "", route: smoothstep}
---
# Stage 1b — Geometry (SVG die-cut panel)

Geometry prep for **family A** (SVG-template / die-cut PANELS). The job is to turn
the authoritative SVG into a coordinate-true contract and a true-aspect geometry
guide that the image model receives as input — so layout is locked **by
construction, not by hope** (spine law 2). The SVG viewBox is the single
**coordinate authority** (law 3): outer contour, internal cutouts, and keep-clear
zones come from the SVG, never from a raster preview.

Flow: [[parse-svg|parse-svg]] reads the geometry → [[classify-roles|classify-roles]]
assigns every shape a role → [[build-guide|build-guide]] renders the true-aspect
guide → [[outset-needed|outset-needed]] decides whether tight cutouts need a drift
buffer ([[outset-cutouts|outset-cutouts]]) before the final
[[verify-coords|verify-coords]] gate.

Tooling: [[svg-geometry-report-py|scripts/svg_geometry_report.py]],
`scripts/build_trueaspect_base.py`, `scripts/outset_cutouts.py`. Skill:
`svg-template-illustration`. Workflow detail:
[[svg-template-workflow|docs/svg-template-illustration-workflow.md]].
