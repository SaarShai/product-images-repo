# Image A Local Patch Execution

Date: 2026-06-17

Source brief:

- `tasks/berlin-skyline-live-example/prompts/image-a-svg-locked-local-patch-brief.md`

## Pass 1

Goal: execute the local patch on Image A while preserving watercolor style.

Result: visually close on the requested content fixes, but the model baked faint
panel/contour lines into the artwork. This is not acceptable for artwork-only
handoff because production SVG lines must be overlaid separately.

Lesson: for skyline local patch image generation, explicitly forbid not only
colored dashed guides but also subtle gray panel outlines, contour outlines,
door splits, knobs, and any production marks.

## Pass 2

Goal: stricter artwork-only local patch.

Prompt constraints:

- no panel borders;
- no contour outlines;
- no gray template outlines;
- no dashed guides;
- no door split lines;
- no knobs;
- no production marks;
- preserve Image A composition and style;
- reduce TV tower;
- nudge horses statue clear of red center;
- restore hotel lower/base section;
- align right bridge span more symmetrically to the saloon-door middle;
- keep white removable background.

Status: pending visual verification before treating as a candidate for SVG
overlay check.

User feedback after overlay review: the artwork looks good, but the overlay is
not correct in its dimensions; it appears lower or squished.

Lesson: do not judge the executed artwork from a suspect overlay. First repair
the overlay registration so the SVG keeps its exact aspect and position; then
run the visual/template review.
