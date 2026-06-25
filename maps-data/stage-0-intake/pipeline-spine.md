---
nid: nobcae
title: "PIPELINE spine"
type: reference
x: 140
y: 450
icon: "📜"
summary: "docs/PIPELINE.md — the end-to-end lifecycle spine + Stage 0 contract"
status: draft
tags: [doc, source-of-truth]
---
# PIPELINE spine

`docs/PIPELINE.md` — the end-to-end lifecycle source of truth. One image task =
one pass through the stages; Stage 0 is universal, stages 1–5 are conditional and
chosen by the family decided here.

It defines the Stage 0 contract this map renders: **Input** (description + refs +
optional SVG / base image), **Does** (classify, ledger, inventory, plan), the
**reviewable artifact** (BRIEF.md + PLAN.md + asset-manifest.json), and the
**gate** (human reviews plan + refs before any spend). It also carries the core
laws — chiefly *reference beats prose* (missing ref ⇒ generate it as a precursor),
which this map's No-branch implements.

Governs every node in [[receive-brief|this map]].
