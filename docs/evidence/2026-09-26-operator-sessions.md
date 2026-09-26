# Operator sessions and neutral dark workspace

Status: locally verified; GitHub review/merge gate pending. This is M2 progress, not private-pilot or complete-song acceptance.

## Mechanical verification

- Rust workspace: 13 ordinary tests passed. Both isolated PostgreSQL integration tests passed against `mvm_test`, including migrations, hash persistence, 12-hour expiry, restart, bootstrap rejection on project routes, bad token/origin rejection, individual/all revocation, issuer rotation, and closure of an already-open SSE stream.
- A streaming JSON request expires after header authentication and before body completion; project creation returns 401.
- `cargo fmt --all -- --check`, locked Clippy with warnings denied, generated OpenAPI TypeScript `--check`, and `git diff --check` pass.
- Bun: 40 tests / 124 assertions pass. Coverage includes bootstrap isolation, no redirects/cache, aborted late responses, expired client writes, and retryable failed sign-out.
- Svelte check: zero errors/warnings. Svelte autofixer: no issues/suggestions. Impeccable detector: no findings on the changed page/CSS. Production web build passes.
- Python: 16 tests, 15 pass and one POSIX-only mode check skipped on Windows. Parallel probe callers share one session exchange; failed exchange is not cached.
- CI now runs all ignored coordinator integration tests explicitly, not only the earlier persistence file.

## Observed browser behavior

Verification moved to the Codex in-app Browser at the user's request; the temporary external Playwright browser was closed. Production preview on 5198 serves this worktree, API 5199 preserves the original development database/media directory. An isolated local fixture API on 5201 uses `mvm_sessions_ui`, local media, and a synthetic test-only key; it is not private RustFS deployment proof.

- Sign-in opens the existing fixture project; the access-key field clears.
- Sign-out keeps the unsaved treatment and old revision, disables Save and Import, and offers reconnection. Reconnection preserves the draft and restores saving.
- Expiring the fixture session in PostgreSQL causes the production-build browser to show the session-ended error, disable Save/Import, and retain the draft.
- User requested dark zinc/neutral surfaces. The visible workspace now uses near-black/neutral zinc surfaces and neutral action/focus colors. Semantic error/success colors remain distinct. Thirty-six sampled text elements had contrast >=6.91:1; this is a scoped measurement, not an accessibility certification.
- Narrow viewport inspection showed wrapped draft text and no horizontal overflow. A requested 390x844 in-app override reported actual `innerWidth=487`, `scrollWidth=468`; this is browser sizing evidence, not physical-device acceptance. Override was reset.
- Keyboard Tab moved from the treatment to the audio-break disclosure. Disabled and focused controls remain distinguishable. The initial external browser logged only a missing favicon 404; it is not a session failure.

## Limits

No Windows installer/WebView2 acceptance, production deployment, production backup scheduling, complete media-generation path, pilot passage, full song, export, or archive acceptance is established here. Creative approvals remain required. No paid calls were made. Existing storage recovery evidence predates sessions; the private RustFS session probe must be rerun before M2 is accepted in full.
