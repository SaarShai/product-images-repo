#!/bin/zsh
set -e
cd "/Users/za/Documents/product images repo"
O=tasks/marriott-hospital/outputs
SR=tasks/marriott-hospital/style-read
LJ=.brainer/tenx/marriott-wc-lora/lora.json
CM=tasks/marriott-hospital/geometry/controlmaps
FLAVOR="polished children's picture-book illustration, fine watercolor and gouache washes over delicate precise linework, fine paper-grain stipple, rich muted color, luminous glowing windows and lantern light, dense storybook detail"
RESTYLE="Repaint this panel in EXACTLY the art style of the reference images: fine watercolor and gouache washes over delicate precise linework, fine paper-grain stipple texture, rich muted color, luminous glowing windows. CRITICAL: keep every structural element in its EXACT current position — nothing moves or resizes. Same crop, do not zoom. ALL signs and buildings are completely BLANK with no letters, no words, no writing anywhere. No photorealism, no 3D render, no felt or fiber texture."
typeset -A CONTENT SIZE
CONTENT[door]="MRWC a friendly children's hospital main entrance building, white stone facade with a domed gable, a blue medical cross badge at the top, a blank rectangular sign board above the entrance, a curved blue entrance canopy with small downlights, a tall arched central doorway aligned to the arch, a blue double door, potted green shrubs and lamp bollards flanking the entrance, tiled forecourt"
CONTENT[left]="MRWC a tall narrow children's hospital garden scene, a big leafy tree, a wooden bench, a blank standing sign board with small heart and smiley icons, flower beds with daisies, a lit ground-floor hospital window, soft clouds in a blue sky at the top"
CONTENT[right]="MRWC a tall narrow children's hospital emergency wing, a rooftop helipad with a white H in a blue circle and a red and white windsock, a blank red sign board over a canopy, a cute white ambulance with a blue medical star under a covered bay, a small blank sign board, flower beds, soft clouds in a blue sky at the top"
SIZE[door]="820 1190"; SIZE[left]="820 2105"; SIZE[right]="820 2105"
for p in door left right; do
  w=${SIZE[$p]% *}; h=${SIZE[$p]#* }
  echo "=== $p stage1 x2 ==="
  python3 scripts/onepass_gen.py --control $CM/$p-control.png --lora-json $LJ --mask $CM/$p-mask.png \
    -n 2 --width $w --height $h --control-scale 0.3 --lora-scale 1.2 \
    --out-prefix $O/r10_${p} --prompt "${CONTENT[$p]}, $FLAVOR"
  for i in 1 2; do
    echo "=== $p stage2 cand$i ==="
    python3 scripts/falgen.py --mode flux2edit --image $O/r10_${p}_s${i}.png \
      --refs $SR/crop-hospital-facade-notext.png $SR/crop-hospital-garden.png \
      --out $O/r10_${p}_c${i}_style.png --prompt "$RESTYLE"
  done
done
echo "=== R10 DONE ==="
