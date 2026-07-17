---
schema_version: 2
title: "Deferral of correctness-affecting item requires user or adversarial-advisor sign-off"
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
  - "observed 2 self-reversals: D5 canary marked 'low value' unilaterally; 0.038% count framing self-triaged"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - governance
  - audit
  - deferral
  - sign-off
  - correctness
  - scope
---

# Deferral of Correctness-Affecting Item Requires User or Adversarial-Advisor Sign-Off

## Core Rule

**If you defer any item that affects correctness (a bug, a failing test, a gate that returned ambiguous, a missing piece of a gate battery), you cannot decide that deferral unilaterally. It requires explicit sign-off from the user or an adversarial-check agent.**

Unilateral deferral ("I marked this as low-value, so I won't fix it now") is a hidden scope-creep that can mask shipped defects or incomplete work.

## Problem Statement

Observed in two audit reversals (2026-07-16):

1. **D5 canary self-triage:** An agent marked a verification canary as "low value" and deferred it. Later session found the defect being measured was actually present and unaddressed. The deferral rationale ("not important for this run") did not hold when the issue re-surfaced in production.

2. **0.038% count framing self-triage:** An agent quoted a metric ("0.038% defect rate") and self-triaged it as acceptable, deferring further investigation. Audit revealed the metric was miscalculated (context-specific, not general); the framing had buried the ambiguity. Only user review uncovered it.

## The Fix

**Correctness-affecting deferral requires explicit sign-off.**

### What counts as correctness-affecting?

- A failing test or gate.
- An incomplete gate battery (e.g., "geometry gate passed; alpha gate deferred to next round").
- A latent bug that may resurface.
- Metric ambiguity (is this threshold right?).
- A decision whose reversal would change the output.

### Who can sign off?

- **User:** Direct approval. "Yes, defer this; accept the risk."
- **Adversarial-check agent:** An independent agent with `/brainer-audit` or `/think` scope to challenge the deferral. "I agree this can be deferred because [reason]."

### What does sign-off look like?

1. **User approval:** User says "OK, defer it" or "Mark that as backlog." Document in ledger / USER-VERDICT.md.
2. **Adversarial check:** Agent runs `/brainer-audit` or `/think` on the deferral rationale; produces a file (e.g., `DEFERRAL-APPROVED.md`) stating the reasoning and consent to defer.

**Cannot defer unilaterally** by:
- Marking it "low-value" yourself.
- Reframing the metric to make it seem acceptable.
- Assuming the user agrees because they didn't object.

## Related Lessons

- [[concepts/human-verdict-user-verdict-file-required-for-gate-acceptance]] — Formalism for human verdicts; deferral sign-off is a special case.
- [[concepts/certification-integrity-verification-must-fail-independently]] — Unilateral deferral is the inverse of certification: hidden drift, no evidence.
- [[concepts/standing-orders]] (if it exists in main CLAUDE.md) — May reference standing deferral rules (if any).

## Open Questions

- Can a user pre-authorize classes of deferrals ("defer all cosmetic gaps")?
- Should deferral require a ticket/issue link, or is explicit sign-off sufficient?
- What happens if a deferred item affects a critical path later (who's responsible)?
