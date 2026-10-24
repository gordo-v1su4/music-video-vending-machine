# Preferred still route and comparison evidence

Snapshot: October 12, 2026. This is a reviewed local configuration for the Rafa/Lune jungle test, not a universal H3 optimum.

## Baseline

Canonical workflow: `D:/user/default/workflows/H3_Turbo_ErosMaxBeta6_2Pass-frame-anchors-Rafa.json`. Its historical filename contains Eros; the preferred active checkpoint is the original Ref2VA. Open UI: `http://127.0.0.1:8188/#13fcd57c-ba5d-41ce-a1bb-02fab01c53aa`. Preserve the complete graph; it had 317 nodes.

| Control | Tested value |
| --- | --- |
| Checkpoint | minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| Turbo/LoRA | none |
| First sampler / scheduler | er_sde / simple |
| First steps / denoise | 50 / 1.0 |
| Native still dimensions | 2560 x 1440 |
| Sigma shift | 12 / 3 |
| Seed | 4102 |
| Reference sizing | max |
| Still latent / decoder | FizgigH3StillLatent / FizgigH3StillDecode |
| Learned latent upscaler | minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors |
| Upscaler settings | multiplier 1.6, alignment32, temporal chunk true, force unload true, cuda/fp16 |
| Upscaled dimensions | 4096 x 2304 |
| Second sampler / scheduler | er_sde / simple |
| Second steps / tested baseline denoise | 10 / 0.10 |
| Delivery / comparison | Lanczos downsample to 2048 x 1152, crop disabled |

The original-model first pass took 147.17 seconds. The user explicitly accepted improved lighting, appearances and Lune's proportions. The 0.10 second pass took 57.95 seconds with the first pass cached. Agent inspection found cleaner hair/fabric/skin detail while maintaining lighting and composition. User requested a 0.20 comparison afterward and then took over running options. Verify its executed settings/results and user choice before promoting 0.20 to the default. Do not conflate the earlier Eros 0.20 test with this original-model test.

## Exact connections

UNET337 -> SigmaShift367 -> reference conditioning365 -> BasicGuider368. Raw image sources reach365; disabled RefModApply385 is not in this route. Fizgig still latent366 -> first SamplerCustomAdvanced372, with RandomNoise369, KSamplerSelect370 and BasicScheduler371. First latent372 -> Fizgig decode373 -> Save374.

First latent372 -> LTXVSeparateAVLatent390 -> **video** learned latent upscaler391 -> LTXVConcatAVLatent392 with original **audio**390 -> second SamplerCustomAdvanced395 (guider368, noise369, sampler394, schedule393) -> Fizgig decode396 -> 4K Save397 -> Lanczos ImageScale400 -> 2K Save401.

First decode373 -> Lanczos ImageScale406 -> 2K Save407. PixaromaCompare410 receives image1=406 BEFORE, image2=400 AFTER, both 2048x1152. Compare mode0 is left/right; verify visible labels and stored compare state. The older MTB compare failed on unequal shapes. Comparison between denoise candidates is a different pair from before/after.

Fizgig makes one latent video frame plus silent audio tokens. Its decoder repeats the latent for VAE context then selects a pixel frame; that is decoding, not a second sampling pass. The learned upscaler preserves T=1. Split/rejoin AV correctly; the upscaler expects a regular video tensor, not the combined AV representation. ImageScale only downsamples the decoded result; it is not the detail-generating stage.

## References and prompt roles

Inputs under `D:/input`:

1. Environment386: `hf_20261007_142933_fe26c478-b4cc-478d-9b1a-9d5be5648b3c.png`.
2. Rafa sheet388: `9d98d0d3-3b9a-43e1-9d8b-a217f4f4b0a5.png`.
3. Latest Lune sheet389: `codex-clipboard-d9138471-a60c-406b-999e-c0a9fad8968f.webp`.

Environment is a world/material/depth/lighting guide, not a requirement to copy the distant establishing shot or make characters gigantic. Describe a new nearby viewpoint at credible human scale. Preserve character identity/outfit/body proportions; replace their sheets' warm studio background/illumination with motivated cool blue/teal night lighting. Avoid contradictory neutral/warm front-light directions. Warm-source leakage is a hypothesis, not an isolated proven cause.

CR Prompt List364 has three prompts: keyframe4 urgent stop/relief, keyframe5 tender embrace/kiss, keyframe6 curious/uneasy look-back. start_index2/max_rows1 selected the third for quality tests; start_index0/max_rows3 selects all three when requested. Verify iteration actually produces three distinct prompts, not three copies of one latent. Include camera, staging, eyelines and observable emotions. The literal both-left-shoulder pose remains a review concern despite accepted visual quality.

## Results and forward use

`D:/output/jungle_keyframes/quality_baseline_ref2va_50step_native_00001_.png` is the accepted native first pass. `original_ref2va_firstpass_2k_00001_.png`, `original_ref2va_secondpass_2k_00001_.png`, `original_ref2va_secondpass_4k_00001_.png` are the matched baseline outputs.

Evidence in `D:/ComfyUI-Easy-Install_v3122/maintenance`: accepted-original-baseline.json, original-secondpass-ui-run.json, original-secondpass-result.json, original-secondpass-settings.json, quality-first-baseline-settings.json. Research: `docs/minimax-h3/STILL_KEYFRAME_RESEARCH.md`. Current user edits/queue take precedence over these snapshots.

Earlier Eros Beta6 8-step stills were faster but softer/plasticky for this test. Eros shift10/3 recommendations do not transfer to original H3. The new baseline changed checkpoint, steps, native pixels and shift together, so it is not a single-parameter causal experiment. Speed is secondary to fidelity here.

Before overnight production, save the chosen baseline, test all three original rows, review wider face sizes and confirm identity/lighting still hold. For each future shot store ID, prompt, seed, reference hashes, actual graph, settings and output paths. Reconcile UI queue first and honor render holds. Do not install VRGameDevGirl's newer nodes just because upstream examples use them; installed node availability differs.

## Final user choice - supersedes the earlier finishing-test plan

The user chose to move forward with H3 only: original Ref2VA first pass, current learned latent upscale multiplier2 (2560x1440 to5120x2880), then er_sde/simple10steps at0.20denoise and Lanczos return2048x1152 as FINAL output401. Preserve this current user-chosen scale; the earlier1.6/0.10 run remains historical comparison evidence. Z-image/FaceUp finishing subgraph412, its Preview413 and experimentalCompare414 are disabled, retained for later. Krea2 editing was investigated and is installed, but was not adopted or run for this task. No new renders were submitted during finalization. The user's finishing test completed on its own; reconcile current queue before any future run. Final saved graph is evidence/workflow-final-h3-output.json. The user asked to finish this chat and continue in the MVVM chat. The original three keyframes4/5/6 still need rendering/review with the chosen route; do not launch an overnight batch before discussing the song/story shot list.
