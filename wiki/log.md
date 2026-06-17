# Wiki Log

- 2026-06-15: Added [[concepts/castle-panel-template-cut-bands]] after
  user-confirmed V6/V7 feedback. The durable rule is that center rectangles and
  the horizontal split may cut only inert background, not fairies, birds,
  butterflies, flowers, windows, or other recognizable motifs.

## [2026-06-15] update | Castle Panel Template Cut Bands

Created `concepts/castle-panel-template-cut-bands.md` from `page` template.

## [2026-06-15] update | Castle Panel Template Fit Loop

Expanded [[concepts/castle-panel-template-cut-bands]] from the V6/V7
cut-band rule into the reusable fixed-template loop: choose empty/wall mode,
score placement sweeps, export scored metadata, then require semantic visual
review and `0` painted centerline hits for custom contours before handoff.

## [2026-06-16] update | SVG Template Whole Redraw From Roughs

Created `concepts/svg-template-whole-redraw-from-roughs.md` from `page` template.

## [2026-06-16] retro | SVG Template Whole Redraw From Roughs

Added [[concepts/svg-template-whole-redraw-from-roughs]] and updated the
SVG-template skills/workflow after top-temp B/C redraws succeeded. Pattern:
pattern:svg-template-whole-redraw-from-roughs. Lesson: when roughs prove layout
but final art looks assembled, feed roughs plus style references to image
generation for a whole redraw, then apply exact SVG checks afterward.

## [2026-06-17] retro | Skyline Local Patch Semantics

Updated `.codex/skills/skyline-template-illustration/SKILL.md` and
`docs/skyline-template-illustration-workflow.md` after Berlin Image A local
patch feedback. Pattern: pattern:skyline-local-patch-semantics. Lesson:
distinguish quiet red-center filler from recognizable features, allow only
controlled top-contour overflow, preserve landmark bases, and check
bridge-to-saloon-door symmetry before the next edit.

## [2026-06-17] retro | Screenery Socket And Polyline SVG Geometry

Added [[concepts/screenery-socket-polyline-svg-geometry]], updated the
SVG-template skill/workflow/review checklist, and added a validator regression
after `np01-back-bottom.svg` exposed two geometry failures. Pattern:
pattern:screenery-socket-polyline-svg-geometry. Lesson: edge sockets/notches are
carved-out cutouts even when their SVG coordinates extend past the paintable
body edge, and open panel paths may require sibling polylines before closure;
future agents must verify both mechanically and visually.

## [2026-06-17] retro | SVG Template Geometry-Approved Style Redraw

Updated `.codex/skills/svg-template-style-agent/SKILL.md`,
`.codex/skills/svg-template-illustration/SKILL.md`,
`docs/svg-template-illustration-workflow.md`, `docs/review-judge-checklist.md`,
`AGENTS.md`, and `tasks/space-svg-exports-batch/` after the approved
`np01-back-top` geometry drifted into locked-geometry local restyle attempts.
Pattern: pattern:svg-template-geometry-approved-style-redraw. Lesson: when the
user approves geometry/dimensions/location but rejects style, use the approved
geometry only as a composition map for attachment-aware whole-panel redraw, then
run exact SVG export/checks downstream.

## [2026-06-17] retro | SVG Geometry Style Orchestration Skill

Added `.codex/skills/svg-geometry-style-illustration/SKILL.md` and drift probes
to make the full SVG geometry -> style-packet -> attachment-aware redraw ->
exact SVG check -> visual judge route explicit. Pattern:
pattern:svg-geometry-style-orchestration. Lesson: future agents should start
with the orchestration skill for end-to-end SVG template plus reference-style
tasks, then delegate geometry, style packet, image generation, and review to
separate skill roles.
