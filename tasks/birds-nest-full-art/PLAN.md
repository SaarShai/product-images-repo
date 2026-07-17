# Birds Nest full artwork reconstruction

## Goal

Create one continuous, front-facing, high-resolution print image that reconstructs the artwork shown across the panels in `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Birds Nest.png`. Match its dusk watercolor/gouache illustration style, palette, lighting, landscaping, skyline, and architectural detail. Use `/Users/za/Downloads/Bird-Nest-Stadium.jpg` only to correct the real stadium identity and make the stadium slightly wider. Remove all product-panel geometry, seams, frames, hardware, feet, door opening, and white studio background.

## Known facts and assumptions

- The product folder contains only the 1420 × 1108 RGB render; there is no Illustrator file or source art there.
- The stadium photo is 1600 × 1000 and supplies identity/proportion evidence, not the target photographic style.
- With no production template dimensions present, use a 3:2 landscape master. This preserves the render's broad composition while giving the stadium the requested extra width.
- Generate a native landscape candidate, then create a 4× print master with a deterministic illustration upscaler.

## Composition contract

- Continuous scene, no panel boundaries or cutouts.
- Slightly wider Bird's Nest Stadium centered across the middle distance, recognizable oval woven-lattice structure.
- Left: large leafy tree, globe lamp, curved planted promenade, layered Beijing skyline.
- Center: open stone-paved approach leading toward the stadium.
- Right: reflecting pool/canal, warm lamp reflections, landscaped promenade, skyline.
- Dusk sky in muted lavender-blue, peach, and apricot; stadium glows warm gold and muted red.
- Professional storybook architectural watercolor/gouache with fine ink/pencil contour and subtle paper tooth; no fibrous/felt texture.

## Non-goals

- Do not reproduce the physical Screenery product, frames, cutouts, door, hardware, or white background.
- Do not turn the scene photorealistic.
- Do not add text, logos, people, vehicles, flags, or unrelated landmarks.

## Done means

1. A continuous RGB PNG exists in the production folder under `Images/finals/`, with no panel geometry or white holes.
2. The final is at least 6000 px wide and preserves a 3:2 landscape ratio.
3. A separate cold visual review confirms style/palette/detail continuity with the render and recognizable, slightly wider Bird's Nest proportions informed by the photo.
4. The final is visually inspected at full frame and representative 100% crops for malformed lattice, seams, text, or generation artifacts.
5. The exact final prompt and candidate/final paths are recorded in this task folder.

## Phases

1. Analyze both source images and freeze the prompt.
2. Generate one reference-attached whole-scene candidate.
3. Cold-review; make at most one targeted regeneration if a load-bearing criterion fails.
4. Upscale the accepted candidate 4×, inspect, and copy to `Images/finals/`.
5. Reconcile every user requirement and request confirmation.
