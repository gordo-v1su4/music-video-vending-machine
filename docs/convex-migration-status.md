# MVVM Convex migration

User-approved target: a dedicated self-hosted Convex instance on home `app-vm`,
named `mvvm`, with RustFS for object storage and Trigger for orchestration.
This supersedes PostgreSQL as the application database. The primary local coordinator now runs the Convex-only binary against the `mvvm` instance and RustFS bucket. No creative approval or paid-call authorization changes.

## Current status

- Local cutover verified: original project records and media retained; revision-7 song unchanged across the Convex-only binary restart. Browser lyrics, analysis and playback passed.
- SQL runtime and dependency removed. PR #7 merged as `24b96cc` after exact-head Greptile 5/5 on `de64fe3`, green CI and resolved findings. Seven disposable HTTP acceptance tests and 30 ordinary Rust tests passed. The reviewed Convex functions/index and coordinator are running locally; saved revision-7 project comparison and browser reload passed.
- Local backup and separate-instance restore checks passed. Explicit same-bucket object recovery passes automated tests and live verification of existing objects. Current-backup database readback passed in a fresh disposable instance, including restart and repeat-import refusal. Scheduled/off-host retention remains incomplete; see [recovery evidence](evidence/2026-09-26-convex-same-bucket-recovery.md) for verification limits.
- Durable private deployment, installed Windows client and the remaining PRD milestones are not complete. Implementation PRs require green CI and resolved findings.

## Chronological evidence

The entries below record intermediate migration states; earlier statements about unfinished adapters or PostgreSQL runtime are superseded by the later SQL-removal and live-binary entries.

## Verified September 26, 2026

- Dedicated `mvvm-convex` backend healthy; authenticated schema deployment passes.
- TypeScript checks pass for the schema and administrator-only migration functions.
- Consistent source snapshot contains 3 projects, 22 project events, 3 assets,
  2 audio-analysis jobs, 3 transcription jobs, and no upload intents or sessions.
- First import was rejected because a saved analysis contains a 30,406-element
  array, above Convex's 8,192-element limit.
- Encoding domain JSON as strings avoids that array limit but does not solve the
  document size limit: one encoded analysis record is 1,238,938 bytes.
- Both import attempts were rejected atomically. Subsequent destination reads
  confirmed it remained empty. Source records were never modified and no jobs
  were submitted.

## Remaining work

Staging import subsequently passed with large result/receipt payloads stored in
RustFS as content-addressed JSON. All 33 logical records match after materializing
and checking payload byte lengths and SHA-256 hashes. Snapshot SHA-256:
`ee55ed67c45bc30bc84f3b31921de38cb540c40d4be3ab93eebd0d0c565910f2`.
The source remained unchanged during comparison; repeat import and anonymous
snapshot reads were refused. This is staging evidence, not application cutover.

Initial internal project/session functions are implemented. Three isolated Convex
tests pass: concurrent revision commits produce one winner and one event; session
revocation rejects subsequent writes and event reads; missing asset ownership
checks leave the project and history unchanged. Four RustFS payload tests also
pass (roundtrip/retry, corruption, ownership/bucket restriction and missing object).
Coordinator wiring, complete session lifecycle, asset operations and worker claims
are still unfinished; these tests do not establish full persistence acceptance.

The Rust Convex transport now passes a live read-only test against the private
deployment: all three staged project documents deserialize into the existing Rust
domain model, and structured authorization errors map correctly. Two unit tests
cover error-envelope sanitization and invalid endpoint rejection. Requests have
timeouts, redirects disabled, an 8 MiB response cap and no automatic mutation
retries. This transport is not yet connected to the running API handlers.

Typed Rust session and project adapters are now implemented. Live session
acceptance passed: create, identify, issuer separation, bootstrap rejection,
current-session retrieval, 12-hour lifetime and issuer-scoped revoke-all. It
created two disposable sessions under an independent synthetic issuer and left
both revoked; those two additional staging records are expected and are not part
of the original migration snapshot. API route wiring remains pending.

Session HTTP routes and project list/get/create now select Convex when supplied
through AppState. The production entry point still selects PostgreSQL while
remaining handlers migrate. A live HTTP-router test uses an intentionally
unreachable PostgreSQL pool and passes sign-in, session lookup, project list/get,
router recreation and revocation. Each run leaves one additional revoked test
session under a synthetic issuer. Project creation is wired but not yet covered
by that live test. The transitional SQL authorization helper rejects Convex-mode
writes; remove the helper and PostgreSQL path after complete migration.

Project edits and event-stream persistence now have a Convex path. Existing asset
media/duration validation was extracted into a shared check, preserving the SQL
behavior while the migration remains incomplete. The live HTTP test, with SQL
unreachable, now also creates a clearly named acceptance project and exercises
two competing edits (one 200, one 409) and a missing-master-asset rejection (404).
The test project remains in staging at revision 1; the user's song was untouched.
Event streaming is implemented but not yet live-stream verified.

Live streaming now passes, including resuming after revision 0 and emitting
`session-ended` after revocation. This caught and fixed Convex's floating-point
revision encoding at the Rust boundary; only nonnegative safe integers are accepted.
Failed diagnostic runs retained synthetic test sessions until their 12-hour expiry;
no real operator issuer was used. Test projects remain clearly named acceptance
fixtures in staging. Upload begin/promote/pending functions are deployed and tested
for atomicity, idempotence, conflicting replay and ownership, but not yet connected
to the Rust upload handler or recovery loop.

Rust upload/list/download/recovery integration now compiles. Live Convex with an
unreachable SQL pool passed interrupted-upload recovery: missing bytes retained
the intent, exact bytes promoted it once, a repeat scan did nothing, and an
authenticated HTTP download returned the exact payload. This test used an in-memory
object store, not RustFS, so it establishes metadata/recovery behavior only. Its
clearly named acceptance project/asset remain staging fixtures; the in-memory
bytes disappear at test end. Remove test fixtures before final migration comparison
and cutover. Multipart intake and real RustFS recovery remain to be verified.

The same HTTP acceptance test subsequently passed with `MVM_TEST_RUSTFS=1`
against the real scoped RustFS bucket: multipart WAV intake, ffprobe duration,
SHA-256, interrupted upload recovery, download, concurrent edits and SSE revocation.
No analysis/transcription provider was enabled in the acceptance test. The source
song is unchanged. Worker lease/fencing implementation is now in progress.

Analysis worker Convex integration now compiles, including claim/save/release,
submission intent before HTTP, uncertain-submission reconciliation, provider identity
checks and RustFS JSON references for large receipts/results. It has not been run
against a provider yet. Analysis API get/start and transcription migration remain
unfinished. Worker functions were tested locally; deploy them before live acceptance.

Worker functions and analysis API endpoints are now deployed. Live HTTP acceptance
with real Convex/RustFS and a loopback fake provider passed: explicit enqueue,
one submission, HTTP 500 treated as uncertain, retained reconciliation-required
state, and a second tick with zero additional submissions. The test refuses to
run the worker if unrelated queued/running/submitting analysis records exist.
No real provider was contacted. Successful provider completion/polling and
transcription worker migration still need acceptance.

Successful analysis acceptance now passes with the fake provider returning queued,
then completed on polling. A 200 kB receipt exercises RustFS externalization;
the API returns the parsed analysis. Invalid fixture provenance/timebases were
rejected during test development. Transcription get/enqueue/recovery mutations
are now drafted; Rust wiring and worker lease integration remain unfinished.

Transcription read/start/recovery HTTP routes now have a Convex path. Recovery
uses the same extracted Rust response-merging logic as PostgreSQL and an atomic
Convex revision/state check. Tests reject stale recovery, repeated completion and
attempts to use recovery to queue paid work. Six Convex tests and fourteen Rust
unit tests pass. Transcription worker pass persistence and live endpoint acceptance
remain outstanding; no paid transcription call was made.

Transcription worker claim/save/release and Rust pass persistence now compile.
Each saved pass renews a ten-minute lease (provider request timeout is five
minutes). Expired workers cannot save; interrupted running jobs retain receipts
and become reconciliation-required rather than queued. Fake-provider HTTP
acceptance is still pending. No real transcription provider was contacted.

Live fake-provider transcription HTTP acceptance now passes with real Convex and
RustFS: failed response is not replayed, operator response recovery completes with
zero further submissions, repeated recovery conflicts, and another asset completes
normally with timed words. Startup can now select Convex via its private URL/admin
environment variables, without opening a PostgreSQL connection; health and session
maintenance have Convex paths. The legacy SQL adapter remains temporarily for
comparison/tests and is not yet removed. Real app cutover has not occurred.

Original media staging passed: all 3 source assets (25,242,410 bytes) were verified
locally, copied with create-only writes, and read back from RustFS with matching
length/SHA-256. One legacy bucket-prefixed object key was normalized to
`projects/<project-id>/originals/<asset-id>` in Convex after verification. Original
files and PostgreSQL metadata were not modified. The final snapshot comparison
must account for that intentional key relocation and remove test fixtures first.
The current bucket remains `music-vending-machine`; canonical `mvvm` bucket/name
cleanup is outstanding alongside the legacy SQL adapter removal.

- Integrate the verified payload reference format into coordinator persistence.
- Replace coordinator SQL persistence, preserving revision conflicts, session
  revocation, upload reconciliation and at-most-once paid submission boundaries.
- Implement and test Convex/RustFS backup and restore together.
- Apply Music Video Vending Machine / MVVM naming to application surfaces and docs.
- Verify the actual app in the in-app browser, then exact-head Greptile 5/5,
  green CI and resolved findings before merging the implementation PR.

Infrastructure runbook: `proxmox-home/docs/mvvm-convex.md`. Existing RustFS bucket
and PostgreSQL identities remain source locations until their migration is verified.
`scripts/stage-convex-migration.mjs` is diagnostic staging tooling, not a cutover
command. It compares full materialized records, including the large analysis result.

## Live browser acceptance — 2026-09-26

- Isolated coordinator on 127.0.0.1:5202 and web preview on 127.0.0.1:5203.
  Original ports 5199/5198 remain running. Runtime process receipt is ignored
  `.runtime/convex-browser-processes.json`.
- `/api/v1/health` reports database `convex`, storage `rustfs`, status `ok`;
  no analysis/transcription provider credentials were passed to this process.
- In-app browser opened I Ran at revision 7: saved treatment, 22 sections,
  139 words / 16 timed lyric chunks, 795 beats, and approved 5:53 master.
- Preview playback advanced to 3.657 seconds and paused; no project edit or
  paid provider submission occurred. Reload/reconnect reopened revision 7.
- UI naming edits now use Music Video Vending Machine and lowercase mvvm mark.
  Svelte autofixer reported no issues; svelte-check had 0 errors / 0 warnings;
  production build passed; Impeccable detector returned no findings.
- The running preview still serves its old branding after rebuild. A preview
  restart command was rejected by automatic approval policy with no specific
  reason. New branding is built but not yet visually accepted. The browser tab
  remains connected to the isolated Convex coordinator with the song open.
- Acceptance fixture projects remain in the staging database. Storage still
  uses the old bucket pending verified mvvm migration. No implementation PR
  has been created or merged; full pilot/export/archive acceptance is pending.

## Canonical bucket preparation — 2026-09-26

- Created private RustFS `mvvm` bucket; full/ranged readback and anonymous 403
  checks passed. Evidence: `docs/evidence/2026-09-26-mvvm-bucket.json`.
- BWS MVVM_S3_ACCESS_KEY / MVVM_S3_SECRET_KEY created and silently verified.
  Policy mvvm-coordinator-v1 grants only projects-prefix GET/PUT and listing.
  Scope denial checks passed; evidence: 2026-09-26-mvvm-scoped-storage.json.
  Canonical infra policy/runbook committed and pushed as proxmox-home 7175d23;
  vault secret inventory updated. Old credentials and source bucket preserved.
- All three original media assets (25,242,410 bytes) copied with create-only
  writes to mvvm and read back with matching SHA-256 and lengths. This copy
  mode does not mutate PostgreSQL, Convex metadata, source files, or old objects.
- Coordinator payload references now use AppState.object_bucket, populated
  from the same MVM_S3_BUCKET configuration as its object store. Existing
  running processes retain their old build/config until explicit cutover.
- JS payload tooling requires an explicit bucket and rejects oversized values
  before writing. Six JS tests and fourteen Rust library tests passed; all
  coordinator integration test binaries compile. Live scope checks above used
  actual new credentials; no real generation/transcription call was made.
- Outstanding before cutover: copy and verify large JSON payload objects,
  atomically update bucket references, archive/remove diagnostic fixtures,
  compare complete source records, and perform Convex/RustFS restore acceptance.
  The browser preview still uses the old bucket; this is preparation, not a
  claim of completed cutover or private-pilot acceptance.

## Payload copy and complete original-data comparison — 2026-09-26

- Copied all 7 large payload references (2,240,197 bytes) from the old bucket
  to mvvm using create-only writes; destination readback validated project key,
  declared length and SHA-256. No live metadata was changed.
- Private before/planned snapshots and receipt are under
  `.runtime/backups/mvvm-bucket-41274502-c9e9-4c14-9da9-d83cf928e6e6/`.
  They are migration snapshots, not proof of a complete recoverable backup.
- `scripts/verify-convex-source.mjs` compared all fields of every PostgreSQL
  source record against materialized Convex records: projects 3, events 22,
  assets 3, analysis jobs 2, transcription jobs 3; no source sessions/intents.
  Exactly one documented legacy asset key relocation was allowed. Both source
  and destination remained unchanged during the check. Original source hash:
  90251cf90111fedf9a77968e56e31e3332343ce1b82ca0cc9c2305ae571dffa5.
- Staging extras are reported separately, not treated as migrated user data:
  13 projects, 23 events, 20 assets, 17 sessions, 11 analysis jobs, 2 transcripts.
- Added administrator-only atomic payload-bucket switch. It rejects any stale
  expected job row, active worker lease, active job, invalid bucket/project key,
  invalid digest shape or out-of-bounds length. Tests cover preserved fields,
  stale retry, concurrent recovery, transaction rollback and active-work guards.
  Convex typecheck and all 11 migration/persistence tests passed.
- The switch function is drafted locally, not deployed or invoked. All live
  references still point to the original bucket. Fixture cleanup, verified
  backup/restore, maintenance-window cutover, new-build browser verification,
  legacy PostgreSQL adapter removal and implementation PR gates remain open.

## Diagnostic fixture cleanup — 2026-09-26

- Added and deployed administrator-only cleanup guarded by a complete expected
  snapshot, explicit fixture IDs, protected original project IDs, fixture document
  identity/revision, exact synthetic media hashes/lengths, loopback provider
  origins and no active jobs or worker leases. Typecheck and 13 Convex tests pass.
- Archived the complete pre-cleanup snapshot with byte-for-byte local readback
  under `.runtime/backups/fixture-archive-d3524ed8-5f0d-41a3-bb03-f93dfd406bc7/`.
  Archive SHA-256: 70891af7ed35b0fef9ac4d4c9941182e641329f0caa6c93108237a34b1b5f38e.
- Removed only 13 identified fixture projects, 23 fixture events, 20 fixture
  asset records, 11 fixture analysis jobs and 2 fixture transcription jobs.
  No stored objects or operator sessions were deleted. The 17 diagnostic
  sessions remain subject to normal expiry/revocation retention.
- Post-cleanup records exactly matched the expected retained snapshot. Re-ran
  full original-data comparison successfully: all three original projects and
  all their events/assets/jobs match, with no extra project-owned records.
- Bucket switch remains uninvoked. Its copied-payload plan predates cleanup;
  export a fresh expected job snapshot for cutover (stale plan must be rejected).
  Full backup/restore acceptance, service cutover, browser naming verification,
  legacy SQL removal and PR gates still remain.

## Backup and object restore preparation — 2026-09-26

- Added `scripts/convex-backup.mjs` with complete referenced-object inventory,
  snapshot/manifest checksums, archived-byte readback, required-object integrity
  enforcement, and explicit missing/incomplete pending-upload states.
- Live backup succeeded after one transient BWS outage; fresh live BWS lookup
  recovered without cache fallback. No service restart or source mutation.
- Accepted archive:
  `.runtime/backups/convex-03fb45b4-7d52-4f48-b305-54f5c1577281/`.
  Manifest SHA-256: 393d321f6d330952f6603f0c827679ff6dde5f7db798eb742b4defa8dd61f968.
  Five referenced objects, 26,480,029 bytes. Source snapshot unchanged during
  backup. This is a local data archive, not scheduled/off-host backup acceptance.
- Ran archive-based object restore to mvvm with create-only writes and full
  destination checksum verification. Existing matching objects are accepted;
  conflicting objects are never overwritten. Source objects remain untouched.
- Prepared `restored-snapshot.json` in that archive, hash
  b5c1479a87915d9a150b92ff2502d61dea5c61b27a77d4d034de0a1d06786b83.
  Prepared restoration revokes all previously live sessions and changes queued,
  submitting or running jobs to reconciliation_required while retaining receipts.
  An old queued record cannot prove the provider was not called after the backup.
- Six backup/restore tests pass: corruption, manifest/snapshot tampering,
  missing pending versus required media, ownership, session revocation/paid-job
  quarantine, and conflicting destination bytes.
- No Convex database import or live bucket-reference switch has occurred.
  Next: isolated Convex import and coordinator readback/recovery acceptance;
  then service cutover, browser checks, legacy SQL removal and PR gates.

## Isolated Convex restore and private API acceptance — 2026-09-26

- Provisioned separate restore-check backend on app-vm ports 13212/13213 and
  mvvm-convex-restore-check-data. Primary 13210 and its volume unchanged.
  Reused existing MVVM instance identity; no new permanent secrets.
- Deployed current schema/functions and imported the checksum-pinned prepared
  archive into the empty restore instance. Complete row comparison passed;
  repeat import was refused. Restored records: 3 projects, 22 events, 3 assets,
  2 analysis jobs, 3 transcription jobs, 17 revoked sessions, no upload intents.
- Started private (not development) coordinator at 127.0.0.1:5204 using mvvm
  RustFS and restored Convex. Process receipt `.runtime/restore-api-process.json`.
  No provider credentials; no paid calls. Original API 5199 remains unchanged.
- Probe verified anonymous and bootstrap-token rejection on data routes,
  session creation/current/revocation, all project documents, and all media SHA-256
  checks (25,242,410 bytes). Legacy omitted optional lyrics field is normalized
  to the Rust domain's null default for comparison; every other field is exact.
- Every analysis/transcription API response exactly matched the original
  PostgreSQL coordinator response, including recovered words and full results.
- Restarted only mvvm-convex-restore-check-backend-1 and repeated all private API
  checks successfully. Primary and restore backends both healthy afterward.
- Infra compose/runbook and vault pointers updated. Restore instance/coordinator
  retained for inspection. Local CLI defaults reset to primary 13210/13211 after
  the isolated deployment to avoid accidentally targeting the test instance.
- Isolated data/API restoration is verified. Scheduled/off-host retention,
  primary bucket-reference switch and app cutover, visible branding verification,
  legacy SQL removal, and implementation PR review gates are still open.

## Local studio cutover — 2026-09-26

- After fresh full source comparison, atomically moved the 2 remaining original
  large payload references to mvvm. All other metadata stayed unchanged.
  Checkpoint: `.runtime/backups/bucket-cutover-c137392a-d44c-44c9-89a4-248dc5c3f981/`.
- Process path + listener ownership guards safely stopped only the identified
  old coordinator/preview and temporary 5202 API. This resolved the earlier
  unguarded preview restart rejection; no broad process termination was used.
- Usual studio URL 127.0.0.1:5198 now uses Convex-backed API 127.0.0.1:5199,
  primary Convex 13210, RustFS mvvm, and scoped MVVM storage credentials.
  Process receipt `.runtime/mvvm-primary-processes.json`. Health reports convex,
  rustfs, ok. Existing local-development loopback mode retained; not a claim of
  a deployed private-web production service. Real provider credentials omitted.
- Full source comparison passed after bucket switch; all original data matched.
  Convex is now authoritative for new local edits. PostgreSQL/old bucket are
  rollback snapshots, not a source to overwrite later Convex edits from.
- In-app browser verified revision 7, saved treatment, 139 words/16 chunks,
  22 sections/795 beats, approved 5:53 master, and playback advancing to 0:06.
  User content was not edited; Save story remained disabled.
- Live title, library label and lowercase mvvm mark verified visually. Reduced
  badge type size to fit four letters; rebuild and mechanical detector passed.
  Main song tab left open; superseded temporary preview tab closed.
- Fresh mvvm backup verified after cutover: five objects, 26,480,029 bytes,
  `.runtime/backups/convex-369cc3c2-f9b9-41ea-a4dd-ac342f866c29/`, manifest hash
  d00108e6cc0025f20b1301254419fbea1e1b1b7f27cf5047fcd5b96de38d6417.
- Remaining: remove legacy SQL runtime adapter, schedule/retain off-host backups,
  complete deployment/client/product milestones and exact-head implementation
  PR Greptile 5/5 / CI / resolved findings. No implementation PR merged yet.

## Fail-closed runtime startup — 2026-09-26

- Removed PostgreSQL connection/migration fallback from coordinator startup.
  Missing CONVEX_SELF_HOSTED_URL now exits with a clear configuration error,
  regardless of DATABASE_URL. Startup/session maintenance only target Convex.
- Removed unreachable local-filesystem asset fallback. Runtime storage requires
  configured RustFS even in loopback development mode; no implicit local asset
  directory is created when bucket configuration is missing.
- Two process-level startup tests pass: absent Convex cannot use DATABASE_URL;
  absent RustFS cannot create MVM_LOCAL_ASSETS. Fourteen coordinator unit tests
  also pass (two explicitly live tests remain ignored in that unit-only run).
- Remaining SQL library route/test adapters and their inert lazy pool field are
  not yet removed; do not describe the dependency removal as complete. Existing
  integration tests and CI still need migration before retiring those adapters.
  Running primary uses its verified copied binary; these startup changes are
  compiled/tested locally but have not replaced that live binary yet.

### Disposable Convex acceptance and CI

- Added `node scripts/test-convex-http.mjs`: starts the pinned Convex backend on a random loopback port, deploys a copied schema in a temporary directory, and runs HTTP acceptance with a fresh test-only admin key and in-memory objects. It does not use the app's deployment settings, BWS credentials, or live projects. The container and temporary configuration are removed afterward.
- HTTP acceptance creates its own project and requires `MVVM_TEST_CONVEX_URL` plus `MVVM_TEST_CONVEX_ADMIN_KEY`; the URL must use loopback HTTP. Removed the assumption that three projects already exist and removed the optional live RustFS test target.
- Local verification passed: disposable-backend HTTP acceptance (1), Convex migration/persistence tests (13), backup/payload tests (12), Convex typecheck, Rust formatting. Docker inventory confirmed disposable container cleanup.
- CI now runs these Convex checks. Existing PostgreSQL acceptance remains temporarily and explicitly skips the separately-run Convex test. Remote CI is not yet verified; SQL adapter removal and implementation PR gates remain open.

### Session acceptance migrated off PostgreSQL

- Replaced the SQL-backed session integration test with `convex_session_boundaries` on the disposable backend. It checks bootstrap-token restrictions, untrusted origins, distinct session tokens, no session delegation, revocation during a delayed request body, issuer-key rotation, and revoke-all. Existing Convex HTTP coverage retains router-recreation durability and live SSE revocation.
- Added deterministic Convex expiry/retention coverage: twelve-hour lifetime, hashed stored token, expiry rejecting identification and writes, seven-day retention, and pruning aged expired/revoked rows while retaining newer rows.
- Both disposable HTTP tests passed; eight Convex persistence tests passed. Targeted Rust Clippy, formatting and Convex typecheck passed. SQL remains in the runtime adapters and other integration suites; this step removes only the session suite's database dependency (its temporary unused AppState pool field remains until the runtime refactor).

### Project and analysis acceptance migrated off PostgreSQL

- Project persistence now runs on disposable Convex: competing revisions, fresh-router readback, multipart audio upload/duration verification, asset ownership and stored-key reads, SSE revisions, checksum download, incomplete/corrupt upload recovery and late object arrival.
- Analysis lifecycle now runs on disposable Convex: competing workers submit once, completed native-confidence/section results survive router recreation, wrong-project reads fail, and ambiguous or interrupted submissions require reconciliation without replay.
- Test-only fixture mutations live under `scripts/fixtures/`, copied exclusively into the runner's temporary deployment. They are absent from the production Convex directory. SQL row locks have no Convex equivalent; the retained recovery checks exercise immutable, idempotent promotion rather than the retired PostgreSQL lock mechanism.
- All four disposable HTTP tests passed together; four ordinary persistence boundary/contract tests passed; targeted Clippy and diff checks passed. Transcription acceptance still requires migration before removing SQL adapters and the temporary AppState pool field.

### Transcription acceptance migrated; PostgreSQL CI service removed

- Both transcription suites now run on disposable Convex with fake provider endpoints. Preserved unavailable-object deferral, competing-worker deduplication, legacy word reconstruction, lyrics asset ownership, ambiguous/interrupted submission quarantine, source-confirmed recovery, stale recovery rejection, retained original receipts, and bounded fallback/timed-tail alignment.
- Test-only state changes remain exclusive to the temporary deployment. The disposable runner now includes all six HTTP acceptance tests across sessions, project persistence, analysis and transcription; all six passed together.
- Removed the PostgreSQL service and obsolete SQL acceptance command from Verify CI. No integration test reads MVM_TEST_DATABASE_URL or executes SQL queries now. Runtime SQL adapters and lazy AppState pool fields still remain to remove.
- Targeted transcription Clippy, formatting and diff checks passed. Remote CI remains unverified until the migration PR is submitted.

### SQL runtime removed

- Removed PostgreSQL route/session implementations, SQL worker dispatch and recovery paths, SQL upload promotion, schema migration entrypoint, and AppState connection pool. Removed sqlx from Cargo dependencies and refreshed Cargo.lock; cargo tree shows no sqlx/PostgreSQL dependency.
- Transcription pass persistence now requires the Convex lease-bound Pass rather than an optional SQL fallback. Session, asset, project and job handlers use Convex and fail closed when its client is absent.
- Verification after removal: workspace Rust tests passed (30 ordinary tests; two optional live homelab probes remain ignored); all six disposable Convex HTTP acceptance tests passed separately. Full workspace/all-target Clippy with warnings denied, formatting and diff checks passed. Graft graph refreshed.
- The live primary and restore coordinator processes still use their earlier copied binaries. This source change is not yet live or reviewed; replacing the process, browser verification, PR/CI and exact-head Greptile remain pending. Historical SQL migration files and the existing PostgreSQL rollback container remain untouched.

### Convex-only binary live in local studio

- Rebuilt coordinator and replaced only the verified primary API process on port 5199 after checking its executable path and listener ownership against the private process receipt. Web process remained running. New coordinator PID 38924; binary SHA-256 6289f1800a755e899d363a54a09d3db6197e6eeb77664f7a1a7d52b8582c2217.
- Credentials were freshly injected from BWS into the child process. Real provider keys remain omitted. API health reports Convex/RustFS, status ok, local development true.
- Compared the entire saved I Ran project response before and after replacement: identical, revision 7. In-app browser Reload saved retained the treatment and disabled Save story, 22 sections, 795 beats, and 139 words in 16 timed chunks. Audio advanced to 0:16 and was explicitly paused using its labelled control.
- This verifies the local browser against the new binary, not durable private hosting, physical-device coverage or installed Windows-client acceptance. The separate restore coordinator remains on its earlier binary. Implementation PR and remote CI/review gates remain pending.
