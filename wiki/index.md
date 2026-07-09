# Wiki Index

Compact catalog. Update after material wiki changes.

## Castle Panels

- [[concepts/castle-panel-template-cut-bands]] - user-confirmed cut-band rule
  and fixed-template scoring/export/semantic-review loop for castle-panel image
  generation.

## Image Repair

- [[concepts/mask-bounded-external-redraw-donor]] - user-confirmed Berlin wave3
  wave6, and wave7 lesson: for localized ghost/haze defects or semantic
  continuity/occlusion failures, use an OpenAI external edit as a donor, then
  composite only masked pixels back onto a banked baseline. For repeated
  architecture, split generation context from final blend masks and verify
  protected floor/window/approved-repair zones stay unchanged.

## Product Image Finishing

- [[concepts/illustrated-product-upscale-and-background-removal-workflow]] -
  sample-proven double Marine Bed Wrapper lesson: upscale first, use hard180
  BRIA background removal for hard alpha, repair over-cut foreground with
  reviewed colored-margin mask surgery, keep white-gap cleanup ROI/manual, and
  batch only after sample approval.

- [[concepts/double-marine-bed-wrapper-background-removal-fusion-pipeline]] -
  fusion pipeline for watercolor marine illustrations on near-white backgrounds:
  border-flood + disagreement-recovery restore → binary alpha (18-image validated).
  v1 works but fails on ultra-pale ghost layers; v2 spec tightens flood (chroma≤5)
  + adaptive boundary erode. Gate: defect_scan_v2.py hi-DPI tiles vs. original-source
  BG model.
