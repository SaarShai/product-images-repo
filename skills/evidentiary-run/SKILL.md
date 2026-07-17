---
name: evidentiary-run
description: Freeze-inputs evidentiary run to validate a released pipeline on a new subject class
status: proposed
source: tasks/transparent-bg-endgame/EVIDENTIARY-RUN-festive.md
learned_at: 2026-07-17
requires_tools: 
disable-model-invocation: true
auto-install: false
refined_at: 2026-07-17
---

# evidentiary-run

> **Proposed skill** — born from `/learn`. Slash-only until trusted: it will NOT
> auto-fire. Promote with the telemetry-gated gate once usage proves it out:
> `python3 skills/learn-skill/tools/learn.py promote --name evidentiary-run` (needs N
> consecutive recorded hits, no trailing abort — see `learn-skill/SKILL.md` → Trust).

## When to Use
Validating any released pipeline (image gen, gating, transform) on a NEW subject class or after a significant pipeline change; whenever a claim like 'generalizes' or 'validated' is about to be made; whenever a sense-check asks 'are we actually converging'.

## Procedure
1) Write EVIDENTIARY-RUN-<name>.md BEFORE execution: frozen inputs (exact paths, prompt blocks verbatim), frozen command WITH EVERY PLACEHOLDER RESOLVED (real --ppi value, real paths — the contract's command line must be copy-paste runnable with zero placeholders), numbered acceptance criteria, explicit no-rescue clause. 2) Run the released pipeline UNCHANGED (for transparent-bg: /usr/bin/python3 scripts/run_c_green_v2.py --policy cgreen-v2-print-binary-v1 --ppi <ppi>). 3) No mid-run rescue: a FAIL is frozen, never patched around in-flight. 4) On FAIL write DIAGNOSIS.md separating gate FALSE-POSITIVES from REAL defects; each root cause gets its own targeted patch + one regression fixture. 5) After patching any gate, re-run gate_battery on the previously-FAILed artifacts BEFORE new diagnosis (a gate patch changes what past verdicts mean). 6) Record the human verdict in VERDICT.md; D-gate REVIEW verdicts at human-judgment tier are resolved there. 7) Claim ceiling: 'passed calibrated gates + human-approved on N subjects', never 'validated'. 8) Adversarially exercise eligibility assumptions: include at least one case that deliberately VIOLATES a claimed precondition, and freeze the expected safe-stop/branch behavior before execution — a declared prerequisite is not a safety control unless the pipeline mechanically branches or refuses when it is false. The contract must NAME the expected concrete signal (e.g. runner exit 2/3, a named precheck FAIL like NO_GREEN_ART, or a forced mode switch like --green-art-present) — 'it should stop' is not freezable. (Festive holly violated 'no essential green content' and exposed advisory-only eligibility.)

## Pitfalls
Rescuing mid-run invalidates the evidence (the run no longer tests the released pipeline). Diagnosing new failures against a stale gate version. Treating a caught failure as an improved result (safe failure != output improvement). Unfreezing acceptance criteria after seeing results.

## Verification
Contract file exists with a pre-execution timestamp/commit; run dirs contain unmodified frozen artifacts; DIAGNOSIS.md lists FP-vs-real split; regression fixtures exist and fail on the pre-patch code; VERDICT.md read back.

<!-- Rationale (why this earns a skill) — scored by write-gate before commit:
Why this earns a skill: because the festive evidentiary run only produced trustworthy conclusions (two distinct root causes isolated, patches proven by re-gate, human-resolvable REVIEW) because inputs and acceptance criteria were frozen before execution and no mid-run rescue was allowed — an unfrozen run would have let the agent silently patch around the D1 false positive and never discover the binding-eligibility gap. Evidence: tasks/transparent-bg-endgame/EVIDENTIARY-RUN-festive.md, DIAGNOSIS.md, VERDICT.md; Sol sense-check prescribed the protocol and it worked as designed (FAIL exit 2 instead of shipping). Recurs: every new subject class and every pipeline change needs the same validation shape, so that future agents do not re-derive it or skip the no-rescue clause.
-->
