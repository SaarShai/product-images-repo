# PLAN — Complete background-removal solution (watercolor marine)

**Owner session:** Codex `019f4a2d-67ad-76b0-aba3-7505d726fe0a` (2026-07-09)
**Prior sessions:** Codex `019f3ff9-633f-7070-8375-c024d7ec63de`; Claude `7fcedd84-88fa-4283-bfbd-6b6c9fad16e5`; Cursor `1cdff87a-6bce-4c6c-b787-182390e01c23`

## GOAL (end-to-end)

Produce a **complete, reusable procedure** that removes white/near-white backgrounds from watercolor marine illustrations such that:

1. **No white fringe** at edges (correct straight alpha and decontaminated foreground RGB; boundary ring not paper-white on any review background).
2. **No wrong cutouts** — pale coral/sand/wash that is paint stays opaque.
3. **Enclosed background holes** (true paper pockets between branches) stay transparent.
4. The workflow makes unavoidable ambiguity explicit: automatic regions are processed unattended, while genuinely ambiguous regions are surfaced for minimal sure-FG/sure-BG input rather than guessed.
5. Procedure is verified on hard cases (image14, image15, plus ≥1 easy control), then the full folder, and documented so a future agent can re-run it without rediscovery.

## WHAT / WHY

- **User-visible outcome:** Correct transparent PNGs + a written SOP that clears all three defect classes.
- **Scope:** Background removal method (mask + post) plus alpha-safe x8 export.
  RealESRGAN processes decontaminated straight RGB only; alpha is independently
  resampled and recombined, never inferred from a temporary plate.
- **Non-goals:** Re-drawing or silently changing source art; claiming a universal one-click pixel classifier where source pixels contain no separating information.
- **Assumptions:** Sources live under Drive `double Marine Bed Wrapper/images`; judge only at native/full-res crops. Correct straight/soft alpha plus foreground-color decontamination is the default edge model; binary export is optional and must clear its own edge gate.

## Testable requirements

| ID | Requirement | How verified |
|----|-------------|--------------|
| R1 | Sources are byte-unchanged; dimensions/scales are intentional | source hashes + dim manifest |
| R2 | Candidate alpha is valid straight alpha; optional binary mode is explicit | histogram + compositing invariance tests |
| R3 | Pale paint is not deleted | independent hand-labelled sure-FG guard masks/points; every guard must remain foreground |
| R4 | True exterior and enclosed paper is removed | independent sure-BG guards, including enclosed holes; every guard must become background |
| R5 | No white/matte fringe on the expected edge | foreground-color contamination metric plus native crops on gray, black, magenta, and white |
| R6 | Works on image14, image15, sample08, then every source in the folder | per-image manifest, uncertainty report, full-resolution vision/user gate |

## done means:

1. A runnable, resumable workflow processes image14/15/08 and the full folder, accepts absolute-precedence FG/BG annotations, and writes only under product `Images/candidates/` and `Images/finals/`.
2. Independent gold guards and negative fixtures prove that all three original failure classes trip the gate; R1–R5 then PASS on the hard set without weakening thresholds.
3. Every source receives a manifest verdict; uncertain regions are enumerated and resolved rather than silently guessed, and no source file changes.
4. Native-resolution review on gray/black/magenta/white is accepted by the user and a cold verifier for the hard set and every flagged full-folder case.
5. The verified SOP, exact commands, limitations, and evidence are banked; scoped changes are committed only after these gates pass.

## Known from prior work (do not rediscover blindly)

- Fusion v1 = FloodFG ∧ BRIA restore — fixed gross overcuts; **user FAIL** on image14 ultra-pale ghosts + residual fringe.
- v2 **specced, never run**: chroma≤5 flood, restore chroma>4, adaptive erode, corner paper model.
- Off-the-shelf: InSPyReNet best overcut among tools but soft alpha; no single tool solves binary+pale-paint.
- Codex path: BRIA hard180 + colored-margin restore; white-gap automation unsafe unattended.
- image15: painted haze→white has no objective boundary — may need design decision.
- The Claude `SEPARATION IS CLEAN` test labelled and evaluated pixels with the same threshold, and its batch PASS checked structure, not semantics; neither is an acceptance oracle.
- Cursor continued the flood/punch/rim family through repeated failures; proxy `white_rim=0` directly contradicted user inspection.
- Semi-auto v12 produced only auto-seed artifacts (`user_fg_px=0`, `user_bg_px=0`). Its current code removes user-FG overrides on paper-like pixels, so the human-supervised architecture has not been fairly tested.
- Regeneration changed composition and retained key-color contamination; it is a segmentation-reference experiment, not a source-preserving solution.

## Phases

1. **Evidence synthesis** (parallel agents) — session digests, defect crop truth, code inventory.
2. **Freeze the oracle** — independent FG/BG guard masks, native review crops, negative fixtures, and a linted loop spec.
3. **Scout distinct routes on image14** — fixed human-seeded trimap + matting/decontamination; SAM 3 semantic proposal + trimap refinement; current Photoshop Select/Mask + decontamination; ComfyUI-native background-removal/matting nodes; and source-side regeneration on deliberately unique non-coral chroma. Stop a route after two same-class visual failures.
4. **Implement the smallest winner** — automatic proposal, absolute-precedence corrections, correct straight-alpha RGB, uncertainty manifest, resumable outputs.
5. **Expand** to image15 + sample08, then all sources; user/cold-verifier gate every flagged region.
6. **Document and commit** only after the whole `done means` block clears.

## Open decisions (ask only if blocking)

- Straight soft alpha acceptable? Default: **yes when foreground RGB is decontaminated and multi-background composites pass**; export binary only when the downstream consumer truly requires it.
- Minimal user FG/BG annotation acceptable? Default: **yes for pixels the workflow flags as ambiguous**; guessing is not a complete solution.
- image15 haze: keep as art vs background? Default: protect it as art until an explicit BG annotation says otherwise.

## Execution loop

```loop
name: double-marine-complete-background-removal
topology: closed · inner · fleet
generator: isolated scout/build agents producing only candidates, code, and tests named by this plan
verifier: separate cold verifier running the frozen machine gate and native-resolution vision rubric, blind to generator rationale
gate: cmd: python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py --manifest tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json && human user approves all flagged native-resolution regions
stop: image14, image15, sample08, and every full-folder manifest entry pass R1-R5; all uncertainty items are resolved; user and cold verifier accept the flagged visual cases
budget: max_iterations=3 architecture rounds, max_wallclock=8h per round
quorum: machine gate passes every case and both user plus cold verifier accept every flagged region
anchor_files: AGENTS.md, tasks/double-marine-bed-wrapper-batch/PLAN-bg-complete-solution.md, wiki/concepts/illustrated-product-upscale-and-background-removal-workflow.md
state_store: tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json
recall: read this plan, state_store, and wiki timeline before each round; compare against all prior user verdicts
writeback: record method, exact inputs/parameters, outputs, per-criterion verdicts, failures, and next action after each round
state_concurrency: single_writer
stuck: same original failure class persists twice or two rounds produce no guard-mask improvement
advisor: separate read-only architecture/research agent; never the verifier
redaction: exclude credentials, .env files, account tokens, and unrelated private content from external model/tool egress
consent: attended user-requested task; user explicitly authorized research and tool experiments
verifier_blind: true
verifier_inputs: original requirements, frozen guards/rubric, candidate outputs, manifests, native review images
on_error: transient network/model errors retry once; bad visual output is an observation; auth/config/permission issues interrupt; unexpected errors halt and surface
```

## Frozen scout verdicts (2026-07-09)

- **Photoshop 27.8 automatic mask:** useful semantic seed and its Remove White Matte pass improves edge RGB without changing alpha, but the mask deletes the pale sandy footprint. It fails the independent `deleted_foreground`, reconstruction, and all three edge gates.
- **ViTMatte-S on MPS:** native 941×1672 inference is practical (0.769 s, padded only). With the prior automatic trimap it passes every frozen FG/BG and edge guard but fails reconstruction (`p99=10`, gate `<=8`) and still visibly retains pale enclosed-paper ghosts. It is the preferred alpha stage only after the semantic trimap is corrected.
- **fal SAM 3 text proposal:** the corrected one-request route returned one binary mask despite requesting 32; it misses fish/bubbles/tips, retains enclosed paper, and has hard rims. Reject as the primary proposal for this artwork.
- **Architecture selected:** Photoshop (or a transparent RGBA annotation overlay) supplies the semantic proposal plus minimal absolute-precedence FG/BG corrections; ViTMatte or closed-form matting supplies soft alpha; regularized foreground recovery plus exact reconstruction checks supplies decontaminated straight RGB. No stage is allowed to stand in for the other two.
- **Parallel lanes added by user:** audit/test ComfyUI background-removal workflows without displacing the selected implementation; compare several generation/edit models and prompt strategies for composition-locked regeneration on a uniquely keyable non-coral chroma. Chroma candidates must separately pass composition fidelity, background uniformity, subject-color collision, spill, post-key fringe, and alpha gates.

## Round-1/2 evidence update (2026-07-10)

- **Correction-led image14 v2:** five sparse red FG strokes, Photoshop proposal,
  ViTMatte-S, foreground recovery, and same-component joint RGB/alpha edge
  decontamination produce a native candidate that passes all 15 FG guards,
  11 exterior/enclosed BG guards, all 3 edge probes, and straight-RGB
  reconstruction (`MAE 0.871`, `p99 6`). It remains
  `PENDING_HUMAN_REVIEW`, not a final.
- **Edge solution:** 4,836 paper-colored boundary pixels are replaced only
  when a colorful high-alpha target exists within 8 px in the same connected
  component. Alpha is least-squares re-solved so source-on-paper error stays
  within 8/255; sure labels are protected and changed alpha never drops below
  17/255. This removes matte RGB without luma-punch deletion.
- **Independent hard set:** image14, image15, and sample08 now have source-only
  guard annotations. Image15 freezes authored base wash as FG, uniform cream
  paper as BG, terminal fade as human review, and case paper color
  `[250,246,241]`; intentional white bubble highlights are not fringe probes.
- **Image15/sample08 auto pass:** the frozen gate correctly rejects the
  uncorrected proposal: image15 needs sparse FG recovery plus enclosed-BG
  corrections; sample08 needs an enclosed-BG correction. This is evidence that
  the correction stage is necessary, not a reason to weaken the gate.
- **ComfyUI native SAM 3.1:** core workflow, point contract, and lint are frozen,
  but both official 1.75 GB checkpoint transfers failed (timeout, then CDN
  reset at 1.305 GB). Partial files were rejected and removed; no Comfy
  candidate exists, so this lane is unavailable evidence rather than a failure
  of the method.
- **Engineered green background:** Flux and Nano generations were closest in
  geometry but direct keys left green rims. Registered source-payload hybrids
  still failed reconstruction/semantic/edge guards. OpenAI recomposed details,
  Kontext ignored the green request, and the prior magenta route collided with
  art colors. Reject every chroma candidate as a complete solution; retain the
  generated plate only as a possible topology proposal.
- **OpenAI native transparency:** both allowed subscription calls returned
  opaque RGB PNGs depicting a checkerboard and changed details. Reject as a
  dependable transparency source.
- **Alpha-safe upscale:** direct ncnn RGBA is close but undocumented; nonlinear
  black/white two-plate recovery leaks foreground texture into alpha. The
  preferred split route runs RealESRGAN on extended straight RGB and Lanczos on
  alpha independently. The real image14 x8 output is 7528×13376 RGBA, source
  hash unchanged, and its alpha matches the prescribed split reference exactly
  (`MAE 0`, `max 0`).
