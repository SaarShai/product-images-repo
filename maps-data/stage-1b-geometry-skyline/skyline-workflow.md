---
nid: nuooka
title: "skyline workflow"
type: reference
x: 400
y: 450
icon: "📄"
summary: "docs/skyline-template-illustration-workflow.md — skyline rules source of truth"
status: draft
tags: [doc, workflow, skyline]
---
# skyline workflow

The human-readable source of truth for skyline / city-scape geometry rules:
`docs/skyline-template-illustration-workflow.md`.

It defines the guide-stroke roles (black borders, yellow margins, blue
separators, red keep-clear, green top-contour, orange saloon arch), the
landmark-integrity rule, the saloon-door arch rule, the top-contour rule, and the
template-lock LAW: **never put template-geometry words in the generation prompt**
and **the SVG is the coordinate authority** — a generated skyline never owns the
physical template.

Governs every step in this stage:
[[allocate-landmarks|allocate-landmarks]],
[[plan-saloon-arch|plan-saloon-arch]],
[[adapt-top-contour|adapt-top-contour]], and the
[[safe-pocket-plan|safe-pocket-plan]] gate. Paired with the
[[skyline-panel-py|scripts/skyline_panel.py]] tool. Skill:
skyline-template-illustration.
