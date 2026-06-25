---
nid: nm42po
title: "Verify"
type: step
x: 1440
y: 300
icon: "✅"
summary: "Measured gate — delta, leak, vision judge, human accept"
gate: "outside delta==0; leak_metric<0.06; vision judge; user accepts"
status: draft
tags: [repair, verify, gate]
---
# Verify

The final measured gate — never claimed, always measured (core law 4):

- **outside-mask pixel delta == 0** — the rest of the image is byte-exact (`compose_fairy.py`).
- **leak_metric < 0.06** — perceptual outside-mask leak (SSIM + LPIPS + DINOv2); raise to
  ~0.12 for big-area erases.
- **vision judge** — VLM verdict over the result (`judge.py`); a passing number is not
  acceptance on its own.
- **user accepts** — human is the final arbiter on aesthetics / sharpness.

**Gate:** outside delta == 0; leak_metric < 0.06; vision judge passes; user accepts.

Beyond this gate sit the [[open-problems|open problems]] — even a passing single-element
repair can still seam against the un-edited scene.
