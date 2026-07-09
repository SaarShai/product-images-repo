# Methods And Failures

## What Failed

### Text/Concept-Only Exploration Was Not Enough

The session began with useful concept lanes, but concept descriptions and boards did not satisfy the later requirement for actual styled generated images.

Failure mode: the agent treated style establishment as palette/motif prose plus layout planning, while the user needed visible image evidence.

### Houses Inside Cutouts Were The Wrong Semantics

Early options placed or implied gingerbread-house architecture inside the cutouts: facades, doors, windows, roof bands, villages, or house details.

Failure mode: the agent interpreted cutouts as miniature canvases for scenes. The user clarified that the panels already are the gingerbread house walls/roof; the cutouts should contain decoration/candy only.

### Procedural Geometry-Safe Candidates Were Not Styled

The rejected candidates appear to have emphasized containment, alpha/background checks, and mechanical boards. The user rejected them as not styled.

Failure mode: mechanical verification checked outside-alpha, filenames, board existence, or geometry, but did not prove reference-style fidelity.

### Palette/Local Compositing Cannot Substitute For Style

The project lesson in the thread is that style lives in object vocabulary, edge language, shape simplicity, watercolor texture, and source-image provenance. Palette shifts, procedural masks, and local compositing can preserve geometry but cannot create the known project style on their own.

### Style Drift After A Good Option

The user later approved the left option in a comparison and said subsequent options drifted worse.

Failure mode: once a good visual anchor exists, later attempts should preserve that anchor's visual grammar rather than restarting broad exploration.

### Masked/Cropped AB5 Outputs Were Wrong For The Requested Deliverable

For AB5, the user liked two options but said the cutout images were masked/cropped by outlines; they needed unmasked/uncropped versions.

Failure mode: confusing fit-preview composites with source artwork assets.

## What Worked Or Became The Correct Route

### Decoration-Only Slots

Correct semantic model: cutouts are decoration slots in gingerbread wall/roof panels. Contents should be candies, icing, ribbons, holly, gumdrops, peppermint, sugar details, and similar elements that complement each contour.

### Reference-First Styled Generation

Correct style route: use actual reference images and style packets as image inputs. The child route advisor recommended `python3 scripts/subgen.py --provider openai` as the repo wrapper, with edge-v4 first as locked base/composition map and Styled V1/style-packet sheets as motif/style references.

### Edge-V4 As Canonical Base

The user explicitly approved `edge-v4-watercolor-piped-artwork.png` for background, edges, style, and geometry. Later work should preserve this base/background and add interior decorations.

### Styled V1 Peppermint As Foreground Motif Reference

The user explicitly named `Styled V1 - Peppermint Icing Ribbons` as the style reference for the items/details placed on top of the edge-v4 background.

### Separate Geometry Gate From Style Gate

Geometry checks are rejection gates only: they can prove containment, alpha, dimensions, and background preservation, but they do not approve production style.

A proper gate needs both: deterministic geometry/background checks and a visual style review against the reference images.

### Use The Approved Left Option As Anchor

Once the user said the left option looked great, the next iterations should use it as the immediate reference/composition anchor and avoid broad style exploration.

### Live Illustrator Geometry For AB5

For artboard 5, stale or guessed geometry led to corrections. The user eventually said the desired bottom-right shape was now present, implying live open-file shape export/checking was required before rendering.

## Practical Handoff Rules

- Do not implement these learnings in this digest task.
- For future generation, attach images; do not rely on prose-only style summaries.
- Treat `edge-v4-watercolor-piped-artwork.png` as the base/composition map for the peppermint overlay lane.
- Treat `Styled V1 - Peppermint Icing Ribbons` and the style packet as foreground item style/motif references.
- Keep review boards separate from source artwork outputs.
- Report geometry verification and style review as separate evidence.
