<!--
TEMPLATE-spatial-anchor.md — reusable image-gen prompt template.

PURPOSE: stop giant-tower-runoff / zoom-crop. Models that paint a single dominant
subject (a tower, a spire, a rocket, one big control opening) tend to ENLARGE it
until it overflows the frame, get cropped at the top, or "zoom in" so the panel
no longer fits its SVG contour. The fix is SPATIAL-GRID ANCHORING: pin WHAT goes
WHERE on an explicit grid (quadrants / bands), and demand small breathing gaps at
the frame edges so nothing runs off. This is a layout contract, not a suggestion.

HOW TO USE
1. Copy this file into your task's prompts/ dir (do NOT edit this template in place).
2. Replace every {PLACEHOLDER}. Delete any grid cell you don't need; keep at least
   the top band (where runoff happens) and the edge-margin rule.
3. Feed the SVG-geometry guide as image 1 and the STYLE references as the other
   images (per the repo's reference-beats-description rule — drive with images,
   never prose alone). The grid words below COMPLEMENT the geometry guide; they do
   not replace it.
4. Pair with `scripts/judge_tiles.py` for review; for TALL panels use
   `--provider openai` (nano is square-biased and recomposes tall panels — subgen
   now warns on this).

PLACEHOLDER KEY
  {SUBJECT}            one finished thing, e.g. "watercolor space control panel", "city skyline"
  {STYLE_LOOK}         palette/brightness/brushwork in one or two lines (copied from the refs)
  {ASPECT_DESCRIPTION} e.g. "TALL, NARROW vertical strip, height ~3.4x width"
  {TOP_*} {MIDDLE_*} {BOTTOM_*} {*_LEFT} {*_RIGHT}  what occupies each grid cell
  {RUN_THROUGH}        element(s) that cross band boundaries continuously (or "none")
  {KEEP_CLEAR}         openings / cutouts / fold lines to leave empty (from the SVG)
  {EDGE_GAP}           how much empty margin at each frame edge, e.g. "a small sky gap (~5% of height)"
-->

Produce ONE finished {SUBJECT} illustration. Single image, single version, clean
white background, no text/labels/arrows/watermark.

CANVAS & FRAMING (critical): the composition is a {ASPECT_DESCRIPTION}. Image 1 is
the EXACT layout/geometry contract — keep every silhouette edge, opening, and
keep-clear zone at its IDENTICAL relative position, size, and shape. Do NOT enlarge
the subject to fill the frame, do NOT crop any edge, do NOT zoom in, do NOT change
the proportions.

SPATIAL GRID — treat as law, not suggestion. Place content by GRID CELL so no
single element grows until it runs off or gets cropped. Think of the frame as a
3-band x 2-column grid and fill it as follows:

- TOP band (top third):
    - left  ({TOP_LEFT}): {TOP_LEFT}
    - right ({TOP_RIGHT}): {TOP_RIGHT}
    - COMPLETE every tall element (spires, towers, antennae, peaks) WITHIN this
      band and leave {EDGE_GAP} of empty space ABOVE the tallest tip. Tips must be
      fully visible — nothing touches or exceeds the top frame edge. No element may
      run off the top.
- MIDDLE band (middle third):
    - left  ({MIDDLE_LEFT}): {MIDDLE_LEFT}
    - right ({MIDDLE_RIGHT}): {MIDDLE_RIGHT}
- BOTTOM band (bottom third):
    - left  ({BOTTOM_LEFT}): {BOTTOM_LEFT}
    - right ({BOTTOM_RIGHT}): {BOTTOM_RIGHT}
    - the base/ground sits inside this band; leave {EDGE_GAP} of empty space BELOW
      it so the bottom edge is not crowded or cropped.

RUN-THROUGH (elements that legitimately cross bands): {RUN_THROUGH}. Draw these
continuously across the cells named above, but they must still respect every frame
edge and every keep-clear zone — no overflow, no crop.

EDGE MARGINS (anti-runoff, applies to ALL four sides): keep {EDGE_GAP} of empty
breathing space inside EACH frame edge — top, bottom, left, right. The subject is
contained WITHIN these margins; nothing bleeds off, touches, or is clipped by any
edge. If an element would otherwise overflow, make it SMALLER — never crop it and
never push it past the margin.

KEEP-CLEAR (from image 1): leave these empty / unpainted — {KEEP_CLEAR}. Do not
draw over, fill, close, move, resize, or reshape any opening, cutout, or fold line.

STYLE — the OTHER attached image(s) are the STYLE REFERENCE and the single source
of truth for the look. Match them precisely: {STYLE_LOOK}. Copy their palette,
brightness, and brushwork exactly; ignore their LAYOUT (layout comes only from
image 1 and the grid above). Do NOT invent a darker, muddier, or different palette.

DO NOT: enlarge the subject to fill the frame; let any element run off, bleed past,
or get cropped at any edge; zoom/crop in; move, resize, rotate, reshape, merge,
add, remove, fill, close, or round any opening; add text, labels, arrows, grid
lines, or watermark. One single finished image, white background, one version only.
