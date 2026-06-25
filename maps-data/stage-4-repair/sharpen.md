---
nid: n2mop1
title: "Sharpen"
type: step
x: 660
y: 540
icon: "🔪"
summary: "Adaptive sharpen / reupscale to fix blur and melt"
status: draft
tags: [repair, blur, sharpen, upscale]
---
# Sharpen

For blur / softness / melt, there is nothing to mask — sharpen or re-render:

```
scripts/adaptive_sharpen.py     # local edge-aware sharpening
scripts/reupscale.py            # creative re-render of the whole clean small
```

`adaptive_sharpen.py` handles local softness. For distorted/melted detail where you want to
keep the style and geometry but rebuild crispness, `reupscale.py` re-renders the whole clean
small image through a creative upscaler (fal clarity-upscaler, creativity≈0.5 / resemblance≈0.6
sweet spot) rather than doing per-defect surgery. (`upscale.py` is the plain enlarge path.)

This branch skips masking — go straight to [[composite|composite]].
