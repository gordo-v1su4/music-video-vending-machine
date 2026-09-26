# Song analysis — work in progress

The sole audio timing source is the user-supplied 137 BPM export package. Earlier
MP3 and analysis are superseded. The reference-only folder is not a timing
authority. The subsequently supplied lyric text is imported as wording only;
its old audio metadata and URLs are not used.

## Media and real service evidence

- Twelve stereo 48 kHz stems had identical 16,951,398-sample lengths. They were
  summed at sample zero with their relative gains preserved. A uniform -0.5 dB
  adjustment produced a 24-bit master with measured -1.1 dBTP. Sample comparison
  agreed with the fixed-gain sum within 1.2e-7.
- At the user's request, the last 0.154125 seconds were removed. The current WAV
  has 16,944,000 samples, exactly 353 seconds; all preceding samples match the
  untrimmed master. A 320 kbps MP3 reports 353.000000 seconds.
- The current MP3 completed `POST /analyze/studio/jobs` followed by polling its
  retained identity at `https://essentia.v1su4.dev`, the same public Studio
  contract used by Beatsmaxxer Pro. Result: duration 352.999977 seconds, 22 raw
  musical sections, 795 beats, 1,341 onsets, measured 136.831284 BPM. The user's
  locked 137 BPM is separate from the estimate. Model section end rounding is
  353.04 seconds; editable application bounds must end at the actual master.
- Live GPU inventory inside `essentia-api`: RTX 4070 Ti, 12,282 MiB. Successful
  structure provenance reports CUDA. This is not evidence of video generation.
- The untrimmed FLAC and MP3 failed strict onset validation. A read-only signal
  diagnostic found one onset at 353.164001 versus decoded duration 353.154104.
  The trimmed resubmission succeeded without changing the deployed service.
- Private media, source hashes, mix provenance, and provider receipts remain
  outside Git. No paid generation was requested.

## Application work and checks

Application changes add atomic upload/analysis enqueue, persisted
provider identity and source checksum, bounded polling, retained raw receipts,
validated measurements, and a Svelte analysis/audition/editor panel. A committed
submission intent with an unknown outcome is quarantined for reconciliation;
it is never automatically sent again. The adapter does not grant approvals.

- Rust parser tests: four passed, including wrong-master rejection and documented
  model-edge rounding without extending the master or admitting late onsets.
- Isolated PostgreSQL analysis lifecycle test passed: duplicate starts retain the
  same identity; concurrent workers submit once; reconstructed API state returns
  saved measurements; cross-project lookup fails; failed/uncertain submission and
  interrupted submission do not re-submit.
- Existing PostgreSQL persistence/session integration tests passed.
- Web tests: 41 passed; Svelte check and production build passed. Component
  autofixer reported no issues; polling lifecycle suggestions were reviewed.
- Impeccable mechanical detector returned no findings for the analysis component.

## Observed in-app browser behavior

- The user reloaded the temporary connection-error page; the blocker is resolved.
- Reused the same visible Codex in-app tab at 127.0.0.1:5198; no external Chrome.
- Imported the current 353s master, selected it, observed durable analysis complete,
  auditioned the first chorus, and saved 22 detected sections at project revision 3.
  Reload retained those sections. The master approval was performed by the user.
- Imported a 353s/192kbps MP3 derived only from the trimmed lead-vocal WAV.
  Observed filename-specific upload/validation and queued/rhythm/structure
  processing in the sidebar. The vocal's separate analysis ultimately failed;
  the master analysis completed. No fabricated upload percentage.
- Waveform is computed from the decoded imported audio. Playing-section status,
  a thin playhead, compact square buttons and rectangular seek handles were observed.
- User-directed styling: zinc base, saturated blue/indigo/purple at low opacity,
  one solid fill per duration block, no internal gradient or decorative outline.
- Deepgram legacy Nova-3 with sentiment enabled: 0 words from master, 1 from vocal.
  Empty transcript now displays No lyrics detected, not successful lyric extraction.
- Matched Project Stack Structure's current call policy: sentiment/entities disabled;
  Nova-3 first; Whisper if duration >=30s and last word <60% or no words; a single
  overlapping tail pass if duration >45s and last word is positive but <85%.
  Tail extraction also works for MP3 via a local FFmpeg WAV derivative.
- Live corrected vocal run: Nova-3 still returned 1 word; Whisper returned 139 words
  in 16 chunks reaching the end of the recording. No third pass was needed.
  Many words have low confidence and remain unapproved. Whisper provided no
  summary/topics/intents; missing metadata is shown honestly. No sentiment claim.
- Every pass receipt is retained privately. An interrupted call is quarantined,
  not automatically replayed. Each source/profile can be requested only once.
- PostgreSQL fake-provider tests cover a complete three-pass recovery with offset
  timestamps and duplicate filtering, plus duplicate starts, restart reads,
  uncertain dispatch and cross-project access. All passed after the test provider
  was corrected to consume request bodies.

## Remaining acceptance

A narrow browser viewport was checked (effective CSS width 525px due app scaling),
with no document overflow; it is not physical-device acceptance. Compact play
buttons measured 32px and solid timing blocks had 0px borders/no background image.
The narrow timeline now scrolls horizontally so section labels remain readable.
Keyboard focus is retained on interactive controls. Project reopening selects
the richest retained transcript without changing the production master. Optional
lyric timing correction and Windows acceptance remain. Revision 6 saves vocal
alignment and director proposals as described below. No finished video or Windows
WebView2 acceptance is claimed. Exact-head Greptile 5/5 and green CI are required
before merging this implementation.
# Lyric cards and director draft follow-up

- Added durable lyric wording/source and explicit zero-offset audio alignment. Asset ownership and matching measured duration are enforced server-side; a master change removes the alignment. Changed lyric context invalidates production approval; legacy projects without context retain their existing fingerprint.
- Exposed word timings, including recovery from retained receipts for already completed jobs without another provider call. Cards assign each word by onset to a half-open section range. Missing timings and uncertain wording remain explicit.
- Imported the newly supplied text through the same visible in-app tab. Only wording was extracted; older audio metadata/URLs were excluded. Source files were not edited.
- Saved a clearly labeled director interpretation and 22 editable section beats at revision 6, then reloaded. Browser inspection confirmed 22 draft beats, recovered words on 10 cards, a 758-character wording reference and no desktop page overflow. The interpretation is assistant-authored, not Deepgram output or user approval. The bridge remains unlocated.
- Deepgram's selected Whisper recovery receipt has no summary/topics/intents. UI now explains the missing summary rather than implying story context was produced.
- Mechanical checks: 20 ordinary Rust tests and all 5 database integration tests pass, including legacy receipt recovery without paid replay, lyric asset ownership, approval compatibility and alignment invalidation. Web check: zero errors/warnings; 43 tests pass; production build passes. Generated contract and Clippy pass. Svelte autofixer reports no issues; polling lifecycle suggestions were reviewed as intentional external async state updates.
- The lead vocal's separate Essentia job is shown as failed; the approved master retains its valid analysis. This does not prevent the completed vocal transcript from supplying draft timing.
- Automatic director generation, exact lyric correction/alignment, character/location choices, creative approval and rendered footage remain unfinished. No new provider or image/video generation request was made for this follow-up.
- Responsive follow-up: DOM measurements at an effective 525 CSS pixels reported no page overflow and single-column cards. Both narrow screenshot capture APIs returned blank images, so narrow visual acceptance is not claimed. Temporary viewport override was reset. Desktop cards, wording, draft text and focus were visually observed; this is not physical-device or WebView2 acceptance.

## Pre-PR review fixes

- Independent Standards review found unavailable-source queue starvation, a parent/child transcript-loading race, and receipt persistence after validation. Spec review independently confirmed the receipt defect. All three were addressed.
- Unavailable transcription objects now wait 30 seconds between reads while other eligible jobs proceed. A fake-provider integration test verifies the unavailable earlier job makes no paid request and does not block a later valid source.
- Successful JSON responses are saved before duration/word validation in every pass. An invalid-duration response remains privately inspectable, stays quarantined and is never automatically resubmitted.
- Project reopening clears old transcript state before mounting result readers, avoiding a late clear after a completed child fetch.
