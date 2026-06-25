---
nid: n2z879
title: "Classify family"
type: step
x: 400
y: 300
icon: "🗂️"
summary: "Run intake.py — classify task family A–F + which stages apply"
gate: "family + applicable stages determined"
status: draft
tags: [intake, router]
---
# Classify family

Run [[intake-py|scripts/intake.py]]. It classifies the task into one of the six
families and decides which downstream stages actually run:

| Family | Has geometry? | Stages |
|---|---|---|
| A. SVG-template / die-cut panel | yes | 0·1a·1b·2·3·4·5 |
| B. Skyline / multi-panel | yes | 0·1a·1b·2·3·4·5 |
| C. Free illustration (no template) | no | 0·1a·(1c)·2·3·(4) |
| D. Finished-illustration repair/refine | no | 0·(1a)·4·(3) |
| E. Element-edit (one element, rest byte-exact) | no | 0·4 |
| F. Upscale / enhance only | no | 0·4(upscale) |

This is the task-type router from the spine — it determines the whole rest of the
pipeline, so it gates: **family + applicable stages determined**. Next: validate the
references at [[inventory-refs|inventory-refs]].
