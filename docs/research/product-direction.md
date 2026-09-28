# Music Vending Machine: product direction (superseded)

Status: **superseded research snapshot.** This was the discovery-interview record before the approved [PRD](../PRD.md) and [implementation plan](../implementation-plan.md); those documents and [CONTEXT.md](../../CONTEXT.md) now govern. Kept as evidence of how decisions were reached. Statements below about open decisions, current capability or implementation status are out of date.

## Intended result

A personal tool turns a finished song into a complete, editable music video. Recurring-character narrative videos are the first target; visible singing and abstract music-driven visuals remain in scope. The user approves a timed still preview with the song, references, and estimated cost before automated video production.

Expected inputs are Suno songs with audio, stems, and MIDI. Verify version and timing alignment among these assets. Audio preparation may propose cleanup and arrangement changes through an Ableton integration; the user approves the production master before video production. Preserve source material and previous masters. Reliable Windows processed-audio export remains an integration test, not an established capability.

The approved master remains intact outside deliberate narrative breaks. Added sound effects are allowed. The agent may propose a prelude, dialogue interlude, break before a bridge, suspenseful cutout, or complete silence over action, subject to preview approval. These are optional story choices; no interruption is required. Dialogue production and each proposal's exact time mapping still need definition.

Use the user's [Essentia analysis service](https://essentia.v1su4.dev/docs). Its live API contract and health were inspected; successful analysis on a project song remains to be verified. Keep musical evidence tied to the approved audio version.

## Interaction model

Use Project Stack Structure as the functional reference, with a calmer, more visual workspace. A programmatic director agent operates the project through concrete actions and visible artifacts. Conversation accompanies planning and changes; it is not the whole product.

Use Storyception as the primary visual/workspace reference: canvas in the center, a compact representational timeline below, and visible characters, references, story sections, and assets. Multiple focused canvas views are proposed over the same project data. Canvas interaction and musical/agent actions drive the work; detailed manual timeline editing is secondary.

Story development is collaborative and has the most back-and-forth. The user brings story ideas, images, and exact references; the agent helps develop and revise the direction with them. Avoid a fixed menu of three treatments as the required entry flow. An evolving visual board/treatment and explicit exact-versus-inspiration reference roles are proposed UI mechanisms.

Editing is primarily automatic and musically driven. Beatsmaxxer Pro is the interaction reference. The user adjusts musical behavior and auditions revisions instead of manually placing every clip. A timeline remains useful for seeing scenes, music, gaps, and review findings. The earlier request for a conventional full timeline editor was refined by the user; do not build an NLE as the primary experience by default.

Keep versions and preview one revision against the previous version. Whether a new revision becomes active automatically and how user edits are protected remain unresolved.

## Automatic editing and review

Select clips using measured attributes and story relevance, including motion direction, color, speed, duration fit, and compatibility with neighboring clips. Evaluate proposed trims and speed ramps as part of the actual edit. Preserve explicit gaps when no candidate fits; do not force weak clips into the sequence.

The confirmed policy is to mark gaps and block final export after allowed repairs fail. Suitability thresholds and retry allowances need calibration and cost research.

Incomplete previews should still show the whole song's planned structure. Use timed keyframes, storyboard images, or labeled placeholders for missing video, with the needed shot intent visible. These states must not be counted as completed clips or silently pass the final-export gate.

Plan unfinished regions at section level when that is sufficient: a representative visual plus what happens, why it matters, and how it connects to the story. A bridge does not need a complete shot-by-shot storyboard to communicate its role. Expand detail progressively rather than requiring exhaustive keyframes up front.

Review combines technical checks with vision/audio evidence and an evaluation component. It also supports prompt revisions and continuity before and during generation. Automatic QC may fix clips and pacing while preserving the approved story and style. A change to that direction returns to the user.

Evaluate JEV or an open alternative as a decision component; JEV's documented text-only input requires a separate media-analysis layer. Evaluate a Gemini video-understanding model for an advisory near-final pass before the user's review of the assembled cut. Reviewer models and their authority are not interchangeable with the director agent.

## Generation and deployment

The first draft should be as local as practical while achieving useful quality. Paid models are optional upgrades for selected shots/revisions, preserving the approved story and edit. The app recommends generation routes; the user chooses, and paid generation is not an automatic fallback. Local-first also guides analysis/review, with optional LLM assistance: user named Codex, Kimi, OpenCode, DeepSeek and GLM as candidates and favors directed Qwen3-VL vision analysis. Distinguish execution harnesses from model providers and select exact integrations through testing. Research costs before setting the spending cap. Candidates named by the user:

- Higgsfield and Midjourney through browser use.
- Local Qwen Image Edit 2.1 and MiniMax H3; exact workflows/access routes require verification.
- Paid Seedance 2.0 and 2.5.

Use a homelab production coordinator with this Windows PC for local GPU work. UI technology is Svelte and WebGPU, delivered through a web app and a Windows-first Tauri desktop app.

Rust is the user's preferred backend direction. Proposed roles are a Rust home-server coordinator and shared production logic plus the Tauri backend, with model runtimes reached through adapters. RustFS already exists on the home server and should be reused.

Local worker hardware: RTX 5090 / 32 GB VRAM, independently observed; 128 GB system RAM, confirmed by the user. Benchmark peak GPU/host memory and schedule generation/review workloads around interactive preview needs.

Desktop and web share the same projects, with autosave from either client and RustFS-backed storage. Coordinate versioned updates centrally to preserve work across clients. Offline/standalone desktop is not a confirmed requirement. The exact WebGPU role and runtime capability/fallback still need definition and a Windows WebView2/browser validation pass.

Jcode at jcode.sh is an agent-engine candidate to test before choosing, not a committed dependency.

## Reuse boundaries

VRGDG is reference-only: build independently of its implementation. UI and appropriate code may come from the user's other repositories:

| Repository | Evidence-backed candidate role |
| --- | --- |
| Creative Studio Pro | Svelte workspace, story cards, approvals, agent decision UI |
| Project Stack Structure | Music structure, clip descriptors/ranking, reference packets, coverage and review, WebGPU effect preview |
| Storyception | References, character sheets, concepts and storyboard alternatives |
| TrailerCraft | Prompt repair, still animatic and musical marker controls |
| Beatsmaxxer Pro | Svelte/WebGPU playback, music-triggered timing and repeatable variations, web/desktop platform boundaries |
| svelte-video-shaders | Svelte music-section clip pools, waveforms, retiming, and effect controls; its existing renderer is WebGL, so WebGPU needs adaptation |

Source audits do not establish runtime correctness. Preserve unrelated work in donor repositories. Do not import their framework assumptions, permissive weak-match fallback, or placeholder results as product behavior.

## Open decisions

- Dialogue/sound-effect production and precise song-to-video time mapping for approved audio breaks.
- Ableton MCP operational capabilities and reliable processed-audio export.
- WebGPU role and capability/fallback policy on Windows desktop and web.
- Exact initial musical controls and how the director exposes them.
- Revision activation/restoration, protected edits, and explicit keep/reject decisions.
- Preview/reference generation spending before production approval; paid/local retry caps.
- First validated generation workflow and browser-worker operation.
- Lyrics alignment/correction and exact-versus-inspiration reference handling within collaborative story development.
- Final export formats, resolution/aspect ratio, and what remains editable.
- Pilot acceptance criteria and sample song/section.

See [discovery history](music-video-discovery.md) and the source-cited assessments in this directory for evidence, rejected assumptions, and unresolved integration details.
