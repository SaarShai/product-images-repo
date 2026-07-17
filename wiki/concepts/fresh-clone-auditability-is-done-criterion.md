---
schema_version: 2
title: "Fresh-clone auditability is a done-criterion"
type: concept
domain: "framework"
tier: semantic
confidence: 0.95
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "observed 442MB + 7 unique files lost on git-clean across 10 session snapshots"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - auditability
  - git
  - evidence
  - done-criterion
  - working-tree
---

# Fresh-Clone Auditability Is a Done-Criterion

## Core Rule

**A claim whose evidence exists only in the working tree (not committed to git) is not done.** On `git clean -fdx`, that evidence disappears. If the claim cannot be verified on a fresh clone, it is not verified.

This applies to **test results, log files, candidate images, metric CSVs, negative-test evidence, and any artifact meant to prove correctness.**

## Problem Statement

Observed during 2026-07-16 audit across 10 session snapshots:

- **442MB + 7 unique files** were only present in working trees, not git-tracked.
- When a session ended and the next agent cloned the repo fresh, the evidence was gone.
- Claims in LEDGER.md or wiki stated "test passed" or "gate rejected X"; the underlying test outputs were in the working tree (untracked).
- On `git clean`, the test results evaporated; audit had to re-derive or trust the ledger prose (which is not proof).

## What Counts as "Evidence"?

Evidence that must be in git:

- **Test results / gate outputs:** If a gate rejected candidate X, the gate's rejection log / metric value / exit code must be committed.
- **Negative test cases:** A gate's negative test input (bad candidate) and its rejection result must be in git.
- **Metric CSVs / audit reports:** If a metric drove a decision, the CSV or report must be tracked.
- **Candidate selection:** If multiple candidates were generated and one was selected, show the selection process (e.g., which candidates + verdict logic + result).
- **Calibration data:** Threshold tuning, sensitivity analysis, or parameter selection must be recorded in git.

## What Does NOT Need to Be in Git

- **Intermediate renders** from a generation script (e.g., all 50 raw model outputs from a batch); keep one exemplar or a summary index.
- **Logs of exploratory debugging** (as long as the final fix is committed).
- **Working copies** of re-derivable artifacts (e.g., images from a script run, if the script + seed are in git).

## The Fix

For any work claiming correctness:

1. **Commit the evidence.** Don't rely on working-tree files.
2. **If evidence is large,** store a **summary index** in git (e.g., a CSV listing candidate paths and verdicts; the images themselves can live in a git-ignored `candidates/` folder for re-runs, but the selection logic + result must be tracked).
3. **Audit the path:** `git clean -fdx` should not destroy the proof of your claim.
4. **Add to `log.md`** / wiki the git-relative path to the evidence, so future readers can find it.

## Related Lessons

- [[concepts/results-collection-must-be-a-gate]] (if it exists) — Catalog all results via a reconcile-from-disk hook (Stop hook), not a discretionary promise.
- [[concepts/certification-integrity-verification-must-fail-independently]] — Certification must be provable; working-tree evidence is not proof.
- [[concepts/doc-fix-rule-repo-wide-grep-for-all-sides]] — Docs claiming facts; facts must have evidence in git.

## Examples

### ❌ Not Auditable (Evidence Lost)
```
Working tree: /private/tmp/candidates/candidate_1.png
LEDGER.md: "Gate rejected candidate_1 (aura > 0.05)"
After git clean: No evidence remains.
```

### ✅ Auditable (Evidence in Git)
```
Committed to git:
- tasks/task-name/round-1/gate-results.json
  { "candidate_1": {"rejected": true, "aura": 0.063, "reason": "aura > 0.05"} }
- REVIEW/task-name/round-1/CANDIDATES.md
  Lists all candidates reviewed + verdicts.

On fresh clone: Evidence is available; claim is auditable.
```

## Open Questions

- What is the maximum size of evidence that should be committed (vs. stored externally)?
- Should CI/CD enforce a "proof in git" check on claims?
- How do we handle evidence that cannot be committed due to size (e.g., a 500MB video)?
