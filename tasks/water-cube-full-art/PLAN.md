# Water Cube full artwork reconstruction

## Goal

Create one continuous, front-facing, high-resolution print image that reconstructs the complete artwork shown across the panels in `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Water Cube/Water Cube.png`. Preserve the visible Water Cube architecture, pool, trees, jellyfish lights, bubbles, waterslide, palette, lighting, and detailed storybook watercolor/gouache finish. Remove all physical product geometry, folds, frames, hardware, feet, arch opening, and white studio background.

## Known facts and assumptions

- The Water Cube product folder initially contains only the 1448 x 1086 RGB render; no source artwork or Water Cube-specific Illustrator file is present.
- The sibling Marriott China production master uses a 3:2, 29194 x 19488, 300-DPI full-art raster, so 3:2 is the correct working composition family.
- The current proven repo workflow for this same Marriott extraction task generates a native 1536 x 1024 candidate, then creates an exact 4x 6144 x 4096 print master with deterministic illustration upscaling.
- The artwork hidden by the arch opening, folds, frame rails, and door must be reconstructed consistently from neighboring scene evidence.

## Composition contract

- One continuous 3:2 scene with no panel boundaries, cutouts, frame, or hardware.
- Left: moonlit tree canopy, moon and clouds, distant blue city skyline, classic warm streetlamp, paved promenade, shrubs, pool edge, three round stone bollards.
- Middle-left: the faceted Water Cube exterior spans the middle distance, with irregular translucent blue polygon cells, cool reflections, and softly glowing lower entrances.
- Middle-right/top: underwater-aquarium-like blue ceiling, suspended luminous jellyfish lights, small warm ceiling discs, floating translucent bubbles, reflective pool water.
- Right: tall curling aqua/cobalt waterslide, lap pool and lane ropes, blue tiled deck, round stone sphere, low aquatic plants, distant trees and skyline.
- Continue plausible architecture, pool, and ceiling detail through areas hidden by the product arch/door and panel folds.

## Non-goals

- Do not reproduce the Screenery product, panel seams, gray felt/stone frame, scalloped panel tops, arch opening, door, hinges, knob, feet, or studio background.
- Do not turn the illustration photorealistic or glossy 3D.
- Do not add text, logos, people, characters, signage, watermarks, or unrelated landmarks.

## Done means

1. A seamless RGB PNG exists under the Water Cube production folder's `Images/finals/`, with no product geometry or white holes.
2. The final is exactly 6144 x 4096 pixels, 3:2, with 300-DPI metadata and is an exact 4x upscale of the accepted native candidate.
3. A separate cold visual review confirms the composition, palette, motif inventory, detail density, and watercolor/gouache finish track the source render.
4. The final is visually inspected full-frame and at representative 100% crops for malformed architecture, waterslide, jellyfish, bubbles, seams, text, or generation artifacts.
5. The prompt, source path, candidate/final paths, and verification evidence are recorded in this task folder.

## Phases

1. Build and inspect a reference style packet from the source render; freeze the prompt.
2. Generate one reference-attached whole-scene candidate.
3. Cold-review the native candidate; make at most one targeted regeneration if a load-bearing criterion fails.
4. Upscale the accepted candidate exactly 4x, inspect it, and place the print master in `Images/finals/`.
5. Reconcile every user requirement and request confirmation.
