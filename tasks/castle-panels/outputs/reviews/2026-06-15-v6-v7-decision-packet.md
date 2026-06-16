# V6/V7 Decision Packet - 2026-06-15

## Review Files

- Decision sheet:
  `tasks/castle-panels/outputs/reviews/20260615T164700Z-v6-v7-decision-sheet.png`
- V6 latest layout recipe:
  `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-scalex090-scaley100-y+50.png`
- V7 same layout recipe:
  `tasks/castle-panels/outputs/reviews/20260615T164700Z-prompt-v7-overlay-cover-scalex090-scaley100-y+50.png`
- V7 source artwork:
  `tasks/castle-panels/outputs/generated/20260615T164700Z-prompt-v7-tall-with-background-wall.png`

## Current Comparison

V6 remains safer for side gutters and overall production breathing room. The
latest non-uniform placement recipe, `scale-x 0.90`, `scale-y 1.00`,
`offset-y +50`, improves its bottom coverage compared with the older uniform
scale export. Its main weakness is still the center lane: too much of the
slot/red-rectangle corridor reads as empty white space.

V7 solves the center-lane problem more convincingly. It fills the slot corridor
with quiet ivory castle-wall texture, and the artwork feels taller and richer.
However, it reintroduces crowding risk: the right-side fairy, side florals,
butterflies/birds, and bottom flowers press closer to the yellow safe-area
logic than V6.

User follow-up clarified that both variants are useful, but for different
center modes:

- V6 is good when the middle should be empty.
- V7 is good when the middle should include "no elements" background, such as a
  quiet wall.
- V6 avoids elements cropped by the middle rectangles.
- V7 crops a bird and butterfly with the middle rectangles.
- Both V6 and V7 let the horizontal top-bottom dividing line cut through a
  right-side fairy.

## Current Recommendation

Do not export V7 as final yet.

Keep both V6 and V7 as valid prompt directions. Use V6 when the desired center
is empty. Use V7 as proof that a quiet wall/background center can work when the
desired center should not be blank.

The next wall-mode prompt should merge V7's center-background idea with V6's
margin and crop discipline:

- keep V7's quiet central wall,
- remove or reduce side fairies/birds/butterflies,
- pull flowers and foliage inward from side/bottom safe margins,
- keep the bottom filled mostly with low, non-focal garden texture,
- avoid large flower heads touching the bottom yellow safe-area line,
- keep birds and butterflies away from the middle rectangles,
- keep fairies, wings, flowers, and other focal motifs away from the horizontal
  top-bottom split.

## User-Confirmed Decision

Proceed with the V7-style center-wall mode for the next single-shot prompt, but
make every production cut path a no-focal-element band. The center slot, red
rectangles, and horizontal panel split may cut through plain wall, path, grass,
or empty background, but not through fairies, birds, butterflies, flower heads,
faces, windows, doors, lamps, flags, roof tips, or decorative symbols.

## Action Taken

- Added `prompt-v9a-empty-center-split-safe.md` for the V6-style empty-middle
  use case.
- Added `prompt-v9b-wall-background-split-safe.md` for the V7-style quiet
  wall/no-elements-background use case.
- Both prompts promote the horizontal top-bottom split to the same hard
  no-focal-element status as the middle rectangles.
- Updated V7 and V8 prompt text to explicitly protect the horizontal
  top-bottom split and side notch areas from fairies, birds, butterflies,
  wings, flowers, windows, lamps, roof tips, and other recognizable motifs.
- Tightened V9B after review: its center wall worked better, but the next pass
  must reduce side/bottom crowding and keep towers, foliage, and flower masses
  inside the template safe margins.

## Reusable Lessons

- Treat the SVG/template as production truth.
- Use prompting for composition and background/focal hierarchy.
- Use overlay placement for exact side gutters and bottom alignment.
- Do not ask the model to solve all geometry with prompt text alone.
- If the center lane must be visible, fill it with non-focal background
  architecture, not blank white and not a fade/erasure.
- Reserve fairies, birds, butterflies, flower heads, windows, doors, lamps, and
  roof tips for zones safely away from the side gutters, split, slot, and red
  keep-clear rectangles.
- Treat the horizontal top-bottom dividing line with the same seriousness as
  the center rectangles: it may cross background texture only.
