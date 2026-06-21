# R-batch-impl — multi-element batch edit + falbatch interpreter fix

## Scope
Two deliverables against `/Users/za/Documents/product images repo`:
- (A) Make `scripts/falbatch.py` robust to the wrong interpreter (`fal_client` is
  only in `.venv-gen`, Python 3.12 — system python is 3.9).
- (B) Build `scripts/batch_edit.py`: apply MANY element edits to ONE image in a
  single run, sequentially accumulating onto one canvas, reusing `scripts/edit.py`.

Constraint honored: modified ONLY `scripts/falbatch.py`, created ONLY
`scripts/batch_edit.py`. `edit.py` was reused (not reimplemented). No secrets printed.

---

## (A) FIX — falbatch.py interpreter shim

**Root cause:** `import fal_client` was a hard top-level import. Under system
python 3.9 (`python3 scripts/falbatch.py`) it raised `ModuleNotFoundError` because
`fal_client` (1.0.0) lives in `.venv-gen/bin/python` (3.12).

**Fix:** wrapped the import in a probe. On `ImportError`, if `.venv-gen/bin/python`
exists and we're not already it, `os.execv` re-execs the same script + argv under
that interpreter (guarded by `FALBATCH_REEXEC=1` to prevent an exec loop). If the
venv is missing, it raises a clear `SystemExit` documenting the required
interpreter. Docstring updated with the INTERPRETER note and `.venv-gen` CLI lines.

**Verification (both pass):**
- `.venv-gen/bin/python scripts/falbatch.py --example` -> prints example JSON, exit 0.
- `python3 scripts/falbatch.py --example` (system 3.9) -> auto re-execs under
  `.venv-gen`, prints identical example JSON.

---

## (B) BUILD — scripts/batch_edit.py

**Design:**
- Input: one `--src` + `--jobs <JSON list>`; each job =
  `{op, element, box, desc, out_suffix}` (plus optional `free`, `ctx_pad`,
  `mask_dilate`, `seed`).
- **Sequential accumulation (REQUIRED, documented in-file):** job 1 edits `--src`
  -> `step_1.png`; job 2 edits `step_1.png` -> `step_2.png`; ... last step = final.
  Composites are NOT parallelized — every edit shares the same canvas, so a
  parallel pair would each be blind to the other's change and the last writer
  would clobber the first (lost edit). This mirrors the hand-chained 3-taxi flow.
- Each job runs `scripts/edit.py` via subprocess (no pipeline reimplementation).
  Parses edit.py's `<out>.json` provenance sidecar + exit code (0=SUCCESS,
  2=NEEDS-REVIEW) into a row.
- Outputs: one final image; a combined `<final>.batch.json` (src, step_chain,
  per-job rows incl. each edit.py sidecar, n_success); a printed summary table
  (per element: op, pixel gate, judge, RESULT). Exits 0 iff all jobs SUCCESS.

**Test run (real fal calls):**
`batch_edit.py --src tasks/nyc-taxi/out/nyc-fixed.png` with a 2-job batch:
1. remove the right small taxi  (box `3200,2950,3760,3320`)
2. redraw the left taxi  (box `150,2950,1260,3370`, desc "a clean classic yellow sedan")

**Results (from `_batch_final.batch.json`):**
| # | element | op | exit | pixel_gate | judge.verdict | leak | text_gate | RESULT |
|---|---------|----|------|-----------|---------------|------|-----------|--------|
| 1 | the small yellow taxi | remove | 0 | OK (delta=0) | FAIL* | PASS | no_text | SUCCESS |
| 2 | the yellow taxi | redraw | 0 | OK (delta=0) | PASS | PASS | no_text | SUCCESS |

\* For `op=remove`, edit.py gates on `leftover_text is False` (True here), NOT on
the VLM `verdict` field — so RESULT=SUCCESS is correct; the table just surfaces the
raw judge verdict. Redraw triggered edit.py's 1-pass auto-repair which erased
stamped "TAXI"/lettering (post-repair text_gate clean).

**Eyeball verification (cropped both regions from the FINAL image):**
- LEFT region: clean classic yellow sedan repainted in place, no leftover text.
- RIGHT region: taxi removed, bg (wall/pavement) reconstructed — vs ORIG crop
  which still showed the "TAXI" sedan.
- Whole-image diff vs original: only 196,085 px changed (1.216%), bbox x=441..3662
  spanning BOTH edit regions (LEFT 147,208 px + RIGHT 48,877 px). Rest untouched.
- step_chain confirms accumulation: `nyc-fixed.png -> step_1 -> step_2` (job 2
  edited job 1's output, not the original).

**Artifacts:** `tasks/improve/_batch_final.png` (+ `_batch_final.batch.json`,
`_batch_final_editov.png`), check crops `_batch_check_{left_redrawn,right_removed,
right_ORIG}.png`, jobs file `tasks/improve/_batch_jobs.json`.

---

## RESULT: PASS (both A and B verified)
- A: shim works both directly and via auto re-exec.
- B: 2-job batch applied both changes to one final image; each job pixel gate
  delta=0; summary printed; eyeballed both edits present and the rest intact.
