# Task-retrospective report

## Task

- Goal: explain why the "styled generated images" oversight happened and
  persist a project-specific prevention gate.
- Future trigger: a Screenery/template image task asks to show styled generated
  images, styled candidates, or reference-style options after geometry-safe
  roughs/procedural previews already exist.
- Definition of done: root cause is named; durable prevention exists in a task
  gate, wiki lesson, and proposed skill; each update is read back and linted or
  gated.
- Evidence quality: high for project rules and file artifacts; medium for
  subjective style judgment because final aesthetic approval remains the user's.

## What happened

- I generated `d1`-`d6` decoration candidates with a local Pillow/procedural
  renderer.
- I verified geometry containment and filenames, then incorrectly presented
  those images as "styled generated images."
- The user correctly rejected them because they were not reference-attached image
  generation outputs and did not meet this project's definition of styled.
- I then checked project rules and memory, built a style packet from the actual
  reference screenshots, generated `styled-v1`-`styled-v3` via OpenAI with the
  references/style-packet attached, and exact-masked those outputs afterward.

## Why It Happened

1. **Layer collapse:** I treated "zero pixels outside the mask" as evidence for
   the broader user-facing claim "styled." Geometry success and style success are
   separate layers.
2. **Method provenance missing:** I did not ask whether the displayed artifact
   came from attachment-aware image generation. It came from a local procedural
   renderer, so it should have been labeled a composition map, not styled art.
3. **Project rule skipped at the display boundary:** The project already says
   procedural/assembled results should route to reference-attached redraws, but I
   applied that only after user correction.
4. **Verifier mismatch:** The verifier checked containment and stale filenames,
   not visual style or generation provenance.

## Reusable Learnings

1. Lesson: never call a Screenery/template candidate "styled generated" unless
   method provenance proves actual reference/style-packet images were attached
   to image generation.
   Applies when: styled/reference-style output is requested after rough geometry
   already exists.
   Trigger/symptom: mask-valid procedural preview is about to be shown as styled.
   Evidence: `d1`-`d6` passed alpha containment but were rejected; `styled-v1`-
   `styled-v3` used reference-attached OpenAI generation and then exact masks.
   Target: `skills/styled-candidate-proof-gate/SKILL.md`,
   `tasks/festive-v1-gingerbread-candidates/CORRECTION-GATE.md`, and
   `wiki/concepts/gingerbread-panel-cutouts-decoration-slots.md`.
   Write-gate: passed for rationale and wiki lesson.
   Action: persisted as a proposed slash-only skill plus task/wiki gates.

## Rejected Learnings

- Candidate: add a broad always-on rule to `AGENTS.md`.
  Reason rejected: `AGENTS.md` already had the broad rule; the failure was a
  missed boundary-specific gate, so a narrower proposed skill and task/wiki
  exemplar is a better target.

## Project Updates

- Updated `tasks/festive-v1-gingerbread-candidates/CORRECTION-GATE.md` with a
  styled-candidate gate.
- Updated `wiki/concepts/gingerbread-panel-cutouts-decoration-slots.md` with a
  style gate and rejected/proper exemplar.
- Added `skills/styled-candidate-proof-gate/SKILL.md` as a proposed slash-only
  skill.

## Remaining Risks

- The new skill is proposed, not trusted. It will not auto-fire until telemetry
  proves it.
- Aesthetic approval is still human; the gate prevents method/provenance
  mislabeling, not all possible style taste misses.
