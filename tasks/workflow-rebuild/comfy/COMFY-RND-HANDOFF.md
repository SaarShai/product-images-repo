# ComfyUI / from-scratch generation R&D — handoff for the next agent

**Written:** 2026-07-07. **Status:** parked mid-investigation, no final verdict.
**One-line:** we are hunting the best *from-scratch* method to generate die-cut panel
art meeting 4 fixed requirements. `gpt-image` is the reigning champion; SDXL closes
the richness gap but has not yet held geometry cleanly. The decisive experiment
(diffusers SDXL-inpaint mask route) is only 1/4 sampled.

---

## THE QUESTION (do not drift off this)
What tool/model/workflow generates panel art **from scratch** (not relock, not
recreation-from-its-own-output) that satisfies all four, judged in this order:

1. **Geometry** — art fills the SVG contour; door portal filled to its exact lineart.
   Measured by `scripts/door_fill_gate.py` (door_fill 0-1; PASS ≥0.90, WARN ≥0.75) + overlay.
   **Overlay-only verdicts — never eyeball a raw for fit.**
2. **Style** — soft transparent watercolor, storybook; judged vs reference exemplars.
3. **Richness** — a complete, characterful building (teddy/dome/clock/topiary tier).
   The bar is `arm-g_s1` from round-3 (see baseline manifest).
4. **Integration** — cutouts/keep-clears painted-framed as design features; **no painted
   text** (diffusion garbles it); door flaps carry only door content.

Full contract + rule (an arm that can't beat the champion on ≥1 axis without losing
another is retired, not re-tuned): [`PROGRAM-CONTRACT.md`](PROGRAM-CONTRACT.md).

---

## STANDINGS (from-scratch only)

| method | geometry | style | richness | verdict |
|---|---|---|---|---|
| **gpt-image** (round-3 arm-g) | good, drifts ~1-2% | excellent | excellent | **CHAMPION** (bar = arm-g_s1, door_fill 0.9877) |
| SD1.5 CN+IP (combe8) | exact | good | PLAIN | geometry proof only — no richness |
| SD1.5 dualregion (2-adapter mask) | exact | mud | mud | **DEAD** — mud at every weight, C3 + C4 |
| SDXL canny CN0.9/e0.8 (C5) | WARN 0.67–0.81, visible miss | good watercolor | **RICH** (teddy/domes/florals, champion-tier) | richness SOLVED; geometry weak; painted-text leak |
| SDXL canny CN1.0/e1.0 (C5b) | FAIL 0.36–0.62 | — | — | CONFOUNDED (IPAdapter silently dropped). Lesson: **canny strength alone cannot hold a die-cut** — hard canny makes SDXL avoid the edge-free portal region |
| SDXL inpaint-mask + canny + IP, *ComfyUI* `SetLatentNoiseMask` (C5c) | FAIL 0.0 (all-white) | — | — | Comfy native mask route failed; mask likely all-zero after `ImageToMask`. **PARKED** |
| SDXL-inpaint **diffusers** `scripts/controlnet_sdxl_gen.py` (C5d) | **WARN 0.8955** (s100 only) | not judged | not judged | **INCOMPLETE — the decisive open experiment.** 1/4 seeds gated. Best geometry of any SDXL arm, but still under the 0.90 PASS line |

**i2i-relock** (baseline init + CN, door_fill 0.99): NOT a from-scratch contender — it
recreates an existing image. Keep it only as a salvage/finishing tool for a drifted
champion. Never score it here.

---

## WHERE C5d ACTUALLY STANDS (the thing to finish first)
- Ran `scripts/controlnet_sdxl_gen.py` (proven region-IoU 1.0 history) as an SDXL-inpaint
  mask route, bypassing ComfyUI's failed native mask nodes.
- **Only s100 completed + gated: door_fill 0.8955 WARN.** s300 raw exists but its gate ran
  before the file landed (FileNotFoundError in `gates-d/s300-gate.log`); s500/s700 never generated.
- So the decisive question — *does a proper mask route hold geometry AND keep richness?* —
  is **half-answered**: geometry improved to borderline-WARN, but no PASS yet and style/richness unjudged.
- Raws: [`round-c5/raws-d/`](round-c5/raws-d/) (s100, s300). Gates: [`round-c5/gates-d/`](round-c5/gates-d/).

### Finish C5d (step 1 on resume)
1. Re-gate the existing s300 raw (it's on disk now): `python3 scripts/door_fill_gate.py --image tasks/workflow-rebuild/comfy/round-c5/raws-d/sdxlinp_s300.png --geom tasks/marriott-hospital/geometry/v3 --panel door --overlay .../s300-doorfill-overlay.png`
2. Generate s500 + s700 (2 more seeds) via the same script, gate them.
3. Board all 4 + do a **cold vision judge** on style + richness vs `arm-g_s1`. Update the standings row.
4. Verdict: if geometry stays sub-0.90 WARN across seeds, mask-strength/denoise/CN-schedule is the next dial — or accept SDXL as "richness engine, needs a geometry post-fix" and pit that hybrid against the champion.

---

## C6 — three untested mechanics (never rendered; re-dispatch fresh)
The C6 agent stacked 13 prompts in the ComfyUI queue and was killed before any raw landed.
**Nothing exists — start clean.** The three probes (each answers a real capability gap):
1. **Multiple refs into ONE IPAdapter** — `ImageBatch` the ref images (avg vs concat via
   `combine_embeds`) instead of the failed two-adapter route. Plausible fix for multi-ref style.
2. **Depth map as a 2nd ControlNet** alongside canny lineart (planned in C2, never rendered).
   `scripts/make_depth_from_mask.py` exists. Tests whether depth holds the portal where canny can't.
3. **In-graph hires-fix** (`LatentUpscaleBy` ~1.63×) — the graph validates, never judged for quality.

Build each brief with **skip-if-exists** (session restarts kill non-nohup'd work + wipe scratchpad).

---

## LANDMINES & LESSONS (paid for in this session — do not re-learn)
- **Codex sandbox cannot reach `127.0.0.1:8188`.** Never route a ComfyUI/localhost lane to
  `codex:*`. Use `glm-executor` (GLM) for anything touching the local server.
- **GLM workers misreport gate verdicts** — caught claiming PASS on WARN/FAIL **twice**.
  ALWAYS cold re-run `door_fill_gate.py` yourself and quote the `verdict` field verbatim.
  Never upgrade WARN/FAIL to PASS.
- **ComfyUI 400 body names the bad node/value**, but `comfy_run.py`'s urllib swallows it.
  `curl` the `/prompt` POST directly to see the real error.
- **IPAdapter default filename is wrong**: installed file is `ip-adapter-plus_sd15.safetensors`
  (not `ip-adapter_sd15.safetensors`). Pass `--ipadapter ip-adapter-plus_sd15.safetensors` explicitly.
- **`ControlNetApplyAdvanced` needs separate positive AND negative conditioning inputs**, not one.
- After adding a model symlink, GET `/object_info` to confirm the exact filename the server sees
  (avoids the `value_not_in_list` 400 trap).
- **Session restarts kill non-nohup'd background work and wipe the scratchpad.** Launch long jobs
  with `nohup … & disown`; bake skip-if-exists into every agent brief.
- Don't `git`-commit generated raws/boards — they're gitignored under `tasks/workflow-rebuild/**`.

## ENVIRONMENT (MPS / Apple Silicon)
- ComfyUI at `~/ComfyUI`; launch: `--use-pytorch-cross-attention --force-fp16 --fp32-vae`,
  env `PYTORCH_ENABLE_MPS_FALLBACK=1`. **`--fp32-vae` is mandatory** or the VAE outputs black/grey.
- Server was left running (PIDs may have changed). If down, relaunch with the flags above.
- SDXL feasibility confirmed on-disk (no downloads): sd_xl_base_1.0, xinsir canny SDXL CN,
  ip-adapter-plus_sdxl_vit-h, CLIP-vision, SDXL-inpaint UNet — see `round-c4/sdxl-feasibility.md`.

## POINTERS
- Contract/standings: [`PROGRAM-CONTRACT.md`](PROGRAM-CONTRACT.md)
- Full sub-round log + working SDXL graph node shapes: [`round-c5/round-c5-log.md`](round-c5/round-c5-log.md)
- Round-3 gpt-image baseline manifest (the bar): `round-c4/baseline-manifest.json`
- Prior pause baton (PIDs now dead): `.brainer/baton/2026-07-07-paused-comfy-rounds-and-boost.md`
- Gate/board scripts: `scripts/door_fill_gate.py`, `scripts/overlay_board.py`, `round-c4/gate_board.sh`
- Builder: `scripts/comfy_build_workflow.py` (workflow JSON assembler)
