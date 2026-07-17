---
schema_version: 2
title: "Prompt+outset-guide geometry adherence fails on cutout-heavy panels — enforcement must be mechanical"
type: fact
domain: "image-generation"
tier: tactical
confidence: 0.9
trust: verified
scope: this-repo
created: "2026-07-17"
updated: "2026-07-17"
verified: "2026-07-17"
sources:
  - tasks/geometry-evidentiary-princess-n02/VERDICT.md
  - tasks/geometry-evidentiary-princess-n02/DIAGNOSIS-attempt2.md
  - tasks/geometry-evidentiary-princess-n02/experiments-outset/outset-c1/metrics-original-svg.json
supersedes: []
superseded-by: []
contradicts: []
tags:
  - geometry
  - svg-template
  - evidentiary-run
  - cutouts
  - gates
---

# Prompt+outset-guide geometry adherence fails on cutout-heavy panels — enforcement must be mechanical

## Summary

On the held-out princess narrow-02 panel, the released svg-geometry-style
pipeline (outset guide + prompt-side keep-clear instruction) produced mean_iou
0.120 with cutouts painted 71.5/98.5/97.5% on both candidates (systematic, not
noise). Geometry compliance must be enforced mechanically — region-map guide,
aperture-lock/punch, composite-back — never expected from prompt language.

## Evidence

Frozen evidentiary run `tasks/geometry-evidentiary-princess-n02/` (contract
frozen at 7a2d4ea, closed 2026-07-17). User verdict: NEGATIVE, 4 circled
defects — overlay red-line error (tooling), bird over panel border, window in
slot keep-clear zone, spires truncated at top contour. Style passed; geometry
failed on every measured criterion.

Two secondary facts from the same run:

1. `export_svg_template_fit.py --require-pass` was a STRUCTURAL false-positive
   gate on templates with `<rect>` cutouts / cutout paths (reported 0
   violations where svg_geometry_check measured 71-98%). Fixed at 40cbd70;
   any historical PASS from it on such templates is not trustworthy evidence.
2. OPEN gap (finding C): the workflow has no composite-embedded-raster-back
   step, so fixed-element sockets (e.g. an embedded door raster) are
   unavoidably "violated" by any generation. Any future contract on a
   fixed-element panel must add socket masking + composite-after before
   "0 cutout violations" is achievable.

## Trigger/symptom

Generating art for an SVG template with internal cutouts/slots and relying on
an outset guide plus prompt instructions to keep them clean; or citing an old
export_svg_template_fit PASS as geometry evidence.

## Related

[[regate-failed-artifacts-after-gate-patch]] · skills/evidentiary-run/SKILL.md
· skills/region-map-guide · gate-per-visible-defect-class (memory)
