---
schema_version: 2
title: "Band-Panel Workflow SOP"
type: concept
domain: "experiments"
tier: procedural
confidence: 0.8
trust: verified
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources:
  - .brainer/task-retrospective/sessions/20260712T135739Z-coral-panel-workflow-retrospective-session-local/laneA-timeline.md
  - .brainer/task-retrospective/sessions/20260712T135739Z-coral-panel-workflow-retrospective-session-local/laneB-failures.md
  - .brainer/task-retrospective/sessions/20260712T135739Z-coral-panel-workflow-retrospective-session-local/laneC-tooling.md
  - .brainer/task-retrospective/sessions/20260712T135739Z-coral-panel-workflow-retrospective-session-local/CONSOLIDATED.md
  - tasks/marine-coral-panels/
supersedes: []
superseded-by: []
contradicts: []
tags:
  - image-generation
  - die-cut-panel
  - band-illustration
  - fit-gate
  - white-key
  - sop
  - gpt-image-2
---

# Band-Panel Workflow SOP (v1 — single-run evidence)

Trigger/symptom: generating style-matched illustration BANDS (reef/border/ground rows) that sit under fixed creatures/elements on die-cut panels, keyed transparent, upscaled, delivered. Also trigger on symptoms: "gen ignores height percentage", "band overlaps creatures", "style similar but not exact".

## Why this SOP exists
First run (tasks/marine-coral-panels, 2026-07-12) succeeded but with 60% rework / 88% gen waste / 6 gen rounds (~102 min). 5 of 10 failures were predicted by already-banked memories not applied up front. Full retrospective: .brainer/task-retrospective/sessions/20260712T135739Z-coral-panel-workflow-retrospective-session-local/ (laneA-timeline.md, laneB-failures.md, laneC-tooling.md, CONSOLIDATED.md).

## Pre-flight (before ANY generation call)
1. Ref provenance: identify which model made the style refs; pin that family. subgen --provider openai is model-UNPINNED (shells to codex); use `subgen.py --provider api` (direct OpenAI Images API, default gpt-image-2; prefer dated snapshot gpt-image-2-2026-04-21; writes .provenance.json).
2. Ask the user 3 questions: (a) confirm ref model if unknown; (b) priority order when full-width vs never-crop vs zero-overlap conflict (run 1 answer: never-crop > overlap > width; 80% width accepted); (c) is the band bottom croppable (die-cut bleed)?
3. Grep the memory index for the task-class mechanics (model pinning, crop wording, gate calibration, key params, folder paths) and instantiate each hit as a concrete gate BEFORE round 1.
4. Calibrate gates from an accepted exemplar FIRST (run 1: reef_v1 = 0.09% creature-alpha overlap).

## Generation
- Composition belongs to PLACEMENT, not prompting: prompt height percentages don't bind (gpt-image-2 overshoots ~1.4x; 5 rewrites in run 1). Prompt for a "short, low, wide" band qualitatively; enforce budget downstream via scale/placement. Never write "begins/continues beyond the canvas edge" (it instructs cropping — run 1 failure #4); say "runs edge-to-edge, fully contained, nothing cut off, clear margin".
- Batch 4-6 candidates in parallel per panel with a stable prompt; gate mechanically; never sequential fix-the-last-image loops.

## Gates (hard, deterministic — before any style ranking or human review)
- scripts/fit_gate.py: creature-alpha overlap (never bboxes), `search` returns largest passing scale, --overlap-max 0.5 (PROVISIONAL — accepted exemplars 0.01-0.12%, no rejected corpus yet); `border` no-crop check (3px strip, >2% FAIL).
- Key with scripts/white_key.py --preset gi2 (thresh 246, erode 0) for gpt-image-2 art — default 238/2 eats pure-white rim highlights (run 1: wrongly_removed 9980 vs 1; regression fixture tests/test_white_key_gi2_preset.py). Gate on wrongly_removed metric + keycheck over dark AND magenta, never an eyeball "clean" verdict.
- Upscale: alpha_aware_upscale.py — output dirs must NOT be named final/finals (reject_final_path() hard-rejects, silent in bg jobs); verify output file EXISTS with expected dims, never trust exit codes.

## Delivery
- Verify the product's existing Images/ tree casing BEFORE writing (capital Images/finals + Images/candidates convention; run 1 delivered to a new lowercase images/finals/ — violation). ls the parent before mkdir.
- REVIEW package: boards + fullres/ + full absolute paths.

## Status / next steps
- Single-run evidence; thresholds provisional. After a 2nd conforming run: build band_pipeline.py orchestrator + promote this SOP to a learned skill via /learn (route-probe classified this as PROCEDURE-CANDIDATE; skill deferred deliberately per advisor ruling — single-run evidence, single-exemplar calibrations).

## Related
- [[concepts/transparent-clear-edge-prompt-recipe]] (prompt recipe this SOP composes with)
