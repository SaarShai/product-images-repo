# Berlin Skyline Live Example Skyline Example Feedback

Use this file during skyline or city-scape example runs. Capture only evidence
that should shape the next prompt, candidate, or skill update.

## Load-Bearing Choices

- City or landmark family: Berlin skyline and Potsdamer Platz family.
- Panel allocation:
  - left narrow panel: Fernsehturm + Brandenburg Gate.
  - central door panel: Berliner Dom + Kaiser Wilhelm Memorial Church style tower/spire + simplified bridge/viaduct base.
  - right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise; optional green Potsdamer traffic-light/clock tower only if approved.
- Run-through element: yellow Berlin U-Bahn low across the set, with rail/stone/water band continuity.
- Saloon-door arch feature: simplified Berlin bridge or viaduct arch over quiet water/stone.
- Top-contour adaptation: trace TV tower, gate dip, dome/spires, and high-rise crown; keep fragile details production-safe.
- White sky/background rule: keep sky/removable background white or very pale paper-white.

## Checkpoint Approval Status

Use compact codes when helpful, for example `1A, 2A, 3A, 4A`.

- Source packet: approved with `1A`.
- Landmark roster: approved with `2A`; do not include the optional green
  traffic-light/clock tower in the first candidate.
- Composition strategy: approved with `3A`; use whole-set-first planning.
- Visual premise: approved with `4A`.
  - run-through element: yellow Berlin U-Bahn low across the set.
  - saloon-door arch feature: simplified Berlin bridge or viaduct arch over
    quiet water/stone.
  - top-contour adaptation: trace TV tower, gate dip, dome/spires, and
    high-rise crown.
  - white/removable sky: keep sky/removable background white or very pale
    paper-white.

## User Feedback Log

Record feedback as concrete production rules, not vague preferences.

```text
date:
artifact inspected:
user feedback:
rule learned:
applies to:
next action: ACCEPT | LOCAL PATCH | PROMPT RESTART | ASK USER
```

```text
date: 2026-06-16
artifact inspected: source/template.svg; refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg; refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg; style-packet/reference-contact-sheet.png; style-packet/style-exemplar-sheet.png; template-manifest.json; prompts/prompt-v2-style-packet-elements-first.md
user feedback: Checkpoint choices 1A, 2A, 3A. Source packet approved; landmark roster approved without adding the optional green traffic-light/clock tower; whole-set-first strategy approved.
rule learned: no durable rule yet; this is a task-specific checkpoint approval. Visual-premise approval was separated into a fourth checkpoint and resolved later with `4A`.
applies to: berlin-skyline-live-example task packet
next action: ACCEPT
```

```text
date: 2026-06-16
artifact inspected: outputs/reviews/checkpoint-1-approval-board.png; checkpoint-1-source-and-composition-plan.md; skyline-example-feedback.md
user feedback: Checkpoint choice 4A. Visual premise approved: low yellow U-Bahn run-through, simplified bridge/viaduct arch in the saloon area, adaptive top contour, and white/paper-white sky.
rule learned: no durable rule yet; this confirms the task-specific Berlin visual premise for the first generation phase.
applies to: berlin-skyline-live-example task packet
next action: ACCEPT
```

Checkpoint note:

- Source SVG and two Berlin/style references are copied into the task.
- Style packet exists and has visual contact/exemplar sheets.
- Visual Checkpoint 1 approval board exists at
  `outputs/reviews/checkpoint-1-approval-board.png`.
- `template-manifest.json` is filled for Checkpoint 1 from the skyline SVG roles and Berlin plan.
- Geometry reporter was attempted with a 10-second alarm and exited `142`; no
  `svg-geometry-report.md` was created.
- No generated candidate exists yet.
- `prompt-v2-style-packet-elements-first.md` has been rewritten from generic control-panel language into Berlin skyline element language.
- `prompt-pack.md` was rebuilt after the prompt rewrite.
- User approved the source packet, landmark roster, and whole-set strategy with
  `1A, 2A, 3A`.
- Do not include the optional green traffic-light/clock tower in the first
  candidate unless the user changes this later.
- User approved the visual premise with `4A`: U-Bahn run-through,
  bridge/viaduct arch, adaptive top contour, and white/paper-white sky.

## Candidate Review Notes

For each candidate:

- Candidate path: `outputs/generated/20260616-berlin-elements-v1.png`
- Overlay/debug path: not applicable yet; this is an element sheet, not final
  SVG placement.
- Style references or packet sheets inspected: Berlin render/style reference,
  Ritz/Beisheim/Potsdamer Platz reference, style-packet contact/exemplar
  sheets, prompt v2.
- Geometry verdict: ACCEPT FOR ELEMENT REVIEW only. Do not treat as final
  template placement approval.
- Style verdict: strong watercolor/pencil match to the reference packet.
- Landmark recognizability: Fernsehturm, Brandenburg Gate, Berliner Dom, Kaiser
  Wilhelm style church, Ritz/Beisheim/Potsdamer high-rise, U-Bahn, base strips,
  and bridge/viaduct arch are present.
- Red-zone/seam safety: deferred to SVG placement. Carry risk that U-Bahn
  doors/windows and birds must stay away from seams/red zones.
- Saloon-door arch fit: bridge/viaduct arch is useful for the central saloon
  area.
- Top-contour fit: landmark silhouette tops are usable; Fernsehturm antenna may
  need thickening/simplification during placement.
- Sky/background: white/paper-white; green traffic-light/clock tower excluded.
- Next move: ask user to approve, request minor changes, or restart element
  generation before SVG-aware placement mockup.

```text
date: 2026-06-16
artifact inspected: outputs/generated/20260616-berlin-elements-v1.png
user feedback: B minor changes first. 1. The hotel/high-rise on the right is missing the lower section of the building. 2. For the middle buildings and bridge, verify what they are by looking them up.
rule learned: first element sheet should include the full Ritz-Carlton/Beisheim/Potsdamer Platz building mass including the lower podium/wing; uncertain reference landmarks must be verified before regenerating.
applies to: berlin-skyline-live-example element generation v2
next action: PROMPT RESTART
```

- Candidate path: `outputs/generated/20260616-berlin-elements-v2.png`
- Lookup note: `checkpoints/berlin-landmark-verification.md`
- Overlay/debug path: not applicable yet; this is an element sheet, not final
  SVG placement.
- Style references or packet sheets inspected: Berlin render/style reference,
  Ritz/Beisheim/Potsdamer Platz reference, v2 prompt, landmark verification
  note.
- Geometry verdict: ACCEPT FOR USER ELEMENT REVIEW only. Do not treat as final
  template placement approval.
- Style verdict: watercolor/pencil style remains close to the Berlin reference.
- Landmark recognizability: v2 keeps Fernsehturm, Brandenburg Gate, Berliner
  Dom, Kaiser Wilhelm Memorial Church, full Ritz/Beisheim/Potsdamer high-rise
  with lower podium/wing, U-Bahn/base strips, and Oberbaum-inspired
  bridge/viaduct arch.
- Red-zone/seam safety: deferred to SVG placement. U-Bahn doors/windows still
  need careful seam routing or quiet strip selection.
- Saloon-door arch fit: bridge/viaduct arch is stronger and cleaner than v1.
- Top-contour fit: landmark silhouette tops remain usable; keep TV tower
  antenna production-safe later.
- Sky/background: white/paper-white; green traffic-light/clock tower excluded.
- Next move: ask user to approve v2 for SVG-aware placement, request minor
  changes, or restart element generation.

```text
date: 2026-06-16
artifact inspected: placement workflow after v2 approval
user feedback: A approved for placement, followed by process correction: use subagents and create several option images at key steps with different prompts/instructions instead of getting stuck in one local parsing path.
rule learned: placement should branch into multiple visual options with distinct placement strategies before choosing a final SVG-aware direction.
applies to: berlin-skyline-live-example placement mockup phase; future skyline placement checkpoints
next action: ACCEPT
```

```text
date: 2026-06-16
artifact inspected: outputs/reviews/placement-options/placement-options-contact-sheet.png; outputs/reviews/scout-tests/scout-tests-contact-sheet.png; image-generation scout outputs displayed in chat
user feedback: The options all look very similar, and the user questioned whether they are good wireframes for generating the full illustration. The user asked for early testing before putting resources into a direction that might not pan out.
rule learned: Faint lookalike wireframes must be treated as weak evidence. Before full skyline generation, run proof-before-spend scout tests with visibly different prompt strategies and judge whether they actually protect composition, red zones, seams, arch use, and top contour.
applies to: berlin-skyline-live-example scout phase; future skyline/city-scape tasks
next action: PROMPT RESTART
```

```text
date: 2026-06-17
artifact inspected: refs/user-feedback/20260616-image-a-artwork-only.png; outputs/reviews/train-exit-repair/train-exit-repair-options-correct-svg-overlay-side-by-side.png
user feedback: The train and tracks seem to stop at the left door flap and reach a barrier; add a tunnel there or a bridge arch that the train goes through.
rule learned: A run-through element must not merely touch a boundary or masonry mass. If a train/track reaches a door flap, bridge tower, seam, or panel transition, the composition should visibly show continuation through a tunnel, viaduct opening, bridge arch, or other plausible infrastructure.
applies to: berlin-skyline-live-example local repair; future skyline/city-scape tasks with trains, roads, bridges, or rails
next action: LOCAL PATCH
```

## Proof-Before-Spend Scout Notes

- Local scripted scout artifacts:
  - `outputs/reviews/scout-tests/scout-0-whole-reference-remix.png`
  - `outputs/reviews/scout-tests/scout-1-reference-faithful-rhythm.png`
  - `outputs/reviews/scout-tests/scout-2-strong-saloon-arch-hero.png`
  - `outputs/reviews/scout-tests/scout-3-continuous-city-band.png`
  - `outputs/reviews/scout-tests/scout-tests-contact-sheet.png`
  - `outputs/reviews/scout-tests/scout-test-report.md`
- Image-generation scout prompts:
  - `prompts/scout-test-imagegen-prompts.md`
- Image-generation scout verdict:
  - `outputs/reviews/scout-tests/imagegen-scout-verdict.md`
- Prompt strategies tested:
  - three-route contact sheet: reference-faithful, strong saloon arch, continuous city band.
  - direct whole-scene control.
  - strict red-zone/seam safety.
- Visual distinctness verdict: scripted boards are still too similar/faint; image-generation scouts are more diagnostic.
- Geometry/red-zone verdict: direct and strict prompts still let recognizable details hit red zones, especially train windows/doors and hotel facade detail.
- Style/cohesion verdict: whole-scene redraw is promising for watercolor cohesion.
- Decision unlocked: use whole-scene redraw for style/cohesion, but enforce SVG and red-zone safety downstream; do not trust direct prompting alone.
- Rule learned: proof-before-spend scout gates are required when the wireframe route is uncertain.

```text
date: 2026-06-16
artifact inspected: refs/user-feedback/20260616-best-option-dimension-drift.png; outputs/reviews/dimension-repair/dimension-repair-contact-sheet.png; outputs/reviews/dimension-repair/dimension-repair-report.md
user feedback: The top option is the most correct and has the best adapted top contour, but its dimensions are off compared to the SVG: the middle door panel is too wide, bottom sub-panels are too low, and the middle/bottom methods made the set much too wide.
rule learned: Use the top option as visual/composition evidence only. Do not accept model-drawn template dimensions. When the best visual option changes panel geometry, measure it against the SVG, test registration only as a diagnostic, and restart from an SVG-locked composition map with artwork-only generation.
applies to: berlin-skyline-live-example dimension-repair phase; future skyline/city-scape tasks
next action: PROMPT RESTART
```

## Dimension Repair Notes

- Best visual option:
  - `refs/user-feedback/20260616-best-option-dimension-drift.png`
- Exact SVG comparison artifacts:
  - `outputs/reviews/dimension-repair/diagnostic-best-vs-svg-aspect.png`
  - `outputs/reviews/dimension-repair/dimension-repair-contact-sheet.png`
  - `outputs/reviews/dimension-repair/dimension-repair-report.md`
- Active aspect verdict:
  - generated content aspect `1.841`;
  - exact SVG content aspect `1.463`;
  - generated frame needs about `0.795x` horizontal scale to match SVG aspect.
- Separator height verdict:
  - generated separator ratio from top `0.487`;
  - exact SVG separator ratio from top `0.400`;
  - bottom sub-panels start too low in the generated option.
- Panel width / center door verdict:
  - physical panel boxes can be forced by panel remap, but seam discontinuity
    and local warping are visible risks.
- Red-zone registration verdict:
  - generated red lanes are not reliable geometry; use the real SVG overlay.
- Saloon arch width verdict:
  - generated bridge/saloon arch reads too wide; next redraw must echo the SVG
    arch rather than replacing it with a wider arch.
- Bottom sub-panel height verdict:
  - lower composition must move upward into the true SVG lower region.
- Top-contour verdict:
  - the visual idea is good; keep the adapted skyline silhouette concept, but
    regenerate/trace it after geometry is locked.
- Repair routes tested:
  - global SVG-aspect registration:
    `outputs/reviews/dimension-repair/repair-option-1-global-svg-aspect.png`
  - panel-by-panel remap:
    `outputs/reviews/dimension-repair/repair-option-2-panel-remap.png`
  - SVG-locked composition map:
    `outputs/reviews/dimension-repair/repair-option-3-svg-locked-composition-map.png`
- Decision unlocked:
  - `SVG-LOCKED RESTART`
- Rule learned:
  - template guide lines should be external SVG overlays; image generation
    should produce artwork only unless a guide is explicitly marked as a rough
    non-production review layer.

## Durable Lessons To Consider Promoting

Promote a lesson only when it is project-specific, reusable, and verified by
the example run or direct user correction.

- Promoted into `.codex/skills/skyline-template-illustration/SKILL.md` and
  `docs/skyline-template-illustration-workflow.md`: run a proof-before-spend
  scout gate before full skyline generation when the composition route is
  uncertain or wireframes are visually similar.
- Promoted into `.codex/skills/skyline-template-illustration/SKILL.md` and
  `docs/skyline-template-illustration-workflow.md`: generated template/guide
  dimensions are not geometry authority; use artwork-only redraws and overlay
  the real SVG afterward.

```text
date: 2026-06-16
artifact inspected: refs/user-feedback/20260616-image-a-artwork-only.png; outputs/reviews/dimension-repair/image-a-overlay-contact-sheet.png; outputs/reviews/dimension-repair/image-a-overlay-report.md
user feedback: Image A should be shown with the SVG contour overlay. Repair options 1 and 2 look good as a plan.
measurement: Image A artwork bbox aspect 1.248; SVG active contour aspect 1.447. Direct width-locked and height-locked overlays reveal different drift modes; global SVG-aspect registration is useful as repair-option-1 diagnostic evidence.
rule learned: For promising artwork-only skyline candidates, make both width-locked and height-locked SVG overlays before choosing a repair route. Treat registration/remap as diagnostic proof, then decide whether final work needs SVG-locked redraw.
next action: review overlay with user before spending on the next generated/redrawn candidate
```

```text
date: 2026-06-17
artifact inspected: outputs/reviews/dimension-repair/image-a-svg-locked-local-patch-plan.png
user feedback: The TV tower extends too far above the contour and should be reduced, while remaining on the left side of the panel and not over the red center. The hotel red-center lane is acceptable because it has no important features, but the lower/base section is cropped on the left side of the narrow panel and must be fixed. The horses statue in the left narrow panel slightly overlaps the red center and needs slight realignment. The bridge on the right side of the door panel should align to the middle of the door flaps for symmetry if possible.
rule learned: In skyline local-patch planning, distinguish acceptable quiet red-center filler from prohibited recognizable features. Allow only controlled feature overflow above the top contour; preserve landmark bases; and check bridge/arch symmetry against the saloon-door center.
next action: LOCAL PATCH / REGISTERED EDIT, preserving Image A as the composition and style base
```

```text
date: 2026-06-17
artifact inspected: outputs/reviews/dimension-repair/image-a-correct-svg-overlay-clean.png; outputs/reviews/dimension-repair/image-a-correct-svg-overlay-diagnostic.png; outputs/reviews/dimension-repair/image-a-correct-svg-overlay-report.md
user feedback: The art is good, but the overlay dimensions are wrong because it appears lower or squished. Show the good art with the correct SVG overlay.
measurement: The square template preview active bbox aspect is 1.447, while exact SVG coordinate bounds give content aspect 1.463. The corrected overlay box on Image A is (0, 122, 1048, 838), using exact SVG aspect rather than preview-crop aspect.
rule learned: For skyline overlay review, do not let a raster preview crop or generated-art registration determine guide proportions. Use exact SVG coordinate bounds for overlay dimensions; use the preview only as the visible guide-stroke source.
next action: USER REVIEW of corrected full-color SVG overlay before applying the same gate to a newer generated candidate.
```

```text
date: 2026-06-17
artifact inspected: latest attempted image-generation patch prompts; .codex/skills/skyline-template-illustration/SKILL.md; docs/skyline-template-illustration-workflow.md
user feedback: "once the model is asked to “think about” contour/panels, it invents its own contour again." There must be a rule in the skill to NEVER do this.
failure: The patch prompt named panel proportions, contour behavior, saloon-door alignment, and guide-related geometry, which invited the image model to redraw/reinterpret the contour instead of applying only the four artwork corrections.
rule learned: For skyline artwork patches, never ask the image model to think about, preserve, adapt, trace, honor, fix, or improve SVG contour/panel/guide geometry. Keep geometry constraints in deterministic overlay/export artifacts and human notes; keep the generation prompt artwork-only and local-defect-focused.
next action: Update the skyline skill, workflow doc, and validation gate before continuing with any patch generation.
```

## Image-Gen Tooling Decision (no-API, subscription)

Confirmed working subscription image-gen paths in this environment (see global
memory `image-gen-no-api-paths`):

- OpenAI image gen via the Codex CLI (`codex exec`, `auth_mode=chatgpt`). Supports
  img2img by attaching the base with `-i <file>` (pass the prompt via stdin; `-i`
  is variadic and eats trailing args). Output lands in
  `~/.codex/generated_images/<session>/ig_*.png`.
- Nano Banana via the Antigravity CLI `agy` (`~/.local/bin/agy`, Google login).
  Headless: `agy --dangerously-skip-permissions --add-dir <dir> --print "<prompt> … save to <abs path>"`.
- The plain `gemini` CLI (oauth-personal) CANNOT generate images (image models 404).
- render-studio (`~/Documents/screenery-lean/render-studio`) is the API-key path
  (metered): pin `gemini-3-pro-image`/`gemini-3.1-flash-image-preview`/`gpt-image-2`,
  supports masked inpaint.

User direction (2026-06-17): OpenAI (Codex) is priority; Nano Banana (agy) for
testing and certain render types.

```text
date: 2026-06-17
artifact inspected: refs/user-feedback/20260617-image-a-train-tunnel-edit.png; outputs/reviews/train-exit-repair/openai-edit-vs-original-side-by-side.png; openai-edit-tunnel-zoom-side-by-side.png; openai-edit-correct-svg-overlay-{clean,diagnostic}.png
method: Codex img2img edit of approved Image A (OpenAI image gen, ChatGPT subscription, no API). Artwork-only safe-lane prompt; no SVG/contour/panel/red-zone/guide language. Strong "preserve entire composition, change only the tunnel" instruction.
result: The train now enters an integrated masonry arched tunnel/viaduct portal under the bridge tower (cream/tan stone, watercolor texture, yellow train visible continuing into the opening). NOT a dark pasted blob — fixes the A2/A3 "guide sketch" rejection. Composition preserved: overlay box (0,116,1048,832) ≈ Image A (0,122,1048,838); top-band drift 3.9, mid/lower ~22 (local edit + watercolor re-render). SVG guides land identically; tunnel near left red-center lane is acceptable quiet infrastructure.
not addressed this pass (still pending from earlier feedback): TV tower height reduction; hotel lower/base left crop; Brandenburg horse statue red-center overlap; right bridge-span symmetry to saloon-door middle.
next action: ASK USER — accept tunnel and move to remaining corrections, iterate the tunnel, or also render a Nano Banana (agy) comparison.
```
