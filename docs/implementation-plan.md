# Implementation backlog

Approved 2026-09-25. Repository is authoritative; mirror in Linear after connection reauthentication. No paid calls without approved quotes.

| ID | Dependencies | Requirements | Boundary and acceptance evidence | Stop condition |
| --- | --- | --- | --- | --- |
| M0 | None | All | Preserve research, Git baseline, PRD/backlog/decisions, CI and reproducible checks | Unrelated changes or secret exposure risk |
| M1 | M0 | R01,R03,R07,R11,R16,R17 | Live capabilities, RustFS round-trip, Essentia real job, Qwen/H3 output, vision, browser/WebView2; Jcode and Ableton separate evaluations; pinned hashes and measured resources | Failed integration blocks dependent work, never mock success |
| M2 | M0, M1 storage | R01,R02,R10,R14,R17 | Durable projects/assets/revisions/approvals/auth, conflicting writes, interrupted uploads, backup restore | Storage/auth failure |
| M3 | M1,M2 | R07,R09,R15 | Dedicated Trigger project, worker arbitration/recovery/cancellation, attempt accounting; interrupt job with no duplicate submission | Unknown provider outcome reconciles before retry |
| M4 | M2 | R02,R03,R04 | Intake, master, analysis, reference/story canvas and timeline; browser and installed-client evidence | Unsupported intake remains explicit |
| M5 | M3,M4 | R04,R05,R06 | Director actions, timed section placeholders, break mapping, bound approval; complete-song preview | Missing creative approval |
| M6 | M3,M5 | R07,R08,R09,R10 | Local generation, selection constraints, deterministic musical variation, pins, Keep/Reject | Attempt allowance exhausted or no acceptable clip |
| M7 | M6 | R09,R11 | Technical + temporal review, bounded repairs, optional external adapter; known defects and deliberate choices tested | Unobserved dimensions stay unknown |
| M8 | M6,M7 | R12,R13,R16 | 720p24 export, archive reimport/rerender; timing agreement within one frame | Any gap/blocking QC in exported range |
| M9 | M2–M8 | R01,R17 | Private deployment, installed desktop, health/restart, backup and rollback evidence | Unverified deployment or restoration |
| M10 | M9 | R18 | User-selected song/references; approved story/production; whole-song preview + 30–60s real passage, watched/listened to | User input/approval or failed pilot |
| M11 | M10 | R12,R13,R18 | Full-song production/review/export/archive and recovery | Any missing coverage or blocking finding |

## Execution loop

Pick a dependency-ready bounded item, inspect source/instructions, implement, run relevant checks, inspect output, repair failures, commit verified work, record evidence and continue. Three failed repair cycles with no new evidence: record blocker and move to independent work. Never lower acceptance criteria to pass. Keep milestones partial until all evidence exists.

## Required GitHub review gate

User instruction, 2026-09-25: commit and push completed work through implementation PRs. Comment `@greptileai` to request review, fix actionable findings, push verified fixes and request review again. Merge automatically only after Greptile explicitly awards **5/5 for the current PR head**, required CI passes and review threads are addressed. Do not advance to the next implementation PR before this gate passes. No review, stale score, inaccessible reviewer, or lower score means blocked, never permission to bypass. Preserve independent preparatory work without representing a blocked milestone as accepted.

## Verification matrix

- Synchronization: concurrent edits, disconnection, interrupted upload, reload and restore.
- Recovery: coordinator restart, Trigger retry, worker disconnect, stale lease, duplicate callback, uncertain submission and cancel.
- Authority: changed master/reference, stale approval, insufficient allowance, pins and paid fallback.
- Timing: boundaries, insertions, cutouts, trims, ramps, preview/export <= one output frame.
- Quality: corrupt/frozen footage, wrong identity, short coverage, poor transition, intentional off-beat cut and exhausted repair.
- Delivery: absent/lost WebGPU, installed Windows client, preview/export distinction, archive restore and deployment rollback.

## Decisions

- UI: dark mode by user preference; use the pinned project-local Impeccable skill for design and testing. Record audit results and actual browser observations; preserve product rules during visual refinement.

- Metadata: dedicated PostgreSQL with transactional revision checks; never Trigger internal tables.
- GPU: one heavy workload at a time until measured coexistence proves otherwise.
- Runtime truth: capability manifest records tested model/workflow hashes, versions, memory and elapsed time.
- Director: Jcode acceptance suite first; application-owned OpenAI-compatible loop if it fails, with identical validated action contracts.
- Private network only initially. Deployment must not expose new public services.
- Source files, generated candidates and accepted versions remain distinct.
