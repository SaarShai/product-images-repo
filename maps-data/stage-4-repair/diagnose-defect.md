---
nid: nktq35
title: "Diagnose defect"
type: step
x: 140
y: 300
icon: "🩺"
summary: "Classify the defect so the right repair engine is chosen"
status: draft
tags: [repair, triage]
---
# Diagnose defect

Look at the finished image and classify the defect — the class decides the engine, so
this is the load-bearing first step. The defect taxonomy:

- **remove** — erase an element (a car, a sign, stray text) and reconstruct the background.
- **redraw-in-place** — repaint one element within its own footprint, keeping its position.
- **restyle** — change the look/medium of a region or the whole figure.
- **reshape** — resize or change the silhouette of an embedded element.
- **edit-text** — replace or re-render text already in the image.
- **exact-geometry** — redraw to a precise contour/cutout (die-cut fit).
- **ghost / haze / occlusion** — a broad faint artifact in a busy scene (the berlin case).
- **blur** — softness/melt; nothing to mask, just sharpen.

The one-command path for the localized pixel edits is [[edit-py|scripts/edit.py]].
Feeds [[route-engine|route to the engine]].
