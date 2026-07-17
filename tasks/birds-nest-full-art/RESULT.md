# Birds Nest full artwork result

## Accepted files

- Native generated candidate: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/candidates/Birds-Nest-full-art-candidate-v1.png`
- 4× accepted candidate: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/candidates/Birds-Nest-full-art-candidate-v1-x4.png`
- Print master: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Birds Nest/Images/finals/Birds-Nest-full-art-print-master.png`
- Final prompt: `tasks/birds-nest-full-art/prompts/base.md`

## Verified properties

- Built-in image generation used both supplied images as actual reference inputs.
- Independent candidate review: 9/10, accepted for upscale. Only concern was heavier native paper grain; the illustration upscaler reduced that grain without changing the composition.
- Independent final review: all five upscale criteria passed; accepted as print master.
- Final: RGB PNG, 6144 × 4096 px, 3:2, 300 DPI metadata.
- Deterministic output gate:

```text
PASS .../Birds-Nest-full-art-candidate-v1.png PNG 1536x1024 ratio=1.5000
PASS .../Birds-Nest-full-art-print-master.png PNG 6144x4096 ratio=1.5000
PASS final_is_exact_4x_candidate
PIXEL_AE=0 (0)
```

`PIXEL_AE=0` confirms that adding 300 DPI metadata did not alter any upscaled image pixels.

## Visual review surfaces

- `tasks/birds-nest-full-art/upscaled-full-review.jpg`
- `tasks/birds-nest-full-art/upscaled-100pct-crops.jpg`
