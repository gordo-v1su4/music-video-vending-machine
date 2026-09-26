# Song analysis review fixes — 2026-09-26

Scope: follow-up to PR #5; not private-pilot or full-song production acceptance.

## Changes

- Interrupted transcription can recover valid retained passes or an operator-verified completed provider response. Recovery checks session, source hash, expected job/version and terminal state under a row lock. It retains original receipts and never calls the provider. If no completed response exists, the job remains unresolved; a new paid attempt still requires a separate approved quote.
- Complementary fallback words in uncovered time ranges survive even below the richer-pass threshold. Preferred-pass wording owns overlapping ranges; original pass receipts remain available.
- Analysis and transcription OpenAPI operation IDs are distinct. Contract generation rejects duplicate or missing operation IDs before generating TypeScript.
- Processing polls active jobs every three seconds and settled projects every thirty seconds; empty projects do not keep polling.
- Waveform rendering waits for completed analysis, uses 8 kHz decoding and a 10-minute/32-MiB eligibility limit, and samples at most 153,600 values. Larger media retain the measured energy display. The display explicitly identifies the sampled waveform.

## Mechanical checks

- Rust workspace: 21 tests passed; clippy with warnings denied passed.
- Five database integration tests passed against a clean isolated mvm_test database, including real FFmpeg continuation preparation. The earlier rerun encountered queued fixtures retained by a failed test; the isolated test schema was reset, leaving mvm_dev untouched.
- Recovery tests cover saved/imported responses, explicit source confirmation, wrong hashes, stale recovery, unauthorized access, retained original receipts, and zero additional provider submissions.
- Web: 45 tests passed, including a fixed-work waveform test over a virtual 200-million-sample recording; Svelte check reported zero errors and warnings; production build passed.
- Generated API contract matches Rust and operation IDs are unique.
- Svelte autofixer: no issues; generic asynchronous-effect suggestions were inspected. Impeccable detector: no findings.

## Observed browser behavior

Codex in-app browser, isolated loopback web/API ports 5208/5209, real Rust coordinator, mvm_test and local synthetic 10-second audio. Provider services were disabled.

The interrupted fixture exposed Recover saved responses. Clicking it returned Transcript ready with two timed chunks and the explicit message that no new paid request was made. The recovery controls disappeared after completion. The existing real song/project and its approvals were not changed.

This was desktop browser functional verification. Narrow viewport, Windows WebView2, long-file browser performance and manual provider-file import were not browser-accepted by this pass; imported-response behavior is covered by API integration tests. No paid calls were made. Exact-head Greptile and CI remain required before merge.
