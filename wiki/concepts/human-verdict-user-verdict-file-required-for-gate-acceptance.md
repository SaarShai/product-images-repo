---
schema_version: 2
title: "Human verdict: USER-VERDICT.md file required to convert gate REVIEW to acceptance"
type: concept
domain: "framework"
tier: semantic
confidence: 0.9
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "transparent-bg-endgame gates (REVIEW → acceptance workflow)"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - gates
  - quality-assurance
  - human-review
  - acceptance-criteria
  - documentation
  - governance
---

# Human Verdict: USER-VERDICT.md File Required for Gate Acceptance

## Core Rule

**A gate that returns REVIEW (ambiguous/subjective judgment needed) cannot be converted to acceptance without an explicit human verdict documented as a file.**

Ledger prose saying "user approved it" is **not an approval artifact**. The verdict must be a tracked file (e.g., `USER-VERDICT.md` in the task or round folder) containing:

1. The date and who made the verdict.
2. What they judged (which candidate, which metric, which round).
3. The explicit accept/reject decision.
4. Rationale (one line minimum; "looks good" suffices if true).

## Why

- **Ledger prose is lossy:** A note in a LEDGER saying "user approved" can be edited, summarized, or lost in compaction. A file commit is immutable.
- **Ambiguity hiding:** If a gate returned REVIEW, converting it to PASS without evidence that a human actually looked and judged is a classification error.
- **Auditability:** On re-run or audit, the reviewer can point to the file and prove the judgment was made and recorded.
- **Scope clarity:** Who decided? Just the builder's impression, or did the user actually review?

## Implementation

For each task/round that includes a REVIEW gate:

1. Create `REVIEW/<task>/<round>/USER-VERDICT.md` (or `tasks/<task>/<round>/USER-VERDICT.md`).
2. Record:
   ```
   # User Verdict — [Round/Gate Name]
   
   **Date:** 2026-07-16  
   **Reviewer:** user or agent name  
   **Candidates reviewed:** (link to images or list)  
   **Decision:** ACCEPT / REJECT / CONDITIONAL  
   **Rationale:** One line (e.g., "alignment to reference is good enough").
   ```
3. Commit the file to git before marking the gate as closed.

## Related Lessons

- [[concepts/certification-integrity-verification-must-fail-independently]] — Verdicts must be independent and tracked; this formalism ensures that.
- [[concepts/deferral-requires-user-or-adversarial-sign-off]] — Sign-off governance; this file is the artifact.
- [[concepts/geometry-must-be-measured-gate]] (if it exists) — Measurement gates are objective; REVIEW gates are human subjective; distinguish and formalize human verdicts.

## Open Questions

- Should USER-VERDICT.md be required in all cases, or only when gate returns REVIEW?
- Can a single verdict cover multiple candidates/rounds, or must each round have its own file?
- What happens if the user does not provide a verdict (should the gate block or default to REJECT)?
