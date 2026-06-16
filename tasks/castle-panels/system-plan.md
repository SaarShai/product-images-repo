# Castle-Panel Illustration System Plan

## Objective

Build a repeatable local workflow for creating and judging fairytale castle
panel illustrations that fit the fixed two-panel template and follow the
production guidelines without needing live user feedback for every iteration.

## Confidence Pre-Flight

- High confidence: the active source of truth is the existing
  `tasks/castle-panels` workflow, the fixed SVG/template assets, and the V6/V7/V9
  review history.
- High confidence: the best prior direction combined V7/V9B wall-center
  composition with V6-level margin discipline.
- Medium confidence: deterministic image metrics can reject many bad candidates
  and select placement recipes, but semantic failures such as a fairy near a cut
  band still need visual/adversarial review.
- Low confidence: prompt text alone can enforce final geometry; the workflow
  should assume compositing and scoring are required.

## Plan

1. Turn the existing review rules into measurable gates where possible.
2. Score generated artwork under multiple placement recipes.
3. Export the strongest candidates with metadata and review sheets.
4. Keep prompt iteration lean: one targeted prompt change, one render, one
   overlay, then score and judge.
5. Capture the final command sequence and adversarial review notes so future
   sessions can continue without rediscovering the same failures.

## Done Means

- A single repo command can score a generated image against the template-fit
  rules and emit machine-readable metrics.
- Placement experiments across existing generated candidates produce a ranked
  report with explicit pass/fail reasons.
- The current best wall-center and/or empty-center candidate is exported with a
  reproducible metadata file and review image.
- The docs identify the current system workflow, acceptance criteria, and known
  limits of automated judgment.
- Fresh verification commands pass, including setup checks and the new scoring
  workflow.
