---
nid: nco1he
title: "Scout (proof-before-spend)"
type: step
x: 140
y: 300
icon: "🔭"
summary: "Generate 2–3 cheap low-res scouts with DISTINCT prompt strategies"
gate: "scouts show distinct hierarchy; landmarks whole within panels; red zones quiet"
status: draft
tags: [generation, scout, skyline]
---
# Scout (proof-before-spend)

Before spending on a polished full illustration, prove the composition route is
likely to work. Generate **2–3 cheap low-res scouts** using genuinely **distinct
prompt strategies** — not the same prompt three times. Useful strategy splits:

- direct whole-scene control from roster + references;
- a rough composition map used only as a whole-redraw guide (not pixels to collage);
- a strict seam-safety scout that stresses no-crop / keep-clear behaviour.

Feed reference IMAGES + the geometry guide (law: reference beats prose). Keep the
prompts free of geometry words — describe the skyline, never the template.

Gate: **scouts show distinct hierarchy; landmarks whole within panels; red zones
quiet.** Faint lookalike placement boards do NOT pass — the hierarchy and route
differences must read within a few seconds. If all scouts fail the same way,
restart the method instead of polishing a wireframe.

Tool: [[subgen-py|scripts/subgen.py]] (cheap low-res variants).
Workflow: [[skyline-workflow|docs/skyline-template-illustration-workflow.md]].
Next: [[choose-strategy|choose-strategy]].
