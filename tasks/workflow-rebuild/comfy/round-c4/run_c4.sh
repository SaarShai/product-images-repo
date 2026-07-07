#!/bin/bash
# C4 render queue — serial through ComfyUI :8188. Leader-authored 2026-07-06.
set -u
R="/Users/za/Documents/product images repo"
C="$R/tasks/workflow-rebuild/comfy/round-c4"
BW="$R/scripts/comfy_build_workflow.py"
RW="$R/scripts/comfy_run.py"
LOG="$C/round-c4-log.txt"
mkdir -p "$C/raws"
cd "$R"

build_run () { # $1=name $2...=builder args
  local name="$1"; shift
  echo "=== BUILD $name $(date +%H:%M:%S) ===" >> "$LOG"
  python3 "$BW" "$@" --out "/tmp/wf-c4-$name.json" >> "$LOG" 2>&1 || { echo "BUILD FAIL $name" >> "$LOG"; return 1; }
  echo "=== RUN $name ===" >> "$LOG"
  python3 "$RW" --workflow "/tmp/wf-c4-$name.json" --out "$C/raws/$name.png" --timeout 900 >> "$LOG" 2>&1 \
    && echo "=== DONE $name ===" >> "$LOG" || echo "=== FAIL $name ===" >> "$LOG"
}

DR_COMMON=(--arm dualregion --control-map-name door-lineart-512x728.png \
  --ref-names baseline-arm-g_s1-512x728.png --mask-name door-portal-mask-512x728.png \
  --refs2-names 03-style_ref.png --mask2-name door-facade-mask-512x728.png \
  --control-strength 1.0 --ipadapter ip-adapter-plus_sd15.safetensors --steps 30 --cfg 6.5 --width 512 --height 728)

build_run dr55_s100 "${DR_COMMON[@]}" --ip-weight 0.5 --ip-weight2 0.5 --seed 100 --prefix c4-dr55_s100
build_run dr55_s300 "${DR_COMMON[@]}" --ip-weight 0.5 --ip-weight2 0.5 --seed 300 --prefix c4-dr55_s300
build_run dr75_s100 "${DR_COMMON[@]}" --ip-weight 0.7 --ip-weight2 0.5 --seed 100 --prefix c4-dr75_s100

CB_COMMON=(--arm combined --control-map-name door-lineart-512x728.png \
  --ref-names ref-arm-l_s3.png --control-strength 1.0 --cn-end-percent 0.8 \
  --ip-weight 0.8 --ipadapter ip-adapter-plus_sd15.safetensors --steps 30 --cfg 6.5 --width 512 --height 728)
build_run combe8_s100 "${CB_COMMON[@]}" --seed 100 --prefix c4-combe8_s100
build_run combe8_s300 "${CB_COMMON[@]}" --seed 300 --prefix c4-combe8_s300

I2I_COMMON=(--arm combined --control-map-name door-lineart-512x728.png \
  --ref-names ref-arm-l_s3.png --init-name baseline-arm-g_s1-512x728.png --denoise 0.5 \
  --control-strength 1.0 --ip-weight 0.8 --ipadapter ip-adapter-plus_sd15.safetensors --steps 30 --cfg 6.5 --width 512 --height 728)
build_run i2id5_s100 "${I2I_COMMON[@]}" --seed 100 --prefix c4-i2id5_s100
build_run i2id5_s300 "${I2I_COMMON[@]}" --seed 300 --prefix c4-i2id5_s300

echo "=== C4 QUEUE COMPLETE $(date) ===" >> "$LOG"
