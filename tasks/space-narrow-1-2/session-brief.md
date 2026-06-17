# Space Narrow 1+2 Illustration Proof

## Source

- Template SVG: `source/narrow-1-plus-2.svg`
- Style references: `refs/*.png`

## Goal

Create one illustration for each of the four yellow-dashed template areas. Work
one area at a time, starting with the top-left region, so the style and cutout
treatment can be reviewed before the remaining three areas are produced.

## Style Direction

Use the attached control-panel references as the visual language: blue
watercolor panel surfaces, soft rounded mechanical forms, navy outlines, pale
highlights, and small coral, yellow, and teal controls.

## Geometry Rule

The SVG is authoritative. Internal dashed yellow or red cutout/clearance zones
should contain no decorative elements.

Do not use the rejected cropping method: do not make a generic rectangular
illustration and crop/mask/erase it into the outline. The composition must be
designed from the contour first, with modules and pipes placed into safe pockets
that avoid the internal cutouts before final rendering.

Final masks are allowed only as verification/export guardrails for exact SVG
edges. They are not a substitute for contour-first composition.

## First Proof

- Area: top-left yellow-dashed region
- Artwork: `outputs/generated/area-01-top-left-artwork.png`
- Overlay review: `outputs/reviews/area-01-top-left-template-overlay.png`
- Metrics: `outputs/reviews/area-01-top-left-metadata.json`

This proof is rejected as a method because it is effectively a clipped/cropped
artwork. Keep it only as evidence for what not to repeat.

## Current Alternate Method

- Script: `scripts/create_area01_svg_native_proof.py`
- Method: SVG-native pocket-planned component layout
- Artwork: `outputs/generated/area-01-top-left-svg-native-v1-artwork.png`
- Overlay review: `outputs/reviews/area-01-top-left-svg-native-v1-template-overlay.png`
- Metrics: `outputs/reviews/area-01-top-left-svg-native-v1-metadata.json`

This method fills the SVG contour as the panel substrate, then renders each
decorative component only after its mask fits inside the computed paintable
region. The metric gate checks both final nonwhite pixels and raw decorative
component masks against the cutouts.

## Reference Style Pass

- Script: `scripts/create_area01_reference_style_proof.py`
- Method: SVG-native pocket-planned layout plus reference watercolor palette
- Artwork: `outputs/generated/area-01-top-left-reference-style-v2-artwork.png`
- Overlay review: `outputs/reviews/area-01-top-left-reference-style-v2-template-overlay.png`
- Metrics: `outputs/reviews/area-01-top-left-reference-style-v2-metadata.json`

This pass keeps the non-cropping geometry method, then restyles the sketch
toward the uploaded control-panel references: lighter watercolor blues, soft
navy outlines, glossy white highlights, and coral/yellow/mint accent controls.

This style pass is rejected as a visual method. It preserved too much of the
dark procedural machinery sketch. The successful part was the SVG-native
template fit; the failed part was assuming palette and highlight changes could
turn the wrong visual vocabulary into the reference style.

## Reference-First Restart

- Script: `scripts/create_area01_reference_restart_proof.py`
- Method: SVG-native geometry plus fresh reference-first composition
- Artwork: `outputs/generated/area-01-top-left-reference-restart-v1-artwork.png`
- Overlay review: `outputs/reviews/area-01-top-left-reference-restart-v1-template-overlay.png`
- Metrics: `outputs/reviews/area-01-top-left-reference-restart-v1-metadata.json`

This restart drops the dark machinery bay and dense pipe vocabulary. It uses
simpler rounded watercolor control-panel forms, sparse sliders, a soft
planet/dial, glossy blue rim highlights, and coral/yellow/teal controls based on
the uploaded references.

This restart still remained too procedural: it borrowed the reference palette
and object categories, but did not fully reproduce the references' soft
watercolor rendering language.

## Reference Watercolor Fix

- Script: `scripts/create_area01_reference_watercolor_v2.py`
- Method: SVG-native geometry plus watercolor-first rendering
- Artwork: `outputs/generated/area-01-top-left-reference-watercolor-v2-artwork.png`
- Overlay review: `outputs/reviews/area-01-top-left-reference-watercolor-v2-template-overlay.png`
- Metrics: `outputs/reviews/area-01-top-left-reference-watercolor-v2-metadata.json`

This fix keeps the successful contour-first geometry but changes the visual
construction method: soft blue washes, blurred texture sampled from the actual
control-panel references, more organic navy edge pooling, fewer larger rounded
controls, and painted highlights. This is the current candidate to review
against the uploaded references.
