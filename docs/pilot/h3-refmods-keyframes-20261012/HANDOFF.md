# H3 keyframes to MVVM - October 12, 2026

## Immediate hold

The user is currently running a few options in ComfyUI, including a requested original-model second-pass denoise 0.20 comparison. **Do not modify the UI, prompts, settings or queue; do not submit/cancel renders until the user resumes.** Do not assume those runs finished or choose their result automatically. The copied workflow is a handoff snapshot, not permission to restore it over newer UI changes.

## New chat objective

Continue the song project in Music Video Vending Machine using the existing storyline, duration, song timing map and loose story points. The song's exact identity/duration must be discovered from current project sources; do not invent them from the jungle test names. First read project AGENTS.md, use its graft context workflow, and read docs/pilot/agent-production-resume.md. That older resume concerns separate motion tests; do not confuse it with the current still-quality experiment.

Draft a very basic shot overview and a broad candidate list with one generation prompt per line. Keep timing/shot IDs/beat assignments in a separate manifest. Include varied medium/wider/closer coverage, emotional actions and coherent staging. The user wants to discuss this after completing the quality test. Do not launch an overnight batch, build a new pipeline or edit application code merely to write the list. Eventual renders should feed the chosen workflow sequentially through the visible top Run button.

## Reusable skill

Installed: `C:/Users/Gordo/.codex/skills/minimax-h3-refmods-keyframes/SKILL.md`.

This packet includes a copy under skill/, all previously collected H3 docs/research under research/, and selected executed workflows/audits/scripts under evidence/. The header inspector was run against the actual files and the skill passed quick_validate. Extraction scripts in evidence are project-specific and can overwrite files; inspect before using. They are recovery evidence, not an automatic next step.

## Preferred route and acceptance

The original `minimax_h3_ref2va_pruned_int8_convrot.safetensors`, no Turbo/LoRA, er_sde/simple, 50 steps, denoise1, shift12/3, native2560x1440, seed4102, max reference sizing was substantially better than the earlier Eros8-step still route in the user's judgment. Lighting, appearances and Lune's body proportions were accepted. First pass 147.17sec. This is a multi-setting configuration comparison, not proof of a single root cause.

Second pass: split AV -> learned H3 latent upscaler 1.6 ->4096x2304 ->rejoin original audio -> er_sde/simple10steps at0.10 ->Fizgig decode -> save4K -> Lanczos return2048x1152. 57.95sec with cached first pass. User accepted the improvement broadly and requested0.20 exploration; that exploration is user-operated and currently unreviewed by the agent.

PixaromaCompare410: before input1 = first decode373 -> scale406; after input2 = refined decode396 -> scale400. Both2K. All317 nodes retained, unrelated routes preserved. Do not mislabel an earlier0.1vs0.2 Eros comparison as this before/after test.

## Live environment and sources

- Workspace `D:/ComfyUI-Easy-Install_v3122`, Python `ComfyUI-Easy-Install/python_embeded/python.exe`, install `ComfyUI-Easy-Install/ComfyUI`.
- UI `http://127.0.0.1:8188/#13fcd57c-ba5d-41ce-a1bb-02fab01c53aa`.
- Canonical `D:/user/default/workflows/H3_Turbo_ErosMaxBeta6_2Pass-frame-anchors-Rafa.json`. Historical name still says Eros; verify active checkpoint.
- Raw environment386, Rafa sheet388, Lune latest sheet389 reach ReferenceToVideo365 directly; RefModApply385 disabled. The preferred still result is currently raw-sheet conditioning, not proof of active RefMod improvement.
- Input environment `D:/input/hf_20261007_142933_fe26c478-b4cc-478d-9b1a-9d5be5648b3c.png`; Rafa `D:/input/9d98d0d3-3b9a-43e1-9d8b-a217f4f4b0a5.png`; Lune `D:/input/codex-clipboard-d9138471-a60c-406b-999e-c0a9fad8968f.webp`.
- Environment is world/lighting inspiration, not exact camera composition. Use credible human scale and a closer location. Preserve character identity/wardrobe; replace the sheets' studio illumination with motivated cold night light.
- Outputs `D:/output/jungle_keyframes/quality_baseline_ref2va_50step_native_00001_.png`, `original_ref2va_firstpass_2k_00001_.png`, `original_ref2va_secondpass_2k_00001_.png`, `original_ref2va_secondpass_4k_00001_.png`.
- Successful0.10run `c49ecf16-30de-4ee9-90e2-be43b3bc689e`; accepted native run `2c34c7ab-8c1f-46d2-8c51-915648be6a16`.

## RefMods

`ComfyUI/models/refmods/Rafa_IdentityEncode_v1.safetensors` has7 independent T1 image members; `Lune_IdentityEncode_v1.safetensors` has6. Audit confirmed header shape `[1,24,1,64,114]`, kindimage. Allselectedviews preserved. identity_encode forces full encode1024, refinement0, mergefalse/motion_onlyfalse. A single bundle can contain multiple independent images; do not silently average/compress them. Rerunning the maker can replace these with a temporal stack; re-audit before use. See skill/references/refmods.md for exact source files and serialization pitfalls.

## Three existing keyframes still to render/review

CR Prompt List364: keyframe4 urgent stop/relief;5 tender embrace/kiss;6 curious/uneasy look-back. Quality tests used start_index2,max_rows1. User wants the original three once the denoise choice is reviewed: start_index0,max_rows3. First reconcile user-run options/queue and get their review; do not queue duplicates while they are testing. Literal left-shoulder pose is still a review concern even though visual quality improved.

## Repository safety

Current MVVM checkout was feat/local-gen-pipeline, origin gordo-v1su4/music-video-vending-machine, with extensive tracked/untracked WIP. Verify live before changes. This handoff added only this packet; no commits, pushes, installs, pipeline code edits or bulk renders were performed. Leave all unrelated changes alone.

## Final user choice - supersedes the earlier finishing-test plan

The user chose to move forward with H3 only: original Ref2VA first pass, current learned latent upscale multiplier2 (2560x1440 to5120x2880), then er_sde/simple10steps at0.20denoise and Lanczos return2048x1152 as FINAL output401. Preserve this current user-chosen scale; the earlier1.6/0.10 run remains historical comparison evidence. Z-image/FaceUp finishing subgraph412, its Preview413 and experimentalCompare414 are disabled, retained for later. Krea2 editing was investigated and is installed, but was not adopted or run for this task. No new renders were submitted during finalization. The user's finishing test completed on its own; reconcile current queue before any future run. Final saved graph is evidence/workflow-final-h3-output.json. The user asked to finish this chat and continue in the MVVM chat. The original three keyframes4/5/6 still need rendering/review with the chosen route; do not launch an overnight batch before discussing the song/story shot list.
