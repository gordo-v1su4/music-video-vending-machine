# Existing Essentia analysis service

Read-only live inspection: 2026-09-25. The operator pointed the app at a self-hosted Essentia HTTP service (`ESSENTIA_API_BASE_URL` in `.env.local`). Direct HTTPS requests returned Swagger docs, OpenAPI, and a health payload reporting `status: ok`, version `4.1.0`. The web browsing tool could not fetch that host from the agent environment, but requests from the workstation succeeded. No audio uploaded, authenticated analysis attempted, or jobs submitted.

## Useful live contract

- `POST /analyze/studio/jobs`: multipart audio upload, required `Idempotency-Key`, HTTP 202 with job ID/status. Documented behavior isolates jobs by API key, rejects key reuse with different bytes (409), and expires terminal jobs after configured retention. Failed jobs do not automatically rerun.
- `GET /analyze/studio/jobs/{job_id}`: `queued`, `running`, `completed`, or `failed`, with a stage and optional result/error. Only completed jobs contain results.
- Studio results use strict `studio-audio-v1`: duration, BPM, beats, confidence, onsets, energy and structure. Energy includes an explicit `sample_rate_hz` and `start_time_s`, useful for aligning the energy curve with song time.
- Studio structure declares `allin1`, sections/boundaries, analyzed duration and provenance. The provenance schema requires `detected`, a method, and `cuda`; sections include start/end/duration, label/original label, and energy. These are contract requirements, not proof an analysis job currently succeeds.
- `/analyze/fast` returns rhythm, energy and structure without waking the heavier classifier/tonal/vocal models on the upload path.
- Separate endpoints cover rhythm, structure and All-in-1 structure, genre/mood classification, tonal key/tempo/pitch, vocal presence and full analysis.

All analysis endpoints declare API-key authentication. Keep credentials in the coordinator's private runtime configuration and use the existing secret workflow at implementation time; none were requested or inspected for this contract review.

## Proposed use

Analyze each approved master version and retain analysis under its immutable audio identity. Use queued studio analysis as the candidate production path, its documented idempotency for safe submissions, and the explicit energy timebase for reproducible edit schedules. Poll persisted job IDs after reconnecting. Save results in our project storage before the provider's job retention expires.

Cross-check MIDI/stem timestamps against the master, preserve uncertainty, and support explicit correction of musical boundaries. BPM confidence is not a guarantee of every beat/section label. Any approved audio rearrangement creates a new analysis version and invalidates timing-dependent edit work for affected regions.

The listed endpoints do not establish lyric transcription/alignment, stem separation, MIDI import, processed audio export, audio mastering, or true-peak/LUFS QC. Those responsibilities need separate tools/verified contracts. This service supplies musical evidence; it does not itself judge cinematic flow.

## Required validation

Use an approved sample to verify authentication, successful queued analysis, aligned duration/beats/energy/sections, persisted result retrieval, and restart recovery without a second submission. Compare returned structure with the actual song before relying on automated labels. No current claim of that end-to-end success.
