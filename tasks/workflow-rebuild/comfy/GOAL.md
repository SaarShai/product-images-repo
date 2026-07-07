# GOAL — ComfyUI workflow lane (2026-07-06)

User directive: develop ComfyUI workflows and TEST them against our requirements —
geometry adherence, style fidelity, details+placement. Vary models, prompts, inputs
(reference images, SVG-derived maps), workflows. Use W1 research; research more as needed.

Baseline to beat/complement: round-3 gpt-image (door_fill 0.958–0.997; user: arm-g_s1
best geometry). ComfyUI value-add = HARD conditioning gpt-image can't do: per-ref
weights, dual ControlNet, regional attention masks.

## Lanes
- C1 bring-up: models via symlink-from-HF-cache first, download only missing;
  server boots headless; smoke render PASS.
- C2 workflow suite: API-format graph builders — (a) geometry-only CN sweep,
  (b) style-only IPAdapter, (c) combined dual-CN+IPAdapter, (d) regional attn-mask
  (door portal) detail placement.
- C3 research: current node names/params (IPAdapterAdvanced, attn_mask,
  controlnet_aux preprocessors), MPS flags, missing-model URLs.
- C4 (parallel, unrelated): fix 3 round_runner gate bugs (ledger S150), re-gate round-3.

## Test matrix (after C1+C2)
Door panel contract v3 (832×1184 gen frame, aspect 0.705). Axes:
CN strength {0.6, 0.8, 1.0} × CN set {lineart, lineart+depth} × IPAdapter weight
{0.5, 0.8} × regional mask {off, door-portal}. Gates: door_fill_gate + overlay
(LAW: overlay-only geometry verdicts) + VLM content judge. Board → user.

## Done means
1. Server renders our door panel from SVG-derived control map.
2. ≥1 board comparing ComfyUI arms vs round-3 baseline, overlay row included.
3. Measured verdict: where ComfyUI beats gpt-image (geometry lock, detail placement), where it loses (style).
