# Separate-verifier rubric

- `[evidence: request_count=1]` Exactly one paid SAM 3 segmentation request.
- `[evidence: request_flags=PASS]` Multiple masks, scores, and boxes were requested.
- `[evidence: all_masks_downloaded=PASS]` Every response mask exists locally and matches its recorded hash.
- `[evidence: union_lineage=PASS]` The union names the selected returned-mask indices and does not use held-out benchmark labels.
- `[evidence: native_artifacts=PASS]` Union, overlay, alpha cutout, and four composites are 941x1672.
- `[evidence: alpha_identity=PASS]` Cutout alpha is byte-identical to the saved union mask.
- `[evidence: redaction=PASS]` Saved metadata contains no key, data URI, or temporary provider URL.
- `[evidence: negative_fixture_rejected=PASS]` The new gate rejects a request-count=2 fixture.
- `[vision]` Inspect every returned mask in the per-mask contact sheet.
- `[vision]` Judge proposal coverage, false-positive blank paper, enclosed-pocket removal, sand preservation, and missed bubbles/fish/tips.
- `[vision]` Inspect native composites on gray, black, magenta, and white plus every named ROI board.

Passing the structural checks does not mean the proposal solves background
removal. Visual observations must be recorded as limitations, not repaired by
changing this one-request scout.

