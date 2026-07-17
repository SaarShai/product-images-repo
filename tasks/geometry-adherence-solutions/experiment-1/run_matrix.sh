#!/bin/bash
# run_matrix.sh -- geometry-adherence-solutions/experiment-1 gen matrix.
#
# RUN (self-documenting: these are the ACTUAL commands used for the 4 scored
# Stage-A gens + the smoke test that validated them). Engine:
# scripts/gen_stage_a.py, a STANDALONE driver (NOT scripts/localgen.py --
# localgen.py stays generic; PARAMS.md's fp32-VAE-decode / IP-Adapter
# style-routing / multi-ref-averaging / hard-composite requirements needed a
# dedicated script). Parameters are PARAMS.md-frozen, including Amendment 1
# (arch-shaped socket exclusion, not the full raster rect) and Amendment 2
# (matte audit + composite_back.py gate refinements) -- see PARAMS.md.
#
# Run from repo root.
set -euo pipefail
cd "$(dirname "$0")/../../.."   # repo root

EXP="tasks/geometry-adherence-solutions/experiment-1"
SCRIPTS="$EXP/scripts"
RUNS="$EXP/runs"

PY_SYS="/usr/bin/python3"        # asset/geometry tooling (numpy+PIL+scipy, no torch)
PY_GEN=".venv-gen/bin/python"    # diffusers/torch/mps generation

# =====================================================================
# 0. Asset build (frozen matte + arch-shaped socket masks, both resolutions)
# =====================================================================
$PY_SYS "$SCRIPTS/build_socket_matte.py"                       # Amendment 1+2: door_socket_rgba.png + audit
$PY_SYS "$SCRIPTS/build_assets.py" --width 1024 --outdir assets      # 1024 kept in place (evidence, now Amendment-1-corrected)
$PY_SYS "$SCRIPTS/build_assets.py" --width 640  --outdir assets-640  # 640x1544 -- AUTHORITATIVE for gen (PARAMS.md card)

# =====================================================================
# Stage A -- geometry-exact base, 640x1544. 2 hole-policy arms (P1: holes
# excluded from paint mask "by construction"; P2: holes painted, punched
# post-hoc in Stage C) x 2 seeds (7, 21, SAME PAIR both arms) = 4 gens.
# Fixed hyperparameters (PARAMS.md card): steps=30 guidance=5.5 strength=1.0
# controlnet_conditioning_scale=0.7 control_guidance=[0.0,0.8] lora_scale=0.75
# ip_adapter_scale={"up":{"block_0":[0.0,0.55,0.0]}} (style-layer-only).
# =====================================================================

# --- cheap IP-Adapter embedding-shape probe (no full diffusion; run once to
# confirm which multi-ref form diffusers 0.38 accepts -- see PARAMS.md card
# note / gen_stage_a.py averaged_ip_embeds() docstring) ---
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" --shape-check

# --- smoke test (4 steps, seed 7, arm P1) -- kept as runs/smoke/, not deleted ---
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 7 --steps 4 --out-dir "$RUNS/smoke"

# --- 4 scored gens, ONE Bash command per gen (pipeline reload per gen; each
# fits comfortably inside a single tool-call timeout: ~100-115s wall each) ---
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 7  --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.7 --cg-start 0.0 --cg-end 0.8 --out-dir "$RUNS/A-P1-s7"

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 21 --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.7 --cg-start 0.0 --cg-end 0.8 --out-dir "$RUNS/A-P1-s21"

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P2 --seed 7  --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.7 --cg-start 0.0 --cg-end 0.8 --out-dir "$RUNS/A-P2-s7"

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P2 --seed 21 --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.7 --cg-start 0.0 --cg-end 0.8 --out-dir "$RUNS/A-P2-s21"

# --- Stage-A metrics (outside-silhouette painted px, per-hole painted %,
# socket/arch zone painted px, paint-region coverage %) ---
$PY_SYS "$SCRIPTS/measure_stage_a.py"   # -> runs/metrics-stageA.json + runs/RESULTS-stageA.md

# =====================================================================
# ROUND 2 (Amendment 4, both advisors converged): round-1 geometry was
# 100% green but content collapsed to flat washes (contour-only lineart gave
# no interior scaffold). Composition map = selective structural canny trace
# of the frozen exemplar outset-c1 raw.png, registered per-axis into the
# body, clipped to paintable_P1 eroded -2px, authoritative SVG strokes
# re-added on top. Retuned conditioning (denser map): cond_scale 0.55,
# cg_end 0.65. P1 only, seeds 7/21 (P2 deferred to post-Stage-C-fix). Does
# NOT touch control_canny.png or any round-1 runs/ output.
# =====================================================================
$PY_SYS "$SCRIPTS/build_composition_map.py"   # -> assets-640/control_composition.png + checks/*

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 7  --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.55 --cg-start 0.0 --cg-end 0.65 \
  --control-image control_composition.png --out-dir "$RUNS/R2-P1-s7"

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 21 --steps 30 --guidance 5.5 --strength 1.0 \
  --cond-scale 0.55 --cg-start 0.0 --cg-end 0.65 \
  --control-image control_composition.png --out-dir "$RUNS/R2-P1-s21"

$PY_SYS "$SCRIPTS/measure_stage_a.py" --run-ids R2-P1-s7 R2-P1-s21 \
  --metrics-out "$RUNS/metrics-round2.json" --results-out "$RUNS/RESULTS-round2.md" \
  --title "# experiment-1 Round-2 results (Amendment 4: composition map, 2 scored gens)"

# =====================================================================
# Stage B -- gated style re-render, base=R2-P1-s21/gen.png (orchestrator
# pick: richest architectural mass). img2img at strength 0.35/0.50, SAME
# checkpoint/pipeline (StableDiffusionXLControlNetInpaintPipeline -- never
# plain img2img, 9-channel UNet) and SAME conditioning as round 2 (CN 0.55,
# cg_end 0.65, IP 0.55 style-layer, LoRA 0.75, guidance 5.5, prompts
# verbatim). --init-image feeds the prior Stage-A gen.png instead of the
# neutral init_canvas.png.
# =====================================================================
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 21 --steps 50 --guidance 5.5 --strength 0.35 \
  --cond-scale 0.55 --cg-start 0.0 --cg-end 0.65 \
  --control-image control_composition.png \
  --init-image "$RUNS/R2-P1-s21/gen.png" --out-dir "$RUNS/B-s21-d035"

PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 $PY_GEN "$SCRIPTS/gen_stage_a.py" \
  --arm P1 --seed 21 --steps 50 --guidance 5.5 --strength 0.50 \
  --cond-scale 0.55 --cg-start 0.0 --cg-end 0.65 \
  --control-image control_composition.png \
  --init-image "$RUNS/R2-P1-s21/gen.png" --out-dir "$RUNS/B-s21-d050"

$PY_SYS "$SCRIPTS/measure_stage_b.py"   # -> runs/metrics-stageB.json + runs/RESULTS-stageB.md

# =====================================================================
# Stage C -- mechanical guardrails (composite_back.py; run on EVERY
# candidate from A + B). KNOWN OPEN ISSUE (found while verifying this run):
# the registration gate, as calibrated (exact-color match, tol=10 RGB
# against the frozen neutral fill), FAILS on real MPS-generated Stage-A
# candidates -- the "kept" (black-mask) socket zone is NOT byte-clean, it
# picks up the documented MPS SDXL-inpaint VAE tint (see
# controlnet_sdxl_gen.py's own comment on this). socket_gates (the actual
# paste-back) still pass; only the neutral-region DETECTION step needs a
# color-tolerant recalibration before Stage C can run on real candidates.
# Not fixed here (out of this lane's scope: Stage-A generation + metrics).
# =====================================================================
# for cand in "$RUNS"/A-*/gen.png; do
#   id=$(basename "$(dirname "$cand")")
#   $PY_SYS "$SCRIPTS/composite_back.py" \
#     --candidate "$cand" --assets-dir "$EXP/assets-640" \
#     --out "$RUNS/$id/exact.png" --metrics "$RUNS/$id/exact.metrics.json"
# done
