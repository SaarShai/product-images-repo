# Space SVG Exports Batch: Checkpoint 1 Prompt Strategy

## Scope And Assumptions

- Batch task folder: `tasks/space-svg-exports-batch/`
- Target source SVGs:
  - `tasks/space-svg-exports-batch/source/np01-back-top.svg`
  - `tasks/space-svg-exports-batch/source/np01-front-bottom.svg`
  - `tasks/space-svg-exports-batch/source/np01-back-bottom.svg`
  - `tasks/space-svg-exports-batch/source/np02-front-top.svg`
  - `tasks/space-svg-exports-batch/source/np02-front-bottom.svg`
  - `tasks/space-svg-exports-batch/source/np02-back-top.svg`
  - `tasks/space-svg-exports-batch/source/np02-back-bottom.svg`
- Excluded by the task brief: `np01-front-top.svg`
- First checkpoint SVGs:
  - simple top-piece: `tasks/space-svg-exports-batch/source/np01-back-top.svg`
  - complex bottom-piece: `tasks/space-svg-exports-batch/source/np01-front-bottom.svg`

Do not generate a rectangular panel and crop it to the contour. Every prompt should tell the image model that the SVG contour, slots, holes, dashed safe areas, and keep-clear zones are hard layout constraints. Final masks are export guardrails only.

## Style Packet Plan

Use the existing watercolor control-panel packet as the style source:

- `tasks/space-svg-exports-batch/style-packet/style-packet.json`
- `tasks/space-svg-exports-batch/style-packet/reference-contact-sheet.png`
- `tasks/space-svg-exports-batch/style-packet/style-exemplar-sheet.png`

Attach only 8 to 10 high-signal crops per generation. Do not attach the entire packet unless a reviewer asks for broader context.

Core style attachments for all runs:

- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-body-texture.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-edge-treatment.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-body-texture.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-edge-treatment.png`

Version A extra attachments:

- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-left-region.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-right-region.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-04.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-right-region.png`

Version B extra attachments:

- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-center-region.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-01.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref01-chatgpt-image-jun-9-2026-11-17-34-pm-accent-component-02.png`
- `tasks/space-svg-exports-batch/style-packet/crops/ref02-chatgpt-image-jun-9-2026-11-19-45-pm-center-region.png`

## Shared Prompt Stem

Use this stem for every SVG and append the SVG-specific notes plus Version A or Version B.

```text
Create one Screenery SVG-template illustration in the exact attached SVG contour.

The SVG is the geometry source of truth. Design the watercolor control-panel illustration inside the contour from the start. Keep all slots, holes, internal cutouts, dashed safe-area gaps, red/yellow keep-clear zones, and production seams free of decorative elements. These areas should remain blank white or quiet background only where the template allows it.

Match the attached style-packet crops, not just their colors: soft blue watercolor wash, dark blue hand-painted rim, slight raised bevel, soft inner shadow, pale edge highlights, rounded simple controls, uneven ink outlines, watercolor granulation, and small coral, yellow, teal, and mint accents.

Do not make a rectangular dashboard and crop it into the SVG. Do not draw hard vector UI, photoreal metal, glossy app widgets, text labels, arrows, numbers, or callouts. Do not let recognizable controls cross holes, slots, seams, or keep-clear zones. The raw image should already look designed for this part before any final SVG mask is applied.
```

## Version A: Monitor And Signal Console

Intent: calmer, screen-led control panel with little monitors and signal readouts.

Append this to the shared prompt:

```text
Version A motif mix: make the part feel like a soft watercolor space monitor console. Use 1 to 2 tiny rounded monitor screens or radar screens, a small circular gauge, slider rails with square colored nubs, a few capsule indicator buttons, tiny screw heads, and sparse dotted signal lights. Keep the main monitors and dials in the largest safe pockets. Use only small dots or quiet blue wash near narrow corridors, slots, and holes. Leave the diagonal slot, rectangular cutout, circular holes, and stabilizer/keep-clear regions clean.
```

## Version B: Switch, Circuit, And Socket Panel

Intent: more tactile hardware variation without becoming dark machinery.

Append this to the shared prompt:

```text
Version B motif mix: make the part feel like a soft watercolor switch and socket service panel. Use rounded toggle pins, small knobs, capsule switches, simple circuit traces, tiny sockets, plug-like washers, bolt heads, and a few short colored bars. Keep circuitry decorative and sparse; route every trace around cutouts before rendering. No dense pipe maze, no dark mechanical bay, no sliced controls at mask edges. Preserve the same pale blue watercolor body, dark blue rim, soft bevel, and rounded friendly control vocabulary from the packet.
```

## SVG-Specific Notes

### `np01-back-top.svg`

One large top-piece contour with contained holes. Keep the small round hole near the upper-left and the large angled rounded path on the upper-right fully blank. Treat the bottom-center neck/notch formed by the outer contour as empty production geometry. Version A should emphasize one small monitor/radar readout, one gauge, and sparse slider/signal details in the broad safe body. Version B should use fewer, larger socket/switch elements and short circuit traces, kept well away from the contained holes.

### `np01-front-bottom.svg`

Two tall paintable panel regions with multiple contained cutouts. Keep the left circular hole, left vertical rounded slot, three right-side polygon/hex cutouts, and the lower-right vertical rounded slot blank and quiet. Version A should split monitor/signal language between the two tall regions without bridging cutouts. Version B should emphasize small sockets, rounded switch banks, and short circuit traces routed around each contained cutout.

### Remaining SVGs

After checkpoint approval, apply the same two-version pattern to the five remaining target SVGs. Before each run, identify which paths are outer paintable regions and which contained shapes are cutouts. Do not infer cutout roles from filenames alone.

## Best Checkpoint Approach After Two Illustrations

Generate exactly two illustrations first, then stop:

1. `np01-back-top.svg`, Version A monitor/signal console.
2. `np01-front-bottom.svg`, Version B switch/circuit/socket panel.

This tests whether the same watercolor control-panel style survives both a simple top contour and a complex bottom contour before spending tokens on all variants. If the checkpoint is approved, count those two images as the first accepted versions and generate the missing paired versions for those SVGs plus two versions for the remaining five target SVGs. If style is strong but one geometry drifts, keep the style prompt and tighten only that SVG's safe-pocket notes. If both are geometry-clean but too procedural, restart with a whole-panel redraw prompt using the raw candidates as composition maps plus the style packet crops. If both miss style, do not palette-shift them; run the style-agent element-sheet route first.

Checkpoint review requires:

- raw generated image;
- SVG overlay or clean-line export;
- debug mask or metadata proving zero painted pixels outside the contour and zero decorative pixels in cutouts;
- visual inspection against `style-exemplar-sheet.png`;
- decision: continue to Version B, local patch, or prompt restart.

Style-agent fallback, only if the checkpoint misses style:

```text
Generate an isolated watercolor control-panel element sheet from the attached packet crops. Do not draw any SVG contour or final panel. Produce separate little monitor screens, radar dials, capsule buttons, knobs, toggle pins, slider rails, tiny sockets, screw heads, short circuit-trace fragments, and blue rim/edge swatches. Match the packet crops in watercolor granulation, soft highlights, dark blue uneven outlines, shadow pooling, rounded friendly shapes, and pale blue body texture. Return a provenance note naming which crop each element family came from and mark the style verdict as REFERENCE-MATCH, PARTIAL, or RETRY.
```

Done means:

- two checkpoint illustrations exist and are reviewed;
- both used the same style packet crop strategy;
- geometry and style verdicts are recorded separately;
- the next move is chosen before generating the rest of the batch.
