# Project Stack reuse assessment and independent-app alternative

Read-only decision artifact for [V1S-235](https://linear.app/v1su4/issue/V1S-235/assess-project-stack-reusable-contracts-and-independent-app). Assessed 2026-10-10. **Approving this assessment does not authorize merging the applications.** The quick generation/review demo (V1S-233) continues without waiting for this decision.

## Target revision

Starting point: the [2026-09-25 UI source audit](ui-project-stack.md) at local `main` `0e8c45c`.

| Item | Observed value |
| --- | --- |
| Checkout | `C:/Users/Gordo/Documents/Github/project-stack-structure` |
| Remote | `https://github.com/gordo-v1su4/project-stack-structure` |
| Local `main` HEAD | `eb1e47a` (2026-10-07), **59 commits behind** `origin/main` |
| Canonical revision assessed | `origin/main` = `646b66e` (2026-10-07 19:45 -0400), confirmed equal to `git ls-remote origin refs/heads/main` |
| Working-tree changes | 15 entries: modified `.gitignore`, `AGENTS.md`, `bun.lock`, `package.json`; deleted `.kilo/plans/...proud-canyon.md`; untracked agent tooling (`.claude/`, `.cursor/`, `.grok/`, `.mcp.json`, `opencode.json`, `.ignore`) |

Everything below was read with `git show 646b66e:<path>` / `git grep ... 646b66e`. The donor's local checkout, working files and branches were not modified, fetched, built or run. No install, render or merge occurred. The local checkout is stale, so the older audit's line numbers (taken at `0e8c45c`) are historical; paths below cite the canonical revision.

## Evidence classes

- **Inspected implemented behaviour**: type and function definitions read at `646b66e` (cited below).
- **Planned/adapter-dependent**: SwarmUI/Trigger/RustFS job submission and export workers. Their source exists, but no runtime was exercised here.
- **Stale historical observation**: the 2026-09-25 audit's line numbers and its "full timeline UI not present" claim. Since then, 59 commits added song-timeline section/range selection (`03de698`), rough-cut review by song parts (`89e199b`) and saved whole-song Effects review (`3b2bafd`). These are commit subjects, not runtime-verified behaviour.
- **Unverified runtime**: all preview, export and generation behaviour.

## Contract comparison against Sequence → Clip → Generated shot

| Concern | Project Stack at `646b66e` | MVVM today | Fit |
| --- | --- | --- | --- |
| Entry point | Footage-first. `VideoMoment` (`src/components/studio/musicVideoProject.ts`) is a detected segment of supplied source (`sourceClipId`, `start/end`, `keyframeTimestamps`, `splitKind`, `contentHash`). Generation fills gaps. | Generation-first. A Clip is a generated or supplied asset (CONTEXT.md "Clip"). Supplied footage is optional for the demo. | **Adapt.** `VideoMoment` ≈ a reviewed Generated-shot range within a supplied Clip. Its detector-derived `splitKind` must stay a *suggestion* in MVVM: detected cuts require review. |
| Reference roles | `ReferenceAssetRole = "character-1" \| "character-2" \| "environment" \| "custom"` plus `ReferenceAssetKind` (character/environment/crowd/prop/vehicle/wardrobe/custom); `GenerationReferenceSelection` has fixed `character1Id/character2Id` slots (`src/components/studio/referenceAssets.ts:3-37`). | Rust `ReferenceRole { Exact, Inspiration }` (`crates/domain/src/lib.rs:43-55`). The production packet adds identity/Look, untimed scene, first/last anchor, timed guide and motion-reference roles. | **Adapt the vocabulary, not the slots.** The `kind` taxonomy and `promptHint` are useful. Fixed two-character slots conflict with Character/Look bindings and must not become the canonical model. |
| Candidate/shot review | `TimelineItem.candidateMatches: SemanticClipMatch[]` with composite scores (`semanticScore`, `motionContinuityScore`, `repetitionPenalty` …) and `ReviewFinding {severity, code, message, sectionId}`. | Independent reviewers record ordinal 1–5 judgments plus hard identity/Look gates. Scores never average away a hard block. | **No reuse for scoring.** Weighted composite match scores conflict with the "scores cannot override hard gates" rule. **Reuse** the small `ReviewFinding` shape (severity + code + message), extended with artifact revision, source range, evidence and reviewer access method. |
| Edit/coverage | `ApprovedPlacement {sourceStart, sourceEnd, songStart, songEnd, kind: "source"\|"gap", reason, origin}` and `placementPlan {inputSignature, revision, policy, placements}`. `RoughCutSwapProposal` carries `before/after`, `trims`, `residualGaps` and a `planSnapshot` because "revision alone cannot detect a restored or edited draft" (`src/components/studio/roughCutArrangement.ts:7-37`). | Rust `Shot {start_ms, end_ms, pinned, status: Gap\|Candidate\|Accepted, attempts}` and `EditRevision {parent_id, approval_fingerprint, status}`; "Usable range" and "Coverage gap" glossary terms. | **Reuse the concept directly.** Explicit `kind: gap` with a reason maps 1:1 to Coverage gap. Before/after proposals with residual gaps match the Keep/Reject repair flow. Snapshot-based staleness (not revision number alone) is a sound rule to adopt in MVVM packet invalidation. |
| Musical trimming | `musicalSourceEnd` trims a short replacement back to a nearby beat/onset, never extending media (`roughCutArrangement.ts`, after line 40). | Musical edit is beat/energy-driven (studio Timing/Arrange). | **Reuse as an algorithm** (pure TypeScript, framework-free). Port with tests; do not import the React modules around it. |
| Stack | Next 16.2.1, React 19.2.4, Zustand ^5, Trigger SDK 4.5.16 (`package.json` at `646b66e`). | SvelteKit 2 / Svelte 5, Rust coordinator, Convex. | **No component reuse.** React components and Zustand stores do not transfer to Svelte; only pure TS and data contracts move. |

## Concrete proposals

1. **Reuse:** `ApprovedPlacement` gap/source semantics and the `RoughCutSwapProposal` before/after/trims/residual-gaps pattern. Map them into MVVM's candidate-edit model as a typed TS contract in `apps/web/src/lib`, with tests mirroring donor cases. *Bounded follow-up slice:* "Port placement/gap and swap-proposal contracts with fixtures" (no UI).
2. **Reuse:** `musicalSourceEnd`-style cue-snapped trimming as a pure function. *Slice:* "Port cue-snapped short-replacement trimming with tests."
3. **Adapt:** the reference `kind` taxonomy and `promptHint` field into the production packet's reference roles. Keep Character/Look bindings unbounded rather than `character1/character2`.
4. **Adapt:** the `ReviewFinding` shape, extended with `artifact`, `revision`, `range`, `evidence`, `reviewer` and `access`.
5. **No reuse:** composite semantic match scoring, the footage-required generation gates, StudioApp orchestration, and React/Zustand state.

## Risks

- **Migration:** donor types are TypeScript interfaces, not versioned schemas. A port must pin a donor revision per contract and record it, or drift is invisible.
- **Approval/lineage:** donor approval is a placement-plan `inputSignature` plus revision. MVVM binds approval to a production packet fingerprint (`approval_fingerprint`). Two staleness models must not coexist on one object.
- **Storage:** donor assets assume RustFS upload states (`storageStatus`). MVVM's demo is file-backed under `.runtime/gen/<plan>/`; mixing the two storage authorities in one registry would break immutability guarantees.
- **License:** no license file in the donor (per the earlier audit). It is the user's own repository; keep attribution when extracting code.

## Independent-app alternative

Keep the two applications separate. MVVM stays generation-first (packet → prompts → visible render → anonymous review → salvage → repair → Keep). Project Stack stays footage-first (supplied footage → story match → rough cut). Exchange work through **manual artifact handoff**:

- **Project Stack → MVVM:** a placement plan export (song ranges with `kind: gap` + reason) becomes MVVM shot briefs for the gaps.
- **MVVM → Project Stack:** a Kept Clip with reviewed usable ranges imports as a supplied source with `VideoMoment`-style ranges.

A shared task packet (JSON with explicit revision) is the transport. No dispatcher or shared database is implied.

**Is a unified shell or merger worth pursuing now?** No. The domains are complementary, but the stacks differ (React/Next vs Svelte/Rust/Convex) and the review rules conflict (composite scores vs hard gates). A merger would block the demo on a framework migration. Extracting three pure contracts (items 1–2, 4) gets most of the value. Revisit after V1S-233 if both apps need one project document.

## Unresolved questions

- Does the donor's saved rough-cut / Effects review (`3b2bafd`, `422a342`) export a stable JSON document suitable as the handoff format? Not verified at runtime.
- Should MVVM adopt snapshot-content staleness for packet approval, in addition to fingerprints?
- Which donor revision is "approved" for extraction once the local checkout is updated? The user owns that decision; this assessment pins `646b66e`.
