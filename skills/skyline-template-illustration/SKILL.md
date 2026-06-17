---
name: skyline-template-illustration
description: Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review.
effort: high
---

# Skyline Template Illustration

Use this skill for skyline, city-scape, cityscape, landmark, storefront skyline,
or similar three-panel Screenery image-generation tasks.

This is a domain wrapper around the repo's SVG-template workflow. Do not fork
the whole process; load the shared skills and then apply the skyline rules.

## Required Reading

1. Read `AGENTS.md`.
2. Read `docs/skyline-template-illustration-workflow.md`.
3. Read `.codex/skills/svg-template-illustration/SKILL.md`.
4. Read `.codex/skills/reference-style-packet/SKILL.md` when references define
   style, palette, landmarks, or prior render examples.
5. Read `.codex/skills/svg-template-review-judge/SKILL.md` before accepting,
   patching, or restarting any candidate.

## Default Source Evidence

- Default template: `assets/skyline/city-skyline template.svg`
- Skyline examples and counterexamples: `assets/skyline/*.png`
- Skyline asset map: `assets/skyline/README.md`
- Shared workflow: `docs/svg-template-illustration-workflow.md`
- Shared judge checklist: `docs/review-judge-checklist.md`

If the user uploads a different skyline SVG, treat the uploaded SVG as the
template authority, but still use this skill's skyline composition rules unless
the user explicitly overrides them.

## Skyline Defaults

- The collection has three physical panels: one large central door panel and
  two narrow side panels.
- The large door panel has one top sub-panel plus two bottom saloon-style door
  flaps.
- Each narrow panel has one top sub-panel plus one bottom sub-panel.
- Create one continuous city-scape family across the three panels.
- Each physical panel should contain one iconic building or landmark, or a
  composite of up to three buildings/landmarks.
- Buildings, landmarks, and recognizable features must not be cropped or split
  between panels.
- Specific features must not be cropped by blue dashed top/bottom separators,
  red dashed rectangles, panel seams, or cut lines.
- Bridges, trains, roads, rivers, rails, cables, and similar run-through
  structures may cross panels when they read as continuous infrastructure, not
  as cropped focal landmarks.
- The green dashed top contour is temporary. Plan how it should trace the tops
  of the chosen buildings/landmarks.
- A landmark may rise above the adapted top contour only in a controlled amount.
  Door-panel domes/spires are a good precedent; a feature that towers far above
  the contour, such as an oversized TV tower, should be reduced or repositioned
  so the production silhouette still feels intentional.
- The orange dashed arch marks the saloon-door flap guide. Prefer a feature
  that fits or stylistically supports this arch: bridge span, entrance, statue,
  archway, doorway, portal, or enlarged architectural feature.
- Building proportions and feature proportions may be modified to fit the
  template, especially to make a door, entrance, statue, or bridge work inside
  the orange arch.
- Landmark bases and lower sections must stay whole inside their physical
  panels. Fix a cropped building base before polishing style.
- Follow the rules exactly when exactness matters and is practical. When strict
  interpretation is impossible, too slow, or visually worse, follow the general
  intent, record the deviation, and ask the user if it changes the premise.
- Keep sky/background areas white by default so the sky can be removed or added
  later.

## SVG Guide Roles

In the default skyline SVG:

- Black strokes are production panel borders, outer contours, door flaps, and
  physical cut/hinge references.
- Yellow dashed strokes are margin/safe-area guides. Primary illustrations
  should fit inside them.
- Blue dashed strokes (`#1c75bc`) are the dividing lines between the top and
  bottom sub-panels (top/bottom separators). Features must read whole within a
  sub-panel and must not be cropped by these dividers.
- Red dashed rectangles (`#ed1c24`) are no-crop/no-focal-feature keep-clear
  zones, unless the user explicitly asks to place a specific simple feature
  there.
- Red-center lanes may contain quiet, non-iconic filler such as plain facade,
  wall, rail, water, or train body. They should not contain recognizable
  features such as statues, signs, faces, text, distinctive roof tips, or named
  landmark details.
- Green dashed strokes are temporary top-contour guides that should be adapted
  to the skyline silhouette.
- Orange dashed strokes mark the central saloon-door arch guide.

Class names and exported path names can drift. Confirm guide roles from SVG
color/stroke evidence and visual inspection, not names alone.

## Template-Lock Rule

The SVG owns production geometry. A generated image may propose artwork and
skyline shape, but it must not become the source of panel dimensions, seam
positions, separator height, saloon-door arch width, red-zone positions, or
guide strokes.

For style/cohesion redraws, prefer artwork-only generation on a white
background. Do not ask the image model to draw black panel borders, yellow safe
margins, red danger zones, green top-contour guides, orange arch guides, door
split lines, knobs, or production strokes. Overlay the real SVG afterward.

Hard boundary: never ask the image model to think about, preserve, adapt, trace,
honor, fix, or improve the SVG contour, panel proportions, guide positions, red
zones, top-contour line, saloon arch, or production geometry during an artwork
patch. Those constraints belong to the deterministic overlay/export step and to
human-readable patch notes only. Image-generation prompts may say
`artwork-only on white background` and may name the local visual defects to
change, but they must not include contour/panel/guide instructions that invite
the model to redraw or reinterpret the template. If a patch needs exact
geometry context, create a mask, crop, or external overlay artifact outside the
model and verify afterward.

Prompt boundary preflight: before sending any skyline prompt to image
generation, read the exact prompt text and remove template-geometry language.
Forbidden prompt concepts include `SVG`, `contour`, `panel proportions`,
`red zone`, `blue separator`, `green line`, `orange arch`, `saloon-door guide`,
`template guide`, `safe margin`, and `production stroke`, unless the prompt is
explicitly for a non-production diagnostic guide image. Put those requirements in the task brief
or verifier checklist instead, then overlay the real SVG after generation.

If a generated candidate includes nice adapted top contour or good composition
but redraws the template wider, shorter, lower, or otherwise off-SVG, keep it
only as visual evidence. Registering or panel-warping it may be useful for a
rough composition map, but final production must restart from a locked SVG map
or exact downstream overlay/export.

For overlay review, the SVG coordinate system owns guide dimensions. Do not
derive final overlay aspect, panel widths, separator height, or saloon-arch
position from a square PNG preview, screenshot crop, or generated artwork bbox.
A raster preview may supply visible guide pixels, but the placement math must
come from the source SVG viewBox/visible coordinate bounds or an explicitly
recorded SVG geometry report.

## Standard Workflow

1. Recover state:
   - Run `git status --short`.
   - Inspect the active task folder if one exists.
   - Inspect `assets/skyline/` and any uploaded references.
2. Start a task packet if needed:
   - Use `python3 scripts/scaffold_template_task.py <task> --svg "assets/skyline/city-skyline template.svg" --refs <refs...>`.
   - Use the user-uploaded SVG instead when provided.
   - For skyline tasks, the scaffold writes `skyline-example-feedback.md`; use
     it during the live example phase.
3. Classify the template:
   - Fill `template-manifest.json`.
   - Record the three physical panels, sub-panels, red zones, yellow safe
     margins, green contour, orange arch, seams, and any ambiguous SVG paths.
   - `scripts/svg_geometry_report.py` may be attempted, but if it stalls or
     misses roles on the skyline SVG, inspect the SVG directly and record that.
4. Build or refresh the reference style packet:
   - Run `python3 scripts/build_reference_style_packet.py tasks/<task>`.
   - Inspect the contact and exemplar sheets.
   - Use only the most relevant packet crops for style/image-gen agents.
5. Write the skyline composition plan before generation:
   - Allocate one landmark/composite per physical panel.
   - Name any run-through elements and why they may cross panels.
- Name the saloon-door arch feature or state that no suitable feature exists.
- When the arch feature is a bridge or similar span, check whether aligning it
  to the middle of the saloon door flaps improves symmetry without making the
  scene feel forced.
   - Name specific features that must avoid red zones and seams.
   - Name how the top contour should adapt to the landmark silhouettes.
   - State whether the sky stays pure white.
6. Ask the user for approval when the plan changes the visual premise:
   - source packet and references;
   - city/landmark roster;
   - saloon-door arch feature;
   - run-through element;
   - top-contour adaptation;
   - white sky/background handling;
   - whether to restart or patch after feedback.
   If the host cannot render native buttons, use compact, highlighted
   button-style choices and log the selected codes in the task feedback file.
7. Run a proof-before-spend scout gate when composition is not obvious.
   - Branch into genuinely different low-cost scout tests before spending on a
     polished full render.
   - Do not treat faint lookalike placement boards as approval evidence. They
     are inventory maps unless the differences are visible within a few seconds.
   - Prefer 2 to 3 distinct routes: direct whole-scene control; rough
     composition-map-to-whole-redraw; and a strict red-zone/seam-safety scout.
   - Use independent visual and geometry reviewers to judge whether the scout
     proves enough to proceed, needs a new route, or falsifies the wireframe.
   - Record the scout prompts, artifacts, failures, and unlocked decision in
     `skyline-example-feedback.md`.
8. Run a template-registration check before treating any scout as a candidate.
   - Compare the active frame aspect, panel edges, top/bottom separator,
     red-zone rectangles, saloon arch width, and bottom-subpanel height against
     the SVG.
   - If generated guide lines are off, do not fix the SVG to match the image.
     Use the image only as composition/style evidence and restart against a
     locked SVG map.
   - If an overlay looks lower, squished, or suspiciously close-but-wrong,
     re-render or re-place it from exact SVG coordinate bounds before judging
     the artwork. Preview-crop aspect is diagnostic evidence only.
9. Generate candidates from the original template and references.
   - Keep style exploration separate from geometry placement when either part
     is uncertain.
   - Do not generate a full rectangle and crop it into the template.
10. Verify with fresh evidence:
   - Export overlay/debug/final artifacts where tooling supports it.
   - Use a vision-capable judge to inspect the actual candidate and overlay.
   - Use `.codex/skills/svg-template-review-judge/SKILL.md` verdicts:
     `ACCEPT`, `LOCAL PATCH`, `PROMPT RESTART`, or `BLOCKED`.
11. Record learning:
   - Add user feedback, decisions, failed assumptions, and accepted rules to the
     task `skyline-example-feedback.md`, `session-brief.md`, or review note.
   - Promote a rule back into this skill or the skyline workflow doc only when
     it is durable, project-specific, and useful for future skyline tasks.

## Parallel Agent Pattern

Use subagents when their evidence lenses are independent. A good skyline split:

- Template/geometry reviewer: checks panel borders, guide roles, top contour,
  saloon-door arch, red zones, and seam safety.
- Visual/style reviewer: checks reference fidelity, landmark recognizability,
  palette, object vocabulary, and white-sky/background handling.
- Scout-test reviewer: tries to falsify whether the current wireframe is useful
  enough for generation, especially when options look visually similar.
- Production judge: inspects final candidate/overlay and recommends accept,
  local patch, prompt restart, or blocked.

Do not dispatch multiple agents to inspect the same image from the same lens.
Verification agents must inspect actual images, not only prompts or metrics.

## Done Means

- The task records the exact template SVG and reference images used.
- A skyline composition plan exists before generation.
- The plan allocates landmark/composite content to all three physical panels.
- Blue/red/yellow/green/orange guide roles were recorded from the actual SVG.
- A visual style packet was built and inspected when references define style.
- A proof-before-spend scout gate was run, or the task records why it was not
  needed.
- Generated template or guide dimensions were not accepted as geometry
  authority; the real SVG was overlaid or measured afterward.
- Candidate review inspected actual artwork and overlay/debug images.
- No building, landmark, character, sign, text, statue, roof tip, or other
  recognizable feature is unintentionally cropped by seams or red zones.
- The saloon-door arch decision and top-contour adaptation are explicitly
  recorded.
- The run-through element and white-sky/background decision are explicitly
  recorded.
- Any user checkpoint approval or correction is logged in the task feedback
  file before generation or repair continues.
- The sky/background default is white unless the user overrode it.
- The final note states exact verification evidence and remaining risk.

## Ask Early

Prefer asking one to three load-bearing questions before generation:

- Which city or landmark roster should drive the three panels?
- Should there be a run-through element such as a bridge, train, road, or river?
- What should occupy or echo the central saloon-door arch?

If references answer these questions clearly, proceed and state the inference.
When these answers are already inferred, ask one final visual-premise approval
before generation: roster, run-through element, arch feature, top contour, and
white/removable sky.
