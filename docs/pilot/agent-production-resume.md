# Resume local agent production

Use this entry point when continuing this experiment or transferring it to another agent system. It is a handoff, not a new render authorization. Read the [production specification](agent-production-spec.md) for the approved design and [role master prompts](agent-production-master-prompts.md) for execution contracts. The [issue map](agent-production-issues.md) records planned implementation; publication does not mean those features are built.

## Copyable bootstrap prompt

```text
Resume Music Video Vending Machine from docs/pilot/agent-production-resume.md in C:/Users/Gordo/Documents/Github/music-video-vending-machine. Read AGENTS.md and applicable shared proxmox-home guidance. Use graft first for repository context. Load the canonical production spec, then only the role prompt and skills relevant to my requested action.

First declare your provider/model, agent host, available tools, native media access, filesystem visibility and permitted actions. Resolve every path and live endpoint on this host; do not assume the previous host's Windows files, browser or ComfyUI exist here. Treat skills as instructions only after opening their actual SKILL.md, and adapters as unavailable until verified.

Read current experiment results and durable queued/executed receipts before proposing work. Distinguish observations, user judgments, model judgments and untested hypotheses. Reconcile existing prompt IDs before any retry. Do not duplicate Run, install models/nodes, rebuild RefMods or dispatch another system merely because this handoff mentions them. Follow my current authorized scope; preserve original references, outputs and unrelated dirty files.

Choose explicitly: sequential roles in one orchestrator context, or independent provider teams with isolated writers and blind reviewers. Manual allowlisted artifact handoffs are valid; do not invent a shared dispatcher. Keep condition/author mappings away from reviewers. Mechanical checks, wardrobe/identity checks and filmmaking/emotion review are separate evidence streams.

Return exact artifact paths, revision/provenance, observed evidence, limitations and the next concrete action. A decoded render is not creative acceptance. Proposed prompts and queued jobs are not completed outputs. Ask only for missing decisions that cannot be discovered from the packet, receipts or current authorized scope.
```

Before handing off, supply the missing envelope values from the [shared contract](agent-production-master-prompts.md#shared-envelope): role, packet revision, allowlisted inputs/private output directory, allowed actions, render allowance and completion criterion. Copy the assigned role prompt after the bootstrap; do not send the whole competing-team workspace.

## Skills and host capabilities

The [local skill audit](../agents/skill-audit.md) and [hashed inventory](../agents/installed-skills.json) verify local files, not every host's command palette or upstream version. Resolve `.agents/skills/<name>/SKILL.md` on the actual host. A missing skill must be reported; copying this document does not install it. Current session authorization governs actions, not a skill or role label.

| Role/action | Load when needed | Verify before acting |
| --- | --- | --- |
| Clarify scope and plan | `grill-with-docs`/`grilling`, `to-spec`, `domain-modeling` | Current packet and prior approvals; do not restart a completed interview |
| Publish/update planned work | `to-tickets`, tracker and triage docs | Actual Linear project/team/issue relations and authorized publishing scope |
| Write handoffs/prompts for agents | `writing-for-agents`; generation prompt skill if exposed | Actual H3 mode/input map; open the skill file instead of assuming its name is enough |
| Research references/capabilities | `research` | Installed node source/object_info and primary documentation; source rights/provenance |
| Render operator | Applicable computer-use skill; operator role contract | Visible browser control, actual endpoint/queue, owned job IDs, local inputs and output receipts |
| Independent reviewer | Reviewer role contract; relevant research guidance for tool selection | Actual video/audio or sampled-frame access, anonymity and coverage limitations |
| Wardrobe/identity checker | [Review-tool audit](../research/deterministic-review-checks.md), checker contract below | Actual serving route/model, frame/crop access, approved Look references and calibration fixtures |
| Implement/debug | `implement`, `diagnosing-bugs`; `tdd` where appropriate; `code-review` | Assigned vertical slice and actual existing implementation; do not call planning implemented |
| UI refinement | `impeccable` plus applicable Svelte skill | Approved PRD, dark theme, actual native browser evidence; fixture proof versus integrated path |

Matt's planning flow is locally present. Other agent systems may require their own skill registration or a manual prompt handoff. Claude/MCP/Gemini/Qwen interface candidates and their limits are linked in [run modes](agent-production-master-prompts.md#choose-a-run-mode); no verified cross-provider dispatcher or Wave integration is claimed. Separate providers and separate independent contexts are different claims.

## Evidence to resume from

Read [render experiment results](rafa-render-experiment-results.md) for current completions, artifacts and acceptance, and [installed H3 guide research](../research/h3-middle-guide-frames.md) for exact node/input behavior. Use receipts rather than workflow titles or filename prefixes to identify an executed condition.

When a continuous-camera clip changes viewpoint near an anchor, read the [camera/guide diagnosis](../research/rafa-camera-guide-diagnosis.md). Match guide framing and action state to the intended camera position at that time; its current explanation is a tested-artifact observation plus a hypothesis, not a universal guide rule.

| Discovery | Evidence and limits |
| --- | --- |
| RefMod alone versus added untimed scene image | Four matched renders, seeds 241137/241138, A/B at 1088 x 608. See results and `.runtime/gen/rafa-refmod-ab`. This small paired-seed experiment does not establish universal quality/cost superiority. Native token estimate is source-derived, not a runtime measurement. |
| Interior guide support | Installed native `MiniMaxH3AddGuide` conditioning supports explicit frame placement. Untimed references, tokenized Picture labels, first/last frames and video motion refs have distinct roles. A textual timestamp is not a wired guide. |
| Two-guide exploratory run | `ab692d87-4bfe-40bb-a103-f8e016e802c8`, guides 62/120, 337.06 s, 1312 x 736, 294 frames/12.25 s. Prompt also changed, so this is a combined intervention. |
| One-guide removal comparison | `ee4f9fae-68e8-4956-a5cf-0c828c761c72`, only falling-boot frame120, 300.18 s; exact prompt/seed/settings matched the two-guide run. Mechanical checks pass; subjective acceptance and causal effect need evidence. |
| User steering feedback | The user found timed guides promising for steering multi-shot work and preferred the falling angle. The ground-contact blur variant brought back stopping/shoe action before the drop in their judgment; timing still needs work. Compatible action state, placement and camera deserve tests; this is not a universal formula or proof that two anchors inherently conflict. |
| Mechanical scans | Decode/ffprobe and detected black/freeze spans are collected. They cannot certify continuous momentum, anatomical correctness, identity, wardrobe, emotion or storytelling. See the separate review-tool audit. |

For the next motion variation, preserve continuous load → crumbling support → sliding boot → descending body. Camera stays with the boot then travels over foot/body; ramp onset is the approved packet's heel-dig/load contact, with blur easing while detail remains readable. This differs from the earlier later-ramp trial. Preserve the earlier good ending where compatible; describe the desired uninterrupted momentum in positive generation text. Keep unwanted-action lists in review criteria rather than embedding them in the generation prompt. These are creative criteria, not physical-proof claims.

The prepared exact next text is **`D:/output/local/MVVM/rafa-blur-guide-1mp/next-heel-ramp-prompt.txt`**. It has **not been queued by this handoff**. File presence is not permission to submit it.

## Existing jobs: reconcile, do not duplicate

The user queued randomized trials through the UI. During this session Sol handled GET-only collection; a future host/session must verify collector/process status rather than assume that agent is still available. Use `D:/output/local/MVVM/rafa-randomized-blur-guide-1mp/` receipts and the latest results before any action. Initial observed IDs were `8db73d23-426f-4431-9f7e-41216c33efab`, `bfc79b1d-97a0-42ac-84d6-7753ce4b7237` and `33916772-71c6-44ab-995f-9b64faca3a84`. Those names are historical queue observations, not a current three-job assertion. Root subsequently confirmed the first completed in 357.09 seconds; consult its collected receipt for checks and acceptance.

A later snapshot had the first running with the second ground-contact blur image, while the user switched pending trials back to image4 `hf_20261009_050057_e1fd9c3a-ca53-4900-8518-e62b3883abe1.png`. The newly observed pending IDs were `5c58b1bc-a31e-400b-ac24-92988398f265` (seed388608669273415), `bcab3e2c-0fe5-4c77-9a1c-23fda292dc81` (seed581137133127615) and `6b401e14-c830-49e3-ba28-654850ef2e7b` (seed987321352725476). Two earlier pending IDs disappeared from queue/history at that snapshot; cancellation was not proven. Read `queue-reconciliation.json`, `reconciliation-summary.json`, queued snapshots and completed histories for actual images and outcomes. Do not infer seed/image from mutable UI state or submit replacements because an old ID is absent. Pending/running/completed state can change after this document was written; wrapping the notes does not require waiting for those jobs.

## Small wardrobe/identity checker contract

The user requested a cheap dedicated vision-checker microservice for fixed shirt/hat/shoes/shorts questions across sampled frames. Treat it as a planned role/service until the [review-tool audit](../research/deterministic-review-checks.md) verifies an actual route. Model-assisted checks are not deterministic truth. Face consistency needs its own calibrated reference/tool evidence; wardrobe agreement is not identity proof.

An existing InsightFace face-similarity script is available, with required packages discoverable in the active Python and models cached in the user's model directory. Inference and identity thresholds are not validated. Missing detections require UNKNOWN; target association and reviewed calibration are needed before gating. See the canonical audit for exact behavior, limitations and runtime findings.

Inputs: immutable clip hash/revision, approved Character/Look references and question set, timestamped frames/crops, sampling strategy and readable/occluded coverage. Output each question with `YES | NO | UNKNOWN`, timestamps, evidence frame/crop paths, reason, uncertainty, model/version/config and coverage. Phrase questions unambiguously, such as "Does the visible shirt match the approved Look?" Occluded or absent evidence is UNKNOWN, not NO or a pass. Report checked versus unchecked intervals and disagreements; do not extrapolate a few sampled frames to the entire video.

Calibrate using approved examples and known mismatches before automated gating. Escalate suspected identity/Look failures for confirmation; retain confirmed hard blocks and uncertain findings separately. This checker does not evaluate filmmaking, causal motion, speed ramps, emotion or final Keep. The independent reviewer still inspects the whole Clip and supplied Sequence context using its declared actual media access.

Done for a resume session means its requested artifact/action is evidenced, existing jobs are accounted for without duplicates, and unresolved acceptance/capability gates are explicit. Follow the [issue map](agent-production-issues.md) for implementation; optional Project Stack assessment does not authorize a merger or block the quick demo.
