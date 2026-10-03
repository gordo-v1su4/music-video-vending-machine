# Music Vending Machine

Status: approved for implementation, 2026-09-25. This document supersedes unresolved proposals in research; research remains evidence, not implemented capability.

## Objective

A personal, local-first studio turns an approved song and collaboratively developed story into a complete editable narrative music video. Automate the software build through verification and private deployment. Retain intentional creative approvals in the product.

## Requirements

| ID | Requirement |
| --- | --- |
| R01 | Shared Svelte web and Windows Tauri clients, homelab Rust coordinator, dedicated self-hosted Convex on home application host (user-approved September 26 database revision), existing RustFS, existing Trigger with a thin Bun task layer, Windows RTX 5090 worker. |
| R02 | Import and preserve source audio, optional stems/MIDI, lyrics, images and clips. Approve an immutable production master. Verify optional timing assets before use. |
| R03 | Use Essentia analysis tied to master identity; preserve uncertainty and manual corrections. Narrative v1 does not promise word-level alignment or lip sync. |
| R04 | Central visual canvas with Story, References, Production and Review views; persistent preview and compact representational timeline. Collaborative treatment, stable character/location identities, exact versus inspiration references. Production presents story/beat planning and prompts, image generation, video generation, automatic beat-derived compositing, and a distinct review stage as a clear progress experience rather than a bare checklist. |
| R05 | Whole-song timed preview with section stills or explicit placeholders and story intent. Approve exact master, treatment, references, breaks, route and allowance before video production. Changed inputs invalidate affected approval. |
| R06 | Inserted breaks pause song progression and extend video time. Cutouts mute audio without stopping song time. Supplied dialogue/SFX only in v1; preserve approved music otherwise. |
| R07 | Local-first image/video adapters with production workflows submitted through SwarmUI. Validate candidate local models and workflow hashes in SwarmUI; standalone ComfyUI probes are exploratory only. Qwen Image 2.1 is a promising image-edit/consistency candidate, not production-enabled until preservation and identity checks pass. No VRGDG implementation reuse, automatic paid fallback, or paid calls without a separately approved quote. |
| R08 | Musical controls: cut density, minimum shot length, beat/bar/onset/validated MIDI source, section energy, motion intensity, bounded speed variation, reproducible seed, pinned shots/protected sections. |
| R09 | Reject unsuitable clips before ranking story/duration/motion/color/repetition and actual adjacent trim/retime boundaries. Unfilled coverage stays explicit. Initial attempt plus at most two replacement attempts per shot. |
| R10 | Candidate revisions never replace the active cut until Keep. Synchronized comparison, Reject, restoration, protected pins and durable lineage. |
| R11 | After automated production self-check and beat-derived compositing, run a distinct Review stage with multiple independent visual reviewers. Compare candidate models (including Gemini Flash and local Qwen VL/DeepSeek options) on the same material before choosing production configuration. Review whole-story coherence and beat fit, visual continuity/character/location, shot suitability, transitions/cuts/timing/rhythm, and technical sequence errors; treat supplied performance footage as an intentional strand and assess lip-sync separately in a later technical pass. Findings retain revision/artifact, time range, evidence, uncertainty, reviewer identity and action; subjective story/style judgments remain advisory. |
| R12 | Export 1280x720 16:9 24fps H.264/AAC MP4. Full export blocks on unresolved gaps or failed checks. Excerpt export validates its whole range. Placeholder previews are never finished exports. |
| R13 | Editable archive includes manifest, master, media, references, edit decisions and provenance; reimport and rerender verified. |
| R14 | Versioned /api/v1 OpenAPI with generated TS client and resumable events. Revision-aware writes reject conflicts. Distinct song/video/source/frame time. |
| R15 | Worker capability/heartbeat/lease/cancellation/artifact receipts. Persist submission intent and provider IDs; reconcile uncertain submissions without blind retry. |
| R16 | WebGPU preview with rendered proxy fallback; authoritative FFmpeg rendering. Browser and WebView2 verified separately. |
| R17 | Private authenticated deployment, scoped worker credentials, BWS secrets, backups and tested restoration/rollback. |
| R18 | First-run pilot selection; whole-song preview and finished 30–60 second passage before full-song acceptance. Real visual/audio evidence, not fixture-only success. |
| R19 | Approved character identity profiles have separately approved Looks. Each hair/costume change is a distinct Character sheet/Look assigned to scenes or sequences before generation; preserve identity and within-sequence hair/costume continuity, favoring fewer changes when the story permits. Include reusable location and visual-style anchors. |
| R20 | One user-authorized Generate action starts a durable unattended run: generate planned media, self-check each shot against prompt/reference/timing/media health, apply the bounded repair allowance, create the beat-derived musical edit, then hand the candidate to independent Review. Continue independent shots after failures; surface unresolved gaps and block export. |
| R21 | Review findings produce issue-appropriate repair proposals: replace, trim, lengthen, reorder, re-render, re-prompt, or fill a gap. Repair scope adapts between a shot and a story/edit chunk; chunk review includes neighboring shots and context handles. The user approves a candidate chunk, which is rechecked locally and then in the full-cut review before it can become the final candidate. |
| R22 | Reviewer comparison and repair turnaround/option counts remain evidence-led and configurable until model evaluations establish reliable capabilities. Review candidates must be compared on shared clips with recorded outputs; do not assume image-sequence review equals native video understanding. |

## Authority and boundaries

UI decision, 2026-09-25: dark mode is the default, with a dark zinc/neutral palette as explicitly requested by the user. Use the pinned Impeccable skill set for UI design and testing, including contrast, keyboard focus, responsive composition and clear production states. Use the Codex in-app Browser for browser verification. These checks support rather than replace Windows WebView2 acceptance. Keep generation self-check (automated production quality control) distinct from Review (independent editorial/technical judgment after compositing).

The director proposes validated project actions. Rust enforces approvals, locks and allowances; agents and reviewer scores cannot override them. Story/style changes return to the user. Approve the supplied song directly in v1; Ableton preparation, generated singing and abstract modes are later milestones. No primary NLE, offline standalone production, public accounts/billing, or social publishing. Performance footage supplied by the user is supported in narrative videos; generated singing and word-level lip-sync scoring are later work.

Use appropriate user-owned donor patterns without modifying donor repositories: Storyception visual organization, Creative Studio Pro Svelte workspace, Beatsmaxxer musical timing, and selected Project Stack/TrailerCraft patterns. Reject their permissive weak-match and placeholder-success behavior.

## Release acceptance

1. Private pilot: homelab web + installed Windows client, one shared durable project, whole-song preview and real 30–60 second rendered passage.
2. Narrative production: complete song, no placeholders/blocking findings, verified MP4/editable archive and recovery. Production is unattended after approved launch, automatic beat-derived compositing precedes multi-reviewer Review, and any repaired chunk receives both local and whole-cut re-review.

The first gate does not establish the second. User selects the real song/references during first-run setup and approves creative direction/production.
