# Top-temp redraw from B/C experiments - 2026-06-16

## Problem

The prior B/C checkpoint candidates are not acceptable final art. They are
useful only as rough input references:

- B: better isolated watercolor control vocabulary and clean geometry.
- C: better use of real reference pixels and fuller arrangement, but visible
  crop/matte artifacts.

The next image-generation step should use B and C as input images and redraw the
panel into one coherent illustration. Do not procedurally place separate
sprites and call that the final.

## Shared Constraints

- Preserve the irregular blue top-temp panel silhouette from B/C.
- Preserve the large diagonal rounded slot, the lower center rectangular cutout,
  and the lower-right round cutout as clean blank negative space.
- Keep all controls/details visibly inside safe material areas, not crossing
  cutouts or outside edges.
- Use the two reference images as the style target: soft watercolor washes,
  hand-painted blue body, dark blue ink outlines, rounded glossy red/yellow/teal
  controls, soft highlights, soft shadows, imperfect paper texture.
- Add detail in the style family: small sliders, dials, bolts, capsule buttons,
  small tick marks, indicator lights, and subtle panel edge highlights.
- Avoid flat vector UI art, photoreal metal, source-crop rectangles, collage
  seams, hard masks through objects, and clutter.

## Experiment A - Whole-panel redraw

Use B and C only as composition/geometry references. Redraw the whole thing as a
single cohesive watercolor object in the style of the two reference panels.
Keep the cutouts as blank white holes. Add more small reference-style controls
and subtle panel details while preserving open blue material around the diagonal
slot.

## Experiment B - Restyle/edit rough input

Start from B as the primary layout and C as secondary style evidence. Preserve
the silhouette and negative-space holes, but repaint the surface and all
controls so they belong to one watercolor panel. Harmonize lighting, remove
sprite seams/halos, shrink/calm oversized controls, and add a few small
reference-style details.

## Experiment C - Art-director reinterpretation

Use B/C as a loose map, not as a source to copy. Imagine this is one product
plate from the same family as the reference blue control panels. Produce a
cleaner, more designed composition: clusters of capsule buttons and slider
rails in safe pockets, small bolts near corners, dial/indicator details away
from cutouts, and a coherent watercolor blue body with hand-painted edge
treatment.

## Review Criteria

- Looks like one generated watercolor panel, not a collage or procedural layout.
- Style resembles the actual reference images beyond palette.
- Cutouts remain visually clean and blank.
- No obvious decorative object is sliced by an edge or cutout.
- The result is worth running through the SVG mask/export verifier.
