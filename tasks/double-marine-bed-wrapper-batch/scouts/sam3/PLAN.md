# SAM 3 semantic-proposal scout for image 14

This is a single paid feasibility request, not a background-removal result.
The source is the original 941x1672 RGB image 14, SHA-256
`925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`.

## Phase 0 decisions

- The existing `scripts/automask.py` call is not a valid multi-object test: it
  omits `return_multiple_masks`, `include_scores`, and `include_boxes`, then
  keeps only one returned mask. It is read-only and out of scope for this scout.
- The fal schema currently documents at most 32 masks. This scout requests 32,
  downloads every returned mask, and preserves provider metadata without mask
  URLs or credentials.
- All masks returned for the semantic prompt are inspected before the offline
  union is chosen. Held-out benchmark labels must not influence that choice.
- A SAM mask is a semantic proposal, not a matte. The scout therefore performs
  no matting, feathering, color decontamination, threshold tuning, or completion
  claim.
- Provider masks are never silently stretched. Native mapping is recorded as
  either aspect-preserving direct resize or centered letterbox removal followed
  by resize.
- Exactly one paid segmentation request is allowed. A local attempt record is
  written before the call and makes rerunning the request command fail closed.

```loop
name: sam3-image14-one-request-scout
topology: closed · inner · single
generator: sam3-scout-agent running one fal request and offline artifact builder
verifier: root separate cold verifier given only this plan and output artifacts
gate: python3 ./tasks/double-marine-bed-wrapper-batch/scouts/sam3/verify_scout.py --self-test && python3 ./tasks/double-marine-bed-wrapper-batch/scouts/sam3/verify_scout.py PRODUCT_OUTPUT_DIR
stop: done after exactly one successful request has every mask downloaded and a separately judged proposal bundle, or blocked after one recorded auth/config/network failure
budget: max_iterations=1, max_paid_requests=1
```

The machine gate proves lineage, completeness, dimensions, alpha identity,
redaction, and the one-request cap. It deliberately does not grade semantic or
visual quality; the root verifier owns that decision using `RUBRIC.md`.

