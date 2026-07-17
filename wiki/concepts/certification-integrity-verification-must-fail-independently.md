---
schema_version: 2
title: "Certification integrity: verification must fail independently"
type: fact
domain: "framework"
tier: semantic
confidence: 0.95
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session (independent auditor + Kimi K3 mining)"
  - "LEDGER.md (R33 'done' reversed; runner --n 0 exit 0 vacuous pass)"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - audit
  - verification
  - certification
  - quality-assurance
  - testing
  - governance
---

# Certification Integrity: Verification Must Fail Independently

## Core Rule

**Nothing counts as verified unless the check itself is proven able to FAIL, run by someone who did not build it, and evidenced in git.**

This is the audited bottom-line lesson from three independent audits (2026-07-16).

## Problem Statement

A verification can be:
1. **Vacuous** — it always passes (e.g., `sum([list]) >= 0` when list is empty; `return truthy` instead of assert-check).
2. **Biased** — run by the builder on their own artifact (author-bias; incentive to declare success).
3. **Untracked** — done on a working tree, not in git; evidence disappears on `git clean`.
4. **Unproven** — never demonstrated to reject bad input (no negative test case).

Any of these renders the certification meaningless.

## Evidence

- **R33 'done' reversal (session 2026-07-16):** Claimed task complete; independent audit found the check was never actually run (exit-code was 0 because the command exited early or the runner died silently, but test output was never examined). Was in LEDGER.md as success; git-tracked, but the underlying script was never validated.
- **Vacuous test pattern:** Observed `runner --n 0` exiting 0 with no test coverage; advisory REVIEW gate promoted to success without evidence; `sum() >= 0` on integer lists (always true).
- **Thin-ice tests:** Removal-step gates claiming pass on a single positive candidate; no negative test demonstrating detection of the failure mode (e.g., verifying the gate detects when a keeper edge is *actually* deleted).

## The Fix: Three-Part Certification

For any gate or verification:

1. **Prove it can FAIL:** Ship a negative test case (a known-bad input) and verify the gate rejects it. Collect the failure evidence in git.
2. **Run independently:** Never verify your own build. Route verification to a peer or adversarial-check agent (e.g., `/brainer-audit` on claimed work).
3. **Track evidence in git:** The test result, test input, and verdict must be committed. Working-tree evidence is forfeit on `git clean`.

## Related Lessons

- [[concepts/every-gate-ships-with-negative-test]] — Complement to this rule; gates must include negative tests.
- [[concepts/deferral-requires-user-or-adversarial-sign-off]] — Ties to governance: who can declare something done.
- [[concepts/fresh-clone-auditability-is-done-criterion]] — All evidence must survive `git clean` and a fresh clone.

## Open Questions

- What tier of independence is sufficient (peer, different session, different agent model)?
- Who is permitted to certify (builder, lead, auditor, user)?
- How should negative tests be sized (minimal reject case vs. representative adversarial)?
