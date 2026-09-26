# Pending-upload backup and restore acceptance

The cold isolated recovery harness now backs up pending upload records alongside completed assets. Available pending bytes are retained by their actual checksum, even when incomplete; missing objects are recorded explicitly. Access errors and service failures fail backup rather than masquerading as missing media. Restored intents point to fresh restore keys and retain their original expected checksum, size and identity.

## Observed live result

- Source: `mvm_storage_acceptance`, with three completed assets and three synthetic pending fixtures: verified WAV, incomplete bytes, and absent object. The acceptance coordinator was stopped and no other source database connections existed during backup.
- Restore: `mvm_storage_restore_a484040584ad46cb9774beee36b1d2c8`, created from the real PostgreSQL dump. All completed media and both existing pending objects were restored into fresh RustFS keys. Logical pending records matched except for deliberately relocated storage keys.
- Dump SHA-256: `85a5da87c9ef7589db9ccddfdb2b31c2752c55f14f027c66f1070dbd2a7a403e`.
- The real coordinator started against the restored database. It completed only verified pending asset `fe8ed90d-2b61-41ad-8677-87dc3dc6bc6e`. Missing and incomplete media remained pending.
- An operator session authenticated the restored media download. SHA-256 matched `56d4af65701c26df20bd4021eda95b6e830348ce3a746086079fe89285548dc9`.
- The first download check used the obsolete direct bootstrap-token authentication and correctly received 401. The check was corrected to exchange that credential for an operator session; download then passed after restarting the same restored coordinator. No restore or upload was repeated.
- Source pending count stayed three. The song's `mvm_dev` database and running UI were not altered. The isolated acceptance coordinator was stopped afterward.

Private receipts and bytes are retained at `.runtime/backups/pending-uploads-20260926/`; fixture and verification helpers are `.runtime/prepare-pending-recovery.py` and `.runtime/verify-pending-restored.py`. Credentials were injected from BWS into the process and were not saved in these receipts.

## Checks and limits

Seventeen Python probe tests passed; the POSIX-only permissions test was skipped on Windows. Added coverage distinguishes missing objects from authorization/service failures, preserves verified and incomplete pending bytes, rejects corrupt completed media, and retains distinct identities for identical content. `git diff --check` passed.

This proves cold isolated pending-upload restoration and coordinator reconciliation. It does not prove production scheduling, off-host retention, installed Windows client acceptance, or portable editable archive acceptance. Incomplete uploads remain unresolved rather than being falsely completed. No generation calls or creative approvals were performed.

## Review follow-up

The restore loop is now directly exercised by automated probes: completed and verified pending objects, incomplete pending bytes, missing pending objects, the correct destination table for each identity, and checksum-failed readback that must not repoint the database record. Nineteen tests passed with one POSIX-only skip. The existing live receipt remains evidence for the original restore; this behavior-preserving extraction was checked by the expanded tests rather than repeating the live backup.
