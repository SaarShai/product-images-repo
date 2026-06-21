# GOAL — fix ONLY the bottom-left fairy in `door - v5.png`, change nothing else

Source (READ-ONLY, copied): `tasks/fairy-fix/src/door-v5.png` (2620×3752).
Target element: the **bottom-left fairy** standing in the flower bed.
Full-res fairy bbox: **(160, 2660) – (480, 3110)** (320×450).
Context crop used for regen: **(60, 2560) – (720, 3300)** (660×740); fairy sub-box within crop = (100,100,420,550).

## Hard requirements
1. **Change ONLY the fairy region.** Every pixel outside the fairy mask must be IDENTICAL to the original (measured: outside-mask max-delta ≈ 0). The castle, door, flowers elsewhere, and the other 4 fairies must not change.
2. Redraw the fairy as: cuter / more "animated", larger head, expressive oversized eyes, small cute nose, simplified body, **more modest outfit**, soft outlines.
3. Fix fine-detail distortions: clean face, exactly 5 well-formed fingers per visible hand, proper feet/toes, natural limb proportions.
4. Keep the EXACT same painterly watercolor style, textured brush strokes, soft lighting, and identical pastel color palette as the rest of the image.
5. Seamless blend — no visible seam/halo where the new fairy meets the original flowers/wall.

## Method (why)
Whole-image regen drifts every pixel → violates (1). So: regenerate the fairy inside a **context crop** (carries surrounding style/flowers), then **soft-mask composite** only the fairy silhouette back onto the untouched original. Outside the mask is byte-identical by construction. Also try Adobe Firefly masked generative fill (true inpaint).

## Acceptance
- Outside-mask delta gate: max-delta ≈ 0 (deterministic, must pass).
- Fairy-quality gate (VLM, advisory): cute/modest/animated, 5 fingers, clean face, watercolor-consistent, seamless.
- Present all candidates full-size with filename links; user picks. Start with bottom-left fairy only.
