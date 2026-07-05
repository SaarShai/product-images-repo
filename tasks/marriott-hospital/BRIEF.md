# Marriott Hospital — Hard Test Task

**Date:** 2026-07-04  
**Status:** Scaffolded (mechanical setup only — no generation, no API spend)

## Goal

Adapt the Updated Hospital 1.png design onto the city-skyline 3-panel template, maintaining Marriott-collection visual style from the two provided reference images (Police Station.jpg + Updated Fire Station.png). This is a hard test of the one-pass flux-control-lora-canny + LoRA route: complex geometry fit across three panels (1 central door + 2 narrow sides) while preserving architectural style consistency.

## User Decisions

- **Template:** city-skyline template (3-panel screen: 1 central door panel + 2 narrow side panels)
- **Style references:** Police Station.jpg + Updated Fire Station.png (Marriott China collection)
- **Approach:** One-pass flux + control-LoRA-canny + style-LoRA integration

## Asset Inventory

| Asset | Path | Dimensions | Role |
|-------|------|-----------|------|
| Source artwork | `source/Updated Hospital 1.png` | 1536×1024 px | Primary design to adapt |
| Style ref (Police) | `refs/Police Station.jpg` | 1400×787 px | Marriott style anchor |
| Style ref (Fire) | `refs/Updated Fire Station.png` | 1448×1086 px | Marriott style anchor |
| Template SVG | `geometry/city-skyline template.svg` | viewBox=6399.64×4376.93 | 3-panel die-cut contour |

## Template Structure

- **SVG viewBox:** 6399.64 × 4376.93 units
- **Top-level panels:** 3 (1 central + 2 narrow sides)
- **Central door panel:**
  - Geometry spec: `geometry/door.spec.json`
  - Aspect ratio: 0.6893
  - Contains door flap + dual-circle hinge elements
  - Black contour (#231f20) with taper geometry
- **Left narrow panel:**
  - Geometry spec: `geometry/left.spec.json`
  - Aspect ratio: 0.3895
  - Black contour (#231f20)
- **Right narrow panel:**
  - Geometry spec: `geometry/right.spec.json`
  - Aspect ratio: 0.3895
  - Black contour (#231f20)

All three panels share SHA signature `6c510169e284dff4` from the SVG template.

## Geometry Spec Tool Results

Spec generation successful for all three panels via `scripts/skyline_panel.py`:

```
spec -> geometry/door.spec.json   panel=door aspect=0.6893 sha=6c510169e284dff4
spec -> geometry/left.spec.json   panel=left aspect=0.3895 sha=6c510169e284dff4
spec -> geometry/right.spec.json  panel=right aspect=0.3895 sha=6c510169e284dff4
```

Each `.spec.json` file encodes:
- Panel geometry (contour + keep-clear zones)
- Aspect ratio constraint
- SHA for content-addressed cache invalidation

## Next Steps (Not Yet Executed)

1. Generate geometry guides (grayscale SVG outlines) for each panel
2. Build reference-style packets from the two Marriott refs
3. Run parallel generation batch (flux-control-lora-canny) across all three panels
4. Apply style LoRA + IP-adapter with consistent references
5. Gate on geometry IoU + VLM quality judges
6. If any panel fails: rerun that panel only, composite final 3-panel result
7. Collect all outputs (raw + exact + overlays) into `RESULTS/Images/`

## Assumptions

- `city-skyline template.svg` is the canonical 3-panel template for all Marriott hard-test work
- Updated Hospital 1.png is a 2D flat illustration (no depth/transparency); style refs confirm Marriott architectural painting aesthetic
- Dual-circle door hinge at center must be preserved (die-cut feature, not decorative)
- Narrow side panels (0.39 aspect) are tight; generation may require explicit framing lock to prevent zoom-out
- LoRA path available; flux v2 or faster model to be selected based on uptime/quota
- No manual masking; automask + measured gates only
