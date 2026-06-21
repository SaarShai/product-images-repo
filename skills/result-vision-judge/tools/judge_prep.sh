#!/usr/bin/env bash
# judge_prep.sh — one-command prep for a vision+geometry judge.
# Draws the SVG-geometry overlay on the candidate AND computes the geometry calc,
# so the judge can SEE (overlay) and CALCULATE (region-IoU / white-IoU) before scoring.
#
# Usage: bash skills/result-vision-judge/tools/judge_prep.sh <candidate_dir> <source.svg> [L,T,R,B]
# Writes into <candidate_dir>: region_overlay.png, region_iou.json, whitecheck.json
#
# REGISTRATION (how the SVG is aligned onto the candidate):
#   CANONICAL  — pass a 3rd arg "L,T,R,B" = the exact panel bbox in candidate pixels
#                (from the SVG <image> transform, a letterbox frame, or template-manifest).
#                Use this whenever the registration is known — it is drift-free.
#   AUTO-BBOX  — omit the 3rd arg; geom_iou detects the panel from non-white pixels.
#                Drift-prone (varies per image); a LEGACY fallback only, not for final verdicts.
set -u
DIR="${1:?candidate dir required}"
SVG="${2:?source svg required}"
BBOX="${3:-}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT" || exit 1

IMG="$DIR/raw.png"
[ -f "$IMG" ] || IMG="$DIR/exact.png"
if [ ! -f "$IMG" ]; then
  echo "judge_prep: no raw.png/exact.png in $DIR" >&2
  exit 2
fi

if [ -n "$BBOX" ]; then REG="CANONICAL (bbox=$BBOX)"; else REG="AUTO-BBOX (legacy, drift-prone)"; fi

# 1. geometry calc + overlay (fill-agnostic region-IoU; draws green/red opening outlines)
python3 scripts/geom_iou.py "$IMG" --svg "$SVG" ${BBOX:+--bbox "$BBOX"} \
  --out-overlay "$DIR/region_overlay.png" --json-out "$DIR/region_iou.json" 2>/dev/null

# 2. white-IoU / painted_frac / outside_frac (cutout cleanliness)
python3 scripts/svg_geometry_check.py "$IMG" --svg "$SVG" \
  --json-out "$DIR/whitecheck.json" 2>/dev/null || true

echo "=== $DIR ==="
echo "candidate:    $IMG"
echo "registration: $REG"
echo "overlay:      $DIR/region_overlay.png   (LOOK at this: green=opening landed right, red=missed)"
echo "--- region-IoU (placement) ---"; cat "$DIR/region_iou.json" 2>/dev/null | head -c 600; echo
echo "--- white/painted/outside (cleanliness) ---"; cat "$DIR/whitecheck.json" 2>/dev/null | head -c 400; echo
echo "Now Read the overlay + candidate + contract + style refs, then score per skills/result-vision-judge/SKILL.md."
