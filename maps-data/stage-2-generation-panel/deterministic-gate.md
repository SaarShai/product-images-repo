---
nid: n6681i
title: "Deterministic gate"
type: step
x: 1180
y: 300
icon: "🚦"
summary: "geom_gate + text_gate — deterministic hard gate, hands to Stage 3"
gate: "geom_gate + text_gate pass"
status: draft
tags: [generation, gate, handoff]
---
# Deterministic gate

The exit of Stage 2. Run the deterministic hard gates over the candidate set before
anything reaches selection: **geom_gate** (silhouette / contour fit) and **text_gate**
(no leftover or unwanted text in the artwork). These are machine-checkable and
cheap; they cull obviously-failing candidates so the vision judge and human in
Stage 3 only ever see plausible ones.

Gate: **geom_gate + text_gate pass**. Candidates that clear it are handed to Stage 3
(Select / Gate) — vision judge over the overlay + human picks from all candidates at
full size. A passing metric here is a floor, not acceptance.
