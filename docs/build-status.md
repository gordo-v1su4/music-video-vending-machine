# Build status

Updated: 2026-09-25. Overall: in progress, not a release.

| Milestone | Status | Evidence / next action |
| --- | --- | --- |
| M0 | Accepted | PRD/backlog, private GitHub baseline and CI; [PR #1](https://github.com/gordo-v1su4/music-vending-machine/pull/1) merged at `86d236c` after Greptile 5/5 on `d42c04e`, passing CI and resolved findings |
| M1 | Partial | [Live probes](evidence/2026-09-25-capabilities.md): private RustFS round-trip and Essentia fixture passed; Qwen still and H3 clip generated and inspected; Qwen edit preservation failed; vision, WebGPU/WebView2, Jcode and Ableton gates pending |
| M2 | Partial | [Private storage/recovery](evidence/2026-09-25-private-recovery.md) passed; [operator session checks](evidence/2026-09-26-operator-sessions.md) pass locally and await the PR gate. Windows sharing and pending-upload backup acceptance remain |
| M3 | Pending | Trigger/worker integration not implemented |
| M4–M5 | Partial | Real Svelte intake, master/story/reference/approval UI and timed audio preview; director, Essentia and installed Tauri verification pending |
| M6–M8 | Partial primitives only | Domain pin/revision/coverage/time rules tested; generation, musical ranking, QC and export pending |
| M9 | Pending | Local development only; no production deployment or installer |
| M10 | Awaiting first-run input later | User will choose song/references and approve production in the app |
| M11 | Pending | Requires verified pilot |

## Known external constraints

- [PR #2](https://github.com/gordo-v1su4/music-vending-machine/pull/2) merged at `e97ed9e` after Greptile 5/5 on `53ec733` and passing CI. Its generation probes do not enable unverified production capabilities.

- Linear connection returned reauthentication required during planning. Repository tracking continues independently.
- No application existed at implementation start. Research and model-file inventories do not prove successful generation.
- Paid generation/review tests require approved quotes; none authorized or submitted.

## Evidence policy

Store redacted reproducible results under docs/evidence; large media and private runtime state stay outside Git. Cite checks with their limits. Never mark a whole milestone complete because a subset of tests passed.

Latest evidence: [foundation verification](evidence/2026-09-25-foundation.md), [live capabilities](evidence/2026-09-25-capabilities.md), [Impeccable dark-mode audit](evidence/2026-09-25-impeccable-ui.md). Local development uses ports 5198 (web), 5199 (API), 55439 (PostgreSQL), and isolated standalone ComfyUI 8198, all loopback-bound. Synthetic fixtures are not real pilot acceptance. Capability probes do not enable production generation or analysis in the API.
