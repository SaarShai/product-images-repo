---
schema_version: 2
title: "Cut-edge authority: composite-to-cut for fixed cuts, art-derived contour for flexible cuts"
type: concept
domain: "svg-template-illustration"
tier: semantic
confidence: 0.7
trust: asserted
scope: this-repo
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources:
  - "/Users/za/Downloads/Wanderland-Packet-2026-07-11/05-scripts-and-logs/work-log_readable.md"
  - "/Users/za/Downloads/Wanderland-Packet-2026-07-11/06-notes/screenery-lean-assembly.md"
supersedes: []
superseded-by:
contradicts: []
tags: [dieline, illustrator, jsx, composite, contour, wanderland]
---

# Cut-edge authority: composite-to-cut for fixed cuts, art-derived contour for flexible cuts

## Summary

Trigger/symptom: "the painted door/window still doesn't sit in the die cut after several regenerations" — or the inverse, "the cut line should follow the artwork's roof/top contour". First ask WHO owns the edge — the die or the art — because the two cases need opposite recipes, and regeneration solves neither.

**FIXED CUT** (die opening immovable — door, window, socket): composite-to-cut. Regenerating can never land a painted element pixel-exact on its cut (Wanderland fire-station: five regens v1–v5 all mismatched; user: "I have tried to generate mutilple images and the problem is still here"). Instead: (1) measure the cut path from the VECTOR .ai pathItems — never a rasterized PDF, because stray anti-aliased pixels break contour detection; (2) cover-fit-scale the art so its painted element fills the die opening (scale = opening_h / element_h); (3) duplicate the exact cut path, group [clipPath, art], set clipping — the element's edge IS the cut by construction, zero mismatch. Then place the keyed facade below to fill the panel. Verified 2026-07-07 (work-log 4515: "we stopped trying to make the generated door land right and instead made the door inherit the cut shape"). This is the executable form of LAW 0 (reference-beats-description / window-as-opening-not-gate): fixed element = geometry, not content.

**FLEXIBLE CUT** (brief lets the contour move — e.g. top sub-panel follows the art's roof): derive the cut FROM the art. Key out white bg, take topmost non-white pixel per column, keep only the roof band, Gaussian-smooth (sigma 6), sample ~72 pts; splice — don't replace — into the original subpanel path so the fixed SKIRT (side walls, bottom edge, hinge tabs) keeps its original points and handles; offset the traced portion ~2mm INWARD along vertex normals so paint always bleeds past the cut (cutting exactly on the paint edge leaves a white sliver); smooth handles only where adjacent-segment dot > 0.85 so gable peaks stay crisp. Verified 2026-07-10.

## Illustrator-JSX gotchas hit while executing both

Recorded so that future assembly runs don't rediscover them:

- add/remove reindexes `layer.pageItems` — match groups by mask geometry and capture object refs BEFORE mutating ("the group indices shifted during my swap", work-log 2172).
- `groupItems.geometricBounds` reports UNCLIPPED bounds — verify clips by rendering, never by bounds.
- `app.activeDocument` reverts between separate osascript calls — set it inside EVERY jsx block (a roof contour got drawn into the wrong open document, work-log 5315).
- setting `clipped=true` on an already-clipped group throws "top item must be a path" — check state first.
- `timeout` does not exist on stock macOS — its absence produced false "Illustrator hung" alarms (work-log ~2473).

## Read-only recon chain (find an element's geometry in an open .ai — verified 2026-07-12, marine v10)

When a task references "the open Illustrator file", get geometry without mutating anything: (1) find the doc by name substring over `app.documents` (beware ambiguity — several versions of a file are often open; match the version token, e.g. "v10"); (2) set `app.activeDocument` inside the same jsx; (3) dump layers + `PlacedItem` `file.name` and `geometricBounds` — element identity comes from the placed FILENAME (the turtle was `print-image-083-turtle-2001.png`), not from item names, which are usually empty; (4) `doc.imageCapture(file, rect, opts)` renders any coordinate rect (`ImageCaptureOptions.resolution` minimum is 72 — request 72 and downscale); (5) map AI pt to capture px linearly: `px_x = pt_x - rect_left`, `px_y = rect_top - pt_y` at 72dpi (AI y-axis points UP; forgetting the flip mirrors every zone). Note: the composed art often lives OUTSIDE the active artboard (staging copies) — locate the composed panel by the cut-layer group bounds that enclose the placed art, not by the artboard.

## Evidence

- Wanderland packet work log: /Users/za/Downloads/Wanderland-Packet-2026-07-11/05-scripts-and-logs/work-log_readable.md (lines 2172, 4378, 4515, 5315).
- Canonical executable runbook: screenery-lean repo, `runbooks/panel-image-swap.md`.
- Why-not-skill: LAW 0 principle already HARD-banked in memory; executable runbook is canonical in screenery-lean; a new skill would overlap the svg-template-illustration family.

## Related

- [[semantic-color-region-map-locks-proportions]]
- [[family-a-architectural-watercolor-panel-proven-recipe-geometry-gate-cap-juluca]]
- [[castle-panel-template-cut-bands]]

## Open Questions

- Bleed-margin default (2mm inward) not yet validated on a second physical print run.
