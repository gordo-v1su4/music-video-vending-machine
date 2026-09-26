# Current-bucket object recovery

The active storage bucket and new backups both use `mvvm`. The original restore
tool required a different destination bucket, so it rejected current backups.
`scripts/restore-convex-objects.mjs ARCHIVE MANIFEST_SHA256 --same-bucket` now
explicitly permits recovery into the source bucket. Without that option, the
same-bucket operation still fails before any object request.

The tool verifies the pinned archive first, writes only with `If-None-Match: *`,
then checks destination length and SHA-256. Matching existing objects pass;
conflicting bytes fail without replacement. Missing objects may be created.
A failed run can therefore leave some restored objects, but cannot overwrite
existing objects. Keep writers stopped during disaster recovery and resolve any
conflict before importing a prepared database snapshot.

The prepared snapshot revokes sessions and quarantines queued, running or
submitting provider jobs. It does not import a database or start workers.
Incomplete/missing upload intents stay intents; recovery does not promote them.
An existing `restored-snapshot.json` is never overwritten.
Object recovery can be retried, but repeating the complete CLI command rejects
an existing prepared snapshot. Retain that snapshot and its checksum for database
import; the command reports failure rather than silently replacing its session
revocation timestamps or emitting a second success receipt.

## Verification

- `node --test scripts/convex-backup.test.mjs scripts/migration-payloads.test.mjs`:
  15 passed. New coverage checks explicit opt-in, missing-object restoration,
  idempotent retries, preservation of conflicting bytes, unchanged archives,
  session revocation/job quarantine, and incomplete/missing upload intents.
  Command-level coverage executes the same exported command used by the CLI,
  substituting only the S3 client and environment. It verifies option validation,
  prepared file/checksum output and repeat-command failure without file changes.
- Live scoped RustFS credentials verified all 5 existing archived objects
  (26,480,029 bytes) in `mvvm`, using manifest SHA-256
  `d00108e6cc0025f20b1301254419fbea1e1b1b7f27cf5047fcd5b96de38d6417`.
  Prepared snapshot SHA-256:
  `08f60e379d7cc0b8f733bcde0e3802ff2aad3bb86782d521618e90b563c256e5`.
  No database import was attempted; workers remain disallowed in the receipt.
- The live check exercises existing matching objects. Missing-object and conflict
  cases are automated test evidence, not destructive tests on live song media.

The prepared current backup also passed a fresh local disposable Convex drill
using the pinned production backend image and production schema. All rows
matched after import and after a container restart: 3 projects, 22 events,
3 assets, 2 analysis jobs, 3 transcription jobs, 17 revoked sessions and no
pending uploads. Repeat import was refused. Docker's dynamically allocated port
was rediscovered after restart. The disposable instance was removed, no workers
started and primary was untouched. Private receipt:
`.runtime/current-backup-restore-drill.json`.

This verifies database readback, not coordinator/browser acceptance against
that disposable instance. Earlier isolated-instance API/session acceptance is
recorded separately. Scheduled/off-host retention remains open; this does not
establish durable production recovery acceptance.
