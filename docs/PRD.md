# Music Vending Machine

Status: approved for implementation, 2026-09-25. This document supersedes unresolved proposals in research; research remains evidence, not implemented capability.

## Objective

A personal, local-first studio turns an approved song and collaboratively developed story into a complete editable narrative music video. Automate the software build through verification and private deployment. Retain intentional creative approvals in the product.

## Requirements

| ID | Requirement |
| --- | --- |
| R01 | Shared Svelte web and Windows Tauri clients, homelab Rust coordinator, dedicated PostgreSQL, existing RustFS, existing Trigger with a thin Bun task layer, Windows RTX 5090 worker. |
| R02 | Import and preserve source audio, optional stems/MIDI, lyrics, images and clips. Approve an immutable production master. Verify optional timing assets before use. |
| R03 | Use Essentia analysis tied to master identity; preserve uncertainty and manual corrections. Narrative v1 does not promise word-level alignment or lip sync. |
| R04 | Central visual canvas with Story, References, Production and Review views; persistent preview and compact representational timeline. Collaborative treatment, stable character/location identities, exact versus inspiration references. |
| R05 | Whole-song timed preview with section stills or explicit placeholders and story intent. Approve exact master, treatment, references, breaks, route and allowance before video production. Changed inputs invalidate affected approval. |
| R06 | Inserted breaks pause song progression and extend video time. Cutouts mute audio without stopping song time. Supplied dialogue/SFX only in v1; preserve approved music otherwise. |
| R07 | Independently validated local Qwen image and MiniMax H3 video adapters. No VRGDG implementation reuse. No automatic paid fallback. Paid integration tests require a separately approved quote. |
| R08 | Musical controls: cut density, minimum shot length, beat/bar/onset/validated MIDI source, section energy, motion intensity, bounded speed variation, reproducible seed, pinned shots/protected sections. |
| R09 | Reject unsuitable clips before ranking story/duration/motion/color/repetition and actual adjacent trim/retime boundaries. Unfilled coverage stays explicit. Initial attempt plus at most two replacement attempts per shot. |
| R10 | Candidate revisions never replace the active cut until Keep. Synchronized comparison, Reject, restoration, protected pins and durable lineage. |
| R11 | Deterministic checks plus directed temporal visual evidence. Findings retain revision/artifact, range, observation, uncertainty and action. Gemini is optional, quoted, advisory and unverified until live-tested. |
| R12 | Export 1280x720 16:9 24fps H.264/AAC MP4. Full export blocks on unresolved gaps or failed checks. Excerpt export validates its whole range. Placeholder previews are never finished exports. |
| R13 | Editable archive includes manifest, master, media, references, edit decisions and provenance; reimport and rerender verified. |
| R14 | Versioned /api/v1 OpenAPI with generated TS client and resumable events. Revision-aware writes reject conflicts. Distinct song/video/source/frame time. |
| R15 | Worker capability/heartbeat/lease/cancellation/artifact receipts. Persist submission intent and provider IDs; reconcile uncertain submissions without blind retry. |
| R16 | WebGPU preview with rendered proxy fallback; authoritative FFmpeg rendering. Browser and WebView2 verified separately. |
| R17 | Private authenticated deployment, scoped worker credentials, BWS secrets, backups and tested restoration/rollback. |
| R18 | First-run pilot selection; whole-song preview and finished 30–60 second passage before full-song acceptance. Real visual/audio evidence, not fixture-only success. |

## Authority and boundaries

The director proposes validated project actions. Rust enforces approvals, locks and allowances; agents and reviewer scores cannot override them. Story/style changes return to the user. Approve the supplied song directly in v1; Ableton preparation, singing and abstract modes are later milestones. No primary NLE, offline standalone production, public accounts/billing, or social publishing.

Use appropriate user-owned donor patterns without modifying donor repositories: Storyception visual organization, Creative Studio Pro Svelte workspace, Beatsmaxxer musical timing, and selected Project Stack/TrailerCraft patterns. Reject their permissive weak-match and placeholder-success behavior.

## Release acceptance

1. Private pilot: homelab web + installed Windows client, one shared durable project, whole-song preview and real 30–60 second rendered passage.
2. Narrative production: complete song, no placeholders/blocking findings, verified MP4/editable archive and recovery.

The first gate does not establish the second. User selects the real song/references during first-run setup and approves creative direction/production.
