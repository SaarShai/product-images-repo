# OpenAI Images API — background=transparent viability probe (image14)

Source image: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png` (941×1672 RGB)

Raw outputs + `metrics.json`: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/bg-gen-api-v1/image14/`

## Probe results

### P1 — images/edits (reproduce existing illustration on transparent bg)
- **Params (as-run):** `model=gpt-image-1`, `background=transparent`, `size=1024x1536`, `quality=medium` (see caveat below), `n=1` × 2 calls, no `input_fidelity`.
- **input_fidelity=high REJECTED de facto:** reproducibly caused `RemoteDisconnected` after exactly ~61.2s on this source image, confirmed across 5 attempts (n=1 and n=2, with and without fidelity). This is a hard server-side ceiling, not a client timeout (client timeout was set to 280-300s).
- **quality=high ALSO fails on this large edit path:** same ~61s RemoteDisconnected, reproducible 3/3 attempts even without `input_fidelity`. Only `quality=medium` completed reliably (34.6s and 58.7s).
- [P1_edit_quality-medium_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P1_edit_quality-medium_out1.png) — RGBA, alpha: 48.55% transparent / 18.51% opaque / 32.94% semi. Bubble survival 6/7. Composition mean-abs-diff-RGB over opaque = 44.3 (source vs regen).
- [P1_edit_quality-medium_out2.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P1_edit_quality-medium_out2.png) — RGBA, alpha: 49.79% / 16.89% / 33.32%. Bubble survival 5/7. Composition MAD = 46.0.
- [P1_edit_quality-medium_out1_diffheat.png](P1_edit_quality-medium_out1_diffheat.png) — per-pixel diff heatmap vs source.
- Edge crops (4x zoom, on white/gray/black/magenta): `P1_edit_quality-medium_out{1,2}_edge-{bubble,coral_tip,fish_outline}_on-{white,gray,black,magenta}.png`
- **Cost:** out1 usage `{input_tokens:371 (image:323,text:48), output_tokens:1584, total:1955}`; out2 same shape.

### P2 — images/generations (net-new watercolor motif, baseline prompt)
- **Params:** `model=gpt-image-1`, `background=transparent`, `size=1024x1536`, `quality=high`, `n=2` (single call, 57.1s, succeeded — generate path does NOT hit the edit-endpoint timeout).
- [P2_generate_quality-high_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P2_generate_quality-high_out1.png) — RGBA, alpha 40.98%/28.71%/30.32%. Closed-shape: 79 stray enclosed background pockets trapped in foreground (mostly 3-24px noise, one 1417px), i.e. noisy/imperfect alpha boundary.
- [P2_generate_quality-high_out2.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P2_generate_quality-high_out2.png) — RGBA, alpha 47.85%(bg calc)/... 169 stray pockets.
- Edge crops: `P2_generate_quality-high_out{1,2}_edge-{bubble,coral_tip,fish_outline}_on-{white,gray,black,magenta}.png`
- **Cost:** usage `{input_tokens:48, output_tokens:12480 (2 images), total:12528}`.

### P2b — images/generations + edge-hygiene instructions, transparent bg (coordinator follow-up)
- **Params:** same as P2 plus prompt suffix demanding closed outlines/crisp edges/no broken contours. `n=1`, 58.3s.
- [P2b_generate_edgehygiene-transparent_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P2b_generate_edgehygiene-transparent_out1.png) — RGBA, alpha 76.05%/14.65%/9.29%. **Closed-shape: only 1 enclosed pocket, area=1px** — essentially perfectly clean alpha boundary vs P2 baseline's 79-169 stray pockets. Strong evidence the edge-hygiene prompt materially cleans up the mask.
- Edge crops: `P2b_generate_edgehygiene-transparent_out1_edge-{bubble,coral_tip,fish_outline}_on-{white,gray,black,magenta}.png`
- **Cost:** usage `{input_tokens:62, output_tokens:6240, total:6302}`.

### P2c — images/generations + edge-hygiene + pure-green keyable background (coordinator follow-up)
- **Params:** same motif+hygiene prompt plus explicit "pure green #00FF00, no gradient/texture/spill" instruction, `background=opaque` (not transparent — normal RGB), `n=1`, 48.5s.
- [P2c_generate_edgehygiene-greenscreen_out1.png](file:///Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My%20Drive/Wanderland%20Folder/Files/Products/Screenery/production%20files/double%20Marine%20Bed%20Wrapper/images/Images/candidates/bg-gen-api-v1/image14/P2c_generate_edgehygiene-greenscreen_out1.png) — RGB, no alpha (as expected for opaque).
- **Chroma-key (Lab ΔE, true CIE76):**
  - `% pixels ΔE<5 vs pure #00FF00 = 0.0%` — the model NEVER renders colorimetrically-pure green; actual background color sampled ≈ RGB(14,208,60), a slightly muted/darker green, watercolor-textured, not a flat digital green-screen value.
  - At a practical keying tolerance (ΔE<60), 76.92% of pixels key as background.
  - Boundary-band green-spill (3px ring inside subject edge): 28.45% green-contaminated — non-trivial spill, a naive key+simple-despill is not clean out of the box.
  - Closed-shape (at ΔE<60 mask): 0 enclosed pockets, fully single background region — topologically the cleanest of all 4 arms (no scattered background islands trapped in the subject).
- [P2c_generate_edgehygiene-greenscreen_out1_keyed-decontam.png](P2c_generate_edgehygiene-greenscreen_out1_keyed-decontam.png) — my own simple chroma-key + despill composite for visual review (uses ΔE<60 mask + green-channel clamp in spill zone). Visually: solid green fill, turtle subject intact, but this is NOT a real production-quality key (see caveats).
- **Cost:** usage `{input_tokens:103, output_tokens:6240, total:6343}`.

## Deterministic finding: images/edits timeout ceiling
Isolated via binary search on parameters (see call sequence): `images/edits` with this ~2MB, 941×1672 source image reliably drops the connection (`RemoteDisconnected`, not a client timeout) at **exactly ~61.2s**, regardless of `input_fidelity` or `n`. `quality=medium` (34-59s) succeeds; `quality=high` and `input_fidelity=high` (both push render time over the ceiling) fail every time tested (5+ trials, 100% failure rate at those settings). This looks like an infrastructure-level idle/response timeout on OpenAI's edge for this endpoint+payload combination, not a documented API limit. `images/generations` (no file upload) does NOT hit this ceiling even at `quality=high`+`n=2` (57s, succeeded).

## Recommendation
**Viable-with-caveats**, split by route:
1. **P1 (reproduce existing art on transparent bg via images/edits):** works only at `quality=medium`; `quality=high`/`input_fidelity=high` are unusable on this file size/dimensions (reliable server timeout). Even at medium quality, composition fidelity is loose (mean-abs-diff ~44-46 over opaque region — this is a *regeneration*, not a pixel-preserving cutout) and bubble survival is inconsistent (5-6 of 7 known small bubbles retained, not deterministic across the two samples). Not a drop-in replacement for a real background-removal pipeline; usable only if some redraw/reinterpretation of the source art is acceptable.
2. **P2 (net-new generation, baseline prompt):** RGBA/alpha is real and meaningful, but the raw alpha boundary is noisy (dozens of stray sub-pixel-scale trapped background islands) — needs cleanup before use.
3. **P2b (net-new + edge-hygiene prompt, transparent):** the edge-hygiene instruction is the single biggest lever tested — cut stray alpha-pocket count from ~79-169 down to ~1. This is the strongest finding of the whole probe: **prompt-time edge-hygiene language substantially improves usable alpha quality for future net-new generations**, worth adopting as a standing prompt addition.
4. **P2c (net-new + edge-hygiene + green-screen, opaque):** does not deliver a colorimetrically pure key color (0% ΔE<5) and has real spill (28.45% in the boundary band) — the green-screen route is not "trivial to remove" out of the box; it needs a real despill/key algorithm (not a flat one-shot mask), though its background topology (single connected region, 0 trapped pockets) is the cleanest of the four arms, which does make a *proper* chroma-key pipeline's job easier than working from a photoreal/complex scene.

Net: the API path is real (unlike the subscription/ChatGPT path's fake checkerboard) and does produce genuine alpha, but every arm has a real caveat (timeout ceiling on edits at high quality, fidelity loss on reproduction, noisy default alpha, imperfect green purity/spill on green-screen). The one clearly transferable, low-risk win is **P2b's edge-hygiene prompt language** for any future net-new transparent generation.
