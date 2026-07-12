You MUST call your image generation / image edit tool.

You are given TWO attachments:
1) The original watercolor illustration on white paper.
2) An erase MASK: WHITE = regions to erase/fill; BLACK = must stay pixel-identical.

Task: fill ONLY the white-mask regions with blank white paper that matches the surrounding paper color/lighting from the black-mask (kept) areas.

Hard rules:
- BLACK-mask pixels must remain unchanged (same art/paper as input 1).
- WHITE-mask pixels become clean white paper — no coral, fish, shells, bubbles, stains, or ghost outlines.
- Do not shift, rescale, or restyle the kept regions.
- Same aspect ratio / framing.
- Output a single RGB PNG.

Save to the exact --out path.
