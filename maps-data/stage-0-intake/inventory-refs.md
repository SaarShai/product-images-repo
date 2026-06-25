---
nid: n21rlw
title: "Inventory references"
type: step
x: 660
y: 300
icon: "🔎"
summary: "Validate every named reference exists + read its dimensions"
gate: "all named references present & readable"
status: draft
tags: [intake, references]
---
# Inventory references

Walk every reference named in the brief and confirm it is actually on disk,
readable, and capture its dimensions (so later stages know aspect / resolution).
`scripts/intake.py` does this inventory as part of its run.

Any reference that is named but missing is **flagged** here — it does not stop the
stage, it routes the plan toward generating that reference as a precursor (1c). A
present-but-unusable file (corrupt, wrong type) counts as missing.

Gate: **all named references present & readable**. The verdict feeds the branch at
[[refs-complete|refs-complete]].
