# Workstation backup schedule

The Windows workstation holds an independent copy of the home Convex/RustFS
project data. This is off the home server, not off-site. Run installation from
PowerShell 7 with Node 24 or newer after the implementation PR passes its merge gates:

```powershell
./scripts/install-backup-task.ps1 -SecretsRunner C:/Users/Gordo/Documents/Github/proxmox-home/shared/bin/agent-secrets.mjs
```

The installer copies the three backup scripts and frozen production dependencies
to `%LOCALAPPDATA%/mvvm/backup-runner`. It does not depend on the app worktree
afterward. The canonical `proxmox-home` secret runner and Node installation must
remain available. The installer refuses to replace an existing runner or task;
upgrades require an inspected replacement rather than silently changing a job.

Archives live in `%LOCALAPPDATA%/mvvm/backups`. The installer disables inherited
ACLs and replaces all existing explicit grants with current-user-only access on
the backup root and its existing files/subdirectories before copying files.
Use a dedicated backup directory, not a shared folder. Linked entries are refused.
Secret values are fetched live from BWS for each run; they are not saved in the
task, configuration or archive. Protected user bootstrap access must already be
configured. The process uses the scoped MVVM storage credentials and dedicated
Convex admin credential. Raw child-process diagnostics are discarded.

The `\MVVM\Verified backup` task runs daily at 03:00 and at operator logon,
with StartWhenAvailable, one instance at a time, and a 20-minute execution limit.
The runner has an earlier 15-minute deadline: it terminates the credential/backup
process tree and records a timeout failure before the scheduler's hard limit.
It runs as the existing user with limited privileges and **requires that user to
be signed in**. It cannot back up while the workstation is off or logged out.
The logon trigger provides a later recovery point, not continuous coverage.

Each archive contains a snapshot, referenced objects, a checksummed manifest and
an acceptance receipt after the source snapshot is rechecked for concurrent
changes. Incomplete/failed directories are not accepted recovery points. The
outer runner re-verifies the archive before updating `last-success.json`.
Failure writes only a stage and timestamp to `last-failure.json` and exits nonzero;
the last known success remains intact. `last-attempt.json` records running and
terminal state, so an interrupted process cannot look like a new success.
Inspect the timestamps and Task Scheduler
LastTaskResult rather than treating an old success file as current health.

All archives are retained. No automatic deletion is installed. New runs refuse
to start with less than 10 GiB free; this is a starting headroom check, not a
guarantee against an unusually large archive exhausting storage. Monitor capacity
and backup age. Tiered retention, automatic alerts and a second off-site copy
remain future operational work.

## Acceptance

- Seventeen backup/payload/runner tests pass locally, including corrupt archive
  rejection, timeout failure receipts, preservation of last success and
  withholding raw failure output. A Windows ACL regression also passes with
  explicit Everyone read grants on both an existing directory and a child file;
  all are replaced with current-user-only access. CI runs this check on Windows.
- The live backup command wrote and verified 5 objects (26,480,029 bytes) directly
  into the independent workstation directory at 2026-09-26T11:21:02Z, with source
  unchanged and manifest `d00108e6cc0025f20b1301254419fbea1e1b1b7f27cf5047fcd5b96de38d6417`.
- PowerShell installer parses successfully. Installation, actual Task Scheduler
  execution, and BWS access from that context still require live verification
  after review. No scheduled-backup acceptance is claimed yet.
- PR #9 merged at `b3104ab` after Greptile 5/5 on `69c9a05`, green CI and resolved
  findings. The first installation failed before task registration: PowerShell
  `Set-Acl` requested SeSecurityPrivilege on existing archive files. The follow-up
  uses the .NET access-control API to persist only DACL changes, preserving owner
  and audit metadata. All paths must already belong to the current user.
  Repeated fixture checks and the actual existing archive ACL update passed;
  task installation remains pending that fix's review.
- The earlier current-backup restore/restart drill is documented in
  [recovery evidence](evidence/2026-09-26-convex-same-bucket-recovery.md).
