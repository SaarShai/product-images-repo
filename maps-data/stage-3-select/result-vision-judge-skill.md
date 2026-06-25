---
nid: nyt5xa
title: "result-vision-judge skill"
type: reference
x: 660
y: 600
icon: "📚"
summary: "skills/result-vision-judge — SOP: judge vision + geometry together, never one alone"
status: draft
tags: [skill, judge, sop]
---
# result-vision-judge skill

The governing SOP for Stage 3 judging: `skills/result-vision-judge`.

Use it whenever judging a generated illustration against a geometry template — by you
or a sub-agent. It mandates judging on **BOTH** vision (look at the candidate **with**
the SVG-geometry overlay) **AND** the geometry calculation (region-IoU / white-IoU) —
never the metric alone and never the raw image alone. It writes a `judge.json` verdict
into the results library.

Governs [[vision-judge|vision-judge]] and pairs with [[judge-py|scripts/judge.py]].
The related [[?svg-template-review-judge|svg-template-review-judge]] skill covers the
accept / patch / restart decision for template-constrained candidates.

LAWS: **metrics lie → look at the overlay**, and **show full-size, all candidates**
(never decide style/sharpness from a low-res board).
