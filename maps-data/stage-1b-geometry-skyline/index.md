---
nid: mqieox
title: "Stage 1b — Geometry (Skyline / multi-panel)"
type: map
kind: process
status: draft
nodes:
  - parse-3panel-svg
  - allocate-landmarks
  - plan-saloon-arch
  - adapt-top-contour
  - safe-pocket-plan
  - skyline-panel-py
  - skyline-workflow
edges:
  - {from: parse-3panel-svg, to: allocate-landmarks, label: ""}
  - {from: allocate-landmarks, to: plan-saloon-arch, label: ""}
  - {from: plan-saloon-arch, to: adapt-top-contour, label: ""}
  - {from: adapt-top-contour, to: safe-pocket-plan, label: ""}
  - {from: parse-3panel-svg, to: skyline-panel-py, label: "", route: smoothstep}
  - {from: allocate-landmarks, to: skyline-workflow, label: "", route: smoothstep}
---
# Stage 1b — Geometry (Skyline / multi-panel)

Geometry prep for Family B (skyline / 3-panel). The SVG is the coordinate
authority: panel widths, aspects, separator heights, red keep-clear zones, the
saloon-door arch, and the top contour all come from the SVG viewBox — never from
a raster preview or a model-drawn guide. This stage derives the per-panel
geometry contract, allocates landmarks so none is split, treats the saloon arch
and top contour as compositional opportunities rather than forced architecture,
and ends on a gate that proves the guide aspect matches the panel and the red
zones hold only quiet/infrastructure filler.

Tool: [[skyline-panel-py|scripts/skyline_panel.py]] (spec → per-panel
`.spec.json`, guide build, panel checks). Workflow source of truth:
[[skyline-workflow|docs/skyline-template-illustration-workflow.md]].

LAW: **never put template-geometry words in the generation prompt** — `SVG`,
`contour`, `panel proportions`, `red zone`, `blue separator`, `green line`,
`orange arch`, `saloon-door guide` and the like belong to the deterministic
overlay/export and the verifier checklist, not the creative prompt. **SVG is the
coordinate authority** — a beautiful skyline never owns the physical template.
