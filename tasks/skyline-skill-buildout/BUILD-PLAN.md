# Skyline Skill — Build Plan (Phase 2, after proposal approval)

Date: 2026-06-17 · Status: **PROPOSED — do not start until the workflow is approved**

Sequenced **low-risk-first**. Each increment ships a runnable test so we can
"test each step" before moving on, exactly as requested. Built in worktree-safe
slices; validated against `tasks/berlin-skyline-live-example` (the live
test-bed). Nothing here mutates the skill until you approve the [PROPOSAL](PROPOSAL.md).

---

## B1 · Consolidate & fix  *(fast, no new behavior)*
**Goal:** make the existing skill self-consistent and name the tooling.
- Fix stale `.codex/skills/...` references → `skills/...` across the skyline
  SKILL.md, the workflow doc, and task briefs.
- Add a **"Generation Tools"** section (the **two subscription routes** +
  command templates + when-to-use table) to the skill + workflow doc; pin the
  tooling decision: **OpenAI via Codex (priority)**, **agy / Nano Banana
  (testing)**, plain `gemini` blacklisted for images. **render-studio is out of
  scope** (no API/metered/inpaint).
- Bake the `assets/skyline` example library into the skill as example-driven
  rules (cite each PNG).
- Add the exact-SVG-bounds constant (aspect 1.463) as the single source.
- **Checkpoint / test:** `python3 scripts/validate_svg_template_workflow.py`
  passes; `grep -r ".codex/skills" skills docs tasks` returns nothing stale;
  the skill names a concrete generation command.

## B2 · Visual-judge gate  ★ *(the bottleneck — highest leverage)*
**Goal:** force "look at the picture" with a measured PASS/FAIL table.
- `scripts/skyline_visual_judge.py`: takes the `export_svg_template_fit`
  artifacts, slices high-DPI crops per skyline rule region (panel / seam /
  saloon arch / top-contour / each red zone / white-sky), upscales each, prints
  the forced 7-row PASS/FAIL table template (native crop/upscale, no external
  deps; crop boxes from SVG coords).
- Upgrade `skills/svg-template-review-judge` to require the high-DPI crops +
  measured table + **cold separate judge** (generator ≠ verifier), mapping to
  ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED.
- **Checkpoint / test:** run it on the existing Berlin candidates; it must flag
  the *known* FAILs — TV-tower overshoot, hotel base crop, Quadriga in the
  red-center — and PASS the clean regions.

## B3 · Per-stage mechanical checkpoints
**Goal:** every stage advances on an exit code, not a claim.
- `scripts/lint_prompt_safe_lane.py` — forbidden-token linter; fail-closed
  before any generation send.
- Skyline geometry scorer — generalize `score_template_fit.py` off its
  castle/baci defaults to the 3-panel skyline (aspect/seams/red-zone/coverage).
- A skyline scout `loop` spec run through `loop_lint.py`.
- An `eval-gate` skyline `rubric.md` + `cases.jsonl` (seed from Berlin
  accept/reject history).
- **Checkpoint / test:** each gate returns non-zero on a known-bad input and
  zero on a known-good one.

## B4 · Learning loop
**Goal:** lessons become retrievable + recurrence-escalating.
- Write `wiki/patterns/skyline-template-workflow.md` +
  `wiki/L3_sops/skyline-render-playbook.md` (the empty homes today); migrate the
  named-but-unwritten patterns from `wiki/log.md`.
- Register skyline signatures in `skills/task-retrospective/lesson_patterns.json`.
- Add `skills/skyline-template-illustration/drift_probes.json`
  (forbidden-geometry-token regex).
- **Checkpoint / test:** `audit_lessons.py` runs clean; a planted recurrence in
  `wiki/log.md` makes it exit 1; the canary probe fires on a forbidden token.

## B5 · End-to-end validation on Berlin
**Goal:** prove the whole pipeline on a real task + clear the punch-list.
- Run Stages 0–10 on `tasks/berlin-skyline-live-example`; close the outstanding
  corrections (TV-tower height, hotel base, Quadriga realign, bridge symmetry,
  tunnel A4) via LOCAL PATCH where bounded.
- **Checkpoint / test:** the visual-judge emits an **all-PASS** 7-row table from
  a cold judge; `HANDOFF.md` punch-list is empty; a LEARN entry is written.

---

## Per-increment involvement
After each increment I show you the runnable test output and pause if the result
is ambiguous or a decision is needed. B2 (the judge) and B5 (Berlin close-out)
are the two you'll most want to eyeball.
