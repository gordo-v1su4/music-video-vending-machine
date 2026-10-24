# Agent production design interview

Status: authorized direction synthesized into [the production specification](agent-production-spec.md), [role master prompts](agent-production-master-prompts.md) and [Linear issue map](agent-production-issues.md), 2026-10-09. These notes preserve interview provenance, not implemented capabilities or a replacement for docs/PRD.md. Remaining choices are explicit run configuration and evidence-led evaluation.

## Agreed direction

- Demo target: next week, as stated on October 8, 2026. Exact date and audience remain open. Demonstrate one solid short finished sequence and an observable review/improvement cycle; rendering live during the presentation is not required.
- Support both a rough brief that becomes a shot plan and an already planned set of shots. Both feed an editable shot plan approved before generation.
- Generate multiple candidates rather than only one result. Compare different LLMs' independent prompt interpretations of the same shot, not merely different seeds of one prompt. Candidate count and seed allocation remain open.
- Use a role-based team: an orchestrator, prompt writers, a render operator and reviewers. Agent model selection may differ by task; Codex, Claude, Cursor and other agent environments are possible. No single agent platform has been selected.
- Keep media rendering local. API LLMs are allowed for assistance, orchestration and review.
- Agents may submit renders programmatically. The user's established approach uses SwarmUI APIs and an existing working folder. Exact workflow, folder and render scheduling need live verification before implementation.
- Execution visibility refinement: the user now wants subsequent renders initiated in the visible ComfyUI browser tab by entering the prompt and pressing the top Run button, so progress and previews are visible. APIs may collect histories and outputs; background API submission is not the preferred next-run path. Clear VRAM before the next prompt when requested.
- Independent prompt writers must not see competing prompts or results during the experiment. Present candidates under anonymous labels such as A/B/C; keep author/model provenance separate from the judging materials. The user does not need to be blinded and can see provenance. Reviewers remain blind to authorship until judgments are recorded.
- Reviewer-model experiment requested: independent GPT-6 Luna, GPT-6.1 Sol and GPT-6 Astra reviews of identical anonymous clips with the same rubric and no access to each other's findings. Record selected model versions and distinguish sampled-frame reviews from native temporal video ingestion.
- Prompt writers share fixed character/environment references, story action, duration and required cuts. They may vary wording, staging and camera treatment within those constraints.
- LLM review should examine rendered video and guide revised generations. Assess technical/render correctness and filmmaking continuity separately from story clarity and emotional performance. Review evidence, automatic repair limits and final selection authority remain open.
- Technical review includes intended motion and travel direction, forward/backward movement, required cuts, fuzzy or damaged image regions and overall image quality. Filmmaking review includes camera behavior and continuity. Story/performance review includes clarity, emotion and expressive faces; identify where a prompt needs more specific performance direction.
- Acceptance refinement: identity and wardrobe/Look drift are hard failures. Incidental debris differences are lower severity unless they break the required causal action or edit continuity. Aesthetic scores cannot override a confirmed unapproved Look.
- RefMod audit: retain Rafa's reported successful single-sheet RefMod as a baseline; test additional consistent same-outfit views and reference combinations before assuming more images will improve preservation. Prepare the girl's reusable identity/Look and environment references as separate deliverables.
- Review/select at generated-shot level regardless of how many shots a Workflow run produces. Preserve strong opening/ending shots even when the middle fails; keep source time ranges, lineage and original artifacts, then recheck joins in the assembled sequence.
- User-positive example: D:/output/video/ComfyUI_00003_.mp4, especially its opening and final wider-to-face falling shot with subtle face/hair/wind motion. The user rejects poor distant framing but explicitly likes this successful wider approach. Live probe: 1024x576,24fps,14.375s; do not describe it as an unverified full-resolution output.
- All next-work tracking belongs in Linear's Music Video Vending Machine project, including the local render workflow, role-based agents, identity auditing and review system. Existing roadmap parents remain open; new slices should preserve their broader production gates.
- Judge technical defects by time range: a mangled opening does not disqualify a strong later segment that can be used in the edit. Entirely technically bad footage is unusable regardless of storytelling. Reviewers should identify usable ranges as well as defects; joining/coverage and contextual acceptance criteria still need definition.
- Each prompt writer may receive timecoded critique of its own results, without seeing competitors' prompts, clips or rankings. Revised candidates undergo blind comparison again.
- An engaging UI to show variations, reviews and the production process is part of the desired demo; the exact presentation remains undecided.
- Reference preparation may combine reusable conditioning, images/first-frame anchors and motion-reference video. Add a reference-scout role for movements that are difficult to describe; verify conditioning support rather than assuming every workflow accepts every reference type.
- Prompt assistance should encode the actual generation mode's grammar and validate enforceable rules programmatically, with continuity and creative quality assessed separately. The user clarified that the remembered Python prompt linter belongs to Seedance/Blood Rush in Creative Studio Pro, not this H3 project; no equivalent H3 linter has been established.
- Demo material will use the existing song and characters already in preparation. The user reports Rafa's RefMod prepared, with the girl's RefMod and one or more environment references still to prepare. Verify the actual artifacts before rendering.
- Rafa source correction: the user confirms his working RefMod was made solely from C:/Users/Gordo/Downloads/9d98d0d3-3b9a-43e1-9d8b-a217f4f4b0a5.png, a character sheet made in ChatGPT. It shows a large facial portrait plus full-body front, side and back views. This exact supplied image is the reported successful RefMod source; older repo identity images and sheets are not evidence of its inputs. The RefMod artifact itself has not been inspected.
- Source image SHA-256, checked locally: CCDDE04998D35A5EE9A75F8D5F6313EFF38476D42A600BF04DEC8D610D547817.
- Approved quick experiment: compare the existing RefMod with and without a separate scene image of Rafa in an environment absent from the RefMod source; distinguish extra-reference conditioning from first-frame anchoring. The user supplied C:/Users/Gordo/Downloads/hf_20261007_150905_29578d4f-909d-43c0-847d-d173e649fa95 (1).png. Execution handoff: rafa-refmod-test-handoff.md.
- Current browser inspection confirms ComfyUI on 127.0.0.1:8188 with workflow PlagueKind_Rafa_14s_RefMod_16x9_06MP_1Kref and Rafa_identity_full visibly enabled. The user confirms the RefMod is already loaded. Reuse this workflow/RefMod; the earlier repo PlagueKind pilot is not the current runtime source of truth.
- Test single-shot generation and multi-cut generations across different motion demands. The user's observation that three cuts can work is a hypothesis to test, not an established acceptance threshold.
- Latest physical-action correction: ground collapse preserves running momentum into a down/back accelerating drop, with no stopping, sitting, crouching or pose reset. Begin at real speed, then ramp gradually into slow motion while descent continues.
- Timed guide capability is verified in the installed native Add Guide node. Current trial `ab692d87-4bfe-40bb-a103-f8e016e802c8` changed the motion prompt and added guides together; it is not an isolated guide A/B, and visual acceptance remains pending in the render evidence.
- Next creative option, not a rewrite of earlier tests: close camera stays with the boot. Rafa steps onto the edge leading heel-first/down and digs the loaded heel in; the heel pushes/shears cracked ground, the whole supporting patch collapses forward/down and takes the boot with it, putting his continuing body momentum into the desired backward fall angle. The camera travels over the foot and along/over his body in slow motion as support gives way, rather than cutting away to a face. Entry state is moving body plus loaded heel on supporting ground; exit state is lost support plus continuous descent. This is a proposed causal staging to test, not proof of physical correctness, and has not authorized another queued render by itself.
- Timing refinement for that next option: begin the speed ramp at heel-dig/load contact; keep the boot sliding through crumbling earth during the ramp while the camera crosses over the boot/body. Earlier fast-then-later-ramp trials retain their own briefs and provenance.
- Controlled follow-up authorized separately: retain only the downward-angled falling-boot guide at frame 120, remove the ground-contact guide at frame 62, and hold prompt/seed/settings fixed. Suspected two-anchor conflict remains a hypothesis; current outcome belongs in the render evidence.
- Next visual hypothesis: stronger fast-motion blur eases through the slow-motion ramp while preserving readable heel/ground detail. Blur cannot hide defects to obtain a pass. The already-queued one-guide comparison remains bound to its executed prompt/settings; later UI blur edits belong to a subsequent submission unless the actual receipt establishes otherwise.

## Material supplied

The supplied image illustrates a small task-specific agent team, orchestration, verification and evidence. It is a design reference, not an instruction to install or use the named marketplace. The accidentally attached model download is excluded at the user's request.

## Open design branches

1. Exact demo date, audience, passage within the existing song/story and presentation surface; locate existing project assets rather than starting new material.
2. Shared creative brief: references, motion, timing and intended cut structure held constant versus freedom for prompt interpretations.
3. Starting matrix of prompt models, interpretations and seeds; render scheduling and retry limits.
4. Scoring/evidence for the agreed technical/filmmaking and story/performance review passes, video ingestion, independent reviewer models, acceptable uncertainty and human final choice.
5. Reference preparation: approved images, reusable character/environment conditioning or a combination; actual RefMod workflow verification.
6. Simple generation-first demo scope versus Project Stack integration. No application merge has been agreed.

## Repository findings

These are inspected code/document capabilities, not fresh runtime or visual acceptance:

- scripts/mvvm_gen/run.py already structures prompts and supports alternate takes; its existing prompt default requests uninterrupted shots.
- scripts/mvvm_gen/graphs.py:216-247 constructs a six-section reference prompt. The MiniMax base-mode prompting skill explicitly excludes full-reference Ref2VA, so its base grammar must not be applied universally to this workflow.
- Its technical checks and contact sheets do not establish a complete temporal LLM review-to-rerender loop.
- scripts/mvvm_gen/plans/i-ran-pilot.json identifies Rafa and Lune and the existing song. Both identity images and sheet sets exist in .runtime/gen; the master audio measures 353 seconds. Existing images are not proof of current user approval or reusable RefMod preparation. Working media also exists at D:/output/local/MVVM/i-ran-pilot. Current listeners, exact active workflow and reference conditioning remain to verify.
- Project Stack Structure provides reference/prompt preparation, candidate approval and edit assembly concepts, with an existing-footage-first workflow. A full application merger has not been established as easy or necessary for this demo.

Capture further decisions here as the interview progresses. Only resolved production terms belong in CONTEXT.md; use ADRs only for consequential trade-offs that warrant a durable rationale.
