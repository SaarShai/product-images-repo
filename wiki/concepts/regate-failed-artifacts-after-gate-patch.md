---
schema_version: 2
title: "Re-gate previously-FAILed artifacts after any gate patch"
type: fact
domain: "quality-assurance"
tier: tactical
confidence: 0.9
trust: verified
scope: this-repo
created: "2026-07-17"
updated: "2026-07-17"
verified: "2026-07-17"
sources:
  - tasks/transparent-bg-endgame/evidentiary-festive/regate-destructive-postpatch/battery.json
  - tasks/transparent-bg-endgame/evidentiary-festive/20260717T062957Z-bf72fc/candidate_1/gates
supersedes: []
superseded-by: []
contradicts: []
tags:
  - gates
  - quality-assurance
  - re-gating
  - gate-patch
  - transparent-generation
---

# Re-gate previously-FAILed artifacts after any gate patch

## Summary

After patching a gate, re-run it on previously-FAILed artifacts BEFORE diagnosing anything new — a gate patch changes what past verdicts mean.

## Evidence

The festive destructive-mode purge FAILed `gate_battery` (D1 yellow false-positive), and after the D1 `h_key` green-sector fix the SAME artifact re-gated to all-blocking-gates-PASS (only sub-visible D1 REVIEW). Without re-gating, a third purge mode would have been wrongly pursued for an already-acceptable artifact.

Files: `tasks/transparent-bg-endgame/evidentiary-festive/regate-destructive-postpatch/battery.json` (PASS) vs `tasks/transparent-bg-endgame/evidentiary-festive/20260717T062957Z-bf72fc/candidate_1/gates` (FAIL).

## Trigger/symptom

About to diagnose a FAIL that predates a gate code change; or a gate fix just landed.

See also: skills/evidentiary-run/SKILL.md (procedure step 5/8).
