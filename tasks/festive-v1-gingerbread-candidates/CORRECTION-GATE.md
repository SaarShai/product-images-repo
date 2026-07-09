# Correction gate

User corrections, 2026-07-08/09.

## General gates

- Reject if a panel already represents the main object and its cutouts contain miniature scenes of that same object class, facades, windows, doors, or text. Cutouts are decoration/detail slots, not scene slots.
- Reject if a route or prompt encourages scene-like contents inside decoration cutouts. Allowed decoration vocabulary must come from the current task's style brief and user-approved exemplars.
- Reject if a candidate is called "styled" only because it fits the cutout mask or uses watercolor-like colors. Styled provenance requires reference-attached generation or equivalent style-packet evidence, followed by visual style inspection and exact containment checks.
- When cutout art looks masked or cropped, restore the geometry-matched artwork without a tight alpha crop before redesigning the motif.
- Distinguish masked cutout-fit previews from unmasked transparent artwork. When the user needs Illustrator-ready pieces, deliver unmasked/uncropped artwork, not only masked composites.

## This product (festive gingerbread) notes

- The panels represent gingerbread house walls and roof, so cutouts should not contain miniature houses, windows, doors, bakery facades, villages, or building/chimney scenes.
- For this task's feedback vocabulary, candy/icing/gingerbread decorations were acceptable: icing scallops, piped ropes, gumdrop beads, peppermint ribbons, candy buttons, sugar crystals, frosted stars, holly/berry sprigs, wafer strips, cocoa swirls, or similar candy decor. This is a task-local accept list, not a universal motif list.
- For chimney cutouts in this product, the user approved biscuit-brick texture as a decoration category (`edge-v8-brick-tree` exemplar). Still reject chimney scenes or building vignettes inside cutouts.
- Wrong exemplar: `v1-cocoa-glaze-village`, `v2-holly-berry-bakery`, and related variants that put little buildings/windows inside cutouts.
- Geometry/composition map exemplar: `d1-*` through `d6-*` local Pillow previews. They were useful for fit but rejected as final "styled" images.
- Styled-route exemplar: `styled-v1-*` through `styled-v3-*` reference-attached OpenAI redraws, then exact-masked to the cutouts.
