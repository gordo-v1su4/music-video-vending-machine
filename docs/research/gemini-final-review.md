# Gemini as the near-final music-video reviewer

Research snapshot: 2026-09-25. Official Google documentation reviewed; no upload, paid inference, installation, or quality benchmark performed. Model and processing mode remain evaluation choices.

## User intent and placement

The user wants a video-capable reviewer to inspect the assembled music video when it feels roughly 90% finished: the last reviewer before the user. It should explain what works, what fails to make sense, and which changes would improve the film. That percentage describes a production stage, not a measured quality score.

This is an advisory review of the complete edit with its music. It supplements per-clip QC and deterministic export checks. It is separate from Jev's text-evidence decision role and the planning agent's execution role. Final creative judgment stays with the user.

## Verified Gemini capabilities and limitations

Gemini processes both audio and visual streams and can return time-referenced observations. Static processing defaults to one frame per second; Google explicitly warns that rapid motion and quick cuts can be missed. Static mode supports custom frame sampling and clipping. Models with a 1M context window support approximately three hours at low media resolution or one hour at high resolution. Some current Flash models also support selective agentic exploration of frames, transcripts, and audio. These are input/processing capabilities, not evidence of exhaustive inspection or calibrated artistic judgment. [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding)

For the pilot, compare a whole-edit static pass against selective exploration where supported. Follow up on uncertain fast sequences at a higher sampling rate. A claimed event's timestamp should be verified against the actual timeline; neither a plausible description nor an exact-looking timestamp guarantees accuracy. This is our proposed evaluation procedure, not a documented music-video quality guarantee.

Gemini supports structured JSON responses with a subset of JSON Schema. Google explicitly requires application validation because structurally valid responses can still have incorrect meanings. Validate time ranges, artifact IDs, priority enums, and empty/unknown observations locally. [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)

## Current model candidates, not a selection

| Candidate | Reason to include in the pilot | Relevant documented status |
| --- | --- | --- |
| `gemini-3.8-flash` | Current stable comparison for cost, speed, and usefulness of criticism. | Listed as stable in the current catalog; [model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). |
| `gemini-3.1-pro-preview` | Compare whether its critique improves enough to justify additional cost. Do not presume a better result from its name. | Preview; video/audio inputs and structured output supported; 1,048,576 input-token limit. [Model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview) |

The live [catalog](https://ai.google.dev/gemini-api/docs/models) currently restricts 2.5 models to prior active users and directs new projects to newer models. Verify availability with the intended account at integration time; avoid hard-coding an older recommendation from memory.

## Review input and proposed rubric

Provide an immutable review render with the original song, timeline/version ID, duration, approved treatment, intended visual mode, and a short list of deliberate creative choices. Include lyrics/section markers only where useful. Do not provide the generator's self-assessment as ground truth.

Ask the reviewer to give a viewer's reading before comparing it with the intended treatment, so the report reveals gaps between intention and what is visible. Proposed dimensions:

- **Comprehension:** what story, feeling, or progression comes across; where motivation, geography, chronology, or symbolism becomes confusing.
- **Musical relationship:** whether imagery, movement, cut rhythm, section changes, and energy support the song; distinguish purposeful contrast from accidental mismatch.
- **Film flow:** opening promise, escalation, repetition, contrast, transition logic, emotional payoff, and ending.
- **Continuity and craft:** recurring characters, environments, visual style, distracting artifacts, framing, and performance believability where relevant.
- **Strengths to preserve:** specific moments and why they work, so revision does not erase successful choices.
- **Prioritized changes:** a small ranked list of actionable improvements, with expected benefit, effort, and an alternative when regeneration is unnecessary.

Every concern should include an observed moment, start/end time or a whole-film scope, interpretation, uncertainty, and a proposed change. Separate an observable defect from a taste preference. “No supported finding” is valid; do not require a quota of faults.

## Proposed report and application behavior

Return `viewer_reading`, `strengths[]`, `findings[]`, `top_changes[]`, and `unassessed[]`. Findings carry `dimension`, `priority`, `start_seconds`, `end_seconds`, `observation`, `interpretation`, `suggestion`, and `uncertainty`. The application attaches the trusted render/version/model metadata itself.

Show findings as timeline-linked notes with keep/dismiss/request-change controls. A suggestion creates a proposed edit or regeneration request; it does not change the film automatically. Preserve the reviewed version and connect subsequent changes to accepted notes. Re-review a changed sequence plus its surrounding context, and run another whole-edit pass only when changes materially affect the overall structure.

## File handling and cost estimation

Use a review proxy with intact timing and music. The Files API documentation lists 2GB per file, 20GB per project, and automatic deletion after 48 hours. It supports explicit deletion. [Files API](https://ai.google.dev/gemini-api/docs/files)

The video overview currently advertises a larger paid-file limit than the Files API page, and gives inconsistent inline-size advice. Until verified, use the Files API with a proxy below 2GB and retain the authoritative render in application storage. Upload capacity is separate from model context capacity. [Video input overview](https://ai.google.dev/gemini-api/docs/video-understanding)

Estimate cost from the selected model, duration, sampling rate/resolution, processing mode, prompt/reference tokens, output/thinking budget, number of follow-up passes, and any cache/storage use. Call token counting where supported and record actual response usage; agentic exploration adds variable thinking and loaded-media usage. [Token accounting](https://ai.google.dev/gemini-api/docs/tokens)

Current Standard paid rates per million tokens: 3.8 Flash input $0.75 and output including thinking $3.75 through 2026-12-31; the page lists later increases. 3.1 Pro Preview uses $2/$12 for prompts up to 200k tokens and $4/$18 above that. These are token rates, not a promised cost per music video; refresh before implementation. [Pricing](https://ai.google.dev/gemini-api/docs/pricing)

## Proof before relying on it

Compare the candidates on the same near-final export, including intentional ambiguity, rapid edits, and known continuity or pacing defects. The user judges which notes are correct and useful, which are merely preferences, and which miss the point. Measure timestamp accuracy, false criticisms, missed important issues, preservation of strong moments, latency, and actual cost. A high rubric score is not a substitute for this evidence or the user's final watch.
