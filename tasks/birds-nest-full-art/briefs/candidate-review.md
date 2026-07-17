GOAL: Blindly verify whether the generated Birds Nest candidate satisfies the user's reconstruction request
IN-SCOPE: Read-only visual comparison of the two sources and one generated candidate; no file edits

PHASE 0 — before any edit: inspect the named files and state any disagreement with the review contract. Silent compliance and silent scope additions are defects.

ACTIVE RULES:
- You are the cold verifier. Do not read the generator's rationale or prior verdicts.
- Judge style and semantic fidelity before dimensions. Palette similarity alone is insufficient.
- Inspect the actual candidate with vision, at full frame and crops if useful.
- No git mutations. Do not edit or create files.

USER-SUPPLIED LITERALS (verbatim):
- `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Birds Nest.png`
- `/Users/za/Downloads/Bird-Nest-Stadium.jpg`

CANDIDATE:
- `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/candidates/Birds-Nest-full-art-candidate-v1.png`

USER REQUEST TO VERIFY:
Create the high-resolution version of the entire underlying image printed across the panel render. Same style, color palette, and details; reconsider only proportions by making Beijing Bird's Nest Stadium slightly wider. The result must be a seamless flat image suitable for placement in Illustrator, not a product mockup.

SCORING (0, 1, or 2 each; PASS requires at least 8/10 and no critical failure):
1. Continuity/unwarping: one seamless flat scene, with no panel borders, seams, door aperture, hinges, feet, white holes, or product perspective.
2. Stadium identity/proportion: recognizable Bird's Nest; broad, long-low oval; approximately 10–15% wider than the render's stadium at similar height.
3. Architectural details: coherent irregular woven pale lattice, warm gold interior, muted red tiers; no melted or nonsensical structure at normal viewing size.
4. Style/palette: render-matched professional storybook watercolor/gouache, fine contour edge language, subtle paper tooth, comparable density and cool/warm dusk palette; not photorealistic or fibrous/felt.
5. Scene fidelity: render-derived left tree/globe lamp/curved planter/paving, central landscaping, right pool/lamp row/reflections, distant skyline and dusk clouds; no text, people, vehicles, flags, extra stadiums, or unrelated landmarks.

CRITICAL FAILURES:
- Any product-panel geometry or white cutout remains.
- Stadium is cropped, narrow/tall, or replaced by a generic arena.
- Style shifts to photorealism, 3D render, vector art, or felt/fibrous craft.
- Large obvious malformed lattice/artifact or any text/watermark.

DONE MEANS:
Return a score for all five criteria, PASS or FAIL, exact visual evidence for any deduction, and either `ACCEPT FOR UPSCALE` or one narrowly targeted regeneration instruction. Do not suggest broad redesign if it already passes.

LANE REPORT: summary <=250 words; changed_paths; evidence; scores; critical-failure check; assumptions; leftovers/concerns. End with exactly one status line: STATUS: COMPLETE | COMPLETE_WITH_CONCERNS (list) | BLOCKED (exact blocker) — then READY FOR JUDGING.
