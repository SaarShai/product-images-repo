#!/bin/zsh
set -e
cd "/Users/za/Documents/product images repo"
O=tasks/marriott-hospital/outputs
LJ=.brainer/tenx/marriott-wc-lora/lora.json
CTRL=tasks/marriott-hospital/geometry/controlmaps/door-control.png
MASK=tasks/marriott-hospital/geometry/controlmaps/door-mask.png
CONTENT="MRWC a friendly children's hospital main entrance building, white stone facade with a domed gable, a blue medical cross badge at the top, a blank rectangular sign board above the entrance, a curved blue entrance canopy with small downlights, a tall arched central doorway aligned to the arch, a blue double door, potted green shrubs and lamp bollards flanking the entrance, tiled forecourt"
typeset -A FLAVOR
FLAVOR[A]="hand-painted watercolor children's book illustration, soft translucent washes, gentle pigment granulation, subtle paper texture, warm palette, soft ambient light"
FLAVOR[B]="polished children's picture-book illustration, fine watercolor and gouache washes over delicate precise linework, fine paper-grain stipple, rich muted color, luminous glowing windows and lantern light, dense storybook detail"
FLAVOR[H]="elegant fine-line illustration with muted watercolor washes, precise delicate linework, refined decorative detail, soft even light"
for k in A B H; do
  echo "=== flavor $k ==="
  python3 scripts/onepass_gen.py --control $CTRL --lora-json $LJ --mask $MASK -n 2 \
    --width 820 --height 1190 --control-scale 0.4 \
    --out-prefix $O/r9_door_$k --prompt "$CONTENT, ${FLAVOR[$k]}"
done
echo "=== R9 DONE ==="
