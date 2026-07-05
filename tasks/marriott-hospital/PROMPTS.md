# Marriott Hospital — 3-panel one-pass generation pack

Route: `fal-ai/flux-control-lora-canny` + Marriott LoRA (trigger `MRCH`, `.brainer/tenx/marriott-lora/lora.json`).
Control maps: `tasks/marriott-hospital/geometry/controlmaps/{door,left,right}-control.png` (silhouette + door cuts; content-edge overlays optional per panel).
Source design being adapted: `source/Updated Hospital 1.png` (5-fold mockup → recomposed to our 3 zones).
Style DNA (from LoRA + refs Police/Fire/Birds-Nest/Water-Cube/Kitchen): dense felt-fiber texture, storybook children's-book architecture, saturated flat color, scalloped cloud-top skies, potted plants + street lamps + signage, warm rim-light.

Common suffix (all panels): ", MRCH felt-textured storybook illustration style, dense wool-felt fiber grain, soft rim lighting, flat saturated color, isolated on pure white background, artwork fills the panel silhouette to its outer contour and nothing outside it, no photorealism, no text artifacts outside signs."

## Panel: DOOR (center, aspect 0.689, domed top — the main entrance)
Content zone: CITY HOSPITAL facade. Domed gable with a blue medical-cross badge at the crown, "CITY HOSPITAL" lettering on the upper facade, a curved blue entrance canopy with downlights, an arched central gateway (align to saloon arch), a hinged blue door leaf with a cross emblem, potted shrubs and bollard lamps flanking the entry, tiled forecourt.
Prompt: "MRCH a friendly children's hospital main entrance building, white stone facade with a domed gable, a blue medical cross badge at the top, CITY HOSPITAL sign, a curved blue entrance canopy with small downlights, a tall arched central doorway, a blue hinged door with a cross, potted green shrubs and lamp bollards flanking the entrance, tiled forecourt" + suffix.

## Panel: LEFT narrow (aspect 0.3895, tall — garden/values wing)
Content zone: hospital garden. Tall leafy tree top, wooden bench, a standing values sign reading CARING / KIND / HEALING / TOGETHER with little heart/smiley icons, flowering beds, a ground-floor hospital window with warm interior, scalloped cloud sky above.
Prompt: "MRCH a tall narrow children's hospital garden scene, a big leafy tree, a wooden bench, a standing sign reading CARING KIND HEALING TOGETHER with small heart and smiley icons, flower beds with daisies, a lit ground-floor hospital window, soft clouds in a blue sky at the top" + suffix.

## Panel: RIGHT narrow (aspect 0.3895, tall — emergency wing)
Content zone: emergency entrance. Rooftop helipad with a white H in a blue circle and a red-white windsock, an EMERGENCY red sign over a canopy, a white ambulance with blue medical star at a covered bay, a 24/7 CARE sign, flowering beds, scalloped cloud sky.
Prompt: "MRCH a tall narrow children's hospital emergency wing, a rooftop helipad with a white H in a blue circle and a red and white windsock, a red EMERGENCY sign over a canopy, a cute white ambulance with a blue medical star under a covered bay, a small 24/7 CARE sign, flower beds, soft clouds in a blue sky at the top" + suffix.

## Run recipe (per panel, best-of-N)
- control_lora_scale sweep {0.35, 0.45, 0.6}; lora scale 0.95; guidance 4.0; steps 30; num_images 2 → ~6 candidates/panel.
- image_size = control map dims (door 820x1190, narrows 820x2105).
- Then per candidate: geom_gate.py (mask = controlmap mask) + VLM style/content check; near-miss → correction loop; finisher clarity 0.5.
- Show ALL candidates full-size + overlay to user; user picks.
