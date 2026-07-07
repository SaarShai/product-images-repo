# Lane R1-retry: practitioner evidence on reference-image conditioning

Scope: community/practitioner-evidence research for reference-first AI image generation pipelines.

Date: 2026-07-06.

Constraint honored: no image-generation calls were made.

Constraint honored: no official API docs were used as evidence.

Evidence standard: every finding below carries a URL, and weak or anecdotal evidence is labeled inline.

## Practitioner per-model findings (gpt-image-1/2, Gemini/Nano-Banana — separate subsections)

### gpt-image-1 / GPT-4o image generation / ChatGPT Images 2.0

- Strong practitioner/news evidence says ChatGPT Images 2.0, powered by GPT Image 2, improved instruction following, detail preservation, text generation, and multi-image-series consistency, but this is not the same as evidence for multiple reference-image role separation. Source: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- The Verge reports that ChatGPT Images 2.0 can create up to eight images at once while maintaining the same characters, objects, and styles across scenes. Actionable delta: useful for generating matched panel sets after a style/look is established, but it does not prove that reference image 1 can reliably mean layout and reference image 2 can reliably mean style. Source: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- The Verge also reports that the model can reason through structure before generating and can use uploaded files. Actionable delta: for panel production, send the geometry/control map as an explicit structural artifact and ask the model to reason about it, rather than relying on style prose alone. Evidence strength: secondary news report of product behavior, not a practitioner multi-reference benchmark. Source: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- A TechRadar practitioner comparison tested ChatGPT Images 2.0 and Nano Banana 2 on the same starting images for realistic edits. The reviewer found ChatGPT slower but stronger on realistic lighting, textures, face treatment, and environmental interaction. Evidence strength: single-reviewer anecdotal A/B test, but directly relevant to using an input image as a reference/edit base. Source: https://www.techradar.com/ai-platforms-assistants/i-compared-chatgpt-images-2-0-and-googles-nano-banana-2-using-real-world-prompts-from-portraits-to-product-shots-and-the-ai-image-generator-that-came-out-on-top-genuinely-surprised-me

- The same TechRadar comparison found Nano Banana 2 often looked polished but more artificial, while ChatGPT Images 2.0 felt more real in the tested photo-editing cases. Actionable delta: when our output needs believable material interaction, shadows, and subtle texture, gpt-image should remain the production path even if Nano is faster for rough ideation. Source: https://www.techradar.com/ai-platforms-assistants/i-compared-chatgpt-images-2-0-and-googles-nano-banana-2-using-real-world-prompts-from-portraits-to-product-shots-and-the-ai-image-generator-that-came-out-on-top-genuinely-surprised-me

- Vox reports a practitioner-style workaround for 4o image generation: ask for a "style transfer" rather than naming a specific living artist. Evidence strength: single author workflow note, not a controlled comparison. Actionable delta: describe the desired art system as medium, edge, lighting, simplification, and palette instead of leaning on artist names. Source: https://www.vox.com/future-perfect/411924/artificial-intelligence-chatbots-openai-chatgpt-anthropic-google-gemini-claude-grok

- Business Insider documented the 2025 4o / Ghibli-style wave and policy inconsistency around broad studio style versus living-artist style. Actionable delta: broad studio/style labels are behaviorally powerful, but risky for compliance and not precise enough for a production pipeline; use our own reference packet and neutral style descriptors. Source: https://www.businessinsider.com/openai-studio-ghibli-style-images-violate-copyright-or-not-2025-3

- The most useful gpt-image-specific evidence found was about quality and series consistency, not about multiple simultaneous reference images with explicit roles. Therefore any pipeline claim like "image 1 = pose, image 2 = style, image 3 = palette" should be treated as an unverified hypothesis for GPT Image unless tested locally in a zero/paid-controlled experiment later. Source searches attempted are listed in Gaps.

- I found no practitioner source proving that contact-sheet/grid reference images work better than separate uploaded reference images for gpt-image-1 or GPT Image 2. Recommendation: do not assume contact sheets are superior for the gpt-image production path. Source searches attempted are listed in Gaps.

- I found no practitioner source proving that burned-in labels or annotations in gpt-image reference images leak into generated outputs. Recommendation: still avoid visible text labels in references because GPT Image 2 is explicitly better at generating text, so text in references is a plausible contamination channel even though this search did not verify it. Source for improved text generation: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

### Gemini / Nano-Banana / Nano Banana Pro / Nano Banana 2

- Stronger practitioner evidence exists for Gemini/Nano-Banana multiple-reference behavior than for gpt-image. Windows Central reports that Nano Banana can upload multiple images to combine concepts, borrow creative elements, or blend scenes. Evidence strength: secondary report quoting Google release notes, so partly vendor-origin but surfaced in practitioner/news coverage. Source: https://www.windowscentral.com/artificial-intelligence/gemini-nano-banana-viral-craze

- Windows Central describes a practical multi-reference case: give Nano Banana two separate images and prompt it to create one image from two subjects while keeping likeness. Actionable delta: Nano is a useful scout for subject-merging and multi-reference ideation, but this is not enough to trust it for exact Screenery geometry. Source: https://www.windowscentral.com/artificial-intelligence/gemini-nano-banana-viral-craze

- Windows Central also cites a Reddit anecdote praising Nano Banana's consistency while rotating a subject. Evidence strength: weak anecdote, but relevant to subject consistency across pose/view changes. Actionable delta: for a pose/layout probe, Nano can be used to explore how a subject might rotate or integrate, but final production still needs geometry gates. Source: https://www.windowscentral.com/artificial-intelligence/gemini-nano-banana-viral-craze

- Tom's Guide reports Nano Banana Pro can accept up to 14 image sources and preserve/recreate up to five people. Evidence strength: news/product report, not an independent degradation curve. Actionable delta: the upper bound is high enough for a decomposed reference packet, but do not send 14 references by default without ablation because the same article frames this as a model promise. Source: https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- Tom's Guide says Nano Banana Pro's multiple-image capability could turn sketches into products or images into photorealistic 3D structures using angles and examples. Actionable delta: multi-angle sheets are plausible for product/form reconstruction, but watercolor panels likely need fewer, cleaner references because style transfer and geometry are separate concerns. Source: https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- TechRadar's Nano Banana figurine workflow says the user should upload a photo, ideally a full-body shot, plus a detailed prompt. Evidence strength: practitioner tutorial/anecdote. Actionable delta: when pose/shape matters, the reference should show the whole subject and the desired posture, not a cropped or ambiguous detail shot. Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend

- TechRadar reports the model understood the visual reference with little fine-tuning in the figurine case, but also noted packaging text/identity drift: a dog image became a named packaged toy based on available visual cues. Evidence strength: weak single anecdote. Actionable delta: avoid reference images that contain stray names, bandanna text, signage, or packaging if text/identity should not enter the output. Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend

- Tom's Guide's Nano Banana prompt examples repeatedly use one uploaded photo as identity/content reference and then prompt a style or context transform, such as action figure, Polaroid, decade transform, TV-show integration, or famous-art insertion. Evidence strength: practitioner prompt roundup. Actionable delta: explicit role language in the prompt matters; say "keep likeness recognizable" and separately specify the target material/style/world. Source: https://www.tomsguide.com/ai/ai-image-video/nano-banana-just-broke-the-internet-with-these-viral-trends-here-are-5-ai-photo-prompts-to-try-now

- Tom's Guide gives a concrete pose-control tip: if you want the subject sitting in the generated scene, upload a photo of the subject sitting. Evidence strength: single practitioner observation after testing many prompts. Actionable delta: for role separation, use a pose/layout reference whose body/object arrangement already matches the desired final pose, rather than asking the model to infer pose from prose. Source: https://www.tomsguide.com/ai/ai-image-video/nano-banana-just-broke-the-internet-with-these-viral-trends-here-are-5-ai-photo-prompts-to-try-now

- A Tom's Guide Valentine's workflow describes using two reference photos, current and childhood, to preserve both identities while harmonizing lighting, color, and style. Evidence strength: prompt-trend article, not controlled benchmark. Actionable delta: multiple identity references can be assigned separate semantic roles in prose, but this remains easier for people/photos than for stylized toy-building panels. Source: https://www.tomsguide.com/ai/forget-flowers-5-viral-nano-banana-trends-reshaping-valentines-day

- TechRadar's Nano Banana 2 prompt-upgrade article says better outputs come from layering composition/aspect ratio, camera and lighting details, text integration, factual constraints, and reference inputs. Evidence strength: practitioner tutorial built from Gemini advice and author experience. Actionable delta: our prompts should not rely on references alone; they should explicitly name framing, lighting, edge treatment, palette handling, and "no text/signage" constraints. Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-upgraded-my-ai-image-prompts-using-geminis-advice-specifying-lighting-layouts-and-even-fonts-changed-everything

- Android Central reports Nano Banana is valued for consistency across edits, preserving unchanged details, and that Pro can use up to 14 reference images. Evidence strength: practitioner explainer/news summary. Actionable delta: Nano is viable for rapid multi-reference exploration, but the production pipeline should still verify exact contours and internal cutouts after any generated result. Source: https://www.androidcentral.com/apps-software/ai/tech-talk-what-the-heck-is-gemini-nano-banana

- I found no measurable practitioner evidence that Nano Banana reference order affects output. Recommendation: if using multiple Nano references, name each role in the prompt and test small permutations only when a failure suggests role confusion.

## Property-decomposition prior art

- Prior art exists in creative tools that explicitly decompose style into properties like stroke weight, color palette, lighting, character design, and photographic style. Adobe Firefly custom-model coverage says custom models can preserve stroke weight, colour palette, and lighting, and are especially useful for illustration styles and character designs. Source: https://www.creativebloq.com/design/design-software/can-adobes-new-custom-firefly-models-finally-tame-ai

- Actionable translation for our stack: represent "watercolor toy-building style" as separable levers: medium/edge language, palette, shape simplification, lighting/shadow, and recurring object vocabulary. Source for property categories: https://www.creativebloq.com/design/design-software/can-adobes-new-custom-firefly-models-finally-tame-ai

- Firefly workflow coverage in Wired describes the web app as a creative workflow suite with image generation, image-to-video, text-to-vector, editing, and reference-image use. Actionable delta: modern practitioner tools treat reference images as reusable workflow inputs, not one-off prompts. Source: https://www.wired.com/story/what-is-adobe-firefly/

- Google Mixboard is a direct moodboard-style prior art example. Tom's Guide describes it as a mood-board/Pinterest-like tool powered by Nano Banana, where users can upload reference images, generate images, blend styles, regenerate, and ask for variations. Source: https://www.tomsguide.com/ai/ai-image-video/i-didnt-believe-the-hype-about-google-mixboard-now-im-obsessed

- The Verge describes Google Mixboard as an AI concepting canvas where users can add personal images, generate visuals, edit with natural language, combine images, and reference uploaded images to generate new visuals. Actionable delta: for our workflow, a style packet/contact sheet is best treated as a concepting board and audit artifact, not necessarily as a single fused model input. Source: https://www.theverge.com/news/783991/google-labs-mixboard-ai-design-canvas

- Midjourney practitioner guidance from Lifewire says users can include a reference image URL in a text prompt to influence style, and combine it with parameters. Actionable delta: the mature practitioner pattern is "reference plus explicit prompt plus parameters," not "reference alone." Source: https://www.lifewire.com/midjourney-basics-8697054

- Lifewire's Midjourney guide also emphasizes descriptive, specific prompts and parameters such as aspect ratio, chaos, and style. Actionable delta: our reference-first pipeline should still carry text constraints for canvas ratio, simplified form, panel composition, and forbidden elements. Source: https://www.lifewire.com/midjourney-basics-8697054

- Architectural Digest's color-trends article gives a professional design example: an interior designer used two Midjourney inputs, one color-scheme reference and one rug image, to show a client why a palette would not work. Evidence strength: practitioner anecdote from interior design. Actionable delta: palette references can be separated from object references, but they can also overrule design intent if not gated by the target object. Source: https://www.architecturaldigest.com/story/color-trend-report-2023

- Canva/Claude integration coverage says Brand Kit applies colors, fonts, and layouts from the first prompt. This is not image-reference conditioning, but it is prior art for property-decomposed brand constraints. Source: https://www.lifewire.com/canva-brand-kit-claude-integration-11893241

- CreativeBloq's Canva AI 2.0 coverage says Canva generates editable layered designs while maintaining branding and layout hierarchy. Actionable delta: layout hierarchy should be a first-class reference channel, separate from color and illustration surface. Source: https://www.creativebloq.com/design/design-software/canva-ai-2-0-can-create-an-entire-brand-campaign-from-a-text-prompt

- Tom's Guide's Lovart brand-kit experiment describes generating coordinated logos, landing pages, product visuals, and videos from a single brand prompt, with later natural-language refinements such as "create a darker color palette." Evidence strength: single reviewer workflow, but relevant to brand-system decomposition. Source: https://www.tomsguide.com/ai/with-one-prompt-i-built-an-entire-brand-kit-in-an-hour-using-lovart

- Research-adjacent but not practitioner: IPAdapter-Instruct frames image-conditioning ambiguity as the same reference image being interpretable as style transfer, object extraction, both, or another role. Actionable delta: if a model does not expose explicit roles, role labels must be in the prompt and verified by output inspection. Source: https://arxiv.org/abs/2408.03209

- Research-adjacent but not practitioner: Stable Diffusion Reference Only separates an image prompt for conceptual/color information from a blueprint image for structure in secondary painting workflows. Actionable delta: this supports our existing distinction between a geometry/control map and a visual-style packet. Source: https://arxiv.org/abs/2311.02343

- Research-adjacent but not practitioner: palette-conditioned diffusion papers treat color palettes as compact but ambiguous controls, and introduce explicit palette-adherence controls. Actionable delta: a swatch strip alone may not be enough; pair it with "use these as dominant/accent colors only, do not import shapes/text." Source: https://arxiv.org/abs/2509.02000

- Research-adjacent but not practitioner: IP-Composer uses multiple references with text specifying what concept to extract from each reference. Actionable delta: the best decomposition format is not just multiple images, but multiple images plus role captions outside the image. Source: https://arxiv.org/abs/2502.13951

## Reference-format best practices

- Best-supported best practice: use clean, role-appropriate references. TechRadar's Nano Banana figurine workflow recommends a full-body shot for a figurine transformation. For us, "full-body" translates to "whole building facade/module visible, not a tight crop, when shape or pose matters." Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend

- Best-supported best practice: align the reference pose to the desired output pose. Tom's Guide says that if you want a sitting generated subject, upload a sitting reference. For toy-building panels, use a facade/layout reference that already has the target orientation and silhouette. Source: https://www.tomsguide.com/ai/ai-image-video/nano-banana-just-broke-the-internet-with-these-viral-trends-here-are-5-ai-photo-prompts-to-try-now

- Best-supported best practice: keep prompt roles explicit. Tom's Guide prompt examples repeatedly say what to preserve, such as likeness, and what to transform, such as packaging, decade, Polaroid, or famous-art style. Source: https://www.tomsguide.com/ai/ai-image-video/nano-banana-just-broke-the-internet-with-these-viral-trends-here-are-5-ai-photo-prompts-to-try-now

- Best-supported best practice: include composition/aspect ratio, camera/lighting, text integration, factual constraints, and reference inputs, not just subject nouns. Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-upgraded-my-ai-image-prompts-using-geminis-advice-specifying-lighting-layouts-and-even-fonts-changed-everything

- Best-supported best practice: if text is not wanted, say so. This is especially important because GPT Image 2 and Nano Banana Pro coverage both emphasize improved text generation. Sources: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2 and https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- Weak but actionable text-leakage evidence: TechRadar's Nano Banana figurine test reports a generated package name emerging from available visual/contextual cues for a dog. Treat this as a warning to remove names, signage, labels, and watermarks from references unless the output is allowed to include them. Source: https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend

- Best-supported reference-count guidance: Nano Banana Pro can reportedly accept up to 14 image sources, but I found no independent quality-degradation curve. Recommendation: use a small default set, then add only if a missing property can be named. Source: https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- Practical default count for our stack: 3-5 references, each with one role, is more defensible than "as many as possible": (1) geometry/control map, (2) target style exemplar, (3) palette/swatch or color exemplar, (4) one object-vocabulary card, and optionally (5) one edge/texture crop. This is a recommendation derived from the sources above, not a directly sourced universal rule.

- Contact-sheet evidence is thin. Mixboard and moodboard tools support boards and style blending, but I found no source showing that a single contact-sheet reference performs better than separate reference uploads for gpt-image or Nano Banana. Sources: https://www.tomsguide.com/ai/ai-image-video/i-didnt-believe-the-hype-about-google-mixboard-now-im-obsessed and https://www.theverge.com/news/783991/google-labs-mixboard-ai-design-canvas

- Contact-sheet recommendation: keep contact sheets as human/audit artifacts and attach separate references when the tool supports separate images. If forced to use one image, make a clean grid with no text labels and use spatial labels in the prompt instead of burned into the image. This recommendation is inference from weak/no direct evidence and the text-leakage risk above.

- Resolution evidence gap: I found output-resolution reporting, such as GPT Image 2 up to 2K, but no practitioner evidence for ideal input reference resolution for gpt-image or Nano Banana. Source for output-resolution context only: https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- Reference-order evidence gap: I found general prompt-order evidence for text-to-image prompting, but no practitioner source that measures first/last reference-image order effects for gpt-image or Nano Banana. Source for general prompt-order context only: https://en.wikipedia.org/wiki/Prompt_engineering

- Busy versus isolated references: the strongest practical evidence favors clear references for identity/pose and explicit prompts for style/context. I found no controlled practitioner comparison of isolated crop versus busy in-context references for these two model families. Recommendation: use isolated crops for style/material/palette cards and in-context references only when context/scene composition is the role.

## Recommendations for our stack (watercolor toy-building panels, gpt-image production path, reference-first pipeline)

- Keep gpt-image as the production path when realism of lighting, texture interaction, and face/object believability matter, because the freshest practitioner A/B found ChatGPT Images 2.0 more realistic than Nano Banana 2 on real-world edit prompts. Source: https://www.techradar.com/ai-platforms-assistants/i-compared-chatgpt-images-2-0-and-googles-nano-banana-2-using-real-world-prompts-from-portraits-to-product-shots-and-the-ai-image-generator-that-came-out-on-top-genuinely-surprised-me

- Use Nano Banana as a scout, not as a geometry authority: it has strong multi-reference/subject-combination evidence, but our Screenery panels need exact SVG contour/cutout fidelity that must be gated downstream. Sources: https://www.windowscentral.com/artificial-intelligence/gemini-nano-banana-viral-craze and https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- Build a decomposed reference packet with separate files, not one crowded collage by default: geometry/control map, watercolor style exemplar, palette/swatch card, object-vocabulary sheet, and edge/texture crop.

- Put role names in the prompt, not burned into the reference images: "Reference A is geometry only; do not copy colors or text", "Reference B is watercolor edge/paint handling only", "Reference C is palette only", "Reference D is shape vocabulary only."

- Remove or mask all text, logos, watermarks, and signage from reference images unless the final panel is allowed to include text. This is a conservative recommendation from weak text-leakage evidence plus the documented improvement in modern text rendering. Sources: https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend and https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- For watercolor toy-building panels, prefer isolated style crops for paint handling and edge language, but include one full-scene style exemplar so the model sees scale, object simplification, and composition rhythm.

- For role-separation tests, start with three references: approved geometry map, one style exemplar, and one palette/object sheet. Add fourth/fifth references only after inspecting a failure and naming the missing property.

- Do not assume "image 1 = pose, image 2 = style" works on gpt-image without a local ablation. The practitioner evidence found supports this pattern better for Nano Banana/photo prompts than for gpt-image.

- Avoid contact-sheet-only conditioning for production. Keep contact sheets for humans, audit trails, and agent handoffs; send separate reference images to the model where possible.

- If a contact sheet must be used, use large tiles, white gutters, no burned-in captions, no visible filenames, and role descriptions in the prompt. This is an inference from weak contact-sheet evidence and text-contamination risk.

- Prompt format recommendation: "Use Reference 1 only for panel geometry and safe pockets; use Reference 2 only for watercolor toy-building paint handling; use Reference 3 only for palette; use Reference 4 only for simple object vocabulary; do not copy text, logos, signs, people, backgrounds, or exact composition from style references."

- Verification recommendation: after generation, judge separately for geometry fit, style match, object vocabulary, palette, and text/sign leakage. A model can pass style while failing geometry, or pass geometry while importing unwanted labels.

- Research recommendation: run a future zero/low-cost local ablation only when spend is allowed: same prompt with separate refs versus no refs versus contact sheet versus shuffled ref order. The current report did not run generation and did not spend.

## Sources (full list of URLs used, deduped)

- https://www.theverge.com/ai-artificial-intelligence/916166/openai-chatgpt-images-2

- https://www.techradar.com/ai-platforms-assistants/i-compared-chatgpt-images-2-0-and-googles-nano-banana-2-using-real-world-prompts-from-portraits-to-product-shots-and-the-ai-image-generator-that-came-out-on-top-genuinely-surprised-me

- https://www.vox.com/future-perfect/411924/artificial-intelligence-chatbots-openai-chatgpt-anthropic-google-gemini-claude-grok

- https://www.businessinsider.com/openai-studio-ghibli-style-images-violate-copyright-or-not-2025-3

- https://www.windowscentral.com/artificial-intelligence/gemini-nano-banana-viral-craze

- https://www.tomsguide.com/ai/nano-banana-pro-is-here-these-are-all-of-the-new-features-in-googles-latest-ai-image-generator

- https://www.techradar.com/ai-platforms-assistants/gemini/i-turned-myself-into-a-3d-figurine-with-googles-nano-banana-heres-how-you-can-hop-on-the-latest-ai-image-trend

- https://www.tomsguide.com/ai/ai-image-video/nano-banana-just-broke-the-internet-with-these-viral-trends-here-are-5-ai-photo-prompts-to-try-now

- https://www.tomsguide.com/ai/forget-flowers-5-viral-nano-banana-trends-reshaping-valentines-day

- https://www.techradar.com/ai-platforms-assistants/gemini/i-upgraded-my-ai-image-prompts-using-geminis-advice-specifying-lighting-layouts-and-even-fonts-changed-everything

- https://www.androidcentral.com/apps-software/ai/tech-talk-what-the-heck-is-gemini-nano-banana

- https://www.creativebloq.com/design/design-software/can-adobes-new-custom-firefly-models-finally-tame-ai

- https://www.wired.com/story/what-is-adobe-firefly/

- https://www.tomsguide.com/ai/ai-image-video/i-didnt-believe-the-hype-about-google-mixboard-now-im-obsessed

- https://www.theverge.com/news/783991/google-labs-mixboard-ai-design-canvas

- https://www.lifewire.com/midjourney-basics-8697054

- https://www.architecturaldigest.com/story/color-trend-report-2023

- https://www.lifewire.com/canva-brand-kit-claude-integration-11893241

- https://www.creativebloq.com/design/design-software/canva-ai-2-0-can-create-an-entire-brand-campaign-from-a-text-prompt

- https://www.tomsguide.com/ai/with-one-prompt-i-built-an-entire-brand-kit-in-an-hour-using-lovart

- https://arxiv.org/abs/2408.03209

- https://arxiv.org/abs/2311.02343

- https://arxiv.org/abs/2509.02000

- https://arxiv.org/abs/2502.13951

- https://en.wikipedia.org/wiki/Prompt_engineering

## Gaps (what you searched for but could not find, and what you tried)

- Gap: I did not find practitioner/community evidence that gpt-image-1 or GPT Image 2 reliably supports explicit multiple-reference role separation such as "image 1 = pose, image 2 = style, image 3 = palette."

- Tried searches: "gpt-image-1 multiple reference images role separation pose style practitioner blog"; "gpt-image-1 multiple images reference style bleed content leakage community"; "GPT image generation multiple reference images contact sheet style reference workflow blog"; "gpt-image-2 multiple reference images practitioner."

- Tried searches: "OpenAI image generation edit multiple images reference guide blog"; "ChatGPT image generation multiple reference images style pose Reddit"; "ChatGPT 4o image generation multiple images references style bleed"; "ChatGPT image generation reference images contact sheet."

- Tried searches: "gpt-image-1 tutorial multiple images reference"; "gpt-image-1 edit multiple input images tutorial"; "gpt-image-1 image array edit multiple"; "gpt-image-1 image-to-image reference style."

- Gap: I did not find a reliable practitioner comparison of separate reference images versus a single contact-sheet/grid reference for gpt-image or Nano Banana.

- Tried searches: "reference image contact sheet AI image generation workflow"; "ChatGPT image generation contact sheet reference image grid works"; "Gemini Nano Banana contact sheet reference images grid"; "AI image model contact sheet style reference grid multiple references."

- Gap: I did not find measured evidence that reference-image order affects gpt-image or Nano Banana outputs.

- Tried searches: "reference image order affects AI image generation Midjourney prompt order image prompts"; "Midjourney order of image prompts matter reference images"; "AI image generation prompt word order affects output reference order"; "Stable Diffusion image prompt order matters IPAdapter multiple references."

- Gap: I did not find practitioner evidence for an ideal input reference resolution for gpt-image or Nano Banana. I found output-resolution claims, but not input-reference best practice.

- Tried searches: "Nano Banana best reference image resolution clear photo prompt guide"; "Gemini Nano Banana clear reference photo best results resolution"; "Nano Banana prompt guide clear photo full body image reference"; "gpt-image-1 best reference image resolution prompt tips."

- Gap: I did not find gpt-image-specific evidence that annotated/labeled reference images leak text into generated outputs.

- Tried searches: "AI image generation reference image labels leak text into output practitioner"; "ChatGPT image generation text in reference image leaks into generated image"; "Gemini Nano Banana text in reference image copied into generated output"; "AI image model annotated reference image text leakage generated output."

- Gap: I found only weak anecdotal Nano Banana text-leakage evidence, not a controlled or repeated practitioner study.

- Gap: I found better prior art for property-decomposed systems in broader creative tools, moodboard tools, brand-kit workflows, Midjourney-style prompting, and research systems than in gpt-image-specific practitioner writeups.

- Tried searches: "AI art workflow style reference palette swatch texture sheet shape language reference images"; "generative AI brand design workflow color palette reference image swatches style guide"; "game asset AI workflow reference sheet palette texture shape language"; "children's book illustration AI workflow style reference sheet palette character sheet."

- Tried searches: "style bible AI image generation reference sheet"; "character sheet style reference AI image generation workflow"; "style guide AI image generation color palette reference image"; "style reference shape language AI image."

- Assumption for recommendations: the user's production stack values exact Screenery geometry, blank/no-signage handling, watercolor toy-building style, and gpt-image as production path; those stack-specific priorities come from the task prompt and repo context, not from external sources.
