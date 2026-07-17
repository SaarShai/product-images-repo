# Print-ready transparent illustration pipeline — v1 (validated 2026-07-13)

The once-and-for-all route for high-res RGBA art destined for Illustrator
print layers (colored panels, spot-white underlay). Every stage has a command
and a gate; machine stages are deterministic; human visual acceptance
remains mandatory.

This file covers **Route P (native alpha)** below, then the fully validated
**Route C-green v2** (§ "Route C-green v2"). Canonical sources: full recipe +
rationale live in `skills/transparent-product-image-gen/SKILL.md` (section
"ROUTE C-green v2 — USER-VALIDATED recipe (2026-07-13)"); session evidence,
measured results and failed-approach log live in
`tasks/transparent-bg-endgame/REPORT.md` (§§6-10, esp. §7 "Validated
pipeline"). If this file and those disagree, SKILL.md/REPORT.md win — refresh
this file to match.

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
2. **Decontaminate + binarize + upscale**: `/usr/bin/python3 scripts/decontam_binarize.py
   --rgba raw.png --upscale 4 --erode 1 --out out-print.png`
   (linear-light ridge unmix → donor pad → RGB neural/alpha monotone upscale →
   threshold LAST → signed-distance erode; writes -softalpha.png sidecar).
3. **Gate**: `/usr/bin/python3 scripts/gates/gate_battery.py --rgba out-print.png
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

## Other lanes (evidence-ranked, use when Route P is unavailable/style-mismatched)
1. **Route C-green v2** — for `gpt-image-2` (no native alpha; HTTP 400 on
   `background=transparent`). Not a rejected fallback: round-7 user verdict
   was **"best yet — bank it"**. Full recipe below.
2. gpt-image-1.5 / chatgpt-image-latest native alpha (canary ROUTE_OK; style drift risk — attach style ref).
3. W-white + white_key — ONLY for art without thin/pale features.

## Route C-green v2 — USER-VALIDATED recipe (2026-07-13, rounds 4-7)

**Canonical entry point: `scripts/run_c_green_v2.py` — runs the full recipe
below in TWO blocking phases (prompt assemble → gen → key → decontam →
D5 prechecks → STOP for human sha256 approval, THEN purge → gate →
review-pack) and writes a manifest.json per run. See "D5 blocking contract"
below for the exact two-phase commands.**

Full end-to-end recipe for NEW art from a model that lacks native alpha
(`gpt-image-2`). Iterated over 4 user-feedback rounds; every element exists
because a defect forced it. Canonical detail + rationale:
`skills/transparent-product-image-gen/SKILL.md` (same section title).
Runners: `tasks/transparent-bg-endgame/round7_outline/gen_round7.py` (prompt
blocks importable from rounds 3/4/6 files alongside it).

**7-step pipeline** (`REPORT.md` §7), now split BLOCKING two-phase by
`scripts/run_c_green_v2.py` (see "D5 blocking contract" below — steps 5-6
never run until a human has approved the pre-purge bytes by hash):
1. Compose prompt: SUBJECT + RICH_STYLE + **SIGNIFICANT_CONTOUR_BLOCK**
   (mandatory, non-negotiable framing — "clearly VISIBLE, continuous, fully
   closed dark ink contour, slim, never chunky; lineless edges = wrong
   image"; medium-strength phrasing gets silently dropped) + NO_FILAMENT_BLOCK
   (no hair-thin filament sprays; junctions merge into solid painted joints)
   + NO_GREEN_ART_BLOCK (no bright/pure/saturated green in the subject —
   plants in olive/sage/teal; color alone can't separate green art from
   trapped key) + EXCLUSIONS + `key_bg_block('#00FF00')` (flat key
   background) + HARD_EDGE_BLOCK.
2. Generate: `gpt-image-2` via the **Responses API async job**
   (`background:true`; the sync connection dies ~75s; supplying
   `input_fidelity` returns HTTP 400). Must run with **`/usr/bin/python3`**,
   NOT bare `python3` — PATH python lacks requests/PIL/numpy.
   (`gen_round7.py` — see note below — is historical generation evidence
   only; do not run or edit it for a new product.)
3. `/usr/bin/python3 scripts/chroma_key.py key in.png out.png --json k.json`
4. `/usr/bin/python3 scripts/decontam_binarize.py --rgba out.png --out d.png --bg-color '#00FF00'`
   — **PHASE 1 STOP here.** `d.png` is scored by `d5_preservation.py`'s
   `NO_GREEN_ART` palette precheck and a source→baseline preservation
   precheck; a pre-purge review pack is built; `prepurge_sha256 =
   sha256(d.png)` is recorded; the runner exits `3`. `green_purge.py` is
   never invoked in this phase.
5. **PHASE 2**, only after a human reviews the pack and re-runs with
   `--skip-gen raw.png --approve-prepurge-sha256 <the recorded hash>`
   (the runner recomputes steps 3-4 deterministically and refuses a
   mismatch): `/usr/bin/python3 scripts/green_purge.py d.png p.png --no-green-art --erode 2 --band 6 --json g.json`
   — v3 passes: alpha erode → edge-band green-dominance repaint → (under
   `--no-green-art`: band declamp, global +8 green cap, geometry-restricted
   olive-notch kill via concave-notch morphological-closing mask, dark-khaki
   neutralize) → small-component near-key ΔE00 kill → strong-green speck
   kill (inscribed-radius-protected so sage seaweed survives) → trapped-bg
   removal → converging dulling sweep. **`--no-green-art` is palette-destructive
   BY DESIGN and only correct when the subject truly has no green art** — if
   the subject has essential green/teal content (holly, a teal bauble, a
   green product), pass `--green-art-present` to `run_c_green_v2.py` instead
   of confirming the "no essential green content" eligibility box; never run
   the bare `--no-green-art` default against such a subject (see "Eligibility
   is BINDING" below).
6. `/usr/bin/python3 scripts/gates/gate_battery.py --rgba p.png --source raw.png --bg-color '#00FF00' --d5-baseline d.png --d5-policy no-green-art --d5-analysis-scale 1 --d5-boundary-budget-px 2 --profile print --out-dir gates/`
   — D5 is now BLOCKING (`advisory:false`): any real protected-art deletion
   makes this exit `2`. (`--d5-policy preserve-all` under `--green-art-present`.)
7. Judge crops at **4× LANCZOS AND 12× NEAREST** on junction/notch pixels —
   board-scale and even 4× hide the artifacts the user will find. Show boards
   + fullres in `REVIEW/<task>/`.

### D5 blocking contract (mandatory, 2026-07-16)

`green_purge.py` unconditionally destroys every key-hue pixel — the only
safeguard against silent art loss is a human looking at the pre-purge
raster BEFORE it runs, bound by a SHA-256 the runner refuses to accept a
mismatch on. `scripts/run_c_green_v2.py` enforces this as two phases:

```bash
# Phase 1 — stop, review candidate_N/prepurge_review_pack/
/usr/bin/python3 scripts/run_c_green_v2.py --subject "..." \
  --out-root OUT --eligibility-confirmed --ppi <panel ppi>
# exit 3; manifest.json candidates[0].pipeline.prepurge_sha256 is the hash

# Phase 2 — finalize the EXACT reviewed bytes (never a fresh generation)
/usr/bin/python3 scripts/run_c_green_v2.py --subject "..." \
  --out-root OUT --eligibility-confirmed --ppi <panel ppi> \
  --skip-gen OUT/RUN/candidate_N/raw_N.png \
  --approve-prepurge-sha256 <the recorded prepurge_sha256>
# exit 0 PASS / 3 REVIEW (human approves) / 2 FAIL (mismatch, palette
# violation, or a real D5 protected-art-deletion FAIL)
```

### Eligibility is BINDING: `--green-art-present` (2026-07-17)

The eligibility checklist's "no essential green content?" question used to be
advisory only — nothing enforced the answer, and a subject with real green art
(confirmed anyway) got silently damaged by the default `--no-green-art` purge
(observed-failure: `tasks/transparent-bg-endgame/evidentiary-festive/DIAGNOSIS.md`
finding 3, holly/teal on the festive subject). `run_c_green_v2.py` now takes a
`--green-art-present` flag (in addition to `--eligibility-confirmed`, kept for
backward compat = all-clear):
- **Set** it for any subject with essential green/teal content. This switches
  the runner to preserve-green mode end-to-end: the phase-1 NO_GREEN_ART
  palette precheck is skipped (it would false-positive on legitimate green),
  the source→baseline preservation precheck runs under `preserve-all` policy,
  `green_purge.py` runs WITHOUT `--no-green-art` (only literal near-key pixels
  are removed), and `gate_battery.py` is gated with `--d5-policy preserve-all`
  instead of `no-green-art`.
- **Leave it unset** for subjects with no green content — unchanged
  destructive `--no-green-art` behavior (backward compatible default).
- Both the confirmation and the green-art-present answer are recorded
  unconditionally in `manifest.json["eligibility"]` (forensic record, not
  just when True).
- **Green-art subjects: run BOTH purge modes on the same frozen raw and let
  the human pick** (2026-07-17 festive verdict,
  `tasks/transparent-bg-endgame/evidentiary-festive/VERDICT.md`): destructive
  mode recolored protected green art sub-perceptually (mean Δ11.8 — user
  accepted); preserve mode eroded structure (holly cluster deleted,
  anchor recall 0.758 — user rejected). The trade-off is subject-dependent;
  neither mode is safe to auto-ship on green-art subjects.

`--policy cgreen-v2-print-binary-v1` bundles the print-route contract
(requires `--ppi`, no silent physical-units fallback; `--profile print` +
`--border-policy auto`; D5 `scale=1/budget=2` 1x defaults) into one flag.
Full algorithm, thresholds, and calibration evidence:
`tasks/transparent-bg-endgame/CALIBRATION.md` ("v5 D5 Blocking-Contract
Notes") and `tasks/transparent-bg-endgame/d5-preservation-corpus.json`
(frozen accepted-artifact hashes + scale/boundary metadata). D5's real
implementation is `scripts/gates/d5_preservation.py`; `gate_battery.py`
delegates to it.

**Measured result (round 7):** both candidates PASS all hard gates incl. the
halo gate (H_L 0.0 on r2); band-green contamination collapsed vs round 6
(110/15 px vs 604); 12× nearest-neighbor junction zooms clean. User verdict:
**"best yet — bank it"**.

**Green beats magenta as the key color:** ~2× ΔE separation (11.5 vs 6.8) and
round-4 A/B showed green ≈4× less halo-prone.

**Do not re-try (failed in-session, `REPORT.md` §8):**
- Hue-snap (force edge-band pixels to nearest interior donor hue) — kills
  green but causes visible color banding/saturation damage. Reverted at
  `git checkout 3b0d0c3 -- scripts/green_purge.py`.
- Bbox-fill solidity as the legit-art test — false-fails wavy/thin leaves;
  use max inscribed radius (>=7px at area>=300) instead.
- ML matting (BRIA/BiRefNet) on fine art — deletes the art.
- Prompt-only non-AA edges without an enforced contour — physically
  impossible; models always paint blended boundary pixels.
- Softly-worded outline instruction — model under-paints it; mandatory
  framing is required.

## Open items
- Full 32-gen covering matrix (advisor §3) once user picks style lanes.
- Style-ref-anchored generation (Responses API image input) for collection consistency.
- Spot-white choke plate derivation (erode binary alpha by printer trap; ask print shop for tolerance).
- Composition with geometry/template workflow (region-map + fit gates) — next task.
