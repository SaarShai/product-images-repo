# Task-retrospective report — evidentiary festive run + audit rounds

Armed after-the-fact 20260717T072405Z. Evidence quality: high (frozen run dirs,
DIAGNOSIS.md, VERDICT.md, battery JSONs, git history).

## Task
- Goal: validate Route C-green v2 on a new, hostile subject class (green holly).
- Definition of done: usable final, gates + human verdict on record.
- Outcome: destructive-mode final accepted by user; two real pipeline defects
  found, patched, regression-tested along the way.

## Reusable learnings (3 candidates, all persisted)
1. **Skill `evidentiary-run`** (`skills/evidentiary-run/SKILL.md`, status
   proposed, slash-only): freeze-inputs protocol — contract-before-execution,
   released-pipeline-unchanged, no-rescue, FP-vs-real diagnosis, re-gate after
   gate patches, hostile-precondition case (Sol's addition), claim ceiling.
   Route-probe exit 3 → dest-3 gate passed; dedup CREATE; write-gate PASS
   (sop/verified); lint PASS. Weakest-executor test (cold gpt-5.6-luna): all 5
   planning steps correct; its 2 AMBIGUOUS flags fixed in the skill text via
   gated patches (placeholders-resolved rule; named safe-stop signal rule).
2. **Wiki fact** `wiki/concepts/regate-failed-artifacts-after-gate-patch.md`:
   a gate patch changes what past verdicts mean — festive destructive FAIL
   flipped to all-blocking-PASS after the D1 fix. Write-gate PASS
   (error/verified). Kept as a page despite overlap with skill step 5 because
   the skill is slash-only (not model-discoverable); cross-linked both ways.
3. **models.yaml probe row**: kimi-k3 via pi CLI (moonshotai provider, 1M ctx);
   runtime 429 engine_overloaded ×3 on 2026-07-17. Maintenance, not a lesson.

## Rejected
- Standalone "green-art run both purge modes" — already banked earlier today
  (wiki + SKILL.md + PIPELINE.md); duplicate.

## Adversarial checks (user-directed model routing)
- GPT-5.6 Sol (codex, high effort, 66K tokens): confirmed C1 skill-shaped,
  called standalone C2 page duplication-risk (accepted with cross-link
  mitigation), contributed the missing lesson (hostile-precondition step 8).
- Kimi K3 via pi CLI: attempted 3× (`pi --provider moonshotai --model
  kimi-k3`), all HTTP 429 engine_overloaded (provider-side). NOT substituted
  per user directive; recorded as unavailable.
- GPT-5.6 Luna (codex workspace-write): wrote the wiki page + index/log
  entries; also served as the cold weakest-executor for the skill test.

## Remaining risks
- `evidentiary-run` is proposed/slash-only: it must be invoked as
  `/evidentiary-run` until telemetry promotes it (3 consecutive hits).
- Kimi K3 unavailability is provider-side; retry on next task, don't assume.
