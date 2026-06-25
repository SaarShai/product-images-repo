---
nid: mbnlo7
title: "Stage 3 — Select / Gate"
type: map
kind: process
nodes:
  - deterministic-gates
  - pass
  - back-to-generation
  - vision-judge
  - build-board
  - human-pick
  - judge-py
  - result-vision-judge-skill
edges:
  - {from: deterministic-gates, to: pass, label: ""}
  - {from: pass, to: back-to-generation, label: "No"}
  - {from: pass, to: vision-judge, label: "Yes"}
  - {from: vision-judge, to: build-board, label: ""}
  - {from: build-board, to: human-pick, label: ""}
  - {from: vision-judge, to: judge-py, label: "", route: smoothstep}
  - {from: vision-judge, to: result-vision-judge-skill, label: "", route: smoothstep}
---
# Stage 3 — Select / Gate

Narrow a candidate set down to one winner. Three filters, cheapest first:
**deterministic hard-gates → vision judge → human picks from all candidates at full
size**.

1. [[deterministic-gates|deterministic-gates]] runs `scripts/geom_gate.py` +
   `scripts/text_gate.py`. Only candidates that clear region-IoU ≥ 0.85 (template) or
   outside-mask delta == 0 (edit) with a clean text-gate proceed; the rest go
   [[back-to-generation|back-to-generation]] (Stage 2).
2. [[vision-judge|vision-judge]] runs [[judge-py|scripts/judge.py]] over the SVG
   overlay with ≥3 judges and hi-DPI crops; `scripts/dup_detect.py` counts on the
   whole-panel context. SOP: [[result-vision-judge-skill|skills/result-vision-judge]].
3. [[build-board|build-board]] assembles a full-size board of ALL candidates with
   `scripts/style_board.py`, and [[human-pick|human-pick]] is the gate where the user
   picks the winner.

Two laws govern this stage: **metrics lie → look at the overlay** (a passing number is
never acceptance), and **show full-size, all candidates** (never decide style or
sharpness from a low-res board).

**MANDATORY contour-overlay fit check (cap-juluca 2026-06-24):** before approving a
die-cut panel, render the real cut paths (outer silhouette + internal cuts like door
flaps + keep-clear slots) as colored strokes over the candidate at matched aspect
(`rsvg-convert` the cut paths → PIL alpha-composite). cap-juluca proved a candidate can
look perfect yet have painted elements badly misaligned with the die-cut — invisible on
the bare image, obvious on the overlay. **Build the overlay INTO the board** — present
every die-cut candidate WITH its contour overlay AND the fed inputs (guide + refs),
proactively; never present a candidate as good and wait for the user to ask "did you check
the outline?" (they had to, in cap-juluca). If the user approves art that conflicts with a
*movable* internal cut, the cut adapts to the art (spine law 8), never silently.
