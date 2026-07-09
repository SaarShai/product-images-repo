---
schema_version: 2
title: "Gingerbread panel cutouts are decoration slots"
type: concept
domain: "concepts"
tier: semantic
confidence: 0.5
trust: user_confirmed
created: "2026-07-08"
updated: "2026-07-09"
verified: "2026-07-09"
sources:
  - "user correction, session 7e80d5b005e05ce4, 2026-07-08"
  - "user corrections, Cursor session 5b86a89c chimney bricks + tree cutout, 2026-07-08/09"
  - "user corrections, Codex Explore gingerbread style options AB5 unmasked deliverable, 2026-07-08/09"
supersedes: []
superseded-by:
contradicts: []
tags:
  - gingerbread
  - cutouts
  - image-generation
  - watercolor
  - screenery
  - prompt-gate
  - style-gate
---

# Gingerbread panel cutouts are decoration slots

## Summary

When a product panel already represents the main object, cutouts within that
panel are decoration/detail slots rather than places for miniature scenes of the
same object class. The allowed decoration vocabulary must come from the current
task's style brief and user-approved exemplars; do not hard-code one motif list
as a universal rule.

## Evidence

- **Trigger / symptom:** Product-panel cutouts are filled with miniature scenes,
  repeated versions of the main object class, facades, doors, windows, or text.
- **Trigger / symptom:** A geometry-safe procedural preview is called "styled"
  even though it was not generated from the actual watercolor reference images
  or a visual style packet.
- **Trigger / symptom:** The user points to a specific styled candidate as the
  good direction, but later iterations drift toward sparser or less styled
  variants while still passing mask/geometry checks.
- **Trigger / symptom:** One side or one repeated cutout group is styled, but
  another repeated or mirrored group remains mostly plain.
- **Trigger / symptom:** A specialized cutout type is filled with scene-like
  content instead of the product-approved texture or pattern category.
- **Trigger / symptom:** Cutout graphics look masked/cropped/truncated, or the
  user asks for artwork without the cutout mask — and the agent redesigns the
  motif instead of restoring the geometry-matched unmasked artwork.
- **Rule:** If the panel already represents the main object, cutouts are
  decoration/detail slots only. Do not place miniature scenes of that same object
  class, facades, windows, doors, or text inside the cutouts.
- **Rule:** Allowed decoration vocabulary comes from the current task's style
  brief and user-approved exemplars. Do not promote a product-specific motif list
  into a universal rule.
- **Rule:** Specialized cutout types may use a user-approved texture or pattern
  category for that product. Still reject scene-like content that violates the
  decoration-slot rule.
- **Unmask-first rule:** When cutout art looks masked or cropped, first restore
  the geometry-matched artwork without a tight alpha crop. Do not invent a new
  redesign until unmasking fails the user's ask.
- **Deliverable rule:** Distinguish cutout-fit masked *previews* from unmasked
  transparent *artwork* assets. When the user needs Illustrator-ready pieces,
  deliver the unmasked/uncropped artwork, not only the masked composite.
- **Gate:** Before generating or approving cutout candidates, reject any route,
  prompt, or candidate where a cutout contains a miniature scene of the panel's
  own object class, a facade, a window, a door, or painted text. Pass only if
  every cutout is decoration-only.
- **Style gate:** A candidate is not "styled" just because it has watercolor-ish
  colors or passes the alpha mask. Styled means the actual references or
  style-packet sheets were attached to generation, and the result visually
  matches the approved style rather than merely fitting the mask. Use mask-valid
  procedural previews only as composition maps for reference-attached redraw or
  restyle.
- **Approved-candidate gate:** When the user identifies one candidate as the
  good styled direction, lock that candidate family as the visual target because
  repeated generation/compositing can regress style while preserving geometry.
  Final options must be visually compared to that approved candidate, then
  separately checked for exact base/alpha preservation.
- **Every-instance gate:** Inspect every major repeated cutout component before
  presenting final options because global alpha/base checks can pass while a
  mirrored or repeated component is underdecorated. Check every instance, not
  just a representative sample.
- **Exemplar:** User correction on 2026-07-08: no houses inside the cutouts.
  Correct route language: peppermint, icing, gumdrop, snowflake, or ornament
  decoration inside a roof/wall cutout. Rejected route language: cottage,
  village, bakery, window, or door inside a cutout.
- **Exemplar:** For the festive gingerbread product, the user-approved
  decoration vocabulary included candy, icing, snowflake, ornament, gumdrop,
  peppermint, sugar, and frosting details. This list is historical evidence for
  that task, not a universal motif list.
- **Exemplar:** User correction on 2026-07-08: the `d1`-`d6` local Pillow
  decoration previews were rejected as "not styled" despite fitting the cutout
  mask. Correct route: build the reference style packet, attach the references
  and rough map to OpenAI/Nano image generation, then run exact mask/export
  checks after a visually styled raw redraw exists.
- **Exemplar:** User correction on 2026-07-08: the left
  `v1style-donor-test` option was the good direction, while later options drifted
  less good. Correct route: promote/follow the `v1style-donor-test` family, keep
  its warm gingerbread base and shaded V1-like candy/icing density, and verify
  separately that the production files still report `alpha_equal=true`,
  `outside_alpha=0`, and `changed_protected=0`.
- **Exemplar:** User correction on 2026-07-09: the two left vertical strips were
  still mostly plain after the right strips were decorated. Correct route:
  decorate component 6 (`x33-203,y874-1732`) and component 8
  (`x285-459,y919-1848`) with the same V1-style candy/icing language, then rerun
  the exact alpha/base verifier.
- **Exemplar:** User correction on 2026-07-08/09: top-right chimney cutouts
  needed biscuit-brick texture for the festive product, not dense holly fill;
  `edge-v8-brick-tree` was approved. This was a user-approved texture category
  for those chimney slots only; chimney scenes still remained rejected.
- **Exemplar:** User correction on 2026-07-08/09: tree cutout looked masked/
  cropped; a green-tree redesign was rejected; user asked to bring back the
  original geometry-matched tree unmasked. Correct route: unmask/restore first.
- **Exemplar:** User correction on AB5: options were good but cutout images were
  masked/cropped by outlines; user needed unmasked/uncropped artwork.

## Related

- [[concepts/no-painted-text-vector-layer-or-omit]]
- [[concepts/illustrated-product-upscale-and-background-removal-workflow]]

## Open Questions

- None yet.
