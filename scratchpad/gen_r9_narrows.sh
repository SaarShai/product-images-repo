#!/bin/zsh
set -e
cd "/Users/za/Documents/product images repo"
O=tasks/marriott-hospital/outputs
SR=tasks/marriott-hospital/style-read
LJ=.brainer/tenx/marriott-wc-lora/lora.json
CM=tasks/marriott-hospital/geometry/controlmaps
FLAVOR="polished children's picture-book illustration, fine watercolor and gouache washes over delicate precise linework, fine paper-grain stipple, rich muted color, luminous glowing windows and lantern light, dense storybook detail"
typeset -A CONTENT
CONTENT[left]="MRWC a tall narrow children's hospital garden scene, a big leafy tree, a wooden bench, a blank standing sign board with small heart and smiley icons, flower beds with daisies, a lit ground-floor hospital window, soft clouds in a blue sky at the top"
CONTENT[right]="MRWC a tall narrow children's hospital emergency wing, a rooftop helipad with a white H in a blue circle and a red and white windsock, a blank red sign board over a canopy, a cute white ambulance with a blue medical star under a covered bay, a small blank sign board, flower beds, soft clouds in a blue sky at the top"
for p in left right; do
  echo "=== $p stage1 one-pass ==="
  python3 scripts/onepass_gen.py --control $CM/$p-control.png --lora-json $LJ --mask $CM/$p-mask.png \
    -n 1 --width 820 --height 2105 --control-scale 0.3 --lora-scale 1.2 \
    --out-prefix $O/r9b_$p --prompt "${CONTENT[$p]}, $FLAVOR"
  echo "=== $p stage2 ref-anchored restyle ==="
  python3 scripts/falgen.py --mode flux2edit --image $O/r9b_${p}_s1.png \
    --refs $SR/crop-hospital-facade.png $SR/crop-hospital-garden.png \
    --out $O/r9d_${p}_refstyle.png \
    --prompt "Repaint this panel in EXACTLY the art style of the reference images: fine watercolor and gouache washes over delicate precise linework, fine paper-grain stipple texture, rich muted color, luminous glowing windows. CRITICAL: keep every structural element in its EXACT current position — nothing moves or resizes. Same crop, do not zoom. All signs stay blank with no text. No photorealism, no 3D render, no felt or fiber texture."
done
echo "=== NARROWS DONE ==="
