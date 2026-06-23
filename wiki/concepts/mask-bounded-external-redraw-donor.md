---
schema_version: 2
title: "Mask-Bounded External Redraw Donor"
type: concept
domain: "product-images"
tier: semantic
confidence: 0.86
trust: user_confirmed
created: "2026-06-23"
updated: "2026-06-23"
verified: "2026-06-23"
sources:
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_feedback_board.png
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_shortlist_verification.txt
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/method_notes.md
supersedes: []
superseded-by:
contradicts: []
tags:
  - image-generation
  - localized-repair
  - openai
  - bounded-composite
  - task-retrospective
---

# Mask-Bounded External Redraw Donor

## Summary

For localized defects in a finished watercolor illustration, generate a broader
external redraw as a donor, then composite only the user-marked issue regions
back onto the banked baseline through a feathered mask. Use this when
conservative local cloning/inpainting removes pixels but leaves synthetic
smears, or when the defect is a broad ghost/haze artifact that benefits from
model resynthesis.

This works because the image model can rebuild coherent local content across the
whole defect, while the final candidate remains mechanically bounded by the mask
so that unrelated artwork stays byte-identical.

## Evidence

- User feedback on the wave3 feedback board: the bottom-right `S09 OpenAI
  redraw` candidate was "near perfect".
- Accepted candidate:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png`.
- External probe notes:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/method_notes.md`.
- Verification:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_shortlist_verification.txt`
  reports `outside_allowed_changed=0` and `hotel_base_changed=0` for `S09`.

## Procedure

1. Bank the current best full-resolution image first and never overwrite it.
2. Draw explicit issue masks from the user's marks or from measured full-res
   boxes.
3. Generate an external edit with OpenAI through
   `scripts/subgen.py --provider openai`, attaching the banked image and the
   mask.
4. Treat the external raw output as a donor only. It may return at a smaller
   size or repaint too much.
5. Resize/register the raw output back to baseline dimensions if needed.
6. Composite donor pixels back onto the banked baseline through the issue mask
   with a feathered edge.
7. Verify changed pixels against the banked baseline, including a negative gate
   for protected regions that must remain unchanged.
8. Build a feedback board that includes conservative local repairs and the
   bounded external redraw, because the best visual result may be the broader
   donor even when it edits more pixels inside the allowed mask.

## Failure Lessons

- Conservative local clone/inpaint variants were mechanically clean but could
  look blocky or smeared in watercolor haze; they are useful as safe baselines,
  not always the best final.
- Nano Banana produced a passing but visually broken bounded candidate in this
  lane due to square/raw-output seams and distorted tower structure.
- Photoshop connector was not reliable here because the tool returned HTTP 403.
- Direct image-generation outputs must not be accepted as final merely because
  they look good; the bounded composite and pixel verifier are the reliability
  layer.

## Related

- [[concepts/svg-template-whole-redraw-from-roughs]]
- [[concepts/castle-panel-template-cut-bands]]
- [[index]]

## Open Questions

- Whether a future helper should automate mask-bounded donor compositing and
  verification for `scripts/subgen.py` edit outputs.
