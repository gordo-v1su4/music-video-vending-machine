# Music Vending Machine

Status: approved for implementation, 2026-09-25; terminology and product decisions refined 2026-09-28. This document supersedes unresolved proposals in research; research remains evidence, not implemented capability.

## Objective

A personal, local-first studio turns an approved song and collaboratively developed story into a complete editable narrative music video. Automate the software build through verification and private deployment. Retain intentional creative approvals in the product.

## Requirements

| ID | Requirement |
| --- | --- |
| R01 | Shared Svelte web and Windows Tauri clients, homelab Rust coordinator, dedicated self-hosted Convex on home app-vm (user-approved September 26 database revision), existing RustFS, existing Trigger with a thin Bun task layer, Windows RTX 5090 worker. |
| R02 | Import and preserve source audio, optional stems/MIDI, lyrics, images and clips. Approve an immutable production master. Verify optional timing assets before use. |
| R03 | Use Essentia analysis tied to master identity; preserve uncertainty and manual corrections. Narrative v1 does not promise word-level alignment or lip sync. |
| R04 | Central visual canvas with Story, References, Production and Review views; persistent preview and compact representational timeline. Collaborative treatment, stable character/location identities, exact versus inspiration references. Production presents story/beat planning and prompts, image generation, video generation, the production self-check, the automatic musical edit, and a distinct Review stage as a clear progress experience rather than a bare checklist. |
| R05 | Whole-song timed preview against the production master with section stills or explicit placeholders and story intent. Approve exact master, treatment, references, Character Looks and their sequence assignments, breaks, route and allowance before video production. Changed inputs invalidate affected approval. Approval authorizes production; the separate R20 Generate action starts it. |
| R06 | Inserted breaks pause song progression and extend video time. Cutouts mute audio without stopping song time. Supplied dialogue/SFX only in v1; preserve approved music otherwise. |
| R07 | Local-first image/video adapters with production workflows submitted through SwarmUI. Validate candidate local models and workflow hashes in SwarmUI; standalone ComfyUI probes are exploratory only. Qwen Image 2.1 is a promising image-edit/consistency candidate, not production-enabled until preservation and identity checks pass. No VRGDG implementation reuse, automatic paid fallback, or paid calls without a separately approved quote. |
| R08 | Musical controls: cut density, minimum shot length, beat/bar/onset/validated MIDI source, section energy, motion intensity, bounded speed variation, reproducible seed, pinned shots/protected sections. |
| R09 | Reject unsuitable clips before ranking story/duration/motion/color/repetition and actual adjacent trim/retime boundaries. Unfilled coverage stays explicit. Initial attempt plus at most two replacement attempts per shot within one production run; a user-approved repair grants the shots it regenerates a fresh allowance of the same size (see decisions). |
| R10 | Candidate revisions never replace the active cut until Keep. Synchronized comparison, Reject, restoration, protected pins and durable lineage. |
| R11 | After the automated production self-check and the automatic musical edit, run a distinct Review stage with multiple independent visual reviewers. Compare candidate models (including Gemini Flash, only under a separately approved quote, and local Qwen VL/DeepSeek options) on the same material before choosing production configuration. Review whole-story coherence and beat fit, visual continuity/character/location, shot suitability, transitions/cuts/timing/rhythm, and technical sequence errors; treat supplied performance footage as an intentional strand; word-level lip-sync scoring is a later milestone outside v1. Findings retain revision/artifact, time range, evidence, uncertainty, reviewer identity and action. Only blocking findings (objective failures, defined in CONTEXT.md) block export; subjective story/style judgments remain advisory. |
| R12 | Export 1280x720 16:9 24fps H.264/AAC MP4. Full export blocks on unresolved gaps or failed checks. Excerpt export validates its whole range. Placeholder previews are never finished exports. |
| R13 | Editable archive includes manifest, master, media, references, edit decisions and provenance; reimport and rerender verified. |
| R14 | Versioned /api/v1 OpenAPI with generated TS client and resumable events. Revision-aware writes reject conflicts. Distinct song/video/source/frame time. |
| R15 | Worker capability/heartbeat/lease/cancellation/artifact receipts. Persist submission intent and provider IDs; reconcile uncertain submissions without blind retry. |
| R16 | WebGPU preview with rendered proxy fallback; authoritative FFmpeg rendering. Browser and WebView2 verified separately. |
| R17 | Private authenticated deployment, scoped worker credentials, BWS secrets, backups and tested restoration/rollback. |
| R18 | First-run pilot selection; whole-song preview and finished 30–60 second passage before full-song acceptance. Real visual/audio evidence, not fixture-only success. |
| R19 | Approved Characters have separately approved Looks. Each hair/costume change is a distinct Character sheet/Look assigned to scenes or sequences before generation; preserve identity and within-sequence hair/costume continuity, favoring fewer changes when the story permits. Include reusable location and visual-style anchors. |
| R20 | One user-authorized Generate action, separate from and requiring a current R05 production approval, starts a durable unattended run: generate planned media, run the production self-check on each shot against prompt/reference/Look/timing/media health, apply the R09 replacement allowance, create the musical edit, then hand the candidate edit revision to independent Review. Continue independent shots after failures; surface unresolved gaps and block export. |
| R21 | Review findings produce issue-appropriate repair proposals: replace, trim, lengthen, reorder, re-render, re-prompt, or fill a gap. Repair scope adapts between a shot and a story/edit chunk; chunk review includes neighboring shots and context handles. The user approves a candidate chunk, which enters a new candidate edit revision, is rechecked locally and then in the full-cut Review, and becomes active only when the user chooses Keep (R10). |
| R22 | Reviewer comparison and repair turnaround/option counts remain evidence-led and configurable until model evaluations establish reliable capabilities. Review candidates must be compared on shared clips with recorded outputs; do not assume image-sequence review equals native video understanding. |

## Authority and boundaries

UI decision, 2026-09-25: dark mode is the default, with a dark zinc/neutral palette as explicitly requested by the user. Use the pinned Impeccable skill set for UI design and testing, including contrast, keyboard focus, responsive composition and clear production states. Use the Codex in-app Browser for browser verification. These checks support rather than replace Windows WebView2 acceptance. Keep the production self-check (automated per-shot quality control) distinct from Review (independent editorial/technical judgment after the musical edit).

The director proposes validated project actions. Rust enforces approvals, locks and allowances; agents and reviewer scores cannot override them. Story/style changes return to the user. Approve the supplied song directly in v1; Ableton preparation, generated singing and abstract modes are later milestones. No primary NLE, offline standalone production, public accounts/billing, or social publishing. Performance footage supplied by the user is supported in narrative videos; generated singing and word-level lip-sync scoring are later work.

Use appropriate user-owned donor patterns without modifying donor repositories: Storyception visual organization, Creative Studio Pro Svelte workspace, Beatsmaxxer musical timing, and selected Project Stack/TrailerCraft patterns. Reject their permissive weak-match and placeholder-success behavior.

## Product decisions, 2026-09-28

Recorded after the spec review of PR #12. Terms follow [CONTEXT.md](../CONTEXT.md).

1. **Repair attempts and R09.** The R09 cap bounds the unattended production self-check for each shot within one production run. Review-driven repair is a separate user-approved step, so it does not draw on that run's cap: approving a repair chunk grants each shot it regenerates a fresh allowance of one attempt plus at most two replacements, recorded in lineage with the originating finding. Trim, lengthen, reorder and gap-fill from existing media spend no generation attempts. Nothing repairs automatically outside an approval; an exhausted repair leaves the gap or blocking finding in place.
2. **Approved repair chunks and Keep.** Approving a repair chunk creates a new candidate edit revision whose parent is the active revision. It runs the local recheck and full-cut Review, and becomes active only when the user chooses Keep after seeing those findings. Chunk approval never replaces Keep.
3. **Generate versus production approval.** They are separate actions. R05 production approval binds the approved inputs by fingerprint; the R20 Generate action starts one run under the current approval, records that fingerprint, and is unavailable while approval is missing or stale. Changing an approved input during a run stops new submissions; finished media stays as candidates tied to the earlier approval and cannot be kept under the new one.
4. **Lip-sync.** "Later" means a later milestone, not a later pipeline step. v1 Review checks supplied performance footage for continuity and technical health only; word-level lip-sync scoring arrives with singing mode after M11.
5. **Gemini Flash comparison.** Any Gemini call, including M1/M7 reviewer comparison on shared clips, requires a separately approved quote that states expected cost and the material sent off-host. Local reviewer comparison proceeds without one. If no quote is approved, Review launches with local reviewers only and records Gemini as unevaluated.

## Release acceptance

1. Private pilot: homelab web + installed Windows client, one shared durable project, whole-song preview and real 30–60 second rendered passage.
2. Narrative production: complete song, no placeholders/blocking findings, verified MP4/editable archive and recovery. Production is unattended after the Generate action, the automatic musical edit precedes multi-reviewer Review, and any repaired chunk receives both local and whole-cut re-review before Keep.

The first gate does not establish the second. User selects the real song/references during first-run setup and approves creative direction/production.
