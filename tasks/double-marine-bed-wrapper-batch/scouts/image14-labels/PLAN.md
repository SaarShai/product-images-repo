# Image 14 sparse correction labels — plan

## What and why

Create a native 941×1672 transparent RGBA human-correction overlay for the Photoshop background-removal proposal. Opaque red labels identify only visually certain foreground that Photoshop deleted; opaque blue labels identify only visually certain background that Photoshop kept. Everything else remains transparent/unknown. The labels are deliberately sparse so a downstream solver can expand from them without receiving a hidden full segmentation.

## Scope

- Read only the named original source, Photoshop proposal alpha, and red diagnostic.
- Write only this scout folder and the product `Images/candidates/bg-assisted-v1/image14-labels/` folder.
- Do not inspect any benchmark or guard artifact.
- Do not change solver code, run a solver, write finals, alter prior candidates/source, or commit.

## Assumptions

- Pixel coordinates use `(x, y)` with origin at the upper-left of the 941×1672 source.
- A short explicit list of visually chosen anti-ambiguous polylines is a faithful model of a brief human correction pass.
- Pure blue is omitted unless a kept region is unambiguously paper background, not translucent watercolor or an enclosed negative space whose status is uncertain.

## Phases and gates

1. Verify exact paths, dimensions, modes, and SHA-256 hashes. Inspect source, alpha, and diagnostic at native resolution.
2. Obtain a separate read-only visual verifier's interpretation and coordinate suggestions. Reconcile disagreements conservatively by leaving disputed pixels unknown.
3. Record explicit stroke coordinates and widths in a deterministic Pillow build script. The script must not infer labels from source colors or copy/threshold the Photoshop alpha.
4. Build the RGBA annotation, source overlay, and review contact sheet in the scout folder; copy the exact deliverables to the product candidate folder.
5. Have a separate verifier inspect the final artifacts, then report facts without issuing a self-verdict.

## Done means

- The annotation is exactly 941×1672 RGBA and contains only transparent `(0,0,0,0)`, opaque red `(255,0,0,255)`, and, only if justified, opaque blue `(0,0,255,255)`.
- Explicit sparse strokes cover only visually certain correction loci; pixel counts, fraction, color counts, stroke count, and widths are reported.
- README, deterministic script, native overlay, and review contact sheet make coordinates and visual reasoning auditable.
- Fresh checks prove dimensions/mode/colors/transparency/nonoverlap and the original source hash is unchanged.
- A separate verifier inspects phase 0 and the final artifacts; no solver run, benchmark access, finalization, source/prior-candidate mutation, commit, or self-verdict occurs.
