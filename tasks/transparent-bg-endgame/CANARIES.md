# Native-alpha canary probes — EMPIRICAL (2026-07-13, run from main session; codex-sandbox rows superseded)

Raw: canary-probes/canaries-empirical.json + canary_*.png (+ *-on-magenta.png visual proofs).
Prompt: coral cluster + edge-hygiene block; 1024x1024, quality=low, background=transparent.

| Probe | Model | HTTP | Alpha | Verdict |
|---|---|---|---|---|
| C1 | gpt-image-1 | 200 | RGBA, 256 uniq, 61.5% zero, 13.4% soft | **ROUTE_OK** (18.1s) |
| C2 | gpt-image-1.5 | 200 | RGBA, 256 uniq, 70.3% zero, 10.0% soft | **ROUTE_OK** (13.8s) |
| C3 | chatgpt-image-latest | 200 | RGBA, 256 uniq, 68.8% zero, 11.4% soft | **ROUTE_OK** (18.8s) |
| C4 | gpt-image-2 | 400 | — "Transparent background is not supported for this model." | ROUTE_UNAVAILABLE (re-confirmed) |
| C5 | fal flux-2-pro / flux-2-flex | schema | no transparent/alpha/background param in schemas | ROUTE_UNAVAILABLE (doc-level; no paid probe) |

Visual verification (Fable, magenta composite): all three OK routes cut cleanly —
the painted background AND the RGB glow around subjects sit entirely under
alpha==0; no white rim visible at 1:1. RGB-under-alpha contains a full painted
scene (expected; irrelevant once composited, but forbids using raw RGB without
alpha downstream).

Matrix consequence: route F (Flux.2) → replaced by **O2 = chatgpt-image-latest**
(image-2-family quality with true alpha). Routes for round 1: O1=gpt-image-1,
O2=chatgpt-image-latest, C=#00FF00+chroma_key, W=white+white_key+dehalo_edge.
gpt-image-1.5 = spare native route if O1/O2 misbehave at high quality.
