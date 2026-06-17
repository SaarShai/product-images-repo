# Method Recommendation

## Recommendation

Use Prompt C when the model supports image editing with multiple crop inputs.
It best matches the user's feedback because it starts from actual packet crop
pixels and converts them into reusable isolated elements before geometry
placement.

Use Prompt A as the default fallback for text-to-image or reference-image
generation. It is narrower than the existing V2 prompt because it attaches 8
high-signal crops instead of all 24 crops, and it asks the agent to reproduce
packet-native element families rather than invent a full panel.

Use Prompt B only after Prompt A or C produces a reference-matching baseline.
Prompt B is useful for expanding the part library, but it has the highest drift
risk because it asks the model to transfer style onto new variations.

## Recommended Pipeline

1. Pick the element mix needed by the geometry plan.
2. Attach 6 to 10 packet crops that directly show those element types.
3. Generate an isolated element sheet with Prompt C if crop editing is
   available, otherwise Prompt A.
4. Score the sheet with `style-agent-evaluation-rubric.md`.
5. Hand only `REFERENCE-MATCH` or strong `PARTIAL` elements to the geometry
   agent for SVG safe-pocket placement.
6. Run geometry/template-fit review separately.

## Why This Beats The Existing V2 Prompt

The existing prompt correctly says to use packet images, but it lists the whole
packet. That can dilute attention and encourage the agent to summarize the
style from memory. These variants keep the packet visual and small:

- Prompt A uses 8 crops for faithful reconstruction.
- Prompt B uses 10 crops for controlled style transfer.
- Prompt C uses 8 component-heavy crops for edit-first extraction.

All three prompts explicitly prohibit final contour composition. That keeps the
style-agent role clean: make usable style elements first, then let a geometry
agent place them inside the SVG template.

## Current Test Status

One small image-generation smoke test was run with the available generator.
The generated image was copied into the lab as:

- `tasks/top-temp-workflow-test/agents/style-prompt-lab/imagegen-smoke-test-01.png`

It is an isolated element sheet and visually matched the packet well,
especially the rounded watercolor controls, blue ink edges, soft highlights,
and shadow pooling.

The test is still method-partial: the available tool used the chat-attached
exemplar/reference images and did not expose direct crop-file attachments. The
exact prompt and review metadata are recorded in:

- `tasks/top-temp-workflow-test/agents/style-prompt-lab/imagegen-test-prompt.md`
- `tasks/top-temp-workflow-test/agents/style-prompt-lab/imagegen-test-review-metadata.json`

Next test should run Prompt C or Prompt A in an interface that can attach the
selected crop PNG files directly.
