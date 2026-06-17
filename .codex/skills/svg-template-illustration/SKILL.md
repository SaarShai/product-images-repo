---
name: svg-template-illustration
description: Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas.
effort: high
---

# SVG Template Illustration

Use this skill for template-constrained image generation and repair work where
the SVG geometry is part of the product spec, not a later crop mask.

## Required Reading

1. Read `AGENTS.md`.
2. Read `docs/svg-template-illustration-workflow.md`.
3. Read `docs/review-judge-checklist.md`.
4. If previous candidates matched geometry but missed style, also read
   `.codex/skills/reference-style-packet/SKILL.md` and
   `.codex/skills/svg-template-style-agent/SKILL.md`.
   For Screenery watercolor control-panel work, also read
   `wiki/concepts/svg-template-whole-redraw-from-roughs.md` and the successful
   2026-06-16 prompt package at
   `tasks/top-temp-workflow-test/prompts/redraw-from-bc-experiments-20260616.md`.
5. If the task is Baci-door or hex-hole repair, also read
   `.codex/skills/baci-template-fit-repair/SKILL.md`.

## First Principles

- The SVG is the geometry source of truth. Screenshots, filenames, and model
  guesses are weaker evidence.
- SVG contours may be split across sibling elements. Before closing an open
  path, inspect nearby `polyline`/`line` segments that may supply the missing
  bottom or side edge. A diagonal auto-close can silently delete valid panel
  area.
- Do not make a generic rectangular illustration and crop, clip, erase, or mask
  it into the contour. Design the composition inside the SVG shape first.
- Treat internal cutouts, red/yellow keep-clear zones, center slots, and shared
  seams as no-decorative-element regions before rendering.
- Treat sockets, bite notches, tabs, and edge-interlocking shapes as carved-out
  negative space in the contour. Their SVG paths may extend beyond the
  paintable body bounds, but the production meaning is cutout, not protrusion.
  Containment by representative point is not enough; check substantial
  intersection with the larger paintable contour and inspect the debug mask
  visually.
- Final clipping is allowed only as an exact-edge export guardrail. It cannot
  rescue a composition whose decorative elements already cross forbidden areas.
- Style fit and geometry fit are separate gates. A metric `PASS` can still fail
  visually, and a style-matched result can still be unusable if it violates the
  contour.
- Do not ask agents to recreate a reference style from memory or prose alone.
  Build a visual style packet and attach its crops/sheets to style-generation
  prompts.
- When a rough candidate has acceptable layout/geometry but looks procedural,
  collaged, or sprite-assembled, use it as an image-generation input for a
  whole-panel redraw/restyle. Do not keep polishing the component-placement
  pipeline. After the redraw looks good, run exact SVG export/checks as the
  downstream geometry gate.
- If the user approves geometry/dimensions/location but asks for style
  adaptation, the approved geometry raster is a composition map and downstream
  gate, not the art source. Route to Whole-Panel Redraw Mode in
  `.codex/skills/svg-template-style-agent/SKILL.md`; do not run local
  locked-geometry restyle scripts or packet-crop compositing as the creative
  pass.
- Any subagent assigned to adapt approved geometry to style must receive the
  style-agent goal from `.codex/skills/svg-template-style-agent/SKILL.md`, not a
  geometry-locking or local repaint goal.

## Standard Workflow

1. Recover state:
   - Run `git status --short`.
   - Identify the task folder under `tasks/<task>/`.
   - Read the task `session-brief.md`, latest review notes, and newest
     `outputs/final/` and `outputs/reviews/` artifacts.
2. Set up the task packet if needed:
   - Use `python3 scripts/scaffold_template_task.py <task> --svg <svg> --refs <refs...>`.
   - Keep source SVGs in `tasks/<task>/source/` and references in
     `tasks/<task>/refs/`.
3. Parse geometry:
   - Run `python3 scripts/svg_geometry_report.py tasks/<task>/source/template.svg --out tasks/<task>/svg-geometry-report.md`
     or the task-specific SVG path.
   - Identify outer contours, holes, slots, dashed safe-area contours, and
     keep-clear zones. If the parser misses polygons, inspect the SVG directly.
   - For Screenery panels with side sockets/notches, inspect the raw SVG for
     open paths plus sibling polylines. Verify the resulting paintable contour
     covers the full bottom/side panel before accepting any mask metric.
4. Plan safe pockets:
   - Name the usable areas where motifs/modules can live.
   - Name every forbidden area that must remain blank or quiet background.
   - Decide what background texture may cross seams and what motifs may not.
5. Draft prompts or procedural layouts from both inputs:
   - Template geometry controls placement.
   - Reference style-packet images control object vocabulary, palette, line
     weight, lighting, simplicity, and rendering language.
6. Build or refresh the style packet when style matters:
   - Run `python3 scripts/build_reference_style_packet.py tasks/<task>`.
   - Inspect `style-packet/reference-contact-sheet.png` and
     `style-packet/style-exemplar-sheet.png`.
   - Use `.codex/skills/svg-template-style-agent/SKILL.md` for independent
     style/image-gen agents that produce element sheets before geometry
     placement.
7. Generate candidates from the original references/templates.
   - Do not keep patching a bad composition if accumulated feedback would make a
     fresh prompt clearer.
   - Patch locally only when the main artwork is good and the failure is bounded
     to a small fixable area.
   - If the best evidence is a pair of roughs, such as a geometry-clean draft
     and a style-closer draft, attach both roughs plus the style references to
     image generation and ask for one coherent redraw. Use the roughs as
     composition maps, not as pixels to collage. Record the prompt under
     `tasks/<task>/prompts/`.
8. Export and score:
   - Save generated images under `tasks/<task>/outputs/generated/`.
   - Produce overlay/debug/metadata artifacts under `outputs/reviews/` or
     `outputs/final/`.
   - Use the task's exact SVG and require zero outside/cutout pixels when the
     exporter supports it.
9. Review with a judge:
   - Use `.codex/skills/svg-template-review-judge/SKILL.md`.
   - The judge must inspect the actual artwork, overlay/debug image, metadata,
     and cutout crops when relevant.
10. Record the decision:
   - Update the task brief, review note, or handoff with commands, paths,
     verdict, remaining risk, and the next reset-vs-patch decision.

## Reset Vs Patch

Restart from the source prompt/references when:

- The composition was designed for a rectangle and only clipped later.
- The style misses the references in object vocabulary or rendering language.
- The prompt relied on remembered/described style instead of visual packet
  images.
- The current result passes geometry but still reads as procedural assembly,
  pasted sprites, or broad crop collage. In that case restart through
  whole-image redraw/restyle with the best roughs as inputs.
- Multiple repair passes are accumulating artifacts.
- User feedback changes the production rule.

Patch locally when:

- The full composition is already good.
- The failure is confined to a bounded area.
- The patch can be verified with exact SVG masks, crop review, and full-frame
  review.
- The raw redraw has the right style and composition but drifts slightly against
  the SVG cutout coordinates; use the exact template only for bounded
  registration/cleanup, not for repainting the whole illustration.

## Done Means

- The task folder records the exact SVG, references, generated candidate, export
  command, metadata, and review artifacts.
- Acceptance review artifacts show one candidate against one SVG geometry. Do
  not group two versions of the same panel in one review image or overlay.
- Geometry checks report no painted pixels outside the allowed contour or inside
  cutouts/keep-clear masks.
- A visual judge has inspected the actual images, not only JSON metrics.
- The result matches the style references in object vocabulary, palette,
  lighting, shape language, and density.
- Style-sensitive work records a visual style packet and an elements-first
  style-agent handoff when appropriate, or a whole-redraw prompt when rough
  geometry/style candidates were used as image inputs.
- The final report states whether the next step is accept, local patch, or
  prompt/source restart.

## Anti-Patterns

- Treating a clipped rectangular image as a valid contour-designed result.
- Calling a result done because metadata says `PASS`.
- Auto-closing open SVG paths without checking whether a sibling polyline
  completes the intended contour.
- Classifying carved-out socket/notch paths as paintable merely because their
  SVG coordinates are not fully contained inside the main panel bounds.
- Fixing style with palette shifts when the visual vocabulary is wrong.
- Asking style agents to infer the look from adjectives while reference images
  sit unused.
- Continuing procedural component placement after the user has accepted rough
  composition but rejected the assembled look.
- Treating an approved geometry image as pixels to repaint, texture, or collage
  locally after the user asks for style adaptation.
- Grouping two versions of the same panel in one acceptance review image, which
  makes contour drift and scale errors harder to diagnose.
- Asking the model to draw final holes or production cutouts.
- Continuing a repair loop without explicitly deciding why patch beats restart.
