# Foundation verification — 2026-09-25

## Observed

- Rust 1.95.0, Bun 1.3.14, FFmpeg/FFprobe available on Windows.
- RTX 5090: 32607 MiB VRAM; 2952 MiB used during initial read-only inspection. No generation or memory benchmark run.
- Created private GitHub repository gordo-v1su4/music-vending-machine; preserved research baseline on main. Implementation on feat/narrative-foundation.
- PostgreSQL 17.10 bookworm local development container bound only to 127.0.0.1:55439, dedicated mvm_dev/mvm_test databases. Image digest sha256:9b18b78397054fce88a9552e9d5a3ad5bb7fd258c5b3cc1c5028e46373d6ea8f. Docker Desktop was initially stopped and started for isolated development tests. No production database changed.
- Rust domain tests cover optimistic conflicts, atomic invalid actions, bound approvals, complete-song gaps versus valid excerpts, candidate rejection, pin protection, revision activation, old-direction reapproval and audio insertion/cutout timing.
- Explicit PostgreSQL integration test passed: concurrent same-revision updates produce one 200 and one 409; fresh connection/router reads committed state; generated one-second WAV inspected by FFprobe, uploaded and retrieved byte-identically; cross-project asset references return 404; forged duration returns 422; SSE resumes at next durable revision.
- Unauthenticated production API request rejected before accessing the database.
- Browser setup and real persisted treatment inspected visually at 1582px width. UI explicitly identifies incomplete story frames and disconnected generation/analysis.
- Browser fixture flow: imported a synthetic 30-second WAV, approved master, saved a timed section and a three-second insertion at song time five seconds. Preview displayed 33 seconds; playback reached video 0:11 while song time showed 0:08. Production approval succeeded and a later treatment edit visibly invalidated it. This is UI/timing evidence, not cinematic/pilot acceptance.
- Final local checks: 9 domain tests, 3 API/auth/schema tests, 1 explicit PostgreSQL integration test, 6 frontend tests; Rust formatting/clippy, generated-contract consistency, Svelte check (0 errors/warnings), two Svelte autofixers and static production build passed.

## Homelab read-only preflight

Canonical proxmox-home remained on main, fast-forward refresh already current; pre-existing .gitignore/.ignore changes preserved. Ran Windows check-ingress.ps1 -Mode all and homelab-healthcheck.ps1.

Hosts Proxmox, app-vm and RustFS reachable; Essentia docs, media health and Trigger health returned 200 through public, origin and expected upstream paths. S3 roots returned expected 403. Trigger artifact public/origin root returned expected 403; direct LAN app-vm:9000 returned 000, consistent with the runbook's loopback-only storage binding. No ingress/container recovery or configuration changes attempted. Caption gateway reachability does not prove model readiness. These checks do not establish authenticated storage round-trip, successful analysis, local model generation or live Trigger task deployment.

## Remaining acceptance

RustFS adapter is implemented but not yet live round-trip tested. Coordinator currently advertises generation/export/Essentia as unavailable. No real pilot song selected. No Tauri installation, model generation, production deployment, video export or archive restoration has passed. Those milestones remain pending. Fixture media is not a pilot deliverable.

## Reproduce

See README development and verification commands. Media fixtures and runtime state live in gitignored .runtime or isolated test storage. No secrets are stored in this evidence file.
