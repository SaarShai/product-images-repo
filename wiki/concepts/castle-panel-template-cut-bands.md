---
schema_version: 2
title: "Castle Panel Template Cut Bands"
type: concept
domain: "experiments"
tier: procedural
confidence: 0.8
trust: user_confirmed
created: "2026-06-15"
updated: "2026-06-15"
verified: "2026-06-15"
sources:
  - tasks/castle-panels/prompts/prompt-v6-narrow-center-safe-gutters.md
  - tasks/castle-panels/prompts/prompt-v7-tall-with-background-wall.md
  - tasks/castle-panels/outputs/reviews/2026-06-15-v6-v7-decision-packet.md
  - tasks/castle-panels/CURRENT.md
  - tasks/castle-panels/final-handoff.md
  - docs/workflow.md
  - scripts/score_template_fit.py
  - scripts/export_composite.py
supersedes: []
superseded-by:
contradicts: []
tags:
  - castle-panels
  - prompting
  - template
  - cut-bands
  - template-fit
  - scoring
  - semantic-review
  - contour
---

# Castle Panel Template Cut Bands

## Summary

Keep two valid center-lane prompt modes rather than forcing one treatment
because the template has two product intents: V6-style empty middle for a truly
blank center, and V7-style quiet center wall for a center that includes only
no-element background.

All production cut paths should be treated as no-focal-element bands. The
center slot/red rectangles and the horizontal top-bottom split may cut through
empty white, plain ivory wall, quiet masonry, soft path, grass, or other inert
background. They should not cut through recognizable motifs.

The repeatable implementation is a fixed-template loop: prompt for composition,
sweep placement with the scorer, export a scored recipe, then do semantic visual
review and contour-hit checks before handoff. This is required because prompt
wording alone did not reliably protect side gutters, center cut bands, bottom
alignment, or custom top contours.

## Evidence

- `tasks/castle-panels/prompts/prompt-v6-narrow-center-safe-gutters.md`: useful
  when the middle should stay empty and when avoiding middle-rectangle crops is
  the top priority.
- `tasks/castle-panels/prompts/prompt-v7-tall-with-background-wall.md`: useful
  when the middle should include a quiet no-elements wall background.
- User feedback on 2026-06-15 confirmed that V7 failed because a bird and
  butterfly were cropped by the middle rectangles.
- User feedback on 2026-06-15 confirmed that both V6 and V7 failed because the
  horizontal top-bottom dividing line cut through a right-side fairy.
- `tasks/castle-panels/CURRENT.md` records the current V9B wall-center PASS
  candidate at score `94.30`, `scale_x=0.70`, `scale_y=1.04`, and `offset_y=0`,
  while still flagging semantic review risk around the horizontal split.
- `tasks/castle-panels/final-handoff.md` records the recreate command and the
  remaining need to build the final exact vector mask/cut contour from the
  authoritative SVG/Illustrator workflow.
- `docs/workflow.md` states that the scorer is a first gate, not a final judge.
- `scripts/score_template_fit.py` implements the measurable rejection/ranking
  gate for side gutters, bottom gap, center lane fill/detail, red zones, and
  cutline detail.
- `scripts/export_composite.py` preserves the selected placement recipe and
  score JSON in export metadata.

## Prevention Rule

1. Treat the center slot and red rectangles as no-focal-element cut bands.
2. Treat the horizontal top-bottom split as the same no-focal-element cut band.
3. Allow only empty white, plain ivory wall, quiet masonry, soft path, grass, or
   other inert background to cross these bands.
4. Keep fairies, birds, butterflies, flowers, faces, windows, doors, lamps,
   flags, roof tips, and decorative symbols away from these bands.

## Template-Fit Loop

1. Start from `tasks/castle-panels/CURRENT.md`; it is the latest state.
2. Pick the intended mode first: empty-center or wall-center. Do not score or
   judge one mode by the other mode's criteria.
3. Generate or select artwork under `tasks/castle-panels/outputs/generated/`.
4. Run `scripts/score_template_fit.py` in the matching mode and sweep
   horizontal scale, vertical scale, and vertical offset before editing prompts
   again.
5. Export the best recipe with `scripts/export_composite.py`, including the
   score JSON so the metadata keeps the source artwork, template, placement, and
   score tied together.
6. Treat `PASS` as a ranking gate only. Review the actual overlay for motifs
   the scorer cannot prove: fairies, birds, butterflies, flower heads, windows,
   doors, lamps, flags, roof tips, and architecture crossing cut bands.
7. If a custom top contour is used, require a contour report with `0` painted
   centerline hits against the placed artwork before production handoff.
8. Update `CURRENT.md`, the relevant review note, and any handoff file with the
   exact command, score, and remaining semantic risk.

## Feedback Harvest Rule

Promote user feedback into production rules when it is positional or geometric:
bottom gap, taller art, side-gutter pressure, center-lane treatment, cropped
motifs, and split-line collisions all become scoring, overlay, or review gates
rather than one-off prompt wording.

## Related

- [[index]]
- [[schema]]

## Open Questions

- None yet.
