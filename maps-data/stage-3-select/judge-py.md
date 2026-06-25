---
nid: n8x7vw
title: "judge.py"
type: reference
x: 660
y: 450
icon: "🛠️"
summary: "scripts/judge.py — VLM judge over the SVG overlay; ≥3 judges, hi-DPI crops"
status: draft
tags: [tool, script, judge]
---
# judge.py

The Stage 3 vision-judge tool: `scripts/judge.py`.

It runs a VLM judge over a candidate **with the SVG-geometry overlay drawn on it**,
not the raw image or the metric alone. Used with **≥3 judges** per candidate and
**hi-DPI crops** for detail; duplicate counting is delegated to `scripts/dup_detect.py`
on the whole-panel context. Writes a `judge.json` verdict into the results library.

Drives [[vision-judge|vision-judge]]. SOP: [[result-vision-judge-skill|skills/result-vision-judge]].

LAW: **metrics lie → look at the overlay** — a passing region-IoU / outside-mask
number is never acceptance; the judge looks at the overlaid candidate.
