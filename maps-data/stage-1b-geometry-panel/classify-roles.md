---
nid: nis03s
title: "Classify roles"
type: step
x: 400
y: 300
icon: "🗂️"
summary: "Fill template-manifest.json — contour, cutouts, slots, safe areas"
gate: "all geometry roles assigned (no ambiguous roles)"
status: draft
tags: [svg, geometry, manifest]
---
# Classify roles

Turn the raw report into an explicit role map. Fill `template-manifest.json`,
assigning **every** shape from [[parse-svg|parse-svg]] a production role:

- **contour** — the outer paintable body;
- **cutouts** — internal holes, slots, notches, seams (paint must avoid them);
- **slots** — named safe pockets where focal motifs/modules are allowed;
- **dashed safe areas** — keep-clear / quiet zones that must stay blank or quiet.

This is where the Screenery cautions are resolved, not deferred: an open
path + sibling polyline is reconciled into one real edge, and an edge socket is
recorded as cutout negative space even though its coordinates run past the body
bounds. If a shape cannot be confidently classified, **stop and name the missing
evidence** — do not guess a role.

Gate: **all geometry roles assigned (no ambiguous roles)**. Feeds
[[build-guide|build-guide]].
