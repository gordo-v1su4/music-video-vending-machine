# Build status

Updated: 2026-09-26. Overall: in progress, not a release.

| Milestone | Status | Evidence / next action |
| --- | --- | --- |
| M0 | Accepted | PRD/backlog, private GitHub baseline and CI; [PR #1](https://github.com/gordo-v1su4/music-vending-machine/pull/1) merged at `86d236c` after Greptile 5/5 on `d42c04e`, passing CI and resolved findings |
| M1 | Partial | [Live probes](evidence/2026-09-25-capabilities.md): private RustFS round-trip and Essentia fixture passed; Qwen still and H3 clip generated and inspected; Qwen edit preservation failed; vision, WebGPU/WebView2, Jcode and Ableton gates pending |
| M2 | Partial | [Private storage/recovery](evidence/2026-09-25-private-recovery.md) passed; [operator session checks](evidence/2026-09-26-operator-sessions.md) passed; PR #4 merged at `c924765` after exact-head Greptile 5/5 on `d00c371`, green CI and resolved findings. Windows sharing and pending-upload backup acceptance remain |
| M3 | Pending | Trigger/worker integration not implemented |
| M4–M5 | Partial | Real Svelte intake, master/story/reference/approval UI and timed audio preview; 22 real-song Essentia sections saved and auditioned; Deepgram recovery returned 139 draft lyric words; director and installed Tauri verification pending |
| M6–M8 | Partial primitives only | Domain pin/revision/coverage/time rules tested; generation, musical ranking, QC and export pending |
| M9 | Pending | Local development only; no production deployment or installer |
| M10 | Song supplied; acceptance pending | User confirmed the 137 BPM stem package and a 5:53 integer ending. Derived master and MP3 are verified; references and in-app production approvals remain pending |
| M11 | Pending | Requires verified pilot |

Current user-facing checklist: [PROGRESS.md](PROGRESS.md). Next priority is the visible audio-to-story flow using only the supplied 137 BPM package. Earlier audio, separate lyrics, and their analyses are superseded. The trimmed 5:53 MP3 completed Essentia Studio analysis with 22 sections; the application adapter and UI were exercised in the same visible browser tab, including upload progress, analysis, audition and saved sections. Full-song lyrics recovery returned 139 draft words; review and director integration remain. PR review is pending.

## Known external constraints

- [PR #2](https://github.com/gordo-v1su4/music-vending-machine/pull/2) merged at `e97ed9e` after Greptile 5/5 on `53ec733` and passing CI. Its generation probes do not enable unverified production capabilities.

- Linear connection returned reauthentication required during planning. Repository tracking continues independently.
- No application existed at implementation start. Research and model-file inventories do not prove successful generation.
- Paid generation/review tests require approved quotes; none authorized or submitted.

## Evidence policy

Store redacted reproducible results under docs/evidence; large media and private runtime state stay outside Git. Cite checks with their limits. Never mark a whole milestone complete because a subset of tests passed.

Latest evidence: [foundation verification](evidence/2026-09-25-foundation.md), [live capabilities](evidence/2026-09-25-capabilities.md), [Impeccable dark-mode audit](evidence/2026-09-25-impeccable-ui.md). Local development uses ports 5198 (web), 5199 (API), 54329 (retained PostgreSQL rollback snapshot, no longer used by the app), and isolated standalone ComfyUI 8198, all loopback-bound. Synthetic fixtures are not real pilot acceptance. Generation/export remain unavailable. The local analysis capability now reflects server configuration; local intake/analysis/audition browser checks passed; broader responsive and installed-client acceptance remain.


## September 26 persistence revision

The user-approved database change is implemented locally: self-hosted Convex on home app-vm and the scoped RustFS `mvvm` bucket. SQL runtime/dependencies and PostgreSQL CI service were removed. Thirty ordinary Rust tests and six disposable Convex HTTP acceptance tests pass; the primary local coordinator was replaced and browser-verified with the existing revision-7 song unchanged. See [migration evidence](convex-migration-status.md). The implementation is not merged or a private production release. Scheduled/off-host backup retention, durable private hosting, installed Windows acceptance, generation, temporal review and export remain open.
