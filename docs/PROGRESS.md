# Music Vending Machine — build checklist

Updated September 28, 2026. This tracks the approved [product requirements](PRD.md) and [implementation plan](implementation-plan.md).

**Where we are:** the current 5:53 master is imported and analyzed. Revision 7 saves the supplied lyric wording, explicitly aligned vocal timing, a director-proposed interpretation and 22 editable story beats. Recovered words appear on 10 of the 22 cards; other cards identify missing timing without claiming silence. These are creative drafts awaiting review. Automatic in-app direction, finished video and the installed desktop release remain unfinished.

**Current task: scheduled backups, then private deployment.** PR #7 migrated PostgreSQL to home Convex/RustFS and PR #8 added explicit same-bucket recovery; both merged after exact-head Greptile 5/5, green CI and resolved findings. Local cutover, source preservation, fresh current-backup restore/restart and browser playback passed. Scheduled runner implementation is under review; task execution is not yet verified.

**Song context.** The user confirmed the 5:53 stem package at a locked 137 BPM as the only source for this song. A 5:53.154 stereo 48 kHz / 24-bit master has been built from all 12 aligned stems, preserving relative levels with a uniform -0.5 dB adjustment (measured -1.1 dBTP). The earlier MP3, separate lyrics file, and earlier analysis are superseded and must not be used. Files in the package's reference-only folder may drift and are not timing authorities. The current trimmed master is connected to durable analysis, visible progress and a saved editable timeline.

**Next visible work:** review the proposed arc and timed cards → choose character, setting and visual references → refine scene actions → preview those parts against the music.

**Lyric reference update:** the user subsequently supplied a new text export as wording context. That explicit instruction supersedes the earlier exclusion for this text only. Its old audio metadata and URLs remain excluded from timing. The current 353-second aligned vocal remains the timing source; unlocated reference lines have no invented timestamp.

**Latest song decision:** the user requested a clean integer ending. The current master and MP3 working copy are exactly **353.000 seconds (5:53)**, with the last 0.154125 seconds removed and all preceding WAV samples verified unchanged. The MP3 completed the public Essentia Studio job on the current RTX 4070 Ti: 22 musical sections, 795 beats, 1,341 onsets, measured tempo 136.831 BPM. The user's locked 137 BPM remains a separate source-of-truth tempo. Earlier untrimmed FLAC/MP3 jobs failed because a padded-frame onset was about 10 ms beyond the decoded song; the successful trimmed job did not require a service deployment. The same current MP3 was then imported and analyzed inside the app. The user approved the master; 22 editable sections were saved at revision 3 and survived reload. The separate service receipt remains diagnostic evidence.

Checked means the stated scope has evidence. A service experiment does not mean the feature works inside the app. Unchecked means unfinished, including partially implemented work. No overall completion percentage is claimed.

## 1. Foundation and saving — mostly working (M0, M2)

- [x] Approve and preserve the product plan, requirements, and backlog.
- [x] Create the Svelte/TypeScript workspace and Rust coordinator.
- [x] Save projects, source assets, story edits, and revisions in self-hosted Convex/RustFS; local migration verified (PR review pending).
- [x] Reject conflicting project writes instead of silently overwriting them.
- [x] Verify private RustFS upload/download, coordinator restart, and completed-asset backup restoration.
- [x] Implement session sign-in/sign-out and retain drafts across disconnection; run local browser checks.
- [x] Merge session work: PR #4 merged at `c924765` after Greptile 5/5 on `d00c371`, green CI, and all findings resolved.
- [x] Verify cold isolated backup restoration with verified, incomplete and missing pending uploads; coordinator completes only verified media. [Evidence](evidence/2026-09-26-pending-upload-recovery.md).
- [x] Remove SQL runtime dependencies and exercise six disposable Convex acceptance tests.
- [x] Verify the Convex-only local runtime preserves the revision-7 song, lyrics, analysis and audio playback.
- [x] Merge Convex migration PR #7 after exact-head Greptile 5/5, green CI and resolved findings.
- [x] Merge PR #8 same-bucket recovery; verify current-backup import and restart in a fresh disposable instance.
- [ ] Install and verify the scheduled independent backup runner.
- [ ] Verify one shared project from both web and an installed Windows client.

## 2. Select a song and break it into editable parts — next priority (M1, M4)

- [x] Import supported audio and select a master in the current app.
- [x] Prove the existing Essentia service can analyze a synthetic track in a separate service test.
- [x] Build and technically verify a master from the supplied 137 BPM stems: identical sample counts, no time shift or stretch, no clipping, and sample-by-sample agreement with the fixed-gain sum.
- [x] Analyze the current 5:53 MP3 through the same public Essentia Studio endpoints as Beatsmaxxer; retain the user's locked 137 BPM independently from measured tempo.
- [x] Connect the selected master to a durable analysis job in the app.
- [ ] Show real analysis progress, failure, and recovery states.
- [x] Display measured tempo, beats, energy, and proposed musical sections on the song timeline.
- [x] Let the user audition sections and correct names and boundaries.
- [x] Preserve analysis against the exact master identity; invalidate stale results after a master change.
- [ ] Verify optional stems/MIDI timing and lyrics intake before using them.
- [ ] Watch the complete select → analyze → sections flow in the same visible in-app Browser tab.

## 3. Turn the song parts into a story — not connected yet (M4, M5)

- [x] Provide manual treatment and timed story-section editing.
- [x] Save wording separately from timing, require explicit stem alignment and display recovered words on matching cards.
- [x] Use the supplied video-director skill to draft a short interpretation and 22 section intentions through the visible UI; save and reload revision 6.
- [ ] Review the draft interpretation, visual direction and uncertain lyric timing with the user.
- [x] Provide reference intake and exact-versus-inspiration roles.
- [x] Provide timed audio preview and insertion/cutout timing primitives.
- [ ] Integrate the director to propose story parts grounded in the song and treatment.
- [ ] Keep stable Character, location and visual-style anchors and reference constraints.
- [ ] Approve each Character's Looks: every hair/costume combination gets its own Character sheet.
- [ ] Assign an approved Look to every scene or sequence before generation, favoring fewer changes.
- [ ] Show the whole song as timed story parts with stills or clearly marked placeholders.
- [ ] Let the user revise and approve master, treatment, references, Looks and their assignments, breaks, route, and attempt allowance; any change invalidates that approval.
- [ ] Verify the complete-song preview against the production master before starting video production.

## 4. Generate and assemble video — service experiments only (M1, M3, M6)

- [x] Generate and inspect exploratory stills and clips through standalone ComfyUI outside the app. These probes do not count as production workflows.
- [ ] Validate candidate image and video workflows submitted through SwarmUI, with pinned model/workflow hashes and measured resources.
- [ ] Validate image-edit preservation and Look identity; the exploratory edit did not preserve the scene adequately.
- [ ] Connect dedicated Trigger jobs and the Windows GPU worker.
- [ ] Implement leases, cancellation, recovery, provider receipts, and duplicate-submission protection.
- [ ] Add a Generate action, separate from production approval, that starts one unattended run.
- [ ] Generate from approved story parts with an initial attempt plus at most two replacements per shot.
- [ ] Run the production self-check on each shot: prompt/reference fit, assigned Look, timing, and media health.
- [ ] Apply musical cut controls, protected sections, seeds, and pinned shots, then assemble the musical edit automatically.
- [ ] Rank acceptable candidates and keep unresolved coverage visibly empty.
- [ ] Integrate candidate comparison, Keep/Reject, and restoration without replacing the active cut automatically.

## 5. Review the moving result — unfinished (M7)

- [ ] Compare candidate reviewer models on the same shared clips; Gemini Flash only under a separately approved quote.
- [ ] Run multi-reviewer Review on the whole musical edit: story coherence, musical fit, continuity, Characters and Looks, cuts and timing, and technical errors.
- [ ] Record findings with revision or artifact, time range, evidence, uncertainty, reviewer, and proposed action; mark reviewer disagreement.
- [ ] Separate blocking findings (objective failures) from advisory story and style judgments.
- [ ] Propose repairs scoped to a shot or a chunk with neighboring context; each approved repair gets a fresh attempt allowance.
- [ ] Put an approved repair chunk in a new candidate revision, recheck it locally, re-review the full cut, then offer Keep.
- [ ] Verify intentional creative choices, supplied performance footage (no lip-sync scoring in v1), and exhausted-repair behavior.

## 6. Export and editable archive — unfinished (M8)

- [ ] Render verified 1280×720, 24 fps H.264/AAC MP4 through FFmpeg.
- [ ] Block exports with gaps or blocking findings in the requested range.
- [ ] Verify preview/export timing agrees within one frame.
- [ ] Export an editable archive with media, references, decisions, and provenance.
- [ ] Reimport the archive and rerender successfully.

## 7. Install and deploy privately — unfinished (M1, M9)

- [ ] Build and install the Windows Tauri client using the shared Svelte UI.
- [ ] Verify WebView2 separately from browser tests, including WebGPU loss/proxy fallback.
- [ ] Deploy the authenticated homelab app with scoped worker credentials.
- [ ] Verify scheduled backups, off-host retention, restart, restoration, and rollback.
- [ ] Complete separate Jcode and Ableton evaluations; do not imply untested integrations work.

## 8. Real-song acceptance — not started (M10, M11)

- [x] User supplies and confirms the 5:53 / 137 BPM stem package as the sole song source; disregard earlier song files and results.
- [ ] User chooses visual references and approves the derived production master in the app.
- [ ] User approves the story and production inputs in the app.
- [ ] Watch/listen to the whole-song preview.
- [ ] Finish and review a real 30–60 second passage as the private pilot.
- [ ] Finish the entire song with no placeholders or blocking findings.
- [ ] Verify the full-song MP4, editable archive, and recovery.

## What the recent work accomplished

Recent work focused on durable saving, private storage, authentication, draft retention, and review fixes. Visible local tests created a project, saved its treatment, reloaded it, and preserved a draft through sign-out/reconnect. Those checks do **not** prove audio segmentation, story generation, or finished video production.

The dark zinc workspace is implemented. Browser testing must stay in the user's visible in-app tab. Local services use web 5198 and API 5199, with Convex on home app-vm and media in RustFS `mvvm`. PostgreSQL 54329 is retained rollback material only; it is no longer the application database. The local API remains development-only and omits provider credentials during migration review.

## Rules that stay in force

- Every implementation PR needs exact-head Greptile 5/5, green CI, and addressed findings before merge and the next implementation PR.
- Creative approval belongs to the user. Paid calls require a separately approved quote.
- Update this checklist at each completed work item or changed blocker, and keep the current and next task at the top accurate.
- Full completion means both the private pilot and the complete-song acceptance pass. A fixture, passing unit tests, or a working service alone is not completion.

## Current UI direction (user corrections, September 26)

- Zinc/neutral dark base; no slate. Accent color is allowed.
- Rectangular seek handles and compact square/rectangular play buttons.
- Every timing block has one solid translucent fill, with no decorative border/outline and no gradient inside a block.
- Saturated blue/indigo/purple hues are softened with opacity, not pastel replacement colors. Shade represents duration; the timeline includes a legend.
- Measured waveform and playing-section feedback are visible. Browser waveform is decoded from the exact imported audio, not a fabricated graphic.
- Derived stems end at exactly 353.000s. MIDI working copies use 137 BPM and end within 0.165 ms of that boundary; note/audio alignment still needs audition.
