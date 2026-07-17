## 1. Recommended architecture

Bet on a hybrid of **4 + 1**:

> Hard-mask inpainting defines where generation is physically permitted; ControlNet drives contour-aware composition; IP-Adapter plus the watercolor LoRA drives style in the same creative pass.

Staged order:

1. Parse the SVG into authoritative masks for:

   - paintable silhouette;
   - holes/cutouts;
   - frozen socket;
   - socket protection collar;
   - composition-safe pockets and top-boundary approach zones.

2. Build a composition control image that routes major forms around holes and makes top-edge behavior explicit—for example, spires tapering, bending, or terminating below/along the contour rather than continuing through it.

3. Run SDXL inpaint with:

   - inpaint mask = paintable silhouette minus holes minus socket protection;
   - Canny/line ControlNet = composition and contour structure;
   - IP-Adapter = actual reference images;
   - watercolor LoRA = collection rendering language;
   - the socket visible as frozen context, but not paintable.

4. Select candidates on style and contour-aware composition.

5. Composite the authoritative socket raster back.

6. Apply the exact SVG mask only for antialiasing/subpixel export cleanup, then run all defect-class gates.

This is effectively architecture 4 as the safety enclosure and architecture 1 as the synthesis engine.

Why this is the bet:

- Hard masking makes outside paint, painted holes, and socket mutation construction errors rather than prompt-following problems.
- ControlNet supplies the missing generation-time composition constraint. The mask alone prevents overflow but cannot teach a spire how to finish gracefully.
- IP-Adapter and the LoRA preserve reference-driven style in the same pass, avoiding the geometry drift and surface-only restyling risk of architecture 2.
- The local evidence already favors one-pass geometry plus LoRA, while the frozen run decisively disfavors guidance-only frontier generation.
- Architecture 3 remains a rescue/export method, not a creative architecture: it can make pixels legal but cannot make clipped composition intentional.

Architecture 2 should be retained only as a bounded fallback: if one-pass style is insufficient, rerender under the **same hard mask and ControlNet**, at low denoise. Do not allow an unconstrained creative-upscaler pass to reopen geometry.

## 2. Socket composite-back

Use the socket twice:

- A proxy appears in the initial inpaint canvas so the model composes around it.
- The authoritative raster is composited again after every creative or upscale operation.

The final composite-back belongs **after generation/upscaling and before export gates**. Never send the authoritative socket through img2img, an upscaler, color correction, or final sharpening.

Use three masks:

- `M_core`: exact authoritative socket alpha/footprint.
- `M_protect`: `M_core` dilated approximately 0.15–0.25% of the long image edge—about 3–5 px at 2048 px.
- `M_edge`: an outer 0.4–0.6% contextual band—about 8–12 px—for an intentional watercolor rim/shadow treatment.

Blending rules:

- Do not feather across `M_core`; every protected socket pixel must remain byte-identical.
- If the source has antialiased alpha, composite it premultiplied and without resampling.
- Feather only into the generated side of the seam, roughly 1–2 px at 2048 px.
- Put the visual join outside the socket: a narrow reference-derived rim, soft contact shadow, or pale highlight in `M_edge`. This makes the socket read as seated in the panel rather than pasted over it.
- Register the final-size authoritative socket once and hash it. Gate `socket-violated` by exact pixel comparison inside `M_core`, not perceptual similarity.

If a scale change is unavoidable, create the final registered socket asset once before the experiment and designate that transformed asset as authoritative; do not repeatedly resize it throughout the pipeline.

## 3. Cheapest discriminating experiment

Use the hardest representative panel: irregular top contour, at least one narrow cutout, one rectangular cutout, and the embedded socket.

Run five generations:

- Two seeds: recommended hard-mask + ControlNet + IP-Adapter + LoRA.
- Two identical seeds: same stack but without hard-mask enforcement.
- One low-denoise second-stage rerender of the best hard-mask result.

Do not spend another arm on frontier guidance-only or loose-gen-plus-clipping; the supplied evidence has already falsified them for this requirement.

Pass/fail:

| Gate | Required pass |
|---|---|
| Outside silhouette | 0 painted pixels in the raw candidate |
| Cutouts | 0 painted pixels in every hole |
| Socket | 0 differing pixels inside `M_core` after composite-back |
| Composition | No salient motif visibly cut by the contour; top forms terminate, taper, or merge intentionally |
| Style | At least one candidate wins a blind reference-match comparison over the geometry-only SDXL baseline |
| Cohesion | No visible hard-mask chop, blank gutter, socket halo, or pasted-raster seam |

Decision:

- If the recommended arm passes all five gates on either seed, adopt it.
- If the unmasked arm also passes both seeds, hard masking may be unnecessary for that class—but the existing frozen evidence makes this unlikely.
- Keep architecture 2 only if its style improvement is clearly preferred **and** it retains zero defect pixels and the same composition verdict. Any geometry regression kills it.
- If the hard-mask arm is geometrically exact but repeatedly produces visibly cut boundary objects, the mask is not the failure: the composition control map is. Revise that map rather than switching to post-hoc enforcement.

## 4. Pre-mortem

- **Conditioning conflict:** Strong IP-Adapter/LoRA influence weakens structural control or copies reference layouts. Expect to tune conditioning scales, not merely add prompt text.
- **Mask-edge artifacts:** Hard masks can create pale gutters, dark rims, or abruptly terminated watercolor texture. Judge full-frame output plus enlarged outer-edge, hole-edge, and socket-edge crops.
- **Registration/color-management drift:** Resizing, non-premultiplied alpha, sharpening, or ICC conversion can alter the socket despite correct masking. Freeze dimensions and color space, composite last, and verify exact pixels.

The project guidance materially reinforces this choice: generation should be designed inside SVG geometry, style must come from reference images, and mechanical masking should remain a verification/export guardrail rather than the mechanism that invents composition.


