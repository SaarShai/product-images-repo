# Print-ready transparent illustration pipeline — v1 (validated 2026-07-13)

The once-and-for-all route for high-res RGBA art destined for Illustrator
print layers (colored panels, spot-white underlay). Every stage has a command
and a gate; a weak agent can run it end-to-end without visual judgment.

## Loop shape (loop-engineering contract)
- Generator: gpt-image-1 `background=transparent` (route O1).
- Verifier (SEPARATE): `scripts/gates/gate_battery.py` (v3, tri-state).
- Gate: `--profile print` → PASS ships to human; REVIEW → human eyes; FAIL → regen.
- Stop: N_pass reached or budget cap (default 4 gens per asset; measured yield ≈ 1/3 auto-PASS).
- Budget cap: hard, enforced in runner.

## Stages
1. **Generate** (native alpha; NO keying, NO matting — those routes measurably
   eat thin art or leave residue):
   `POST /v1/images/generations {model: gpt-image-1, background: transparent, quality: high, size: 1024x1536}`
   Prompt = R4 recipe blocks + ANTI-AURA tail + ANTI-GROUND + ANTI-BACKDROP
   clauses (templates: `tasks/transparent-bg-endgame/round2_yield/prompts/`).
   Pixel-verify alpha immediately (histogram nonconstant).
2. **Decontaminate + binarize + upscale**: `python3 scripts/decontam_binarize.py
   --rgba raw.png --upscale 4 --erode 1 --out out-print.png`
   (linear-light ridge unmix → donor pad → RGB neural/alpha monotone upscale →
   threshold LAST → signed-distance erode; writes -softalpha.png sidecar).
3. **Gate**: `python3 scripts/gates/gate_battery.py --rgba out-print.png
   --profile print --border-policy auto --ppi <panel ppi> --out-dir gates/`
   Exit 0 = ship to human; 3 = human review with crops; 2 = discard/regen.
4. **Human sign-off** on dark composite (#111) + panel color. Machine pass is
   never final (standing rule).
5. **Deliver** to `<production folder>/Images/candidates/` → user promotes to
   `Images/finals/` (never auto-promote).

## Measured evidence (this session)
- Round 1 (8 gens, 4 routes × AA/HARD): W route shreds thin strokes
  (white-key flood-fill); C route (green key) clean but saturation drift;
  O2 (chatgpt-image-latest) clean alpha but style drift; O1 best style+cut.
- Round 1.5/2 (11 O1 gens): 3/9 processed candidates auto-PASS all print
  gates; residual defect class = stochastic painted pale patches (backdrop
  wedge / ground blob) — content defects, correctly caught by donor-referenced
  D1; replicate-and-reject handles them.
- Binary alpha (soft_px=0) confirmed on all processed outputs; no halo ring
  visible over #111 in any processed candidate (Fable visual + D1 agree).
- Advisor corrections adopted: threshold LAST, ridge unmix F=(a²F0+λD)/(a²+λ),
  soft-alpha sidecar retained for wash-layer option.

## Fallback lanes (evidence-ranked, use when O1 unavailable/style-mismatched)
1. C-green: gpt-image-2 on #00FF00 → chroma_key DE_OPAQUE=11 → decontam_binarize.
2. gpt-image-1.5 / chatgpt-image-latest native alpha (canary ROUTE_OK; style drift risk — attach style ref).
3. W-white + white_key — ONLY for art without thin/pale features.

## Open items
- Full 32-gen covering matrix (advisor §3) once user picks style lanes.
- Style-ref-anchored generation (Responses API image input) for collection consistency.
- Spot-white choke plate derivation (erode binary alpha by printer trap; ask print shop for tolerance).
- Composition with geometry/template workflow (region-map + fit gates) — next task.
