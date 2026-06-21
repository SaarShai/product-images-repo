# Q — auto-repair loop (redraw → erase stamped text → re-judge)

Reconstructed by the main agent (subagent Q ended before writing its own report).

## Problem
`edit.py --op redraw` (Flux Fill) produces a clean element BUT often STAMPS unwanted
signage/text on it ("TAXI", "CLASSIC") despite positive no-text prompting — the known
flux-fill heal/add-text bias. The judge + text_gate correctly FLAG it (leftover_text=True)
→ RESULT NEEDS-REVIEW. Goal: close the loop so the edit self-heals instead of stopping.

## Approach (implemented in scripts/edit.py)
After the judge step, if `_has_unwanted_text` (judge.leftover_text OR text_gate found text):
1. Locate text — prefer PaddleOCR boxes (`text_gate.py --json`), map to full-image coords;
   fallback = `automask.py --prompt "text and lettering on the car"` over the element bbox.
2. Build a tight mask of the text boxes (dilated), erase with fal Bria eraser on a context
   crop, composite back with `compose_fairy.py --diffmask` (outside-mask byte-exact).
3. Re-run judge + text_gate. Stop when clean or after 2 passes. Record `repair_passes` +
   per-pass log in the provenance JSON.

## Bug found + fixed (by the end-to-end capstone, not unit tests)
First run did 2 passes but `cleared=False` — it erased the WRONG region (top-left corner).
Root cause: OCR boxes from `text_gate` run on the JCROP are jcrop-LOCAL, but were applied as
FULL-image coords (jcrop origin never added). Fix: `textgate_boxes_to_full(tg, jcrop_box)` now
offsets every box by the jcrop origin (jx0,jy0). Lesson: always test the full pipeline on a
REAL task with REAL (long) inputs — short-input unit checks missed both this and the gencache
OSError.

## Verified result
Capstone (melted mid taxi → "a clean classic NYC yellow sedan"):
- BEFORE fix: text_bbox ~[312,55,560,237] (jcrop-local) → erased corner → RESULT NEEDS-REVIEW.
- AFTER fix: text_bbox [2160,3020,2408,3202] (the cab), **1 repair pass**, judge leftover_text=False,
  text_gate no_text=True, pixel gate 0, leak PASS, **RESULT SUCCESS**. Eyeballed: clean sedan,
  no "TAXI/CLASSIC" lettering.

Closes the generate→verify→repair→re-verify loop. See memory [[edit-pipeline-harness]].
