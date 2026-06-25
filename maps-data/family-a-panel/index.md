---
nid: metgr1
title: "Family A \u2014 SVG die-cut panel"
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

# Family A — SVG die-cut panel

Top map for **Family A** (SVG die-cut product panels). Stages run left→right; 1a/1b are parallel constraint-prep. Each node drills into its child map. Spine: `docs/PIPELINE.md`.
