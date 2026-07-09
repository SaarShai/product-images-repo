# Assistant Claims

- Claimed V8/V9 brick-tree candidates were generated and copied into the festive production images folder; V8 had the clearer brick grid and V9 had softer mortar/more tree ornaments.
- Claimed the selected V8 was modified with a large red/white swirl candy in the top gable, then upscaled with "Real-ESRGAN 3x" and exported as transparent `edge-v8-swirl-artwork-hires.png` at `4200x5697 RGBA`.
- Claimed the tree cutout was fixed by removing a tight mask, adding green Christmas-tree fill with candy ornaments, and adding a scalloped piped icing border; later claimed the original V8 geometry-matched tree was restored unmasked.
- Diagnosed the blurry-upscale issue as baked-in soft interiors plus black-background confusion: hard rim protected, low-contrast cookie interiors smoothed, and mixed edge types causing patchy results.
- Claimed four upscale methods were compared on `best option 2-05.png`: A Real-ESRGAN x4plus on black, B Real-ESRGAN anime on cream, C fal clarity-upscaler on cream, D fal Recraft Crisp on cream, plus E cream -> ESRGAN x4plus -> adaptive sharpen.
- Claimed method C was `fal-ai/clarity-upscaler` via `scripts/reupscale.py`, with preprocessing to cream paper and params: `creativity 0.2`, `resemblance 0.9`, `factor 4`, `steps 22`, plus a gingerbread/icing prompt, then keyed back to transparent.
- Claimed first magenta samples used `magenta -> cream paper -> fal clarity (creativity 0.2, resemblance 0.9, factor 2x, steps 22) -> transparent`; user rejected these as blurry.
- Claimed an x8/detail path for magenta series: `cream -> downscale short side to 240 -> clarity 4x -> 2x texture -> detail C 1.5x`.
- Claimed three detail approaches on magenta-06: A adaptive sharpen, B `clarity 1.25, creat 0.4`, C `clarity 1.5, creat 0.5`; C was positioned as strongest new sugar/crumb detail.
- Claimed detailC batch hit fal limits for tall images: `01`, `02`, and `04` hit the 32 MP cap or a fal tiling bug, so the assistant split tall images into vertical halves and stitched them.
- Claimed gingerboy used the same pipeline as the magenta series: `cream -> downscale 240 short -> clarity 4x -> 2x texture -> detail C 1.5x`, producing `detail-gingerboy-C-clarity-1.5-c0.5.png` / `gingerboy-clarity-8x-detailC.png`.
- Claimed candy-creative probe used settings vs approved detailC: `factor 1.25`, `creativity 0.65`, `resemblance 0.55`, with prompt terms for gumdrop facets, star-tip icing ridges, sugar crystals, and jewel translucency.
- Claimed candy-creative batch used `1.25x / creat 0.65 / res 0.55` for eight outputs; user later rejected 01-04 outputs due magenta and green artifacts.
- Claimed artifacts came from the creative pass, not the clean 8x/detailC source; attempted palette-locked redo with `creat 0.55 / res 0.62`, then a milder no-enlarge creative pass plus speckle scrubbing.
- Claimed final artifact-safe rebuild for 01-04 restarted from original magenta sources, not healed bad outputs: `magenta -> cream -> downscale 240 -> clarity 4x -> 2x -> detailC (1.5 / 0.5 / 0.7)`, with artifact check `mag% = 0, neon% = 0`.
- Claimed downloads pilot on `Image (6)2.png` first used the candy-creative pipeline, but after user approval of `img62-clarity-8x.png`, switched the rest to "same 8x clarity method only (no candy-creative)."
