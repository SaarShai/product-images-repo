# Wiki Log

## [2026-07-13] create | Print-Ready Transparent Pipeline

Created `concepts/print-ready-transparent-pipeline.md` from verified 2026-07-13 generation canaries. Recorded native-alpha generation route (gpt-image-1/1.5/chatgpt-image-latest with `background=transparent` param; gpt-image-2 returns HTTP 400, Flux.2 exposes no alpha param), complete pipeline (R4 clean-edge recipe + decontam_binarize linear-light ridge unmix + gate_battery print-profile tri-state classification), measured yield (3/9 auto-PASS; residual defects = stochastic pale patches, donor-referenced halo gates), route comparison (gpt-image-1 best style+cut, white_key floods thin strokes, chroma-green wins metrics but visual rejection), detector lesson (absolute edge-brightness false-positives on honest AA; working metric = donor-referenced p95-delta-L* in linear light), and banked advisor corrections (threshold LAST never before unmix; binary alpha print-invisible at ≥300ppi opaque-edge only; rank worst image not mean).

## [2026-07-12] update | Transparent-clear-edge prompt recipe — dehalo_edge + halo-gate steps

Updated [[concepts/transparent-clear-edge-prompt-recipe]] recommended pipeline: added mandatory `scripts/dehalo_edge.py` edge-decontamination step (fixes white-halo that white_key binary alpha produces on darker backgrounds; nearest-interior RGB extension + distance-floor alpha re-solve) + MANDATORY visual gate before delivery (composite edge-crop over #111111, verify no white rim). Recorded v1/v2 calibration lessons: per-pixel error-rejection creates speckled rims (coherence beats accuracy); alpha re-solve without distance-floor punches pale-art holes.

## [2026-07-12] create | Band-Panel Workflow SOP

Created `concepts/band-panel-workflow-sop.md` from verified single-run workflow (tasks/marine-coral-panels, 2026-07-12; 60% rework avoided via pre-flight checklist). Recorded pre-flight checklist (ref provenance/model pinning, 3 user questions, memory grep for precedents, exemplar calibration), generation discipline (placement not prompting, batch-parallel not sequential), hard gates (fit_gate.py overlap check, white_key.py gi2 preset with regression fixture, alpha-aware upscale validation), and delivery checklist (Images/ casing verification). Single-run evidence; thresholds provisional; deferring band_pipeline.py orchestrator + /learn skill promotion until 2nd conforming run.

## [2026-07-12] add | Three gotcha lessons from transparent-clear-edge session

Added three fact entries from verified 2026-07-12 session:
- [[concepts/codex-exec-needs-stdin-closed]]: `codex exec` backgrounded without stdin closes hangs forever; fix: `</dev/null` redirect.
- [[concepts/gate-metrics-on-keyed-deliverable-not-raw-render]]: aura_index measured 3-4× different on raw vs. keyed output; gate the shipped artifact, not intermediates.
- [[concepts/dont-derive-runner-scripts-via-sed]]: sed-derived runner chains break silently (blank-line-after-backslash corruption); write fresh or parametrize ONE template.

## [2026-07-12] create | Transparent-Clear-Edge Prompt Recipe

Created `concepts/transparent-clear-edge-prompt-recipe.md` from verified 4-round experiment (26 generations, user-judged each round). Recorded winning prompt structure for gpt-image generation with clean closed contours and tinted interior highlights, keyability modules (AVOID / KEYABLE-FINE), critical conflict-resolution rule for thin features (deviation-authorization sentence = 3/3 compliance), and white_key.py `--reopen-interior` upgrade (verified 4/4 tests, 48 regions reopened on real candidate).

## [2026-07-06] create | Marriott Hospital T2 Method-Matrix

Created `concepts/marriott-hospital-t2-method-matrix.md` from user-confirmed t2 finalist verdict: gpt-image (codex free) wins; nano-banana killed from die-cut pipeline due to aspect recompose. Recorded new style-bible axis (intentional-complete-building; slight-overhang OK), method scorecard, open items (emblem discipline, artifact logging, panel coverage), and next-phase direction.

- 2026-06-15: Added [[concepts/castle-panel-template-cut-bands]] after
  user-confirmed V6/V7 feedback. The durable rule is that center rectangles and
  the horizontal split may cut only inert background, not fairies, birds,
  butterflies, flowers, windows, or other recognizable motifs.

## [2026-06-15] update | Castle Panel Template Cut Bands

Created `concepts/castle-panel-template-cut-bands.md` from `page` template.

## [2026-06-15] update | Castle Panel Template Fit Loop

Expanded [[concepts/castle-panel-template-cut-bands]] from the V6/V7
cut-band rule into the reusable fixed-template loop: choose empty/wall mode,
score placement sweeps, export scored metadata, then require semantic visual
review and `0` painted centerline hits for custom contours before handoff.

## [2026-06-16] update | SVG Template Whole Redraw From Roughs

Created `concepts/svg-template-whole-redraw-from-roughs.md` from `page` template.

## [2026-06-16] retro | SVG Template Whole Redraw From Roughs

Added [[concepts/svg-template-whole-redraw-from-roughs]] and updated the
SVG-template skills/workflow after top-temp B/C redraws succeeded. Pattern:
pattern:svg-template-whole-redraw-from-roughs. Lesson: when roughs prove layout
but final art looks assembled, feed roughs plus style references to image
generation for a whole redraw, then apply exact SVG checks afterward.

## [2026-06-17] retro | Skyline Local Patch Semantics

Updated `.codex/skills/skyline-template-illustration/SKILL.md` and
`docs/skyline-template-illustration-workflow.md` after Berlin Image A local
patch feedback. Pattern: pattern:skyline-local-patch-semantics. Lesson:
distinguish quiet red-center filler from recognizable features, allow only
controlled top-contour overflow, preserve landmark bases, and check
bridge-to-saloon-door symmetry before the next edit.

## [2026-06-17] retro | Screenery Socket And Polyline SVG Geometry

Added [[concepts/screenery-socket-polyline-svg-geometry]], updated the
SVG-template skill/workflow/review checklist, and added a validator regression
after `np01-back-bottom.svg` exposed two geometry failures. Pattern:
pattern:screenery-socket-polyline-svg-geometry. Lesson: edge sockets/notches are
carved-out cutouts even when their SVG coordinates extend past the paintable
body edge, and open panel paths may require sibling polylines before closure;
future agents must verify both mechanically and visually.

## [2026-06-17] retro | SVG Template Geometry-Approved Style Redraw

Updated `.codex/skills/svg-template-style-agent/SKILL.md`,
`.codex/skills/svg-template-illustration/SKILL.md`,
`docs/svg-template-illustration-workflow.md`, `docs/review-judge-checklist.md`,
`AGENTS.md`, and `tasks/space-svg-exports-batch/` after the approved
`np01-back-top` geometry drifted into locked-geometry local restyle attempts.
Pattern: pattern:svg-template-geometry-approved-style-redraw. Lesson: when the
user approves geometry/dimensions/location but rejects style, use the approved
geometry only as a composition map for attachment-aware whole-panel redraw, then
run exact SVG export/checks downstream.

## [2026-06-17] retro | SVG Geometry Style Orchestration Skill

Added `.codex/skills/svg-geometry-style-illustration/SKILL.md` and drift probes
to make the full SVG geometry -> style-packet -> attachment-aware redraw ->
exact SVG check -> visual judge route explicit. Pattern:
pattern:svg-geometry-style-orchestration. Lesson: future agents should start
with the orchestration skill for end-to-end SVG template plus reference-style
tasks, then delegate geometry, style packet, image generation, and review to
separate skill roles.

## [2026-06-17] update | Space NP01 Front-Bottom-02 Watercolor Panel Generation

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract np01-fb-02-base-trueaspect-1440x2560.png and style references, saving the raw output to tasks/space-np01-front-bottom-02/experiments/BoN2-nano-s1/raw.png.

## [2026-06-17] update | Space NP01 Front-Bottom-02 Watercolor Panel Generation (BoN2-nano-s2)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract np01-fb-02-base-trueaspect-1440x2560.png and style references, saving the raw output to tasks/space-np01-front-bottom-02/experiments/BoN2-nano-s2/raw.png.

## [2026-06-17] update | Space NP01 Front-Bottom-02 Watercolor Panel Generation (RESTYLE-nb-v1-s3)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract exact.png and style references, saving the raw output to tasks/space-np01-front-bottom-02/experiments/RESTYLE-nb-v1-s3/raw.png.

## [2026-06-17] update | Space NP01 Front-Bottom-02 Watercolor Panel Generation (SRC-nb-s8)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract np01-fb-02-base-trueaspect-1440x2560.png and style references, saving the raw output to tasks/space-np01-front-bottom-02/experiments/SRC-nb-s8/raw.png.

## [2026-06-17] update | Space NP01 Front-Bottom-01 Watercolor Panel Generation (space_control_panel_1781738909664)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract np01-fb-01-base-outset30-1440x2560.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/11ab6649-4f9a-4e06-b4dd-b0221e279e88/space_control_panel_1781738909664.jpg.

## [2026-06-17] update | Space NP01 Back-Bottom-01 Watercolor Panel Generation (watercolor_space_panel_1781740733425)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract base-outset30-1440x2560.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/ad03fc04-4205-4f64-ae68-7043fb660ff7/watercolor_space_panel_1781740733425.jpg.

## [2026-06-17] update | Space NP01 Back-Top Watercolor Panel Generation (watercolor_control_panel_1781740848112)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract base-outset30-sq-1700x1620.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/e22e08d7-71f3-4d61-bcd4-186ddf12f23d/watercolor_control_panel_1781740848112.jpg.

## [2026-06-17] update | Space NP01 Back-Bottom-02 Watercolor Panel Generation (watercolor_control_panel_1781741152887)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract base-outset30-1440x2560.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/2ff7a0d3-42b1-4e7f-85d0-a16c5283da6b/watercolor_control_panel_1781741152887.jpg.

## [2026-06-17] update | Space NP02 Front-Top Watercolor Panel Generation (space_control_panel_1781741159760)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract base-outset30-sq-1700x1620.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/4f963e22-f0d7-43df-8a5a-01de2f41528a/space_control_panel_1781741159760.jpg.

## [2026-06-17] update | Background routes must write resumable checkpoints

Created `concepts/background-routes-must-write-resumable-checkpoints.md` from `page` template.

## [2026-06-17] update | A route needs a success-criterion and measure gate before launch

Created `concepts/a-route-needs-a-success-criterion-and-measure-gate-before-launch.md` from `page` template.


## [2026-06-17] retro | two-session task-retrospective (current ca17625c + previous "SVG geometry style skill cleanup" 34d36036), cross-vendor verified via codex/GPT
- CURRENT escalations (repeated past prose gates → mechanical boundary block): + .claude/hooks/artifact_guard.py PreToolUse + .claude/settings.json wiring + lesson_patterns.json pattern:edit-without-read (re-escalated) + pattern:file-op-without-verify (new)
- PREVIOUS lessons banked (write-gate PASS, user_confirmed): + wiki/concepts/background-routes-must-write-resumable-checkpoints.md pattern:daemon-work-needs-checkpoints + wiki/concepts/a-route-needs-a-success-criterion-and-measure-gate-before-launch.md pattern:route-spec-with-success-gates
- subscription reinforcement: memory subscription-image-gen-one-path (extend subgen.py, no parallel module) pattern:subscription-always-working-fallback
- recurrence across BOTH sessions: results-collection / no-post-op-verify, style-render-must-use-reference-images (already gated)

## [2026-06-18] update | Space NP02 Front-Bottom-01 Watercolor Panel Generation (space_control_panel_1781771362280)

Synthesized a high-resolution watercolor space control-panel illustration using generate_image matching layout contract base-silhouette-v2-1440x2560.png and style references, saving the raw output to /Users/za/.gemini/antigravity-cli/brain/49f562c7-91a7-4482-808c-a9589a5fa3dc/space_control_panel_1781771362280.jpg.

## [2026-06-18] retro | multi-panel generation stretch (9 SVGs, agy debugging, edge-socket fix)
- root causes: background drivers died silently (nohup& in bg-wrapper detach; broad pkill killed siblings); reported gen-status without verifying output; zsh bare-glob no-match aborted commands; agy 429 quota + health-lies + Pillow code-fallback.
- gates/tools (this repo only, per user): + scripts/genbatch.sh (supervised pgroup runner, status=real raw count, scoped stop) + scripts/build_silhouette_base.py (edge-socket/polyline silhouette base) + glob-no-match-abort drift probe (skills/verify-before-completion/drift_probes.json) pattern:glob-no-match-abort + artifact_guard fixed to block only Images-as-destination.
- lessons banked (memory): background-gen-supervision, zsh-glob-abort-guard, edge-socket-panel-recipe; subscription-image-gen-one-path updated (nano 429/health-lies/openai fallback).
- canonical Brainer: added SCOPE note to skills/task-retrospective/SKILL.md — never run task-retrospective on the Brainer repo itself, only in the consuming/current repo.
- accepted results: np01-back-bottom-02 = OPENAI-s2 (then 6 nano v2/v3 alternates); np02-front-bottom-01 = 6 nano + openai (pending pick).

- 2026-06-21 element-edit retrospective: banked element-edit-diffmask-composite, image-edit-engine-routing, reference-lock-for-consistency (.claude memory); Flux.2-pro=engine, diffmask gate.

- 2026-06-21 window-widen (n02): exact-geometry element reshape — blob-mask Fill FAILED to widen; WIN = no-redo stretch (anchored) -> Flux Kontext cleanup -> arched-mask composite + reattach alpha. Banked element-reshape-stretch-then-refine.
## [2026-06-23] update | Mask-Bounded External Redraw Donor

Created `concepts/mask-bounded-external-redraw-donor.md` from `page` template.

## [2026-06-23] retro | Berlin wave3 localized image repair

User confirmed the bottom-right `S09 OpenAI redraw` candidate was near perfect.
Banked the reusable rule in [[concepts/mask-bounded-external-redraw-donor]] and
updated `skills/element-edit/SKILL.md` plus `docs/image-generation.md` so future
localized watercolor artifact repairs try the mask-bounded OpenAI donor route
alongside conservative local repairs, then verify outside-mask/protected-region
delta before presenting results.

## [2026-06-23] retro | Berlin wave6 bridge stair continuity

Task-retrospective evidence showed that local raster/linework stair patches were
either invisible or crude. User confirmed the top-right OpenAI donor candidate
for the bridge-stair repair was near perfect. Updated
[[concepts/mask-bounded-external-redraw-donor]], `docs/image-generation.md`, and
`skills/element-edit/SKILL.md` to route semantic continuity plus occlusion
repairs to a mask-bounded OpenAI redraw donor, because the model can redraw the
object and occluder relationship together while the final masked composite keeps
unrelated pixels bounded.

## [2026-06-23] retro | Berlin wave7 hotel roof and protected floors

User confirmed the top-right hotel-roof donor look was perfect, but the large
context verification showed the raw donor was not safe as a final composite: it
changed `floor_guard_changed_vs_pre_roof=227064` and
`stair_protected_changed_vs_pre_roof=631275`. Updated
[[concepts/mask-bounded-external-redraw-donor]], `docs/image-generation.md`, and
`skills/element-edit/SKILL.md` with the guard-zone extension: use broad donor
context as a visual target, then apply a separate final blend mask, restore or
protect repeated structures such as hotel floors/windows, and present a larger
context board before banking the result.
## [2026-06-24] update | Family-A architectural watercolor panel — proven recipe + geometry-gate (cap-juluca)

Created `concepts/family-a-architectural-watercolor-panel-proven-recipe-geometry-gate-cap-juluca.md` from `page` template.

## [2026-07-05] add | ONE-PASS geometry×style route SOLVED

Added [[concepts/onepass-geometry-style-route-flux-control-lora]]: fal-ai/flux-control-lora-canny + trained style LoRA + control_lora_scale dial (0.35 proven) eliminates two-phase bottleneck. First-shot silhouette-IoU 0.975–0.988 on Cap Juluca + Marriott 3-panel. Evidence: .brainer/tenx/lora-pilot/ONEPASS-FINDINGS.md; commits 53f2e2e/7041dd4/d46e227. Wrapper: scripts/onepass_gen.py.

## [2026-07-05] add | Two-gate acceptance proven necessary

Added [[concepts/two-gate-acceptance-silhouette-iou-plus-vision-judge]]: silhouette-IoU alone insufficient (Marriott r3_right_s1 scored 0.976 but was near-empty). Vision judge caught content failure. Rule: always gate both geometry (measured IoU) and visual quality (vision judge). Never accept on IoU alone.

## [2026-07-05] add | No painted text rule

Added [[concepts/no-painted-text-vector-layer-or-omit]]: diffusion garbles signage/lettering. Rule: text is vector layer (.ai) / omitted (blank plaques) / manual (hand-draw post-gen). Auto-clause baked into onepass_gen.py. User rule 2026-07-04.

## [2026-07-05] add | fal image_size bucket drift

Added [[concepts/fal-image-size-bucket-drift]]: fal API snaps image_size to buckets (spec 820×2105 → actual 576×1536). Score resize-normalized, assemble at spec bbox_svg positions in shared viewbox. Silent failure: no error raised; assembly breaks on stale dimension assumptions.

## [2026-07-05] add | Trained LoRA registry pattern

Added [[concepts/trained-lora-registry-pattern]]: per-collection lora.json (lora_url / trigger_word / status); usable iff status == "COMPLETED". Enables onepass generation, prevents duplicate training, tracks collection style. Schema example: cap-juluca (CJWC), marriott (MRCH).

## [2026-07-07] update | Illustrated product upscale and background-removal workflow

Created `concepts/illustrated-product-upscale-and-background-removal-workflow.md` from `page` template.

## [2026-07-08] review | GLM 5.2 adversarial pass on upscale/background SOP

Ran a GLM 5.2 adversarial review of
[[concepts/illustrated-product-upscale-and-background-removal-workflow]]. Accepted
the review's strongest concerns by narrowing the SOP from all illustrated
watercolor assets to similar/folder-style assets, adding the binary-alpha
default plus reviewed one-pixel anti-aliasing exception, and making unattended
non-default routes explicit.

## [2026-07-08] update | Double Marine x8 background-removal batch verified

Updated [[concepts/illustrated-product-upscale-and-background-removal-workflow]]
from sample-proven to full-folder batch-proven because the double Marine Bed
Wrapper run produced `19/19` x8 transparent PNG finals, the verifier passed
`19/19`, and the manifest reported `0` semi-transparent alpha pixels. Recorded
the guarded colored-margin restore default (`256` px minimum repair component)
because smaller candidates produced speck-like restore noise on the first batch
image.

## [2026-07-08] update | Clarify internal x16 scratch vs delivered x8 finals

Updated [[concepts/illustrated-product-upscale-and-background-removal-workflow]]
to require delivered-scale verification and x16 scratch cleanup when an x8
deliverable uses a temporary x16 stage, because transient `@x16` artifact names
can make users reasonably think the wrong scale was produced.

## [2026-07-08] add | Double Marine Bed Wrapper — Background Removal Fusion Pipeline

Added [[concepts/double-marine-bed-wrapper-background-removal-fusion-pipeline]]:
watercolor marine illustration batch-processing (x18 images). v1 fusion pipeline
(border-flood + disagreement-recovery restore) validated: 18/18 binary alpha,
exact dims, 0 intrusions. v1 failures: ultra-pale ghost corals, residual
white-ish edges, image15 haze-to-white ambiguity. v2 spec: flood chroma≤5 +
tint-coherence restore + contrast-adaptive boundary erode. Gate: defect_scan_v2.py
(hi-DPI tiles, BG model from original source, not white-filled RGB). Tooling
lessons: codex sandbox paths, codex-rescue one-shot forwarding, edge judgment
at full-res only.
## [2026-07-08] update | Gingerbread panel cutouts are decoration slots

Created `concepts/gingerbread-panel-cutouts-decoration-slots.md` from `page` template.

## [2026-07-08] update | Gingerbread cutout styled means reference-attached redraw

Updated [[concepts/gingerbread-panel-cutouts-decoration-slots]] after the user
rejected the local Pillow `d1`-`d6` decoration previews as not actually styled.
Lesson: for festive gingerbread cutouts, alpha-mask containment is not enough;
styled means the actual watercolor reference images or style-packet sheets were
attached to image generation, with procedural mask-valid previews used only as
composition maps before exact mask/export checks.

## [2026-07-08] retro | Styled candidate proof gate

Added proposed slash-only skill `skills/styled-candidate-proof-gate/SKILL.md`
and task report `tasks/festive-v1-gingerbread-candidates/RETROSPECTIVE-styled-oversight.md`
after the styled-image oversight. Root cause: geometry containment was allowed to
stand in for the user-facing style claim. Prevention: prove method provenance
and visual style before exact mask containment when showing "styled generated"
Screenery/template candidates.

## [2026-07-09] update | Follow the approved styled gingerbread candidate

Updated [[concepts/gingerbread-panel-cutouts-decoration-slots]] after the user
identified the left `v1style-donor-test` option as the good direction and said
later variants drifted less good. Lesson: when a user points to a specific
styled cutout candidate, lock that candidate family as the visual target because
geometry-valid variants can still regress in style/density. Verify style against
the approved candidate and verify `edge-v4` base/alpha preservation separately.

## [2026-07-09] update | Check every gingerbread cutout instance

Updated [[concepts/gingerbread-panel-cutouts-decoration-slots]] after the user
caught that the two left vertical strips were still mostly plain while the right
strips had candy/icing. Lesson: global geometry/base checks and a representative
visual sample are not enough; inspect every repeated cutout component, especially
left/right strip pairs, before presenting final Screenery cutout candidates.

## [2026-07-09] update | Festive clarity Stage C probe-only + cutout gotchas

Task-retrospective on Cursor chimney/tree + Codex gingerbread-style sessions.
Updated [[concepts/illustrated-product-upscale-and-background-removal-workflow]]
with a magenta/neon Stage C candy-creative artifact trigger (single-probe ≠ batch;
regenerate from clean sources; recipe in
`tasks/festive-v1-gingerbread-candidates/outputs/upscale-research/DIAGNOSIS.md`).
Updated [[concepts/gingerbread-panel-cutouts-decoration-slots]] and
`tasks/festive-v1-gingerbread-candidates/CORRECTION-GATE.md` with chimney
biscuit-brick texture (not scenes), unmask-first before redesign, and
unmasked artwork vs masked preview deliverable rules. No new skill — route-probe
FACT-shaped; Fable advisor endorsed patch-existing over `/learn`.

## [2026-07-09] update | Generalize cutout and upscale rules

Generalized [[concepts/gingerbread-panel-cutouts-decoration-slots]] and
[[concepts/illustrated-product-upscale-and-background-removal-workflow]] to remove
design-specific standing rules. Product details such as festive chimney texture,
candy motifs, candidate names, and task recipes remain only as labeled exemplars
or task-local notes.

## 2026-07-12 — Wanderland packet retrospective (task-retrospective)
Harvested 3 lessons from the external successful session packet
/Users/za/Downloads/Wanderland-Packet-2026-07-11 (fire-station door panel):
[[concepts/fixed-cut-composite-flexible-cut-art-derived]] (composite-to-cut for
fixed die openings, art-derived contour for flexible ones, + Illustrator-JSX
gotchas), [[concepts/semantic-color-region-map-locks-proportions]] (user-invented
color-zone guide that ended the regen mismatch loop), and
[[concepts/playwright-cdp-real-chrome-chatgpt-web-gen]] (bot-block-proof scripted
ChatGPT-web gen; reference only — subgen.py stays the single path). Dropped as
already-banked: incremental result gating, reference-beats-prose, white-bg
prompt discipline.
