# Style Element Placer Review

Verdict: ACCEPT

Evidence inspected:
- `tasks/top-temp-workflow-test/source/template.svg`
- `tasks/top-temp-workflow-test/template-manifest.json`
- `tasks/top-temp-workflow-test/style-packet/style-packet.json`
- `tasks/top-temp-workflow-test/agents/strict-pocket/generate_strict_pocket.py`
- `tasks/top-temp-workflow-test/agents/style-element-placer/place_style_elements.py`
- `tasks/top-temp-workflow-test/agents/style-element-placer/placements-demo.json`
- `tasks/top-temp-workflow-test/agents/style-element-placer/style-element-placer-artwork.png`
- `tasks/top-temp-workflow-test/agents/style-element-placer/style-element-placer-preview-white.png`
- `tasks/top-temp-workflow-test/agents/style-element-placer/style-element-placer-overlay.png`
- `tasks/top-temp-workflow-test/agents/style-element-placer/style-element-placer-mask-debug.png`
- `tasks/top-temp-workflow-test/agents/style-element-placer/style-element-placer-metadata.json`

Passes:
- The placer reuses the strict-pocket SVG parser/mask behavior and keeps `path[0]` as the outer contour while treating `path[1]` and `path[2]` as internal keep-clear cutouts.
- Each placement is transformed into its requested box, converted to an alpha mask, and checked against the eroded paintable mask before compositing.
- Four packet-crop stand-ins are accepted with `outside_eroded_paintable_alpha_pixels: 0` and `inside_cutout_alpha_pixels: 0`.
- Two intentional unsafe placements are rejected before drawing: one crosses the diagonal slot, and one crosses the lower-right round cutout/edge margin.
- Final exported artwork has `final_outside_outer_alpha_pixels: 0`, `final_outside_paintable_alpha_pixels: 0`, and `final_cutout_alpha_pixels: 0`.

Verification command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tasks/top-temp-workflow-test/agents/style-element-placer/place_style_elements.py --require-pass
```

Verification output:

```json
{
  "planned_placements": 6,
  "accepted_placements": 4,
  "rejected_placements": 2,
  "accepted_outside_eroded_paintable_alpha_pixels": 0,
  "accepted_inside_cutout_alpha_pixels": 0,
  "final_outside_outer_alpha_pixels": 0,
  "final_outside_paintable_alpha_pixels": 0,
  "final_cutout_alpha_pixels": 0
}
```

Failures or risks:
- The demo uses opaque style-packet crops as stand-ins, so the checker treats each resized crop rectangle as element alpha. This is stricter than a future transparent isolated PNG, but less visually polished.
- This is a placement harness demo, not final production artwork.

How this separates style agents from geometry agents:
- Style/image-generation agents only need to return isolated PNG elements plus provenance from the style packet.
- `placements-demo.json` is the handoff surface: it names element image paths and desired boxes, without asking the style agent to understand the SVG.
- `place_style_elements.py` owns SVG geometry, path roles, eroded paintable-mask checks, rejection, compositing, overlay/debug exports, and final alpha verification.
- Rejected placements remain visible only in overlay/debug/metadata, which makes geometry failures diagnosable without contaminating the clean artwork.

Next move:
- Replace the packet-crop stand-ins with transparent element PNGs from a future style agent and keep the same placement/verification harness.
