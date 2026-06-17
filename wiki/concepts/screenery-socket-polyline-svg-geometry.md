# Screenery Socket And Polyline SVG Geometry

Pattern: `screenery-socket-polyline-svg-geometry`

## Lesson

Screenery SVG exports can represent one production contour with multiple SVG
elements. A paintable panel may be an open `<path>` completed by a sibling
`<polyline>`, and an edge socket/notch is carved-out negative space in the
contour even when its SVG coordinates extend outside the paintable body bounds.

## Failure

In `np01-back-bottom.svg`, the right panel path ended near the socket/notch
area while a separate polyline supplied the bottom/right closing edge. Ignoring
that polyline caused an artificial diagonal close, which removed the legitimate
lower-right panel area. The right-side socket/notch path also extended past the
paintable body edge, so a representative-point containment test misclassified it
as paintable.

## Rule

- Before closing an open SVG path, inspect sibling `polyline` or `line`
  elements that may complete the intended bottom or side edge.
- Treat sockets, bite notches, tabs, and interlocking shapes as carved-out
  cutouts even when their SVG coordinates extend outside the larger paintable
  body bounds.
- Do not rely only on representative-point containment for cutout detection;
  also check substantial intersection with a larger paintable contour.
- Judge the actual artwork and debug mask. A metric pass is not enough when a
  contour looks underfilled or a socket/notch is filled blue.

## Mechanical Gate

`scripts/validate_svg_template_workflow.py` includes a regression check for
`tasks/space-svg-exports-batch/source/np01-back-bottom.svg`:

- path `0` must classify as `cutout`;
- path `3` must classify as `paintable`;
- path `3` must keep the full lower-right panel area and bottom bound.
