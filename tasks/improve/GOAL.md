# GOAL — improve the Screenery illustration-editing pipeline

## North star
Raise QUALITY, EFFICIENCY, and RELIABILITY of our image-editing workflow. Find ≥20 concrete improvements (then ≥20 more), implement each, and VERIFY each with a test before moving on. Bottleneck-first. Borrow-then-build. Simplify ("best part is no part").

## What our pipeline does (context)
We edit finished **watercolor + ink children's-book illustrations** that sit on **fixed SVG die-cut templates** (Screenery skyline panels, castle doors, etc.). Recurring task classes:
1. Redraw/restyle ONE element, change NOTHING else (byte-exact outside a mask).
2. Remove an element (car, text, sign) and reconstruct background in-style.
3. Move/relocate an element.
4. Fit generated artwork to an EXACT SVG contour + avoid internal cutouts/keep-clear zones.
5. Fix anatomy (hands, faces, car shapes) while matching the surrounding style.
6. Judge candidates (geometry fit + style + defects) and gate accept/patch/restart.

## Engines/tools today
- fal.ai via `scripts/falgen.py`: kontext (instruction edit), fill (masked inpaint), flux2edit, **eraser (Bria object removal)**.
- `scripts/openai_edit.py` (gpt-image-1 masked inpaint), `scripts/falref_apply.py` (Flux.2 reference-locked edit), `scripts/localgen.py` (local SDXL+watercolor-LoRA+IP-Adapter on Apple M3 Max / MPS), mflux (Flux.2-klein local).
- Composite + measured gate: `scripts/compose_fairy.py --diffmask` (outside-mask delta must be 0).
- Judges: VLM (Claude / GLM-executor) on hi-DPI crops; geometry gates via skyline_panel.py / geom_gate.

## Known bottlenecks / pain (from this + prior sessions)
- **MASK GENERATION is the #1 bottleneck** — masks are eyeballed/coded by hand; this session wasted ~dozen iterations with coords ~100px off. Need automatic, precise, prompt/click-driven masks.
- Removal reliability — flux-fill heals text back / adds cars; only a real eraser works.
- Verification is manual (I eyeball every crop) — need automated VLM/geometry checks in the loop.
- Geometry fitting to exact SVG still hard without ControlNet/img2img.
- Free/local vs paid routing not fully optimized.

## Hard rules (carry into every step)
- REFERENCE/GEOMETRY beats DESCRIPTION (feed images + geometry, not prose).
- "Change nothing else" must be MEASURED (gate=0 outside mask).
- Source art in Drive is READ-ONLY → copy first.
- Verify before claiming done; show full-size results; link text = filename.
- Prefer borrowing proven OSS/services over building from scratch; prefer free/local when competitive.

## Done-means (per improvement)
Each improvement has: (a) a one-line statement, (b) why/which bottleneck, (c) an implementation, (d) a concrete TEST that passes, (e) a banked lesson/memory if durable.
