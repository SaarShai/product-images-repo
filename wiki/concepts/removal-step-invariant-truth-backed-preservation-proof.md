---
schema_version: 2
title: "Removal-step invariant: truth-backed preservation proof required"
type: fact
domain: "experiments"
tier: semantic
confidence: 0.95
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit + Kimi K3 session mining"
  - "transparent-bg-endgame (REPORT.md)"
  - "observed ML-matting deletion of 18.7% thin strokes; white_key erode on rims; green_purge self-donation"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - image-processing
  - background-removal
  - gates
  - ml-matting
  - quality-assurance
  - removal-pipeline
  - preservation
---

# Removal-Step Invariant: Truth-Backed Preservation Proof Required

## Core Rule

**ANY step that removes pixels (chroma-key, ML matting, erode, repaint, alpha-blending) must ship with a truth-backed proof per tool that legitimate keeper content is NOT deleted.**

This is a cross-route invariant, not per-route. The lesson holds across `white_key.py`, `green_purge`, `chroma_key`, birefnet/SAM/BRIA matting, and any other removal step.

## Problem Statement

Removal tools are inherently destructive: they delete pixels that may contain legitimate artwork. Three observed failure modes:

1. **ML-matting overage:** SAM/BRIA/birefnet trained on photographic backgrounds delete thin strokes, feathered edges, and pale highlights. Measured impact: 18.7% of thin watercolor strokes deleted in production runs.

2. **Erode self-harm:** `white_key.py --erode 2` (default) eats pure-white rim highlights and fine detail. Koreanite and coral panels lost contour definition.

3. **Self-donation loops:** `green_purge` (chroma-key variant) can measure a keeper as "too green" and delete it in the same gate that was supposed to protect it.

## Evidence

- **ML-matting:** `tasks/transparent-bg-endgame/REPORT.md` documents 18.7% thin-stroke deletion across 200+ watercolor samples. No single threshold isolates legitimate pale art from true background.
- **Erode rim loss:** White rim highlights on coral panels (pure white, 255/255/255) were removed by `--erode 2`; fix to `--erode 0 --thresh 246`.
- **Green_purge:** Cross-route invariant: a green-keyed foreground element measured as "too green" in one round was deleted by the gate in another, because the gate measured the keeper, not the background.

## The Fix: Truth-Backed Preservation Proof

For each removal step, document:

1. **Tool-specific failure mode:** What does this tool delete? (ML edges? Eroded pixels? Color-range misclassifications?)
2. **Keeper definition:** What must be preserved? (feathered edges, rim highlights, thin strokes, specific color ranges?)
3. **Preservation test:** A concrete test case (image + tool run) where a known keeper is fed to the tool and proven NOT deleted. Metric: per-pixel preservation comparison (e.g., "100% of rim pixels survive `--erode 0 --thresh 246`").
4. **Failure evidence:** If a prior tool invocation deleted keepers, that failure is **also** tracked (not buried). E.g., "white_key v1 (`--erode 2`) deleted rim highlights; v2 (`--erode 0 --thresh 246`) preserves 99.8%."

## Cross-Route Invariant

This rule applies uniformly to all removal pathways:

| Tool | Failure Mode | Preservation Proof |
|------|--------------|-------------------|
| ML-matting (SAM/BRIA) | Thin strokes, pale highlights | Tested on real thin-watercolor samples; quantified % kept |
| white_key.py | Eroded rim detail | Tested on white=255 rims; threshold calibration |
| chroma-key variants | Color-range misclassification | Tested on keeper-colored regions; hue distance matrix |
| erode/dilate | Detail loss | Tested on feathered edges; morphological preservation measure |

## Related Lessons

- [[concepts/every-gate-ships-with-negative-test]] — Preservation tests are the negative-test side of removal gates.
- [[concepts/illustrated-product-upscale-and-background-removal-workflow]] — Known workflow lesson; documents double-Marine-Bed strategy to avoid ML-matting thin-stroke loss.
- [[concepts/print-ready-transparent-pipeline]] — Complete native-alpha pipeline; documents gate-battery tri-state to avoid false-positive removal.

## Open Questions

- How should preservation proofs be measured (pixel-count, IoU, perceptual)?
- What is acceptable preservation threshold (99%, 99.5%, 100%)?
- Should each route publish a "keeper survival matrix" per tool combo?
- Do ML-matting tools need to be replaced entirely, or can they be front-ended with a keeper-preservation guard?
