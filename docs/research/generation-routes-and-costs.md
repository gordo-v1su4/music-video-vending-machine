# Generation routes and quote inputs

Research checked 2026-09-25. Planning evidence only: no generation, uploads, account changes, installation, or spending. Prices and model catalogs require refreshing when a project is quoted.

## Decision being supported

Build the first draft as locally as practical. A full-song rough preview can contain representative section visuals and story notes wherever footage is missing; mark those segments as placeholders. Paid generation is an optional later upgrade for selected shots, chosen by the user from app recommendations. A preview that spans the song is not proof that every final shot has been generated.

## Local candidates

| Candidate | Verified scope | Readiness implication |
| --- | --- | --- |
| Qwen-Image-2.1 | Official unified image generation/editing model, including reference images and identity-oriented editing. The model card identifies a 7B visual component and the Qwen Research License. | Suitable candidate for concepts, character references, section stills and image revisions. The exact local edit workflow still needs validation. |
| MiniMax H3-Base | Released local model family covers FL2VA and Ref2VA. The open base release produces 768p, 24 FPS video with stereo audio, with documented 4–15 second output. | Candidate for local moving shots, including first/last-frame and reference-conditioned generation. Do not promise the complete hosted H3 system locally. |

Sources: [official Qwen model card](https://huggingface.co/Qwen/Qwen-Image-2.1), [official MiniMax model card](https://huggingface.co/MiniMaxAI/MiniMax-H3). H3's hosted Context-IR preprocessing/orchestration is excluded from the open release, and its 2K regeneration component is not released as local weights. These are named model licenses, not a verified claim of permissive Apache licensing.

The existing [VRGDG integration audit](vrgdg-integration.md) records Qwen 2.1 BF16/INT8, its image-edit encoder, and H3 FL2VA/Ref2VA quantized filenames on this PC. It separately records Qwen Image Edit 2511; that is not a substitute for the requested 2.1. File presence does not establish integrity, loading, GPU fit, registered nodes, throughput, or output quality. No specific Qwen 2.1 image-edit Builder adapter was located. The H3 adapter has its own frame-grid and length constraints; generated duration and final timeline trim must remain separate.

Local marginal provider charges may be zero, but GPU time, power, storage, failed attempts and operator time are real costs. Do not publish a local minutes-per-shot estimate until a representative edit and H3 clip have run successfully. The existing slideshow runner can assemble timed stills with the song before full motion is ready.

## Optional paid routes

Higgsfield now documents a standalone dollar-billed API with durable request IDs, polling/webhooks and output downloads. Its API balance is separate from website subscription credits; its MCP/ChatGPT routes use plan credits. Those are different billing routes even when they expose similarly named models. The public pricing page did not expose a usable signed-out plan quote during this research, so the user's actual plan, credits, entitlements and per-operation quote remain unknown. [Official API overview](https://higgsfield.ai/blog/higgsfield-api), [website pricing](https://higgsfield.ai/pricing).

The live API model pages verify both requested Seedance versions through Higgsfield:

| Route | Public configuration range | USD per 1,000 billable video tokens, before customer discount |
| --- | --- | --- |
| Seedance 2.0 | 4–15 seconds; 480p through 4K | Without video reference: $0.014 at 480p/720p/1080p, $0.008 at 4K. With video reference: $0.0084 and $0.0048 respectively. |
| Seedance 2.5 | 4–30 seconds; 480p–720p | Without video reference: $0.0214. With video reference: $0.01284. |

Both pages calculate tokens as `ceil((input_video_seconds + generated_video_seconds) * output_width * output_height * 24 / 1024)`. Image/audio references do not add video-input seconds. A lower reference-video token rate does not necessarily yield a cheaper request because input duration also counts. These are Higgsfield API prices, not website credit prices or a claim about direct ByteDance billing. [Seedance 2.0 live model page](https://open.higgsfield.ai/models/bytedance/seedance-2.0/reference-to-video/playground), [Seedance 2.5 live model page](https://open.higgsfield.ai/models/bytedance/seedance-2.5/reference-to-video/playground).

Higgsfield browser use remains a proposed adapter, not a tested production route. It requires authenticated access, the exact configuration/quote, recoverable job identification, and verified download behavior. The inspected local package has no Higgsfield browser adapter. Official integrations offer a clearer request lifecycle to evaluate alongside the browser preference. Unlimited/fair-use plans can have changing queue speed and concurrency, so they do not establish a completion-time guarantee. [Higgsfield access terms](https://higgsfield.ai/terms-of-use-agreement).

Midjourney lists monthly Basic/Standard/Pro/Mega at $10/$30/$60/$120, with different Fast GPU allocations; extra Fast time is $4/hour. These are subscription/GPU-time costs, not a fixed image price. Its published terms prohibit automated access or asset generation, and its official FAQ does not offer a public API. Treat manually generated assets imported into this app as the currently supportable planning route; unattended browser generation is not a verified supported integration. [Plan comparison](https://docs.midjourney.com/hc/en-us/articles/27870484040333-Comparing-Midjourney-Plans), [terms](https://docs.midjourney.com/hc/en-us/articles/32083055291277-Terms-of-Service), [official FAQ repository](https://github.com/midjourney/docs/blob/main/data/faq.txt).

## Quote design and short validation

Keep three ledgers: measured local GPU work, subscription credits/GPU hours, and incremental API dollars. Show estimates and remaining caps in their native units; avoid presenting unused subscription allowance as new cash spending.

A project quote needs the number of shots and generated seconds including handles; actual dimensions; reference-video seconds; attempts per shot; concept/reference-image revisions; audio options; upscale work; QC/review passes; and paid shot selections. Show a range for retries and reserve budget before submission. Persist provider job IDs before polling so an uncertain response does not trigger an accidental duplicate paid request.

Validate one Qwen reference edit, one representative H3 shot and one full-song placeholder preview on the local worker. Record configurations, peak memory, wall time, output metadata, visible quality and failed attempts. Then compare one candidate paid-shot configuration using its current quote without submitting it. Only after that evidence should the app recommend local versus paid upgrades or estimate a whole project's cost and completion time.
