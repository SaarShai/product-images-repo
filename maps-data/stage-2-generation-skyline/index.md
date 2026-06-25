---
nid: mqy62v
title: "Stage 2 — Generation (skyline / multi-panel)"
type: map
kind: process
nodes:
  - scout
  - choose-strategy
  - polish
  - overlay-check
  - subgen-py
  - skyline-workflow
edges:
  - {from: scout, to: choose-strategy, label: ""}
  - {from: choose-strategy, to: polish, label: "best scout"}
  - {from: polish, to: overlay-check, label: ""}
  - {from: scout, to: skyline-workflow, label: "", route: smoothstep}
  - {from: polish, to: subgen-py, label: "", route: smoothstep}
---
# Stage 2 — Generation (skyline / multi-panel)

The skyline / multi-panel flavour of Stage 2. Produce candidate skylines for the
three-panel die-cut template, fed with references (1a) + the geometry guide (1b).
Multiplicity over one-shot: prove the route cheaply first, then polish only the
chosen strategy with ≥3 attempts.

Flow: [[scout|scout]] (proof-before-spend) → [[choose-strategy|choose-strategy]]
(which scout reads best?) → [[polish|polish]] (full-res, ≥3 attempts of the picked
strategy) → [[overlay-check|overlay-check]] (`skyline_panel.py` geometry gate).

Two laws govern every node here:

- **Reference beats prose** — drive generation with reference IMAGES + the
  geometry guide, never description alone.
- **No geometry words in the prompt** — never write `SVG`, `contour`, `red zone`,
  `blue separator`, `saloon arch`, `top contour`, or `panel proportions` into a
  generation prompt. Those constraints belong to the deterministic
  overlay/export step and the verifier checklist, not the creative prompt.

Tooling: [[subgen-py|scripts/subgen.py]]. Workflow source of truth:
[[skyline-workflow|docs/skyline-template-illustration-workflow.md]].
