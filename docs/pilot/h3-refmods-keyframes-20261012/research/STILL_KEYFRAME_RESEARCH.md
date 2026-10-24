# H3 still keyframes: verified research, 2026-10-12

## What is running locally

The current image branch uses MiniMax H3 Reference to Video for conditioning only, FizgigH3StillLatent for a true one-frame joint AV latent, and FizgigH3StillDecode for decoding. The conditioning node's five-frame LATENT output is unused. The three raw image references are the environment, Rafa sheet, and the user-selected Lune sheet. Saved character RefMods are bypassed for this comparison.

The first pass uses Eros Max Beta 6, er_sde/simple, 8 steps, shift 10/3, seed 4102, 2048x1152. These are experimental settings, not an established quality solution. The three-frame render completed in 103.51 seconds. Expressions and the closer jungle viewpoint improved, but skin remains smooth and the requested look-back pose is incomplete.

The new detail comparison keeps the third prompt and first pass fixed, saves the first-pass image, splits its AV latent, applies the installed learned H3 spatial latent upscaler to 2560x1440, rejoins the original audio latent, then samples with res_multistep/simple, 3 steps, denoise 0.2 before Fizgig still decode. This is an adaptation under test, not a published Fizgig preset.

## Primary implementations

- [Fizgig H3 Still](https://github.com/shootthesound/ComfyUI-Fizgig-H3-Still): one latent video frame, plus two audio tokens. Its decoder repeats that frame into five latent frames for VAE context, then retains pixel frame 3. This repetition is decoding, not a second denoising pass. The author recommends results from 3 MP upward. The documented faster example uses the official FL2VA checkpoint and v4 step-600 EMA Turbo LoRA at 0.38, er_sde/simple, 20 steps. The higher-quality example uses no Turbo and 50 steps at 8 MP. The model settings are different from our Eros checkpoint; do not transfer those step counts blindly.
- [VRGameDevGirl H3 image nodes](https://github.com/vrgamegirl19/comfyui-vrgamedevgirl/blob/main/VRGDG_MiniMaxH3ImageReference.py): the newer Text / Reference to Image node makes a five-frame burst, locks the audio stream, and optionally wraps a static image prompt. Select Still Frame chooses the middle decoded frame by default. The image node itself does not sample or perform a second pass. Its default image-edit prompt treats Picture 1 as a composition source; that default is inappropriate for our environment-only inspiration unless changed or bypassed with raw_h3.
- [VRGameDevGirl two-pass workflow](https://github.com/vrgamegirl19/comfyui-vrgamedevgirl/blob/main/Workflows/MiniMaxH3_2Pass_LatentUpscale_Shareable.json): separate first sampler, learned latent upscale, and second sampler. It is a video workflow and is not proof of a validated one-frame preset.
- [Eros Max model card](https://huggingface.co/TenStrip/10Eros-Max): Beta 6 author reports 10/3 shift and 8-12 steps with several samplers; no universal single-frame optimum is specified. The prior 12/3, 16-step comparison did not match this Beta 6 range.

The running local installation does not register VRGDG_MiniMaxH3StillImage or VRGDG_MiniMaxH3LearnedLatentUpscale, although these exist upstream. Research snapshots are kept separately; no node installation or update was performed.

## Earlier workflow and supplied videos

`H3_Turbo_ErosMaxBeta6_2Pass_with_prev_v7.json` contains two active samplers: first pass 6 steps, then separate video/audio latents, learned video upscale, rejoin, second pass 3 steps at 0.2 denoise. Its upscaler target was connected to a 0.8 MP primitive. In the current large workflow those original video samplers/upscaler remain present but disabled; the new keyframe branch was separate and one-pass until this detail test.

The embedded executed prompt in `PlagueKind_JungleRave_comparison_00013_.mp4` contains one sampler and the hybrid FL2VA/Ref2VA checkpoint. Its final close-up demonstrates better lighting/identity than the moving medium shot, but is not evidence that this particular video used two-pass sampling. Motion blur and fewer face pixels also affect the medium shot.

## Reddit references, with limits

- [Behold: MiniMax-H3 Image Generation](https://www.reddit.com/r/comfyui/comments/1vfqdbx/behold_minimaxh3_image_generation/): older pseudo-image workflow generates a short sequence and extracts a decoded frame. The author's length/index 8/8 is experimental and must not be applied to Fizgig's one-frame path.
- [Consistent character sheets](https://www.reddit.com/r/comfyui/comments/1wxixua/minimax_h3_image_generation_create_consistent/): author reports 8 steps for speed versus 25 for quality at 4096x1536 with their Turbo-fused workflow. This is a different checkpoint/workflow and not a prescription for Eros Beta 6.
- [September 26 round-up](https://www.reddit.com/r/comfyui/comments/1wqwpah/a_quick_minimax_h3_news_roundup_26th_september/): firsthand Fizgig still test at 8 MP/30 steps with Kitchen Attention. Useful evidence that the method works; not a test of our two characters or lighting.
- [SelfLift and sharper latent upscale](https://www.reddit.com/r/comfyui/comments/1wz3s0q/minimax_h3_seamless_long_videos_no_color_shift/): video author reports improvements from a second stage, refined upscaler and reduced upscale ratio. It does not establish guaranteed face repair or a one-frame setting.

The remaining warm cast may reflect illumination from the character sheets, model preference, or both. The prompt now preserves identity/outfit and replaces reference illumination. The causes of facial softness and identity drift have not been isolated. Evaluate the detail comparison before adopting it across all three frames.

## Subsequent 4K comparison and accepted finding

The learned latent upscale and second sampler were tested at 4096x2304, then downsampled with Lanczos to 2048x1152. Both 0.10 and 0.20 denoise used res_multistep/simple, three steps, the same shared first-pass latent, seed and references. The render completed in 35.68 seconds with cached first-pass work. These are genuine latent refinement passes; the ImageScale nodes perform only the final downsample.

The user judged the before/after upscale a win for eye clarity and facial edges. The difference between the two denoise variants was much smaller. Those are distinct comparisons and should not be conflated. The PixaromaCompare node added by the user receives 0.10 in image1 and 0.20 in image2, both 2048x1152. The earlier MTB compare failed because it paired the 2048x1152 first pass with a 2560x1440 refinement.

The accepted refinement is backed up in `maintenance/approved-eros-4k-refinement-before-baseline.json`. The next single-frame quality-first baseline uses the original `minimax_h3_ref2va_pruned_int8_convrot.safetensors`, no Turbo, er_sde/simple, 50 steps, native 2560x1440, max reference sizing, seed 4102 and native H3 shift 12/3. This is a deliberate fidelity test; it changes the candidate generation configuration and is not a single-parameter causal experiment. Results must be reviewed before declaring the original model better.

## Original-model baseline accepted and second pass rendered

The original Ref2VA first pass completed in 147.17 seconds. The user explicitly judged its lighting, character appearances and Lune's proportions substantially better and matching the references. This establishes a preferred configuration for this tested shot, not a universal checkpoint ranking or an isolated explanation for the earlier artifacts. Executed workflow: `maintenance/accepted-original-baseline.json`; output: `D:/output/jungle_keyframes/quality_baseline_ref2va_50step_native_00001_.png`.

The second pass reused the exact cached first-pass latent, split video/audio, performed learned spatial latent upscale by 1.6 to 4096x2304, rejoined the original audio and sampled with er_sde/simple, 10 steps, denoise 0.10. It completed successfully in 57.95 seconds. Both before and after were returned with Lanczos to 2048x1152 for PixaromaCompare node 410: image1 is the first pass, image2 is the refined result. All 317 nodes were preserved; alternative tests remain disabled. The connected workflow was saved through the UI.

Outputs: `D:/output/jungle_keyframes/original_ref2va_firstpass_2k_00001_.png`, `original_ref2va_secondpass_2k_00001_.png` and `original_ref2va_secondpass_4k_00001_.png` in the same directory. Agent inspection found cleaner hair/fabric/skin detail with similar lighting and composition; user review of this second pass is still pending. Execution evidence: `maintenance/original-secondpass-ui-run.json` and `maintenance/original-secondpass-result.json`.

After this review, the user wants to continue in Music Video Vending Machine (MVVM), retrieve the existing song duration, timing map and loose story beats, and compose a plain one-shot-per-line candidate list for sequential overnight keyframe rendering. Discuss the shot list after finishing this quality test; do not queue a large batch before that discussion.
