# Top Temp Checkpoint 2 Approach Plan

Date: 2026-06-16

## User Feedback Promoted Into This Checkpoint

- The top-temp geometry may be too complicated for an early workflow test.
- In checkpoint 1, the strict-pocket top-left result was the only acceptable
  geometry result.
- That strict-pocket result still failed on style. Geometry success and style
  success must stay separate.

## Parallel Tests

1. `strict-style-polish`
   - Keep the strict-pocket geometry behavior.
   - Improve watercolor/control-panel style from the references.
   - Decide whether the good geometry candidate can be locally improved or
     whether style requires a fresh reference-first restart.

2. `micro-pocket-style`
   - Reduce the geometry load to one simple safe pocket.
   - Test whether style vocabulary improves when the model is not asked to solve
     the whole contour at once.
   - This is a style proof, not a complete production candidate.

3. `component-library`
   - Separate style from placement.
   - Build reusable reference-style controls first, then place them into safe
     pockets only if their bounds fit.
   - Test whether component-first composition makes geometry more reliable.

4. `simple-full-panel`
   - Keep the full template, but use fewer and larger motifs.
   - Test whether sparse composition avoids the dense procedural look and
     reduces collisions with cutouts.

## Checkpoint 2 Acceptance Read

For each result, judge these separately:

- geometry: outside contour and path[1]/path[2] cutout cleanliness;
- method: whether motifs were planned inside safe pockets before final masking;
- style: watercolor texture, uneven dark-blue outline, raised rounded hardware,
  soft highlights, simple friendly control-panel vocabulary;
- next move: accept, local patch, prompt restart, or abandon approach.
