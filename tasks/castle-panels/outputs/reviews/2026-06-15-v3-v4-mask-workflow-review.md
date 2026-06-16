# V3/V4 Mask-First Workflow Review - 2026-06-15

## Prompt V3 - SVG Mask Artwork Only

Result:
- Successfully stopped the model from redrawing the production dieline.
- Created a much clearer center slot corridor than the A/B/C prompt pass.
- Still used a lower-center castle door/path as a focal anchor.
- Overlay showed the SVG slot mostly landed on blank space, but the lower
  keep-clear rectangle and horizontal divide remained risky.

Learning:
- Mask-first is the right workflow direction.
- "Leave blank/pale areas" can produce a faded or erased-looking center, which
  is visually wrong for this product.

## Prompt V4 - Clearance Bands And Side-Weighted Castle

Revision after user feedback:
- Replaced fade/wash language with intentional composition language.
- The protected center is described as a designed courtyard/light-well gap
  between two castle wings.
- Added explicit negative instruction against faded, erased, airbrushed, foggy,
  or pale-wash avoidance.

Result:
- Strong improvement: the center reads as deliberately open, not faded away.
- Central slot overlay lands in a real open gap.
- No centered castle door.
- Side-weighted castle composition feels much closer to the needed production
  logic.

Remaining issues:
- Some flying details still enter the horizontal split area.
- Lower red keep-clear zone crosses path stones; this may be acceptable only if
  path texture is considered non-focal.
- Side foliage/towers are close to the safe-area/crop in places.
- Top skyline may need more deliberate production contour planning, depending
  whether the final contour is derived from the art or kept closer to the SVG
  guide.

## Current Best Prompt

`tasks/castle-panels/prompts/prompt-v4-clearance-bands.md`

## Recommended Next User Check

Ask the user to judge:

- Does V4 feel intentionally designed around the center, or still too empty?
- Is the lower-center path acceptable in the keep-clear zone, or should that
  zone be pure white/open space?
- Are the fairies and birds desirable, or should characters be removed until
  the geometry is solved?
- Should the top contour be driven by two side tower clusters, or should the art
  include stronger broad tower shapes near the center top as well?
- Is V4 worth refining, or should the next prompt return closer to the original
  single dense castle mass while preserving the slot and divide clearance?

## User Feedback After V4

- The intended open-center composition is correct: the illustration should be
  designed around the protected areas, not faded or erased to avoid them.
- V4 does not respect the side safe margins enough; artwork extends too close
  to or beyond the yellow dashed safe-area boundary.
- Next prompt should keep all towers, foliage, flowers, birds, fairies, wings,
  roof tips, and decoration comfortably inside the safe area.
- A useful next test is whether the left and right tower clusters can reconnect
  near the top with a high architectural bridge/parapet above the short upper
  red keep-out rectangle while preserving the blank center corridor below.

## Prompt V5 Direction

`tasks/castle-panels/prompts/prompt-v5-safe-margin-top-bridge.md`

Changes from V4:
- Stronger outer safe-margin language.
- Narrower left/right side clusters.
- High castle skybridge/parapet/terrace reconnecting left and right tower
  groups above the upper keep-out zone.
- Explicitly avoids fade/erasure language and keeps the open center as designed
  architecture.

## User Feedback After V5

- The overlay looks good overall.
- Main remaining issue: side-panel margins are still not respected enough
  relative to the yellow dashed safe-area lines.
- The center gap does not need to be as large as V5 made it.
- Hypothesis: the model protected the center by pushing the castle wings
  outward, which made the side-margin issue worse.
- Next prompt should keep only a narrow center keep-clear lane around the true
  red rectangles/slot and use the recovered space to pull the castle wings
  inward inside the yellow safe-area gutters.

## Prompt V6 Direction

`tasks/castle-panels/prompts/prompt-v6-narrow-center-safe-gutters.md`

Changes from V5:
- Reduces center clearance from a broad white aisle to a narrow engineered
  slot/red-rectangle lane with a small buffer.
- Keeps the top architectural bridge/parapet reconnection.
- Emphasizes white side and bottom gutters outside the yellow safe area.
- Allows castle walls, gardens, and paths to approach the center lane more
  closely without entering it.

## V6 Scaling Check

User insight:
- Instead of forcing the model to solve all safe margins inside the prompt, the
  artwork layer can be scaled relative to the fixed template lines.
- Reducing the artwork layer under the unchanged SVG may solve side margins
  more reliably than another prompt-only generation.

Review previews created:
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-096.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-092.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-090.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-090-y-45.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-092-y-35.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-088.png`

Current read:
- `0.92` improves the side margin but remains crowded in places.
- `0.88` protects the gutters better but starts to make the artwork feel small
  relative to the top contour.
- `0.90` with a slight upward offset looks like the best compromise so far:
  side gutters improve while the top bridge still participates in the skyline.

Follow-up user observation:
- Reduced-size artwork improves side margins, but centered scaling creates too
  much blank space at the bottom.
- The artwork can be moved downward as long as the top bridge stays clear of
  the short upper red keep-out rectangle.

Downward placement checks created:
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-090-y+25.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-090-y+50.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-092-y+25.png`
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-cover-artscale-092-y+50.png`

Current best placement:
- `tasks/castle-panels/outputs/reviews/20260615T132212Z-prompt-v6-overlay-current-best.png`
- Based on `0.90` artwork scale with approximately `+50 px` vertical offset.
- This improves the bottom gap while keeping side gutters acceptable.
- The top bridge remains above the short upper keep-out rectangle.
- `0.92` with downward offset keeps more size but applies more side-margin
  pressure, so it is less safe for production.

Reusable workflow lesson:
- Keep the SVG/template fixed as production truth.
- Generate artwork with the right composition.
- Then scale/position the artwork layer underneath the SVG/safe-area mask during
  review and final compositing.
- Treat outer safe margin compliance as a compositing/layout step when prompt
  wording gets close but remains unreliable.
