# FROZEN parameter card — experiment-1 (reconciled Sol + Kimi, 2026-07-17)

Sources: sol-hyperparams.md, kimi-hyperparams.md. Where they disagreed, the
choice + reason is noted. Frozen before first gen; changes require a new card.

## Ruling (CORRECTED 2026-07-17, builder-measured): socket = raster placement; st1 = top contour
Builder measurement (overlap area 0, verified by overlay review): st1 bbox
(103,105 -> 1747,759) is the TOP ARCH/DOME contour edge; the embedded door
raster sits at (122.83,1572.21 -> 875.37,2378.14). The DIAGNOSIS label "door
zone (st1)" misattributed the id; Kimi's "carve st1" read was also wrong (it
would remove the dome). FROZEN: socket mask = raster placement rect (excluded
from paintable both arms, neutral fill in init canvas, composite-back Stage C);
st1 contributes to silhouette/lineart ONLY. Holes for arm policy = st4 x2
slivers + st2 x2 bars. st3 fold band + st0 bottom rect = keep-clear
(paintable, clearance-gated, never in hole masks). Supersedes the earlier
"st1 is the SOCKET" ruling in this file's history.

## Card

| knob | value | source |
|---|---|---|
| canvas | 640x1544 portrait (aspect-exact round8 of body 1644.10x3981.68; bucket-native 640x1536+8) | Kimi (Sol's 704x1472 pad rejected: aspect fidelity beats width; matches measure tooling mapping) |
| orientation | portrait, no rotation | both |
| controlnet_conditioning_scale | 0.7 | Kimi (+0.1 over 0.6 precedent to resist IP+LoRA; Sol 0.65 close) |
| control_guidance start/end | 0.0 / 0.8 | Kimi (release last 20% for texture; edges committed by ~70%) |
| control stroke | 3 px bold / 1 px faint (scaled for 640) | Kimi |
| IP-Adapter | plus ViT-H, BOTH refs as multi-ref input, STYLE-LAYER-ONLY routing ("up" block_0) scale 0.55 | Sol routing (mechanically blocks layout copy) + Kimi multi-ref; refs center-cropped square, NEVER stretched (Kimi fix) |
| IP fallback | if layout copying appears in first 2 gens: single ref (princess style 01), same routing, scale unchanged | Kimi |
| lora_scale (fused) | 0.75 | midpoint of Sol 0.70 / Kimi 0.80; both argued vs 0.9 default |
| guidance | 5.5 | Kimi (checkpoint-specific waxiness claim); Sol 5.0 close |
| steps Stage A | 30 | Kimi (converged by ~28); Sol 35 |
| strength Stage A | 1.0 | Kimi (white-init contamination < 1.0); Sol 0.99 |
| mask feather | 0 px (NEAREST binary resize) | both |
| seeds | 7 and 21, SAME PAIR in both arms (paired comparison) | Kimi values, Sol pairing principle |
| Stage B | same checkpoint, same StableDiffusionXLControlNetInpaintPipeline, image=Stage-A out, same mask/conditioning/seed; strength 0.35 and 0.50, steps 50 | both (Sol: 9-channel UNet forbids plain img2img pipeline; Kimi concurs) |
| dtype | fp16 everywhere + VAE forced fp32 before decode | Kimi (failure layer is VAE; fp32-everywhere wastes memory) |
| memory | attention_slicing ON, vae_slicing ON, vae_tiling OFF, batch 1, no xformers | union |
| env | PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0; no silent MPS-fallback env | Kimi |
| generator | torch.Generator("cpu").manual_seed | both |
| load order | LoRA -> fuse_lora(0.75) -> load_ip_adapter -> set_ip_adapter_scale(routing dict) | Kimi |
| hard white composite outside contour | ON in both arms (outside-contour pin); holes composite per arm policy | Kimi mechanics |

## Prompt (verbatim, all gens)

Positive:
watercolor children's book illustration of a fairytale princess castle,
soft pastel washes on textured paper, gentle ink outlines, tall narrow
vertical composition, airy, delicate, hand-painted

Negative:
photo, realistic, 3d render, glossy, text, words, signage, watermark, frame,
border, clutter, people, oversaturated, heavy black outlines, vector, flat
color blocks, sideways architecture, cropped main towers, floating fragments,
duplicated buildings

(Kimi minimal prompt chosen — prompt is deliberately the weakest conditioner;
Sol's truncation negatives appended. No geometry/production words — geometry
belongs to mask + CN only.)

## Arms

- A-P1 seeds 7,21: paintable = body − holes(st4x2,st2x2) − socket(st1)
- A-P2 seeds 7,21: paintable = body − socket(st1)  [holes painted over, punched Stage C]
- B on best base: strength 0.35, 0.50
- Stage C on all: silhouette re-mask -> punch holes -> door composite-back -> gates

## Required code adaptations before gen (localgen.py-shaped entry)

1. Shared aspect-preserving transform — no input stretching (both advisors).
2. Multi-ref IP input + style-layer routing dict; refs center-crop square, native res.
3. Hard white composite of outside-contour (and holes in P1) from
   controlnet_sdxl_gen.py mechanics.
4. VAE fp32 cast + slicing settings + watermark env.
5. control_guidance_end=0.8 plumb-through.

## Amendment 1 (pre-run, advisor-adopted): socket exclusion = arch alpha footprint +1px

Adopted before any scored gen. Advisor verdict (Sol): the socket exclusion
must be ARCH-SHAPED, not the full raster placement rect. Rect-masked gen
pins the neutral init fill into the raster's white-background corners,
which later reads as a pasted beige card regardless of Stage-C policy.

Frozen matte: `scripts/build_socket_matte.py` alpha-keys ONLY the
border-connected near-white background of `assets/door_socket.png` (flood
from image borders, thresh=246, sat=18, erode=0, feather~0.8px, no interior
reopening; RGB bytes byte-preserved) -> `assets/door_socket_rgba.png`
(canonical, resolution-independent; copied into each `--outdir`).
`build_assets.py`'s `build_socket_arch_mask()` projects that matte's alpha
footprint through the shared placement transform onto the working
resolution (NEAREST resize, strictly binary) and dilates +1px ->
`socket_mask.png` / paintable_P1 / paintable_P2 exclusion (replacing the
earlier full-rect exclusion). `init_canvas.png` neutral-fills ONLY inside
the arch footprint (rect corners are real paintable wall). `control_canny.png`
draws the arch outline (matte alpha edge) as a bold stroke instead of the
rect boundary, so the model paints an intentional frame around it.
`composite_back.py` composites the frozen RGBA (alpha-over) back at that
footprint instead of an opaque rect paste.

## Amendment 2 (pre-run, 2nd advisor, independent confirmation): matte audit + gate refinements

Confirms Amendment 1; tightens (never weakens) the matte/gates:

1. Matte keying reuses white_key.py conventions (thresh=246, sat=18,
   erode=0, feather~0.8, no interior reopening — see Amendment 1) plus an
   over-removal AUDIT: a conservative GLOBAL (non-flood) foreground test at
   a looser threshold (~235) flags any pixel unambiguously colored/non-white;
   any such pixel the flood matte removed must sit within 2px of the matte's
   background boundary (AA fringe only, never a deep interior chunk) and the
   total count must stay under a 500px budget. Asserted in code
   (`build_socket_matte.py`); measured result: 0 over-removed px, 0 deep
   violations (audit passed with maximum margin).
2. Byte-exact gate zoning (`composite_back.py` `socket_gates`): alpha=255
   pixels byte-exact vs the resized matte; the feather ring (0<alpha<255)
   must equal the deterministic alpha-blend expectation (computed and
   diffed, not left unchecked); alpha=0 unconstrained. NOTE: this surfaced
   a real compositing bug during implementation — PIL's
   `.paste(im, box, mask=im_alpha)` onto a transparent canvas followed by
   `alpha_composite` double-applies the alpha weight at partial-alpha
   pixels (max delta 47/255 at the ring). Fixed by a single direct numpy
   "over" blend; gate now passes exactly (max delta 0).
3. Registration gate replaced bbox-corner offset with boundary-distance
   registration (max symmetric boundary offset between the expected arch
   footprint and the candidate's actual untouched neutral region) <= 1.5px
   AND footprint area ratio within +/-2%. Fail-but-write (exit 3) preserved;
   the shifted-fixture FAIL test (`test_composite_back.py`) updated to shift
   the ARCH mask (not a synthetic rect) — both tests re-pass (`pytest -v`:
   2 passed).
4. NEW corner-integration gate (`corner_integration` in metrics.json): in
   the (old placement-rect minus arch) corner/margin zone, >=95% of pixels
   must be non-neutral painted (not within ~10 RGB of the neutral fill
   222,213,199, not near-white) — proves the wall was painted up to the arch
   as a design feature. Reported per candidate; informational (not a hard
   process-exit gate — only registration hard-blocks, per the original
   "explicit registration/offset check" design).

## Amendment 3 (post-gen, detection-only recalibration; gate thresholds unchanged)

Problem found on real MPS SDXL-inpaint gens (`runs/A-P{1,2}-s{7,21}/gen.png`,
Stage A, the first real generation output run against this pipeline):
`composite_back.py`'s registration gate depends on locating the candidate's
actual (untouched) neutral socket fill, and the original detector matched
absolute RGB against the fixed `--init-fill` (222,213,199) with a tight
tolerance. Real generations keep the socket region's *shape* untouched (it's
excluded from the paintable mask) but the VAE encode/decode roundtrip tints
its RGB uniformly — measured on all 4 real gens:

| gen | mean RGB | max per-channel drift from init-fill | internal std |
|---|---|---|---|
| A-P1-s7 | (158.8, 145.3, 135.8) | 67.7 | 4.3–4.7 |
| A-P1-s21 | (152.3, 142.6, 130.4) | 70.4 | 7.4–8.1 |
| A-P2-s7 | (160.5, 147.6, 138.2) | 65.4 | 4.0–4.5 |
| A-P2-s21 | (152.5, 143.2, 131.2) | 69.8 | 8.3–8.9 |

Absolute-RGB matching against the fixed init-fill therefore matched nothing
on any of the 4 (registration exit 3, "no_neutral_region_found") even though
the region was genuinely untouched — the reported bug. Chosen tolerance
margin: the fix's detector no longer compares against `--init-fill` at all
(see below), so this drift magnitude only needed to be *understood*, not
budgeted for directly.

**Fix — two-stage, position-honest detection** (`actual_neutral_region()` in
`composite_back.py`, full rationale in its docstring and the module's
`NEUTRAL_*` constants):

1. **Stage 1 (position, shift-safe):** find the largest LOW-TEXTURE (local
   pixel std ≤6 over a 3×3 window) connected blob within a 60px neighborhood
   of the expected arch mask's bbox, scored by IoU against the expected mask
   (floor 0.3) — texture-based, so it needs no color assumption and naturally
   separates the kept region from adjacent differently-colored painted
   content (a real color edge shows up as a local-variance spike).
2. **Stage 2 (precision refine):** sample the reference color from the
   eroded core (3px) of stage 1's own blob and refine within a 1px dilation
   of that SAME blob (color tolerance 30, then a 3px morphological close) —
   recovers the few px stage 1's texture threshold misses right at the
   model's bold outline stroke (Amendment 1's control_canny convention draws
   one directly on the arch boundary).

Critically, **neither stage ever samples color from, or bounds its search by,
the *expected* mask's own location** — only stage 1's IoU scoring references
it, purely to pick among discovered blobs, never to relocate one. An earlier,
simpler version of this fix *did* sample the reference color from an eroded
core of the expected mask itself and search only a tight dilation of it; that
version self-referentially "found" whatever solid color happened to sit at
the expected location, including — in calibration — the plain painted body
fill left behind at the *original* location after a synthetic 15px shift,
because that background color coincidentally fell within its (generous, 70)
color tolerance. It silently PASSED
`test_shifted_tinted_socket_fails_registration`, a real gate-weakening
regression. Caught before shipping by testing shift+tint fixtures together
(requirement 2 below), not shipped.

**Verification (`test_composite_back.py`, `pytest -v`: 8 passed):**
- `test_aligned_socket_passes_registration` / `test_shifted_socket_fails_registration` (pre-existing, untinted) — still pass.
- `test_aligned_tinted_socket_passes_registration` (NEW: exact placement, −70/255 uniform socket-fill tint, sharp synthetic edges) — PASSES registration (offset 1.0px, area_ratio 1.0103).
- `test_shifted_tinted_socket_fails_registration` (NEW: SAME −70/255 tint, 15px shift) — FAILS registration (offset 21.9px ≥ 14).
- `test_real_gen_socket_and_corner_gates` (NEW, parametrized over all 4 real gens) — `socket_gates` byte-exact, `corner_integration` ≥99.99% pass, registration genuinely COMPUTED (no longer `no_neutral_region_found`), `area_ratio` 0.989–0.993 (well inside ±2%).

**Open finding, not silently forced to pass:** on all 4 real gens,
`max_boundary_offset_px` measures 3.0–3.16px — computed by the verified
shift-safe detector above, i.e. not a detection artifact — consistently
*above* the unchanged `--reg-tol=1.5` default. This reflects genuine ~3px
edge softening in real SDXL-inpaint output at the mask boundary (VAE-latent
granularity / anti-aliasing), which `reg_tol=1.5` — calibrated only against
synthetic sharp-edge fixtures — was never validated against. `composite_back`
therefore still exits 3 ("registration: fail") on all 4 real gens even after
this fix; `socket_gates` and `corner_integration` pass on all 4. Whether
`reg_tol` itself should be recalibrated for real diffusion output is an open
question outside this fix's "detection-only, thresholds unchanged" scope —
deliberately left for separate review rather than silently loosened here.

## Amendment 4 (round 2, both advisors converged): composition map from outset-c1

Round-1 result: geometry 100% green all 4 gens; content collapsed to washes
(contour-only lineart gave no interior scaffold). Pre-registered rule fired:
revise the composition map. Round 2, frozen before any round-2 gen:
- Interior lineart = SELECTIVE canny trace of the frozen frontier exemplar
  outset-c1 raw.png (structural edges only: tower silhouettes, roofs, window
  rows, gate; NO texture/foliage/speckle edges), registered per-axis
  (sx~0.833, sy~1.122, corner-to-corner) into the 640x1544 body, clipped by
  paintable_P1 dilated -2px (erases strokes in holes/socket/keep-clear by
  construction), then authoritative SVG strokes re-added on top.
- Conditioning retune (inseparable from denser map; emboss already observed
  at sparse 0.7/0.8 on seed 21): controlnet_conditioning_scale 0.55,
  control_guidance 0.0->0.65, interior strokes 2px, boundary/arch strokes 4px.
- Everything else UNCHANGED (prompt card-verbatim — verified the scored runs
  used it, the "cottage" file was a never-read stray; IP 0.55 style-layer-only;
  LoRA 0.75; guidance 5.5; steps 30; strength 1.0).
- Matrix: P1 only, seeds 7 and 21 (2 gens). P2 deferred to post-Stage-C-fix.
- Claim ceiling: proves/disproves "exemplar-conditioned composition inside
  exact geometry" — NOT composition generalization (later round, procedural map).
- Escalation lever if emboss persists at 0.55: dual ControlNet (geometry 0.8 +
  composition 0.45), not further global cuts.

## Amendment 5 (registration gate redesign per advisor consult, kimi-reggate.md)

Amendment 3's open finding (measured 3.0–3.16px real-gen noise floor, `reg_tol`
1.5 impossible to clear) plus a NEW finding on Stage B: the appearance
detector 100%-false-positives on painterly candidates — flat washes merge
into the low-texture blob it keys on (offsets ~120px, area_ratio 1.84–1.99 on
both B-s21-d035 and B-s21-d050) — while `socket_gates`/`corner_integration`
pass on both. Consulted kimi-reggate.md: the paste is already deterministic
(`rasterize_geometry()` re-derives `socket_rect_px` from the frozen SVG at
compose time; `composite_socket_arch()` blends at exactly that rect), so
appearance detection carries no information about WHERE the paste landed —
only about candidate drift `corner_integration` already bounds.
- **Registration REDESIGNED**: PRIMARY (hard) gate is now
  transform-provenance (`registration_provenance()` /
  `independent_provenance_rect_px()`) — re-derive the socket footprint px
  rect via a genuinely separate code path (parse
  `assets-dir/door_socket_placement.json`'s `placement_svg_units` +
  `assets-dir/transform.json`'s `src_rect_svg_units` directly, reapply the
  `px=(svg-min)*scale` formula, WITHOUT calling
  `BA.rasterize_geometry`/`BA.compute_src_rect`/`BA.extract_door_raster`),
  assert it matches the compositor's own footprint within 0.5px, PLUS assert
  `door_socket_rgba.png`'s sha256 against `assets-dir/provenance.json`
  (bootstrapped on first run if absent). Exit `REG_FAIL_EXIT` (3) on either
  mismatch.
- **Appearance detection DEMOTED to advisory**: `arch_registration()` /
  `actual_neutral_region()` mechanism UNCHANGED; status renamed
  `advisory_pass`/`advisory_anomalous`/`no_neutral_region_found`, reported in
  `metrics.json` under `registration_appearance_advisory`, but NEVER sets the
  exit code. `--reg-tol` default widened 1.5 → 5.0px (58% headroom over the
  measured 3.0–3.16px real-gen floor); `area_ratio` tolerance unchanged
  ±2%.
- **Junction crop, every run**: `<out stem>-junction.png` — tight
  bounding-box crop of `final.png` around the composited arch footprint's
  boundary ring, ±8px — for human review.
- **Paste-measuring gates unchanged**: socket byte-exact interior delta=0,
  feather-ring deterministic-blend-exact, alpha==frozen matte,
  `corner_integration` ≥95% painted — all untouched by this amendment.
- **Verification**: extended `test_composite_back.py` (13 tests, all
  passing) — provenance-pass; provenance-fail on a tampered footprint (copy
  of assets dir with `placement_svg_units` shifted +50 SVG units, compositor's
  own paste unaffected since it never reads that JSON, independent
  re-derivation reads the tampered numbers and disagrees by ≫0.5px, exit 3);
  6px-shifted synthetic fixture reads `advisory_anomalous` at the new 5.0px
  tol; the existing 15px-shifted and tinted fixtures reads
  `advisory_anomalous`/`advisory_pass` as appropriate (no longer affecting
  exit code); then `composite_back.py` on all 6 real candidates (4 Stage-A +
  2 Stage-B) against `assets-640` — exit 0 on all six:

  | candidate | provenance | socket_byte_exact | corner_pct | appearance_advisory |
  |---|---|---|---|---|
  | A-P1-s7 | pass | True | 100.0% | advisory_pass (offset 3.0px) |
  | A-P1-s21 | pass | True | 100.0% | advisory_pass (offset 3.0px) |
  | A-P2-s7 | pass | True | 99.995% | advisory_pass (offset 3.162px) |
  | A-P2-s21 | pass | True | 100.0% | advisory_pass (offset 3.0px) |
  | B-s21-d035 | pass | True | 99.986% | advisory_anomalous (offset 120.42px) |
  | B-s21-d050 | pass | True | 99.986% | advisory_anomalous (offset 123.81px) |

  Confirms the redesign's premise: provenance + paste gates pass on every
  candidate regardless of appearance-detector class-level failure on Stage B.
