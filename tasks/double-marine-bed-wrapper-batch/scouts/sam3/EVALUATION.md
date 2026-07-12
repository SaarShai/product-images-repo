# SAM 3 image 14 scout evaluation

## Request evidence

- Endpoint: `fal-ai/sam-3/image`
- Request ID: `019f4a67-1eb4-74a2-8219-e2472d2cd65b`
- Paid segmentation requests: 1
- Estimated cost: USD 0.005
- Upload: 11.631734 seconds
- Segmentation request: 4.125812 seconds
- Total before local artifact generation: 16.544318 seconds
- Returned masks: 1, despite `return_multiple_masks=true` and `max_masks=32`
- Returned score: 0.8247258067131042
- Returned normalized box `[cx, cy, w, h]`:
  `[0.5014574048876382, 0.5067954302974865, 0.9366594774690116, 0.9382071358165102]`
- Raw mask: 941x1672 `L`, exactly source-sized, SHA-256
  `5e18d133a3fc06d815d72d6c262a98753df405a133e1000f60389f5c3271afb4`
- Mask alpha: binary only, 869,952 opaque and 703,400 transparent
  pixels; 55.2929033% opaque; zero soft pixels.

The response contained one concept-instance mask. All returned masks therefore
means mask 0. It was selected unchanged after inspecting the per-mask contact
sheet; no held-out benchmark annotation was consulted.

## Visual verdict

**FAILED as a complete background-removal route.** It is a useful coarse
semantic foreground proposal, but not a usable alpha or a sufficient trimap by
itself.

- **Proposal coverage:** The main coral, seaweed, and sandy base are broadly
  covered. Several detached objects appear only as fragments.
- **Enclosed background:** Failed badly. The mask treats the large coral mass as
  a mostly solid silhouette, retaining extensive blank white paper between
  coral branches. `roi-cutout_02.png` and the full magenta/black composites make
  this unambiguous. Some smaller pockets are removed, but coverage is
  inconsistent.
- **Sand preservation:** Broadly successful. The starfish, shells, rocks, pale
  sand, and most subtle sand wash remain in `roi-sand_base.png`.
- **Missed bubbles, fish, and tips:** Failed. Multiple bubbles and small fish
  are missing or fragmentary; `roi-outer_soft.png` shows a fish reduced to a
  partial fragment. Fine detached tips/details are also absent in the full
  magenta composite.
- **False-positive paper:** Failed. Large white paper regions remain fully
  opaque throughout the coral silhouette, including the target enclosed-pocket
  class.
- **Edge quality / white pixels:** Failed by construction. The returned mask is
  hard binary and performs neither matting nor foreground-color recovery.
  Pale/white rims remain conspicuous on black and magenta, especially in
  `roi-fringe_00.png` and along narrow seaweed edges.
- **Wrong deletion:** Failed. Detached illustrated elements are dropped or
  truncated, while some pale painted detail at the semantic boundary is cut by
  a hard mask.

## Architectural conclusion

The corrected multi-mask schema does not repair the underlying mismatch: the
long prompt produces one coarse whole-illustration instance mask, not a union of
fine object masks, and that mask collapses internal topology. SAM 3 may still be
useful as one source of sure-foreground/sure-background evidence, but it cannot
be promoted directly to alpha. It would require independent topology/trimap
supervision plus a matting and color-decontamination stage; those are outside
this one-request scout and must be judged in the parent architecture.

