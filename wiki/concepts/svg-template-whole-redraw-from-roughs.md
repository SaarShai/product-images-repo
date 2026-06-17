---
schema_version: 2
title: "SVG Template Whole Redraw From Roughs"
type: concept
domain: "product-images"
tier: semantic
confidence: 0.82
trust: user_confirmed
created: "2026-06-16"
updated: "2026-06-16"
verified: "2026-06-16"
sources:
  - tasks/top-temp-workflow-test/checkpoints/style-packet-fit-checkpoint-1-review.md
  - tasks/top-temp-workflow-test/outputs/generated/redraw-from-bc-20260616/experiment-a-whole-panel-redraw.png
  - tasks/top-temp-workflow-test/outputs/generated/redraw-from-bc-20260616/experiment-b-restyle-edit.png
  - tasks/top-temp-workflow-test/outputs/generated/redraw-from-bc-20260616/experiment-c-artdirector-redraw.png
  - tasks/top-temp-workflow-test/agents/imagegen-artdirector/method-c-candidate-01.png
supersedes: []
superseded-by:
contradicts: []
tags:
  - pattern:svg-template-whole-redraw-from-roughs
  - svg-template
  - image-generation
  - screenery
---

# SVG Template Whole Redraw From Roughs

## Summary

When SVG-template roughs prove usable layout/geometry but fail as final art
because they look procedural, collaged, or sprite-assembled, use those roughs as
image-generation composition inputs for a whole-panel redraw/restyle. This works
because the image model can synthesize one coherent watercolor object, while the
exact SVG exporter/checker can remain the downstream geometry gate.

## Evidence

- `tasks/top-temp-workflow-test/checkpoints/style-packet-fit-checkpoint-1-review.md`
  recorded the earlier B-style fitted proof as mechanically clean enough to
  learn from but not acceptable final art.
- `tasks/top-temp-workflow-test/outputs/generated/redraw-from-bc-20260616/`
  contains three direct redraw experiments from B/C roughs. The user described
  the resulting redraws as beautiful and said all were great.
- `tasks/top-temp-workflow-test/agents/imagegen-artdirector/review.md` records
  the remaining production caveat: a raw redraw can be visually strong while
  still drifting against exact SVG cutout coordinates, so exact SVG checks still
  happen after the creative pass.

## Workflow

1. Attach the best rough geometry/layout candidates as composition maps.
2. Attach original style references and the style packet/contact sheets.
3. Prompt for one coherent watercolor redraw, not pasted sprites or crop
   collage.
4. Include the reference edge language: dark blue rim, slight bevel, soft inner
   shadow, pale edge highlight, and occasional subtle rim/lip around contours
   and cutout rims.
5. Run exact SVG export/checks only after a visually promising redraw exists.

## Related

- [[index]]
- [[schema]]
- [[concepts/castle-panel-template-cut-bands]]

## Open Questions

- Whether a future exporter should automate bounded SVG registration/cleanup for
  good raw redraws that drift slightly against exact cutout coordinates.
