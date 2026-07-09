# Gingerbread panel cutouts are decoration slots

## Summary

For gingerbread-house wall and roof panels, the panel itself is the gingerbread
house. Cutouts are decoration slots only: candy, icing, snowflake, ornament,
gumdrop, peppermint, sugar, or frosting details. Do not put miniature houses,
buildings, windows, doors, or painted text inside the cutouts.

## Evidence

- **Trigger / symptom:** Festive v1 gingerbread-house panel cutouts are being
  filled with miniature houses, buildings, windows, or doors.
- **Trigger / symptom:** A geometry-safe procedural preview is called "styled"
  even though it was not generated from the actual watercolor reference images
  or a visual style packet.
- **Trigger / symptom:** The user points to a specific styled candidate as the
  good direction, but later iterations drift toward sparser or less styled
  variants while still passing mask/geometry checks.
- **Trigger / symptom:** One side or one repeated cutout group is styled, but
  another repeated group such as the left vertical strips remains mostly plain.
- **Rule:** Cutouts must receive candy/icing/ornament decorations only because
  the surrounding panel already represents the gingerbread house wall or roof.
- **Gate:** Before generating or approving cutout candidates, reject any route,
  prompt, or candidate where a cutout contains a house, building, window, door,
  or painted text. Pass only if every cutout is decoration-only.
- **Style gate:** A candidate is not "styled" just because it has watercolor-ish
  colors or passes the alpha mask. For this project, styled means the actual
  reference images or style-packet sheets were attached to image generation, and
  the result reads as coherent watercolor candy/icing artwork rather than local
  procedural placement. Use mask-valid procedural previews only as composition
  maps for attachment-aware redraw/restyle.
- **Approved-candidate gate:** When the user identifies one candidate as the
  good styled direction, lock that candidate family as the visual target because
  repeated generation/compositing can regress style while preserving geometry.
  Final options must be visually compared to that approved candidate, then
  separately checked for exact base/alpha preservation.
- **Every-instance gate:** Inspect every major repeated cutout component before
  presenting final options because global alpha/base checks can pass while a
  mirrored or repeated strip is underdecorated. For festive vertical strips,
  check both left strips and both right strips, not just a representative side.
- **Exemplar:** User correction on 2026-07-08: no houses inside the cutouts.
  Correct route language: peppermint, icing, gumdrop, snowflake, or ornament
  decoration inside a roof/wall cutout. Rejected route language: cottage,
  village, bakery, window, or door inside a cutout.
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

## Related

- [[concepts/no-painted-text-vector-layer-or-omit]]

## Open Questions

- None yet.
