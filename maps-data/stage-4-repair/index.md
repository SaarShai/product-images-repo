---
nid: mn7bij
title: "Stage 4 — Repair / Refine"
type: map
kind: process
nodes:
  - diagnose-defect
  - route-engine
  - use-eraser
  - flux-fill
  - donor
  - sharpen
  - mask
  - composite
  - verify
  - edit-py
  - mask-bounded-donor
  - open-problems
edges:
  - {from: diagnose-defect, to: route-engine, label: ""}
  - {from: route-engine, to: use-eraser, label: "remove"}
  - {from: route-engine, to: flux-fill, label: "redraw"}
  - {from: route-engine, to: donor, label: "ghost"}
  - {from: route-engine, to: sharpen, label: "blur"}
  - {from: use-eraser, to: mask, label: ""}
  - {from: flux-fill, to: mask, label: ""}
  - {from: donor, to: mask, label: ""}
  - {from: mask, to: composite, label: ""}
  - {from: sharpen, to: composite, label: ""}
  - {from: composite, to: verify, label: ""}
  - {from: diagnose-defect, to: edit-py, label: "", route: smoothstep}
  - {from: donor, to: mask-bounded-donor, label: "", route: smoothstep}
  - {from: verify, to: open-problems, label: "", route: smoothstep}
---
# Stage 4 — Repair / Refine

Fix one element of a finished image without disturbing the rest, remove ghosts/haze,
harmonize sharpness across a composite, and upscale. This is where the berlin-hotel
family lives (it went 16 reactive repair waves — Stage 4 is the most load-bearing,
least-solved stage). The contract: outside the edit mask, the image stays **byte-exact**.

Flow: [[diagnose-defect|classify the defect]], then [[route-engine|route to the engine]]
that matches the operation. Localized pixel edits (remove via [[use-eraser|Bria eraser]],
redraw via [[flux-fill|Flux Fill]], broad ghost/haze via the [[donor|mask-bounded donor]])
all flow through the [[mask|auto-mask + guardrail]] before a diff-mask
[[composite|composite]]; sharpness fixes ([[sharpen|adaptive sharpen / reupscale]]) skip
masking and composite directly. Everything ends at [[verify|the measured gate]].

The one-command entry point is [[edit-py|scripts/edit.py]] (automask → guardrail → engine →
diff-gate → judge). The donor path is documented in
[[mask-bounded-donor|the mask-bounded external redraw donor concept]]. Note the
[[open-problems|open problems]] — sharpness harmonization, reliable single-element
regen-and-composite, and standalone-plate integration are all STILL open. SOP: the
`element-edit` skill.
