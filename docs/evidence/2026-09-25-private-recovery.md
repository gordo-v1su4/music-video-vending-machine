# Private storage and recovery acceptance

## Results

The actual Rust coordinator used the existing RustFS service with dedicated application credentials, a separate PostgreSQL database, `development: false`, and bearer authentication. It ran on loopback port 5201; the user's development workspace continued on web 5198/API 5199 with its original local database and assets.

| Scenario | Observed result |
| --- | --- |
| Scoped S3 access | PUT/GET/range passed under `projects/*`; anonymous read 403; deletion, writes outside prefix, reads of the unapproved capability prefix, another bucket's listing, outside-prefix listing and bucket-root listing denied. [Current recheck receipt](2026-09-25-scoped-storage-recheck.json). |
| Legacy access | An actual legacy-format fixture passed both scoped S3 and authenticated API readback. Writes and deletion at that key were denied. [Receipt](2026-09-25-legacy-storage.json). |
| Bucket discovery | RustFS returns a filtered list containing only `music-vending-machine`, rather than denying ListBuckets. |
| API authority | Anonymous project listing 401; authenticated cross-origin mutation from an untrusted origin 403. |
| Real upload/download | One-second synthetic WAV uploaded through the API and retrieved from RustFS through authenticated API download; SHA-256 matched. |
| Conflicting writes | Two concurrent changes at the same revision produced HTTP 200 and 409; one treatment was persisted. |
| Coordinator restart | Stopped the process, started the same binary against the same database, then compared the complete project and downloaded-media checksum. Both matched. |
| Cold backup | Stopped the acceptance API, confirmed no other source database clients, captured a PostgreSQL custom dump and every completed asset's bytes, and verified their checksums. No pending upload intents existed. |
| Separate restoration | Restored the dump into a newly created database and copied backed-up bytes to fresh `projects/<restore-id>/restored/<hash>` keys. Compared complete project/event/intent records and asset identities; all matched. |
| Restored application | Started the coordinator against the restored database; the original project and authenticated media download matched the pre-backup state and checksum. The media was served from restored keys, not original keys. |

Fixture project: `b6e6a6a4-962a-48b8-a7d8-fa7e8b00b193`; asset: `9a8a0cff-c30c-4aeb-bead-395604dabb22`; media SHA-256: `56d4af65701c26df20bd4021eda95b6e830348ce3a746086079fe89285548dc9`.

Source database: `mvm_storage_acceptance`. Restore database: `mvm_storage_restore_d4337770c9354f758149cdb1fa98f8cc`. PostgreSQL 17.10 in the isolated development container. Dump SHA-256: `7a509d449b94a968f350f812b1608d905c5f5d8176f2d7022ad62281f16de75b`. The database uses the existing loopback-only test role; this is not production database credential acceptance.

Private artifacts retained outside Git:

- `.runtime/private-api-acceptance.json`: original state and restart verification.
- `.runtime/private-restored-api-acceptance.json`: restored API verification.
- `.runtime/backups/storage-acceptance-20260925/`: `database.dump`, checksum-named media, manifest with original/restored keys and comparison results.
- `.runtime/private-api*.log`: process logs. The acceptance service is stopped after verification; its databases and media are retained.

## Implementation

New uploads use `projects/<project-id>/originals/<asset-id>`, matching [the scoped policy](../../infra/rustfs-coordinator-policy.json). Previously the writer repeated the bucket name inside the key. Downloads now select `object_key` together with metadata from the ownership-filtered database row instead of deriving a location from IDs. Existing local/legacy assets retain their recorded locations. The policy grants read-only compatibility for `music-vending-machine/*/originals/*` inside the application bucket; no new writes or deletion are allowed there.

The integration test covers the new writer prefix, normal download, an asset moved to its recorded legacy key, and rejection under a different project. The restored live API additionally proves reads from a fresh, non-derived key.

Credentials are stored only in BWS private collection: `MVM_S3_ACCESS_KEY`, `MVM_S3_SECRET_KEY`, and `MVM_OPERATOR_TOKEN`. Values were generated, stored and silently readback-verified before installing the dedicated IAM identity. New values were not written to the repository or command text. Canonical homelab and vault inventories contain names and scope only.

IAM policy `mvm-coordinator-v1` grants bucket location, listing restricted by `s3:prefix` to `projects/*`, GET/PUT under `projects/*`, and read-only legacy compatibility; it grants neither deletion nor administration. Installation used RustFS's signed private admin API on the existing Tailscale route. The live API required `x-amz-content-sha256`. A missing-policy lookup returned HTTP 500, so policy absence was verified using the actual policy inventory before creation. The later review fix updated only this application's owned policy after comparing its existing definition to the committed version; other policies and the storage service configuration were unchanged. [Official IAM API reference](https://docs.rustfs.com/en/security-compliance/iam/policies).

## Reproduction

Use `agent-secrets run` to inject only the named BWS values needed by each command. The probes and recovery harness make real calls; they are not CI fixtures or production scheduling services.

```powershell
# Dedicated key scope, requiring MVM_S3_ACCESS_KEY and MVM_S3_SECRET_KEY:
uv run scripts/probe-scoped-storage.py --output .runtime/new-scoped-receipt.json

# Start a separately configured, non-development coordinator on 127.0.0.1:5201
# with the isolated mvm_storage_acceptance database and scoped RustFS credentials.
# Inject MVM_OPERATOR_TOKEN for both API calls:
uv run scripts/probe-private-api.py start --receipt .runtime/new-api-receipt.json
# Stop/restart that coordinator with the same configuration, then:
uv run scripts/probe-private-api.py verify --receipt .runtime/new-api-receipt.json

# Stop the acceptance coordinator. Inject scoped S3 credentials:
uv run scripts/verify-local-recovery.py --directory .runtime/backups/new-acceptance
```

The recovery harness deliberately uses only `mvm-dev-postgres` and `mvm_storage_acceptance`. It creates a new restore database and new object keys; it never cleans/replaces the source or an existing database. Retain partial state if a command fails and inspect it before another attempt. To verify the restored API, start the coordinator with the manifest's `restoredDatabase`, the same scoped storage, and port 5201; use a copy of the original API receipt with `state: ready_for_restart`, retaining the expected project/checksum. No secret is needed in that receipt.

Validation: `cargo test --workspace --locked` (13 pass, one database test intentionally ignored by default); the database test was separately run against `mvm_test` and passed; `cargo clippy --workspace --all-targets --locked -- -D warnings` passed. Live commands above passed. No UI source changes occurred in this batch.

## Review regression acceptance

Greptile identified a restore-key collision for distinct assets with identical bytes. Restore keys now include asset identity as well as checksum: `projects/<restore-id>/restored/<asset-id>/<hash>`. The second live run backed up two separate, identical WAV assets (including one legacy-format source), restored both, compared all logical records, and downloaded both through the restored authenticated API. Both identities survived with two different object keys. [Recheck receipt](2026-09-25-recovery-recheck.json); private backup at `.runtime/backups/storage-duplicates-20260925/`.

The backup root is restricted before writing private bytes. POSIX uses directory mode 0700 and a 0077 umask; Windows explicitly removes inherited access and grants the current SID access, retaining Windows' privileged owner/system/administrator rules. Live ACL inspection confirmed inheritance disabled on the new root and file access inherited only from those restricted identities. The earlier retained fixture backup root was also restricted. Three new regression tests cover identical-content key separation, nonempty/exact bucket discovery and POSIX directory privacy; Windows runs 13 passing tests with the POSIX-only test skipped, while CI runs that mode check on Linux.

## Remaining requirements

M2 remains partial: the Windows client is not installed, operator authentication still uses a shared operator token rather than session lifecycle management, and restoration of pending uploads is not covered by the cold fixture. Production backup scheduling, off-host retention, production database credentials, private deployment and rollback remain M9 work. This recovery harness does not claim the portable editable project archive or rerender acceptance required by M8.
