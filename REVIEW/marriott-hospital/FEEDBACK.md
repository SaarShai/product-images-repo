# Marriott Hospital — review + feedback

Full folder path: `/Users/za/Documents/product images repo/REVIEW/marriott-hospital/`

## CURRENT CANDIDATE: r9 (two-stage route — geometry + true watercolor)

Your geometry catch fixed. New route: geometry-locked init (arch cut edges in the
control channel + new MRWC watercolor LoRA) → ref-anchored watercolor restyle with
position lock. Result = style B (luminous storybook watercolor) at correct geometry.

Look at:
1. `r9-screen-preview.jpg` — the full 3-panel screen. **Main deliverable.**
2. `r9d_overlay.png` — door with red cut paths: saloon arch aligned (your check, now standard).
3. `r9d_door_cut.png`, `r9d_left_v2_cut.png`, `r9d_right_cut.png` — full-res panels.
   IoU: 0.966 / 0.974 / 0.974; geom_gate PASS; all signage blank.
4. `r9-overlay-board.jpg`, `r8-overlay-board.jpg`, `geometry-overlay-board.jpg` — the
   geometry evidence trail (why restyle-only and prompt-only both failed).

## Notes
- Left panel first version painted "CITY HOSPITA" — root cause: my style-ref crop
  contained the lettering; re-cropped text-free and re-ran (Rule 0 now covers restyle refs).
- Remaining polish available on request: per-panel best-of-N at this recipe, finish
  chain (2x upscale + cutout), A/H flavor variants of the same recipe.

## Your feedback
- r9: good direction? adjustments (wash intensity, luminosity, detail density, palette)?
- Promote to production Images/finals? (yes/no + Drive folder if applicable):

---
Earlier rounds kept in this folder for comparison: style-options-board.jpg (8 styles
A-H), r3 smooth / r4 felt / r5 fiber (rejected) / r6 loose watercolor / r7 read probe.
