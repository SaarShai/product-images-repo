---
nid: ntmgsn
title: "Deterministic gates pass?"
type: decision
x: 400
y: 300
icon: "❓"
summary: "Branch on whether a candidate cleared the deterministic hard-gates"
status: draft
tags: [decision, gate]
---
# Deterministic gates pass?

Branch on the verdict from [[deterministic-gates|deterministic-gates]].

- **No** — the candidate failed region-IoU / outside-mask delta / text-gate → it does
  not get judged. Route it back to Stage 2 at
  [[back-to-generation|back-to-generation]] to regenerate.
- **Yes** — the candidate cleared every deterministic gate → promote it to the vision
  judge at [[vision-judge|vision-judge]].

A passing metric only earns a candidate the right to be looked at — it is never
acceptance on its own (law 4).
