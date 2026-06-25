---
nid: myyoxw
title: "Family B \u2014 Skyline / multi-panel"
type: map
nodes: [s0-intake, s1a-style, s1b-geometry, s2-generation, s3-select, s4-repair, s5-export]
edges:
  - {from: s0-intake, to: s1a-style, label: ""}
  - {from: s0-intake, to: s1b-geometry, label: ""}
  - {from: s1a-style, to: s2-generation, label: ""}
  - {from: s1b-geometry, to: s2-generation, label: ""}
  - {from: s2-generation, to: s3-select, label: ""}
  - {from: s3-select, to: s4-repair, label: ""}
  - {from: s4-repair, to: s5-export, label: ""}
---

# Family B — Skyline / multi-panel

Top map for **Family B** (skyline / multi-panel). Same stage spine as A; geometry (1b) + generation (2) are skyline-specialized. Spine: `docs/PIPELINE.md`.
