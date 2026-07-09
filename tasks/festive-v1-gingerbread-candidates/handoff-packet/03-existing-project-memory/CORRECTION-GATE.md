# Correction gate

User correction, 2026-07-08:

The panels represent the gingerbread house walls and roof. The cutouts should not contain miniature houses, windows, doors, bakery facades, villages, or building/chimney scenes. Cutout artwork should be candy/icing/gingerbread decorations only.

Gate:
- Reject if a candidate contains house/building/window/door/facade motifs inside the cutouts.
- Reject if the title/prompt route encourages house/village/bakery contents inside the cutouts.
- Accept for feedback only if cutout contents are contour-following decorations such as icing scallops, piped ropes, gumdrop beads, peppermint ribbons, candy buttons, sugar crystals, frosted stars, holly/berry sprigs, wafer strips, cocoa swirls, or similar candy decor.

Exemplar:
- Wrong: `v1-cocoa-glaze-village`, `v2-holly-berry-bakery`, and related variants that put little buildings/windows inside cutouts.
- Correct: decoration-only variants named `d1-*` through `d6-*`.

Styled-candidate gate, added after user correction:
- Reject if a candidate is called "styled" only because it fits the cutout mask
  or uses watercolor-like colors.
- Reject if the candidate was produced only by local/procedural rendering
  without the actual reference images or style-packet sheets attached to image
  generation.
- Accept as styled for feedback only if method provenance shows reference-
  attached OpenAI/Nano generation or equivalent, visual inspection shows
  coherent watercolor object vocabulary from the references, and exact mask
  containment is checked afterward.

Styled exemplar:
- Wrong: `d1-*` through `d6-*` local Pillow previews as final "styled" images;
  they are geometry/composition maps only.
- Correct: `styled-v1-*` through `styled-v3-*` reference-attached OpenAI redraws,
  then exact-masked to the cutouts.
