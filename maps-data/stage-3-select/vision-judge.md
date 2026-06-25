---
nid: nd7j6t
title: "Vision judge"
type: step
x: 660
y: 300
icon: "👁️"
summary: "≥3 VLM judges over the SVG overlay + duplicate count on whole-panel context"
gate: "≥3 judges; judged on the overlay, not the metric alone"
status: draft
tags: [judge, vision, vlm]
---
# Vision judge

The mandatory look (law 4: metrics lie → look at the overlay). Run
[[judge-py|scripts/judge.py]] over the candidate **with the SVG-geometry overlay
drawn on it** — never the raw image alone and never the metric alone.

- **≥3 judges** per candidate so a single VLM hallucination can't decide.
- Judge **detail** from **hi-DPI crops**, not a downsampled whole-panel image
  (downsampling makes judges hallucinate on tall panels).
- `scripts/dup_detect.py` counts duplicates on the **WHOLE-panel context, not
  tiles** — tiling hides duplicates across a seam.

Skill: [[result-vision-judge-skill|skills/result-vision-judge]] is the SOP for
judging an illustration against a geometry template (vision + geometry together).

Gate: **≥3 judges; judged on the overlay, not the metric alone.**

Passing candidates flow to the comparison board at [[build-board|build-board]].
