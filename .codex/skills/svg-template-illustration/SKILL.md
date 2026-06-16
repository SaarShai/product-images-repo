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
4. If the task is Baci-door or hex-hole repair, also read
   `.codex/skills/baci-template-fit-repair/SKILL.md`.

## First Principles

- The SVG is the geometry source of truth. Screenshots, filenames, and model
  guesses are weaker evidence.
- Do not make a generic rectangular illustration and crop, clip, erase, or mask
  it into the contour. Design the composition inside the SVG shape first.
- Treat internal cutouts, red/yellow keep-clear zones, center slots, and shared
  seams as no-decorative-element regions before rendering.
- Final clipping is allowed only as an exact-edge export guardrail. It cannot
  rescue a composition whose decorative elements already cross forbidden areas.
- Style fit and geometry fit are separate gates. A metric `PASS` can still fail
  visually, and a style-matched result can still be unusable if it violates the
  contour.

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
4. Plan safe pockets:
   - Name the usable areas where motifs/modules can live.
   - Name every forbidden area that must remain blank or quiet background.
   - Decide what background texture may cross seams and what motifs may not.
5. Draft prompts or procedural layouts from both inputs:
   - Template geometry controls placement.
   - Reference images control object vocabulary, palette, line weight, lighting,
     simplicity, and rendering language.
6. Generate candidates from the original references/templates.
   - Do not keep patching a bad composition if accumulated feedback would make a
     fresh prompt clearer.
   - Patch locally only when the main artwork is good and the failure is bounded
     to a small fixable area.
7. Export and score:
   - Save generated images under `tasks/<task>/outputs/generated/`.
   - Produce overlay/debug/metadata artifacts under `outputs/reviews/` or
     `outputs/final/`.
   - Use the task's exact SVG and require zero outside/cutout pixels when the
     exporter supports it.
8. Review with a judge:
   - Use `.codex/skills/svg-template-review-judge/SKILL.md`.
   - The judge must inspect the actual artwork, overlay/debug image, metadata,
     and cutout crops when relevant.
9. Record the decision:
   - Update the task brief, review note, or handoff with commands, paths,
     verdict, remaining risk, and the next reset-vs-patch decision.

## Reset Vs Patch

Restart from the source prompt/references when:

- The composition was designed for a rectangle and only clipped later.
- The style misses the references in object vocabulary or rendering language.
- Multiple repair passes are accumulating artifacts.
- User feedback changes the production rule.

Patch locally when:

- The full composition is already good.
- The failure is confined to a bounded area.
- The patch can be verified with exact SVG masks, crop review, and full-frame
  review.

## Done Means

- The task folder records the exact SVG, references, generated candidate, export
  command, metadata, and review artifacts.
- Geometry checks report no painted pixels outside the allowed contour or inside
  cutouts/keep-clear masks.
- A visual judge has inspected the actual images, not only JSON metrics.
- The result matches the style references in object vocabulary, palette,
  lighting, shape language, and density.
- The final report states whether the next step is accept, local patch, or
  prompt/source restart.

## Anti-Patterns

- Treating a clipped rectangular image as a valid contour-designed result.
- Calling a result done because metadata says `PASS`.
- Fixing style with palette shifts when the visual vocabulary is wrong.
- Asking the model to draw final holes or production cutouts.
- Continuing a repair loop without explicitly deciding why patch beats restart.
