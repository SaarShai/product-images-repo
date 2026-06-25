---
nid: momj93
title: "Stage 5 — Finalize / Export"
type: map
kind: process
nodes: [keep-raw, composite-to-template, raw-vs-exact, deliver-raw, deliver-composite, register, sync-library, export-fit-py, law-never-ruin-raw]
edges:
  - {from: keep-raw, to: composite-to-template, label: ""}
  - {from: composite-to-template, to: raw-vs-exact, label: ""}
  - {from: raw-vs-exact, to: deliver-raw, label: "Yes"}
  - {from: raw-vs-exact, to: deliver-composite, label: "No"}
  - {from: deliver-raw, to: register, label: ""}
  - {from: deliver-composite, to: register, label: ""}
  - {from: register, to: sync-library, label: ""}
  - {from: keep-raw, to: law-never-ruin-raw, label: "", route: smoothstep}
  - {from: composite-to-template, to: export-fit-py, label: "", route: smoothstep}
---

# Stage 5 — Finalize / Export

Composite the approved artwork into the template at exact SVG coords, verify the fit,
and log every result image. Law 5: **never ruin a good raw** — bank it first; a degrading
exact-composite is rejected in favor of the raw. Results collection is a GATE, not a promise.
