# Independent agent production and review specification

Status: authorized planning scope, 2026-10-09. This extends the approved [PRD](../PRD.md) for a bounded local demo; it does not declare production milestones complete. Implementation work is tracked in the [issue map](agent-production-issues.md). Operational role prompts live in [master prompts](agent-production-master-prompts.md).

## Problem Statement

The user has a working local H3/RefMod workflow but needs dependable prompt assistance, independent candidate creation, actual video review and a visible improvement cycle. A technically generated clip can still contain wrong identity, wardrobe changes, unclear causality, broken motion or useful shots surrounding a failed middle. Comparing seeds alone does not answer whether different prompt writers improve the result. A large existing-footage editor would obscure the short demo's core value.

## Solution

Start with the existing song, characters and working local workflow. Convert a rough brief or an existing shot plan into an approved Sequence containing candidate Clips and reviewed Generated shots. Audit references, compile mode-correct prompts, run isolated prompt teams, launch generation visibly, collect durable receipts, review anonymous video independently, retain usable ranges, assemble a short Musical edit and demonstrate one approved repair. The user can inspect prompts, provenance, outputs, findings and Keep/Reject decisions.

Media generation remains local. LLM provider/model/host assignments are configurable and recorded. Current GPT Luna/Sol/Astra trials compare models within one provider; they are not evidence of cross-provider integration. A team can run through verified adapters or explicit artifact handoffs. Listing Codex, Claude or Cursor is not a transport implementation. Support a sequential single-orchestrator mode and isolated independent teams in parallel; the shared local GPU queue still arbitrates render capacity.

## User Stories

1. As the director, I want a rough brief turned into an editable plan, so I can approve the intended action before rendering.
2. As the director, I want an existing shot plan accepted directly, so I can retain prepared creative work.
3. As the director, I want Sequence → Clip → Generated shot shown separately, so multi-shot outputs are understandable.
4. As the director, I want the existing production master and assets located, so the demo uses current material.
5. As the director, I want Character and Look assignments per sequence, so identity and costume remain intentional.
6. As a reference scout, I want each asset's role and source audited, so contradictory references do not enter production silently.
7. As the director, I want Rafa's existing RefMod retained as the baseline, so a successful setup is not rebuilt unnecessarily.
8. As the director, I want the girl's identity/Look and environment preparation tracked separately, so missing conditioning remains visible.
9. As a prompt writer, I want the actual workflow's input map and grammar, so picture/audio labels resolve correctly.
10. As a prompt writer, I want deterministic lint findings, so missing labels, conflicting durations and unsupported guide inputs are caught before GPU use.
11. As the director, I want independent prompt interpretations with controlled references and settings, so wording can be compared fairly.
12. As a prompt writer, I want an isolated workspace and only my own critique, so competitors do not influence my revision.
13. As the director, I want configurable provider/model assignments, so the same experiment can be repeated across verified environments.
14. As the render operator, I want the approved prompt and settings entered in the visible UI, so progress and previews are observable.
15. As the render operator, I want exact submitted graphs, histories and outputs collected, so each candidate can be reproduced and attributed.
16. As the director, I want intermediate guide images distinguished from untimed references, so their effect and target time are explicit.
17. As a reviewer, I want anonymous candidates and the same brief, so author/model reputation does not bias the comparison.
18. As a reviewer, I want temporal video access and declared sampling limits, so observations reflect what was actually inspected.
19. As the director, I want full-clip review as well as shot review, so a strong frame does not hide broken progression.
20. As the director, I want confirmed identity/Look drift to block selection, so aesthetic scores cannot excuse the wrong character.
21. As an editor, I want source in/out ranges and defect boundaries, so strong shots can survive a failed middle.
22. As an editor, I want joins reviewed with neighboring context, so salvage does not create incoherent motion or geography.
23. As the director, I want repair proposals tied to evidence and allowance, so retries improve a specific problem.
24. As a prompt writer, I want revised candidates reviewed anonymously again, so improvements are tested fairly.
25. As the director, I want candidates kept separate from the active cut until Keep, so repair experiments preserve recovery.
26. As a demo viewer, I want a concise process view and playable before/after, so the end-to-end value is clear.
27. As the director, I want unresolved coverage and uncertainty displayed, so an incomplete output is not called finished.
28. As the director, I want a reproducible export and evidence package, so the demo can be played without live rendering.
29. As a demo viewer, I want a polished production/review journey across prompts, progress, shots, clips and salvage, so the process is engaging and understandable.
30. As the director, I want a read-only Project Stack reuse assessment and an independent-app alternative, so I can decide on reuse without assuming a merger or delaying the quick demo.

## Implementation Decisions

### Production packet and hierarchy

One revision-bound production packet carries the brief, approved master, Character/Look/location bindings, reference audit, timing, intended cuts, camera/action constraints, candidate matrix, capabilities, workflow identity and allowance. Changes invalidate affected approvals. Sequence groups Clips; a Clip is an immutable generated/supplied artifact that may contain multiple Generated shots. Each shot stores reviewed source-frame ranges and lineage. Detector-proposed cuts require review and do not define truth automatically.

Use existing durable project, asset, revision and approval boundaries. A supplied-clip import and a local generation receipt enter the same candidate registry. Avoid a new parallel project database or a wholesale Project Stack merger. Existing footage remains optional for this demo.

### Demo UI and optional reuse assessment

Refine the existing dark production/review surface into a legible approved-packet → prompt variants → visible progress → shot/whole-Clip/Sequence review → salvage/Keep journey. Preserve approved PRD behavior and existing components/tokens; use the local Impeccable/Svelte guidance during implementation. Fixture visual proof and native-browser evidence of the real integrated path are separate. This is scoped product refinement, not a redesign mandate.

Track Project Stack Structure assessment as a separate optional branch. Reuse the [existing historical source audit](../research/ui-project-stack.md) as a starting point, then resolve the actual current canonical checkout/revision before comparing existing-footage and generation-first entry points, reference assets, shot review, edit and coverage contracts. Deliver concrete reuse/adapt/no-reuse recommendations with risks and an independent-app alternative. This decision artifact does not authorize merging applications and does not block the short local demo.

### References, prompts and guides

Audit exact sources, hashes, crop/resize, identity/Look consistency and intended roles. Keep identity conditioning, scene reference, concrete first/last frame, timed interior guide and motion reference distinct. More references are a testable hypothesis, not an automatic improvement. Confirm the actual RefMod's contents and registration; old repo sheets do not identify its source.

Compile H3 Ref2VA's six fields against the actual reference order. Lint label existence and stable meaning, mode/role compatibility, duration versus actual frame grid, shot timing bounds, unsupported inputs, contradictory actions and stale packet revision. Enforce structural rules mechanically; creative fidelity and causal plausibility remain review tasks. Treat the remembered Seedance linter as a different project's capability.

Native Add Guide accepts explicit target-frame indices and H3 AV latent conditioning. Support an approved one-or-more-guide packet and controlled zero/one/two-anchor comparisons. Record actual frame indices, image transformation and reference-map behavior; guide images do not automatically acquire new tokenized picture labels. Keep ordinary references, RefMod, prompt, seed and settings unchanged when studying guide-count influence. If the prompt changes with guides, report a combined intervention rather than an isolated A/B guide test.

### Independent teams and execution

Give each writer/team an immutable shared packet and private output area. Competing prompts, clips, rankings and peer findings remain inaccessible during independent creation. A privileged orchestrator maintains attribution and a render queue. Reviewers receive anonymous clips, allowed reference evidence and the brief, with no author/condition key or peer review. User-visible provenance is allowed; review isolation still applies.

Provider adapters must demonstrate media/input/output support. Manual file handoff is a valid, explicitly recorded transport. Compare actual provider/model/host revisions, not brand labels. Track native video, streamed playback, sampled-frame and text-only access separately; unobserved temporal behavior stays unknown.

The current demo launches through the visible ComfyUI UI: paste the approved exact prompt, verify settings/refs/seed, press Run and collect its prompt ID. APIs may upload authorized local inputs and read queue/history/output receipts. Do not silently switch to background API submission. Broader unattended production remains the PRD's SwarmUI route and requires its own validation. An exploratory standalone browser render does not satisfy that release gate.

### Review, salvage and repair

Production self-check covers decode, coverage, dimensions, black/frozen spans and other deterministic media checks. Independent Review progresses through shot → whole Clip → Sequence context. Record technical findings, brief/action fidelity and artistic/performance judgments separately. Review whole-clip action progression, identity/Look, environment, motion/anatomy, camera/continuity, image quality, subtle expression and emotional clarity, then whole-sequence rhythm and neighboring joins. A technical pass does not establish visual quality.

Confirmed identity or unapproved Look drift is a hard selection/export failure. A reviewer allegation is recorded pending deterministic evidence or user confirmation; unsupported certainty cannot create acceptance. Scores never average away a hard failure. Incidental debris changes are advisory unless they break the required action or contextual continuity. Findings carry artifact/revision, source range, evidence, severity, uncertainty, reviewer identity/access method and proposed action.

Salvage uses reviewed source ranges, with unsafe trim boundaries marked. A failed opening or middle does not discard a valid later shot, but the retained action must make sense and cover its required slot. Recheck assembled joins and the entire candidate Sequence. Objective gaps remain explicit.

Repairs can trim, replace, reorder, re-prompt, rerender or fill a gap. User approval binds scope and allowance. The production run permits initial attempt plus at most two replacements per shot. A separately approved review repair receives its own equivalent allowance; existing-media edits consume no render attempts. Return only each writer's own timecoded critique. Re-review repair locally and in context, then offer Keep/Reject; active media changes only on Keep.

### Current motion acceptance

Rafa's ground-collapse example preserves momentum: moving body → supporting ground gives way → body continues into a down/back fall. There is no stop, sit, crouch, pose reset or fresh fall start. Speed-ramp timing belongs to each approved packet: earlier trials start with real-speed accelerating descent and slow later; the latest proposed variation begins the ramp at heel-dig/load contact. The boot keeps sliding through collapsing ground while the camera crosses over it and travels along/over the body. Descent continues throughout. Camera continuity and expression evolve with that action. Still guides must support progression; matching their pixels alone is insufficient.

### Demo boundary and evidence

Target next week's demo, as requested on October 8; the exact date remains configuration. Deliver a finished short Sequence and an observable review/improvement cycle using the existing master and approved references. Candidate counts, provider assignments, seed matrix and exact presentation date are configuration, not invented defaults. Pre-rendering is acceptable. Local rendering avoids provider render fees but still consumes GPU time/VRAM, storage, queue capacity and operator time; expose those costs and enforce an allowance. Show reference audit, independent prompts, anonymous review, selected/salvaged ranges, repair and playable before/after. Preserve the user's earlier approved good opening/ending as candidate source ranges until contextual review establishes a reason to replace them. A 30–60 second production pilot, installed Windows acceptance and full-song release remain separate existing gates.

The two-guide trial started from the visible UI as job `ab692d87-4bfe-40bb-a103-f8e016e802c8`. Its motion prompt changed along with the guides, so it is a combined trial. See [current render evidence](rafa-render-experiment-results.md) for execution, collection and review state; a completed render/mechanical pass does not establish motion or subjective acceptance.

The user also requests a controlled follow-up retaining only the downward-angled falling-boot guide at frame 120 and removing the ground-contact guide at frame 62, with prompt/seed/settings fixed. The suspected two-anchor conflict is a hypothesis; see the dynamic results rather than treating either guide arrangement as accepted.

## Testing Decisions

Prefer one external production-packet → candidate → findings → approved repair → candidate edit → Keep/export seam, with real existing adapters and media receipts. Each vertical slice must expose a user-visible artifact and a reproducible behavior check. Fake transports may test isolation, conflict and lost-response behavior, but do not establish provider support or video quality.

Exercise missing/stale approvals, wrong Look, label mismatch, frame-grid timing, duplicate/uncertain submission, reviewer access limitations, invalid usable ranges, unsafe joins, exhausted allowance and restoration. Compare reviewers on identical anonymous clips with known defects and retained good ranges. Require actual watched/listened-to local media for the demo, and a fresh full-clip/Sequence review after any repair. Browser evidence and Windows WebView2 acceptance remain distinct.

## Out of Scope

Wholesale application merger implementation (the optional read-only assessment is in scope), a primary manual NLE, automatic paid fallback, public publishing, new model installation, invented cross-provider transport, automatic user approval, generated singing/lip-sync evaluation, and declaring existing production milestones complete from this experiment.

## Further Notes

The interview notes preserve provenance and unresolved configuration. Render receipts and current trial outcomes are maintained separately in the experiment results; capabilities are researched separately. Existing roadmap parents retain their broader acceptance criteria and state. New tickets are narrow children/related work with native dependency edges. Wave's identity/capabilities are unresolved; no integration or visibility promise is made.

Capability ledger: the first demo uses shared task packets, independent provider sessions and manually imported responses. [Claude's headless interface](https://code.claude.com/docs/en/headless) is a possible later adapter, not an installed dispatcher. [MCP tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) supply a protocol; they do not supply queue leases or application orchestration. [Gemini video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) needs sampling-aware evaluation for fast action. [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL) documents video preprocessing, but local serving/media ingestion remains unverified. Existing contact sheets are frame evidence, not temporal LLM review.
