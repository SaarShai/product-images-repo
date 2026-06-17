# Top-temp style-packet geometry fit checkpoint 1

## Result

Best current route:

1. Build a style packet from the actual reference images.
2. Ask a style agent to generate isolated watercolor control elements from that packet.
3. Hand the isolated elements to a geometry placer that owns SVG contour/cutout masks.

Best proof artifact:

- `tasks/top-temp-workflow-test/agents/style-imagegen-fit/style-imagegen-fit-preview-white.png`
- Summary: 12 of 13 proposed placements accepted, 1 rejected by the geometry gate, 0 outside-paintable pixels, 0 cutout pixels.

Checkpoint sheet:

- `tasks/top-temp-workflow-test/checkpoints/top-temp-style-packet-fit-checkpoint-1.png`

## Method Comparison

### A. Style-agent element sheet

- Source: `tasks/top-temp-workflow-test/agents/style-prompt-lab/imagegen-smoke-test-01.png`
- Verdict: strongest style match so far.
- Why: the agent received the actual style packet/reference sheet and produced reusable isolated parts instead of describing the style from memory.

### B. Style-imagegen fit

- Source: `tasks/top-temp-workflow-test/agents/style-imagegen-fit/style-imagegen-fit-preview-white.png`
- Verdict: best current geometry-fitted proof.
- Why: keeps style generation independent from SVG placement and lets the geometry gate reject unsafe placements.
- Remaining issue: composition still needs art direction; several controls are large/crowded and the lower-left gauge is too close to the edge.

### C. Packet-crop matte fit

- Source: `tasks/top-temp-workflow-test/agents/style-matte-elements/style-matte-elements-preview-white.png`
- Verdict: acceptable backup method.
- Why: uses true reference pixels and passes geometry, but still carries halos/background texture from source crops.

### D. Direct crop collage

- Source: `tasks/top-temp-workflow-test/agents/style-crop-collage/style-crop-collage-preview-white.png`
- Verdict: avoid for production.
- Why: mechanical geometry is clean, but broad crop patches bring source-background seams and scale mismatch into the fitted illustration.

## Next Prompt/Workflow Adjustment

Use separate agent roles:

- Style agents generate or transform isolated UI/control elements from the style packet only.
- Geometry agents place those elements in safe pockets derived from the SVG only.
- Review judges score style and geometry separately; geometry pass does not imply style pass.

Next image-gen prompt should ask for a larger isolated element sheet with more small/medium controls and fewer oversized large controls, then rerun the geometry placer with a pocket-aware composition plan.
