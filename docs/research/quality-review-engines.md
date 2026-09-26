# Quality review engines: Jev and open alternatives

Research snapshot: 2026-09-25. Official documentation and source review only; no models installed, paid requests made, or review accuracy measured. These are evaluation candidates, not an architecture decision.

## What the user wants

Technical, musical, and film-flow review for an automated music-video generator. Jev from TypeSafe AI, or a similar open-source option, is a candidate. Jcode remains a separate candidate for the planning/tool-using agent.

## Jev: useful judgment component, not a media viewer

Jev returns typed choices, rubric scores, or yes/no probabilities. It does not converse, generate prose, or run a tool-using agent loop. The vendor explicitly distinguishes it from a coding-agent model. [Official agent explanation](https://docs.typesafe.ai/introduction/coding-agents)

The current documentation is explicit: **text only; no image, audio, or video input**. It can judge a treatment, shot descriptions, or evidence extracted by other systems; it cannot directly watch the edit or hear the song. A text summary that misses an artifact also deprives Jev of that evidence. [State](https://docs.typesafe.ai/concepts/state)

It is available headlessly through `POST https://api.typesafe.ai/v1/systemone`, with API-key authentication and typed JSON requests/responses. Python and JavaScript clients are published. This is a remote evaluation service; no browser UI is needed for normal requests. [API](https://docs.typesafe.ai/api), [SDKs](https://docs.typesafe.ai/sdk)

The documented model is `jev-1.13.0`; version pinning matters when tuning thresholds. No downloadable Jev weights or self-hosted Jev runtime were found in the official documentation or public organization. The SDKs and comparison adapter are MIT-licensed; that does not make the hosted model open source. [Models](https://docs.typesafe.ai/models), [Official repositories](https://github.com/typesafe-ai)

Choice/Score confidence is computed from the output distribution. It is not independent proof that a judgment is correct; thresholds need testing on our clips and rubric. The vendor documents weaknesses with numerical operations, complex indirection, irrelevant context, and adversarial input. Keep timing arithmetic in code. [Confidence](https://docs.typesafe.ai/confidence), [Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)

## Two open candidates worth testing

| Candidate | Verified capability | Proposed use and gap |
| --- | --- | --- |
| [TypeSafe System One Adapter](https://github.com/typesafe-ai/system-one-adapter-python) — MIT | Python replacement for the typed evaluation interface, using LLM providers or custom OpenAI-compatible endpoints; sync/async, structured output, retries, usage diagnostics. | Compare hosted Jev against a self-hosted text model over identical extracted evidence. It provides an interface, not Jev weights or equivalent calibration. |
| [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni) — Apache-2.0 code and [Thinking checkpoint](https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Thinking) | Open audio/image/video/text understanding with local Transformers/vLLM examples, including video with its audio. Official cookbooks cover music analysis, scene transitions, and audio-visual questions. | Candidate for time-stamped perceptual observations and creative criticism. Domain-specific QC accuracy, temporal localization, and full-song narrative judgment remain unproven. |

The adapter's current provider message type is `content: str`, so it is not a ready-made multimodal transport even when its underlying model supports media. Use a separate media-analysis adapter, then feed its structured text evidence into the decision interface. [Provider source](https://raw.githubusercontent.com/typesafe-ai/system-one-adapter-python/main/src/system_one_adapter/providers/base.py)

Qwen3-Omni is a substantial hardware candidate: the official BF16 Transformers table lists about 68.74 GB for a 15-second video with the Thinking checkpoint. Quantization, smaller excerpts, or another serving arrangement need separate validation; local PC feasibility is not established. [Hardware table and inference examples](https://github.com/QwenLM/Qwen3-Omni#minimum-gpu-memory-requirements)

## Proposed review boundary (architectural inference)

The application owns artifacts, timeline versions, generation attempts, cost limits, and every action. Jcode or another planner proposes direction and repairs. Review engines return evidence and judgments; they do not bypass approvals or directly spend a replacement budget.

1. **Technical checks:** decodeability, dimensions/frame rate, actual versus required duration, timeline gaps, original-song placement and duration, signal levels, and detectable frozen/black segments. Measurements and comparisons belong in deterministic tools; some anomaly detectors still need contextual review.
2. **Musical review:** analyze beats, downbeats, sections, lyrical phrases, and energy changes; compare edit positions to those features. Estimated musical markers carry uncertainty. Intentional off-beat cuts are not automatically defects.
3. **Film review:** inspect actual clips and adjacent transitions for continuity, motion artifacts, framing, character consistency, shot variation, and dramatic progression against the approved treatment. Review local sequences and the complete assembled export, not only isolated stills.
4. **Decision routing:** optional Jev/alternative scores atomic rubric items over measured facts and perceptual observations. The application combines them with hard checks and routes to accept, revise, or human review.

Every finding should retain artifact/version ID, time range, dimension, severity, evidence, uncertainty, and suggested action. Unobserved dimensions must remain unknown. Preserve original takes and user edits when proposing repairs.

## Small comparison pilot before choosing

Use the same 20–30-second music excerpt and a few deliberately defective edits: shifted song, frozen shot, continuity mismatch, repetitive cutting, and a purposeful off-beat cut. The user labels acceptable versions and meaningful failures. Compare deterministic-only checks, perceptual review plus the open adapter, and perceptual review plus Jev against those labels.

Measure missed serious defects, false alarms, agreement with the user's taste, localization accuracy, cost, latency, and local memory needs. Keep review advisory during this pilot. Only grant bounded automatic repair after measuring it; calibrate each rubric/action separately rather than selecting an arbitrary global confidence threshold.

Interview decision still needed: when QC finds a problem, should the app automatically fix technical issues, also regenerate creative scenes within a chosen allowance, or ask first? Neither a numeric allowance nor acceptance thresholds are settled yet.
