---
nid: nimr3m
title: "skyline_panel.py"
type: reference
x: 140
y: 450
icon: "🛠️"
summary: "scripts/skyline_panel.py — spec → per-panel .spec.json, guide build, panel checks"
status: draft
tags: [tool, script, skyline]
---
# skyline_panel.py

The Stage 1b skyline geometry tool: `scripts/skyline_panel.py`.

It emits the per-panel geometry contract (`spec` → `.spec.json`) from the SVG
viewBox, builds the geometry guide image, and runs the panel-typed checks
(guide-aspect-equals-panel preflight, side-fill / taper gates, red-zone lane
crops). The `.spec.json` is the single source of geometry consumed by both the
generation guide and the judge — agents never hand-author a guide.

Drives [[parse-3panel-svg|parse-3panel-svg]] and the
[[safe-pocket-plan|safe-pocket-plan]] gate. Workflow:
[[skyline-workflow|docs/skyline-template-illustration-workflow.md]].
