---
schema_version: 2
title: "Doc-fix rule: fixing a contradiction requires repo-wide grep for all sides"
type: concept
domain: "framework"
tier: semantic
confidence: 0.85
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "observed 3 one-side-only fixes: AGENTS.md vs image-generation.md, CLAUDE.md vs SKILL.md, install.sh claims"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - documentation
  - maintenance
  - git
  - consistency
  - audit
---

# Doc-Fix Rule: Fixing a Contradiction Requires Repo-Wide Grep for All Sides

## Core Rule

When you fix a claim that contradicts another part of the codebase, **do not fix only one side.** Grep the entire repo for all instances of the claim, and fix every contradicting statement.

Fixing only the instance you noticed leaves dormant contradictions elsewhere, which:
- Create confusion on re-reads.
- Break audits (different tools/skills point to incompatible truth).
- Will resurface as drift bugs later.

## Problem Statement

Observed across three sessions (2026-07-16 audit):

1. **AGENTS.md vs image-generation.md:** One document claimed "Model X is the primary route for task Y"; the other claimed "Model Z is used instead." Only one was fixed; the contradiction persisted silently.
2. **CLAUDE.md vs SKILL.md:** Routing rule stated in CLAUDE.md conflicted with the actual trigger in SKILL.md. Fix to CLAUDE.md; SKILL.md left unchanged. Later session misread the divergence.
3. **install.sh claims:** install.sh script documented a tool installation as "skipped if already present"; no other docs mentioned this; when the tool broke, the script was never consulted, and the claim was not in git.

## The Fix

When fixing a contradicting claim:

1. **Identify the claim.** Example: "Model X handles background removal."
2. **Grep the entire repo:** `rg "Model X handles|background.*removal.*Model X" --type md` (adjust pattern to the actual claim).
3. **List all locations** where the claim appears (or the contradicting claim appears).
4. **Fix all of them** in a single commit, or clearly mark why one side is intentionally left un-fixed.
5. **Document the fix** in the commit message: "Reconcile contradiction: AGENTS.md / image-generation.md now both state Model X is the fallback."

## Implementation Checklist

- [ ] Identify the factual contradiction (two docs claim incompatible things).
- [ ] Grep for the claim across the entire repo (`wiki/`, `skills/`, `tasks/`, `CLAUDE.md`, `AGENTS.md`, etc.).
- [ ] Record all instances (file path + line number).
- [ ] Decide on the single source of truth (which side is correct?).
- [ ] Update all instances to match the truth.
- [ ] Commit with a message naming the files touched and the resolved contradiction.

## Related Lessons

- [[concepts/fresh-clone-auditability-is-done-criterion]] — Contradictions that exist only in working-tree docs are never auditable.
- [[concepts/certification-integrity-verification-must-fail-independently]] — Contradictions are a form of failed verification; someone should have caught them.

## Open Questions

- Should this be enforced by lint (CI/CD fails on contradicting claims)?
- What level of semantic similarity counts as a contradiction (exact text match, paraphrase, or logical incompatibility)?
- Should a deferral be allowed (document the contradiction + open a ticket, rather than force-fix immediately)?
