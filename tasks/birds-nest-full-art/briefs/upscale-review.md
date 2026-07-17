GOAL: Verify that the 4× print candidate preserves the accepted artwork without introducing upscale defects
IN-SCOPE: Read-only visual comparison of one native candidate and its 4× upscaled PNG; no file edits

ACTIVE RULES:
- Inspect both actual files with vision. Judge full frame and representative 100% crops.
- Do not read generator rationale. No git mutations. Do not edit or create files.

NATIVE CANDIDATE:
- `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/candidates/Birds-Nest-full-art-candidate-v1.png`

4× PRINT CANDIDATE:
- `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/candidates/Birds-Nest-full-art-candidate-v1-x4.png`

REVIEW SURFACES:
- `/Users/za/Documents/product images repo/tasks/birds-nest-full-art/upscaled-full-review.jpg`
- `/Users/za/Documents/product images repo/tasks/birds-nest-full-art/upscaled-100pct-crops.jpg`

PASS CRITERIA:
1. 4× image is 6144 × 4096 RGB PNG and preserves the 3:2 composition.
2. No new seams, halos, ringing, doubled contours, block boundaries, melted lattice, text, or edge artifacts.
3. Stadium lattice, lamps, skyline, foliage, paving, and water reflections remain coherent at full frame and 100% crops.
4. Upscale does not materially shift the render-matched palette or push the image toward photorealism.
5. The smoothing does not erase essential architectural detail; any reduction of coarse grain is acceptable.

DONE MEANS:
Return PASS or FAIL for each criterion and either `ACCEPT AS PRINT MASTER` or one exact blocker. Include changed_paths: none. End with STATUS and READY FOR JUDGING.
