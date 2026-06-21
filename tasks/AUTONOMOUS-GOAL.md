# GOAL — autonomous run (user away; do not stop until told)

Purpose: learn as much as possible — experiment, test approaches, judge results, improve the workflow.
No user feedback available → gate with MULTIPLE judges (VLM subagents + codex GPT + GLM-5.2) and objective
tools. Be careful + methodical; verify each step before the next.

## Tracks (independent → parallelizable)
### T1 — Skyline themes (template: city-skyline, 3 panels: 1 door panel + 2 narrow)
Create all 3 illustrations per theme (door panel + 2 narrow), ONE PANEL AT A TIME, many approaches.
- T1a READING CORNER — study refs (tasks/skyline-reading-corner/refs), build style packet, compose, gen, gate.
- T1b GINGERBREAD HOUSE — study refs (tasks/skyline-gingerbread/refs), build style packet, compose, gen, gate.
Rules (skyline skill): one continuous themed scene across 3 panels; one focal element/composite per panel;
NEVER crop a focal feature by seams / blue separators / red keep-clear; saloon-door arch feature on the door
panel; adapt top contour; sky WHITE (removable); ARTWORK-ONLY on white — NEVER ask the model to draw
template guides/borders; overlay the real SVG afterward (template-lock). Be creative with included elements.

### T2 — Princess improvement (source: tasks/princess-improve/source, COPIES of read-only Drive)
Improve door-panel, narrow-01, narrow-02 via different methods; learn what's easy vs hard:
- detail refinement: faces, hands, fingers, feet, toes (anatomy) — framing-locked edits / region edits.
- geometry "tightening": make the art fit the die-cut even better (register/overlay/gate).
Record per change-type: which method worked, effort, fidelity.

### T3 — Blueprint steps not needing the user
Advance docs/whole-panel-VALIDATED-RECIPE + tooling; run the objective-gate harness on real outputs; build
the regression/gold set from accepted results; record learnings.

## Method (every gen)
LAW 0: reference IMAGES + geometry, never prose for what must be exact. Study refs (don't blind-copy).
Maximize fan-out (openai concurrent; nano serial + square-biased → skip for tall/narrow). Gate: objective
(geom_gate fill/contour + size; element-count→VLM count-on-context; edges) THEN multi-judge (≥3 VLM +
codex + GLM) for structure; AESTHETICS = no human here → use multi-judge consensus + record uncertainty,
do NOT claim a winner on one number. Show all results full-size with links (for later human review).

## Judges
- VLM subagents on hi-DPI tiles + whole-panel context (count there, not tiles).
- codex GPT-5.5 + GLM-5.2 as independent reviewers for plans, prompts, and result critiques.
- objective tools: objective_gate_report (geom+size hard; dup advisory→VLM), style_board for ref-vs-cand.

## Cadence / safety
One panel at a time. Verify before continuing. Log every step in the ledger + per-task STATE.md.
Subagent contract: "READY FOR JUDGING" + attempts/assumptions, never "done"; inline rules (hooks don't fire
in subagents); re-verify subagent output in the main loop. Worktree-isolate parallel writers.
Keep going across phases; checkpoint artifacts so a resume is clean.
