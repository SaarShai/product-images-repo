# Berlin Skyline Live Example Handoff

Date: 2026-06-17

This is the project-local handoff for continuing the Berlin skyline /
city-scape three-panel Screenery task. It collates the relevant session log,
decisions, artifacts, corrections, and next steps so a new Codex session can
pick up without relying on Codex-only state.

## Start Here

1. Read `AGENTS.md`.
2. Read `.codex/skills/skyline-template-illustration/SKILL.md`.
3. Read `docs/skyline-template-illustration-workflow.md`.
4. Read this file.
5. Read `tasks/berlin-skyline-live-example/skyline-example-feedback.md`.
6. Inspect the latest images listed in "Current Visual State".

Useful commands:

```bash
git status --short -- tasks/berlin-skyline-live-example .codex/skills/skyline-template-illustration/SKILL.md docs/skyline-template-illustration-workflow.md
python3 scripts/validate_svg_template_workflow.py
python3 tasks/berlin-skyline-live-example/make_image_a_correct_svg_overlay.py
```

## Current Status

We are building a reusable skyline/city-scape skill and simultaneously using a
Berlin live example to learn from real feedback. The reusable skill and workflow
doc were already updated and pushed with a key rule: do not let image generation
reinterpret the SVG/template geometry.

Committed change:

- `da8855f Add skyline prompt boundary preflight`

The Berlin task folder still contains many untracked local artifacts. That is
expected. Do not delete them. They are the working evidence for this example.

Current user focus:

- The chosen Berlin artwork is visually good, but it needs local corrections.
- The most recent correction concerns the U-Bahn: the train/tracks appear to
  stop at the left saloon door flap and hit a barrier.
- We tried tunnel/bridge-arch repair concepts.
- The user rejected the "guide sketch" quality and asked for the tunnel/arch to
  be integrated into the illustration.
- An integrated local mockup now exists, but it is not final.

## Source Inputs

Template:

- `tasks/berlin-skyline-live-example/source/template.svg`
- Original default template:
  `assets/skyline/city-skyline template.svg`

Main references:

- `tasks/berlin-skyline-live-example/refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg`
  - User-provided 4-panel Berlin watercolor render reference.
  - Style and palette reference.
  - Contains Berlin landmarks, U-Bahn, and a separate right-side tower panel.
- `tasks/berlin-skyline-live-example/refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg`
  - User-provided reference for Ritz-Carlton / Beisheim / Potsdamer Platz
    high-rise.

Task notes and logs:

- `tasks/berlin-skyline-live-example/session-brief.md`
- `tasks/berlin-skyline-live-example/skyline-example-feedback.md`
- `tasks/berlin-skyline-live-example/template-manifest.json`
- `tasks/berlin-skyline-live-example/asset-manifest.json`
- `tasks/berlin-skyline-live-example/review-judge.md`

Style packet:

- `tasks/berlin-skyline-live-example/style-packet/reference-contact-sheet.png`
- `tasks/berlin-skyline-live-example/style-packet/style-exemplar-sheet.png`
- `tasks/berlin-skyline-live-example/style-packet/style-packet.json`

## User-Approved Choices

Checkpoint approvals:

- `1A`: source packet approved.
- `2A`: Berlin landmark roster approved.
- `3A`: whole-set-first composition strategy approved.
- `4A`: visual premise approved.

Approved visual premise:

- One Berlin city-scape family across the three panels.
- Low yellow Berlin U-Bahn runs through the set.
- Central saloon-door area uses a simplified bridge / viaduct arch motif over
  quiet water/stone.
- Top contour adapts to building silhouettes.
- Sky/removable background stays white or very pale paper-white.

Panel content:

- Left narrow panel: Fernsehturm + Brandenburg Gate.
- Central door panel: Berliner Dom + Kaiser Wilhelm Memorial Church style
  tower/spire + simplified bridge/viaduct base.
- Right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise.
- Do not include the optional green Potsdamer traffic-light/clock tower unless
  the user later asks for it.

## Landmark Verification

The user asked to verify unfamiliar central landmarks/bridge.

Record:

- `tasks/berlin-skyline-live-example/checkpoints/berlin-landmark-verification.md`

Verified / adopted:

- Berliner Dom for the central dome.
- Kaiser Wilhelm Memorial Church for the damaged/old tower or spire-like church
  element.
- Oberbaum Bridge only as inspiration for a Berlin bridge/viaduct arch.
- Ritz-Carlton / Beisheim Center / Potsdamer Platz for the right high-rise,
  including its full lower podium/wing.

Important: the bridge should not need readable signage or literal exactness.
It can be a simplified Berlin bridge/viaduct motif.

## Current Visual State

Primary artwork base:

- `tasks/berlin-skyline-live-example/refs/user-feedback/20260616-image-a-artwork-only.png`

Correct SVG overlay for that base:

- `tasks/berlin-skyline-live-example/outputs/reviews/dimension-repair/image-a-correct-svg-overlay-clean.png`
- `tasks/berlin-skyline-live-example/outputs/reviews/dimension-repair/image-a-correct-svg-overlay-diagnostic.png`
- `tasks/berlin-skyline-live-example/outputs/reviews/dimension-repair/image-a-correct-svg-overlay-report.md`

Important overlay facts:

- Exact SVG content aspect: `1.463`
- Correct overlay box on Image A: `(0, 122, 1048, 838)`
- Template preview active aspect was `1.447` and must not be used as final
  geometry authority.
- The preview PNG may provide visible guide pixels only.

Latest train/tunnel repair artifacts:

- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/train-exit-repair-options-side-by-side.png`
  - First rough A/B: tunnel portal vs bridge arch.
- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/train-exit-repair-options-refined-side-by-side.png`
  - A2/B2 refined but still sketch-like.
- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/train-exit-repair-options-refined-correct-svg-overlay-side-by-side.png`
  - A2/B2 with correct SVG overlay.
- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/option-a2-vs-a3-integrated-tunnel-side-by-side.png`
  - A2 compared to A3.
- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/option-a3-integrated-tunnel-portal-artwork.png`
  - Latest integrated local tunnel mockup.
- `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/option-a3-integrated-tunnel-portal-review.png`
  - A3 with correct SVG overlay.

Current judgment:

- A2 solved placement/readability better than the first sketch, but the user
  correctly said it was still just a guide sketch.
- A3 is more integrated: masonry, shadow, rail continuation, watercolor texture.
- A3 is still probably too dark and visually central for the delicate Berlin
  watercolor style.
- Next best step is not more guide drawing. Either:
  - lighten/refine A3 locally into a subtler illustrated bridge/tunnel portal;
    or
  - use A3 as a very explicit visual target for an artwork-only image edit /
    regeneration, then overlay the real SVG afterward.

## User Feedback To Preserve

Earlier key corrections:

- Top option from the three-option generated set was most correct, but its
  dimensions did not match the SVG. The middle and bottom options were too wide.
- The good generated artwork may be used as visual/composition evidence only
  when dimensions drift.
- The door panel in the generated options became too wide and bottom sub-panels
  too low compared with the SVG.
- Correct overlay must use the SVG coordinate system, not a square screenshot
  or generated guide geometry.

Specific artwork corrections still relevant:

- TV tower extends too far above the contour. Reduce it. Keep it left so it
  does not cross the left panel's red center lane.
- Hotel/high-rise: quiet facade in the red center is acceptable, but the lower
  section/base is cropped on the left side of the right narrow panel and must
  be fixed.
- Brandenburg Gate horse statue slightly overlaps the red center and needs a
  small realignment.
- Bridge on the right side of the central door panel should align more closely
  to the middle of the door flaps for symmetry if possible.
- Train and tracks must not terminate at a wall/barrier. Add a believable
  tunnel, bridge arch, viaduct opening, or similar infrastructure so the train
  visibly continues.

Most recent user feedback:

- The tunnel concept is directionally right, but the previous tunnel was not
  properly illustrated; it was just a guide sketch.
- The tunnel/arch must be integrated into the illustration.

## Hard Rule Learned: Prompt Boundary

This is the most important process lesson from the session.

Never ask the image model to think about, preserve, adapt, trace, honor, fix,
or improve the SVG contour, panel proportions, guide positions, red zones,
top-contour line, saloon arch, or production geometry during an artwork patch.

Reason: once the model is asked to think about contour/panels, it invents its
own contour again.

The skill and workflow now include:

- hard boundary against template-geometry language in generation prompts;
- prompt boundary preflight;
- forbidden prompt concepts unless making a non-production diagnostic guide:
  `SVG`, `contour`, `panel proportions`, `red zone`, `green line`,
  `orange arch`, `saloon-door guide`, `template guide`, `safe margin`,
  `production stroke`.

Put those constraints in:

- task notes;
- verifier checklist;
- deterministic overlay/export step;
- masks/crops outside the model.

Do not put them in the creative image-generation prompt.

## Safe Creative Prompt Lane

If using image generation for the next repair, keep the prompt artwork-only and
local-defect-focused. Do not mention SVG, contours, panels, guide colors, red
zones, saloon-door guides, or template proportions.

Safe prompt direction:

```text
Using the same delicate Berlin watercolor cityscape artwork and preserving the
overall composition, integrate a believable small masonry railway tunnel or
viaduct opening where the yellow train and tracks currently end. The train
should visibly continue into the opening instead of stopping at a wall. Match
the existing bridge stonework, pencil line weight, muted cream/tan masonry,
soft blue-gray shadows, and pale watercolor texture. Keep the sky/background
white. Do not add labels, guide marks, dashed lines, borders, or technical
template marks.
```

Optional local-defect additions, still safe:

```text
Also keep the tunnel subtle and secondary so it does not become the visual
focus. It should feel like part of the existing bridge/rail infrastructure, not
like a new dark object pasted on top.
```

Avoid prompt language like:

- panel
- SVG
- contour
- red center
- guide
- saloon arch
- safe margin
- template geometry

Those belong only in review notes and overlay verification.

## Verification Requirements

Before claiming a repair is done:

1. Inspect artwork-only candidate.
2. Create correct SVG overlay using exact SVG aspect:

   ```bash
   python3 tasks/berlin-skyline-live-example/make_image_a_correct_svg_overlay.py
   ```

   If using a newer candidate, adapt the script or the `ART_PATH` to that local
   image first.

3. Inspect overlay image manually/visually.
4. Check:
   - no generated template lines or guide marks are accepted as geometry;
   - train continuation reads clearly;
   - tunnel/arch is integrated, not a guide sketch;
   - tunnel/arch does not become too dark or central;
   - specific features avoid red lanes where practical;
   - no new crop/split of landmarks;
   - sky remains white/paper-white.

## Scripts Created During This Session

Dimension / overlay:

- `tasks/berlin-skyline-live-example/make_image_a_correct_svg_overlay.py`
- `tasks/berlin-skyline-live-example/make_image_a_contour_overlay.py`
- `tasks/berlin-skyline-live-example/make_dimension_repair_tests.py`
- `tasks/berlin-skyline-live-example/make_image_a_local_patch_plan.py`

Scout / placement:

- `tasks/berlin-skyline-live-example/make_placement_options.py`
- `tasks/berlin-skyline-live-example/make_scout_tests.py`
- `tasks/berlin-skyline-live-example/make_scout_test_probes.py`

Current train repair:

- `tasks/berlin-skyline-live-example/make_train_exit_repair_options.py`

Note: these scripts are local workflow artifacts. Some are untracked. Do not
assume they are polished library code.

## Process Lessons Already Promoted

Promoted into:

- `.codex/skills/skyline-template-illustration/SKILL.md`
- `docs/skyline-template-illustration-workflow.md`
- `scripts/validate_svg_template_workflow.py`

Lessons:

- Run proof-before-spend scout gates when composition route is uncertain.
- Faint lookalike wireframes are weak evidence.
- Generated guide/template dimensions are not authority.
- Use the real SVG as coordinate authority.
- Overlay review dimensions must come from SVG coordinate bounds.
- Never ask the image model to reason about template geometry during artwork
  patch prompts.

Validation:

```bash
python3 scripts/validate_svg_template_workflow.py
```

This passed before commit `da8855f`.

## Current Risks

- A3 tunnel may be too dark and visually central.
- The tunnel area may still feel patched rather than naturally redrawn.
- If a broad image-generation edit is used, it may accidentally change the
  whole composition or reintroduce incorrect contour/guide geometry.
- The TV tower, hotel base, horse statue, and bridge symmetry comments remain
  pending unless addressed by a later integrated candidate.
- Many Berlin task artifacts are untracked. Avoid broad cleanup or reset.

## Recommended Next Step

Use the current A3 integrated portal as evidence, not final approval. The next
iteration should produce a more integrated, lighter, watercolor-consistent
tunnel/viaduct opening.

Preferred path:

1. Create one local lighter A4 repair variant from A3:
   - smaller/duller dark mouth;
   - more cream/tan stone;
   - softer pencil lines;
   - fewer black speckles;
   - rail continuation remains visible;
   - blends into existing bridge deck and water reflections.
2. Show A3 vs A4 artwork-only.
3. Show A4 with correct SVG overlay.
4. Ask the user whether A4 is integrated enough, or whether to use image
   generation for a more natural redraw.

If using image generation:

1. Use the safe creative prompt lane above.
2. Do not mention any template geometry concepts.
3. Save the resulting local candidate image into
   `tasks/berlin-skyline-live-example/outputs/reviews/train-exit-repair/`.
4. Overlay the real SVG afterward.

## Suggested New Session Opening

```text
Please continue the Berlin skyline live example. Start by reading
tasks/berlin-skyline-live-example/HANDOFF.md, then inspect the latest A3
integrated tunnel artifact and create a lighter/more naturally integrated A4
tunnel/viaduct repair. Keep all template geometry out of creative prompts and
verify with the correct SVG overlay afterward.
```

