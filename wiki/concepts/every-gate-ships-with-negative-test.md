---
schema_version: 2
title: "Every gate ships with a negative test proving it can fail"
type: concept
domain: "loop-engineering"
tier: semantic
confidence: 0.9
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "transparent-bg-endgame gates (print-ready pipeline)"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - gates
  - quality-assurance
  - testing
  - verification
  - negative-test
  - pipeline
---

# Every Gate Ships with a Negative Test Proving It Can Fail

## Core Rule

Each removal/acceptance/quality gate must include **a concrete negative test case** — a known-bad input that the gate provably rejects. The test result (rejection) must be checked into git. No gate can claim to work if it has never been demonstrated to reject bad input.

## Why

- **False confidence:** A gate that passes on all positive candidates but has never been tested on a bad input may be vacuous (always passes).
- **Silent degradation:** When a gate fails to catch a real defect, post-mortems often reveal it was never tested on that defect type.
- **Auditability:** Signed-in test results prove the gate actually works; undocumented "passes" are unverified.

## Example: Removal-Step Gate Negative Test

A gate claiming to detect over-removed foreground edges should include:

**Positive:** A candidate where the edge is correctly preserved. Gate says PASS. ✓

**Negative:** A corrupted candidate where the edge is actually deleted (e.g., over-eroded, matting removed too much). Gate should say REJECT/FAIL. ✓ Evidence in git.

Absence of the negative test means you don't know if the gate detects the failure.

## Implementation

For each gate, commit:
1. A **known-bad test input** (e.g., an image with a deliberate defect or a tool run with bad params).
2. The **gate's rejection output** (exit code, log line, metric value that fails threshold).
3. A **comment in the test suite** explaining why this input is bad and what defect the gate should catch.

This is **not** optional for any gate that claims to prevent shipped defects.

## Related Lessons

- [[concepts/certification-integrity-verification-must-fail-independently]] — Certification must be provable to fail; negative tests prove it.
- [[concepts/removal-step-invariant-truth-backed-preservation-proof]] — Removal steps must preserve keepers; negative test validates the gate catches over-removal.

## Open Questions

- Should negative tests be automated (fail CI/CD if gate always passes) or manual review?
- What coverage is sufficient (one negative case per defect type, or exhaustive)?
- How do we track negative-test coverage across the codebase?
