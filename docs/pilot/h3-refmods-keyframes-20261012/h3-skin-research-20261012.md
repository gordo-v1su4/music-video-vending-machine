# H3 skin refinement: source notes and controlled tests

Research date: 2026-10-12. Scope: the supplied Reddit discussion, its latent-contrast implementation, RES4LYF sampler code, and the linked Larry/Silver weights. This note does not record a download, installation, workflow change, or completed render. The original reference-conditioned keyframe workflow remains the comparison baseline.

## Live baseline and scope

The render operator reports that the [original IR-099 PNG](D:/input/IR-099_00001_.png) embeds RAW Ref2VA, `er_sde/simple` at 50 steps in pass 1, a 2× latent upscale, and `er_sde/simple` at 10 steps / denoise 0.20 in pass 2. References are raw image inputs: environment 423, Rafa 388, and Lune 389 through reference node 365; seed is 4102. This is an operator observation of image metadata, not an upstream default or a new executed condition. In particular, the Reddit author's non-reference Turbo condition differs from this baseline.

A GET-only query of the active [ClownSamplerSelector_Beta catalog](http://127.0.0.1:8188/object_info/ClownSamplerSelector_Beta) during this research confirmed the exact selectable name **`exponential/res_2s_stable`**, alongside `exponential/res_2s` and `exponential/res_2s_rkmk2e`. The operator reports the installed Tr1dae pack lacks the latent-contrast node; upstream source availability does not establish installed availability.

The user's current scope is individual quick tests, **no batch**. They are also considering a short ordinary Ref2VA video and selecting frames instead of the Fizgig still wrapper. That is a separate route comparison: preserve the same identity/place inputs and report temporal sampling, frame selection, and runtime differences explicitly. This note does not establish which route is better.

## What the Reddit thread establishes

The author reports that reducing latent contrast before VAE decode improves perceived detail, with excessive reduction harming quality. Their example used LightX2V eight-step **non-reference** Turbo. Comments disagree about whether the change adds useful detail or mostly reduces contrast. Other commenters suggest Larry EMA600, Silver adapters, and `res_2s_stable`; those are community observations, not matched tests of our RefMod still route. The author also mentions Euler ancestral with `beta57`. None of these reports establish preserved likeness or younger-looking skin for our characters. [Supplied Reddit thread](https://www.reddit.com/r/StableDiffusion/comments/1wbt2ey/a_little_solution_for_the_plastic_skin_with/)

The supplied screenshots show two distinct conditions: contrast **0.90 / preserve_norm false** and **0.85 / preserve_norm true**. The illustrated placement is `SamplerCustomAdvanced.output → MiniMax H3 Latent Contrast → VAE Decode.samples`. These are observations of the supplied screenshots, not verified settings from our executed workflow.

## What latent contrast actually does

The node exposes a LATENT input, a contrast factor, and `preserve_norm`. It calls `contrast_nested_latent`; its description says video-only, leaving audio unchanged. A factor of 1 is the identity. [Node source](https://github.com/Tr1dae/ComfyUI-MiniMaxH3_LatentUpscaler/blob/main/nodes.py)

For each channel, the implementation computes its mean across the spatial/temporal dimensions, then applies:

```text
adjusted = mean + contrast × (source − mean)
```

Below 1 compresses deviations from the channel mean. With `preserve_norm=true`, it additionally rescales each token across the channel dimension back to its original vector magnitude. Therefore 0.85/true is not simply a stronger version of 0.90/false. The helper replaces only the video member of the latent container and retains other members and metadata. It performs tensor arithmetic, with no learned detail model or diffusion inference. It changes latent values; it is not merely a hint passed to the VAE. [Implementation](https://github.com/Tr1dae/ComfyUI-MiniMaxH3_LatentUpscaler/blob/main/utils.py)

**Inference:** VAE decoding of altered latent values can change visible texture and shading, but this operation cannot be credited with reconstructing missing skin information without measured evidence. It also acts globally on the video latent, so clothing, hair, scene contrast, and lighting require review alongside the face. It incurs arithmetic and another decode for an A/B; “no additional computational cost” is not literally zero cost. A cached sampler output can avoid resampling, provided the latent is retained and the upstream condition is unchanged.

## `res_2s_stable`: compare work, not just step labels

RES4LYF registers `res_2s_stable` as an exponential method. Its coefficient case has two stages (`ci=[0,1]`) and a two-row tableau. “2s” here describes stages, not two historical multistep evaluations. [Coefficient source](https://github.com/ClownsharkBatwing/RES4LYF/blob/main/beta/rk_coefficients_beta.py)

The sampler iterates stage rows and calls the model through its RK machinery. Terminal zero-sigma handling and optional controls can change the exact count; it exposes `model_call_counts`. Roughly half as many steps is therefore a useful initial **compute-budget hypothesis**, not equal convergence, equal images, or guaranteed half wall time. Different sigma spacing, CFG, preprocessing, decoding, cache behavior, and terminal handling all affect the comparison. Measure actual calls and elapsed time. [Sampler implementation](https://github.com/ClownsharkBatwing/RES4LYF/blob/main/beta/rk_sampler_beta.py)

The thread's claim that this sampler fixes plastic skin remains unverified for our reference-conditioned stills. A sampler change can alter the image even when the seed remains fixed; a shared seed controls the starting noise, not the integration trajectory. Test it separately from latent contrast and adapters.

## Adapter candidates and compatibility limits

Larry's current card recommends `minimax_h3_turbo_v4_step600_ema.safetensors`, strength **1.0**, `simple`, and **6–8 steps**; it cautions that more than eight can add sharpening artifacts. Its micro-detail and reduced plastic-look statements are the author's claims. The card documents T2V/I2V use and a dedicated Turbo sampler, including full/pruned-base support. It does not explicitly certify our Ref2VA RefMod still route. [Larry model card](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora)

The custom loader contains time-conditioning reinjection for pruned bases and accounts for visual reference/keyframe conditioning when constructing time rows. That provides implementation-level reference awareness, but it is not a creative-quality or exact-workflow compatibility guarantee. Verify the actual checkpoint type, mapped adapter keys, reference conditioning, and installed sampler behavior before comparison. [Larry custom-node source](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo/blob/main/__init__.py)

Silver's repository mixes FL2V, Ref2V, experimental, and merged diffusion-model artifacts. Its `ref2v_dareties` directory contains explicit Ref2V Turbo variants with `fro095` through `fro0995` suffixes. These suffixes are artifact names, not recommended user LoRA-strength settings. No model card was available at `README.md` during this check, and the listing does not identify one universally best variant. Select an exact Ref2V candidate rather than substituting an FL2V file or a merged diffusion model. [Silver repository](https://huggingface.co/silveroxides/MiniMax-H3_tests/tree/main), [Ref2V candidates](https://huggingface.co/silveroxides/MiniMax-H3_tests/tree/main/ref2v_dareties)

## H3 FaceRefine: newly prioritized face-detailer route

The second supplied thread links **Carasibana/ComfyUI-H3-FaceRefine**. Its demonstrated intervention is tracked face crops regenerated with H3 and stitched into the source video; commenters' timing and quality reports are anecdotes, not our benchmark. [Face-detailer Reddit thread](https://www.reddit.com/r/StableDiffusion/comments/1vn4uho/ok_this_is_cool_minimax_h3_face_detailer/)

The current published examples use **core `MiniMaxH3ReferenceToVideo`**, character and second raw image references, and a prompt. `H3InjectVideoLatent` replaces the generated zero video latent with VAE-encoded real face crops. NativeAudioLock and the per-frame denoise patch precede sampling, then VAE decode feeds stitch. The supplied template instructs operators to mirror the source clip's own model/sampler/LoRA/references rather than assume a shared preset. It is not a RefMod-loading example. [Auto Select example JSON](https://github.com/Carasibana/ComfyUI-H3-FaceRefine/blob/main/example_workflows/H3_Face_Refine_Auto_Select.json)

Important code distinctions:

- `identity_reference` selects/tracks the person; the tracker report explicitly says it anchors **tracking only**. It does not reinforce the face generated by H3. Wire the approved headshot separately into the Ref2VA generation conditioner.
- `H3FaceTrackCrop` accepts an IMAGE batch, detects boxes, smooths their trajectory/size, and makes constant-canvas crops. `H3InjectVideoLatent` VAE-encodes those crops into the video member while retaining the AV container.
- Frame count is aligned upward to H3's `17k+5` grid. A one-image batch is structurally plausible for crop/stitch but entails padded video refinement, with extra frames discarded. The reviewed examples are video pipelines; no drop-in single-frame Fizgig wrapper integration was established.
- Per-frame denoise requires its **MODEL output to reach the guider**, in addition to its LATENT output reaching the sampler. It changes model/noise-mask handling; wiring only the latent is incomplete.

[FaceRefine implementation](https://github.com/Carasibana/ComfyUI-H3-FaceRefine/blob/main/nodes.py)

The README currently recommends face-context crops around 2–3× face height, defaults a 768 canvas, and distinguishes face-only pasting from full-crop pasting. Wider context helps generation but should not become a rectangular pasted patch. SAM is optional; its input should be the **source crops**, not regenerated output. Templates require VideoHelperSuite, NativeAudioLock, and Impact Pack; GGUF and SAM are optional muted branches. The nodes need a face detector, with optional person segmentation fallback; Python requirements include ultralytics, scipy, insightface, and scenedetect. These are declared requirements, not confirmation of this installation. [FaceRefine README](https://github.com/Carasibana/ComfyUI-H3-FaceRefine)

**Minimal proposed test for our source:** keep the original 2048×1152 source untouched and test one character once. Prefer a short real Ref2VA clip for the published video route; a still-only adaptation needs explicit padding/length verification. Use the existing H3 model/VAEs and the approved character headshot in generation conditioning; inspect the selected face and crop preview before sampling. Start with the optional SAM and audio-specific additions only where the actual input requires them, with the dependencies and AV layout verified. Keep the original prompt/reference ordering and fixed seed. Crop at a restrained canvas, use a low-denoise schedule appropriate to the **actual H3 sigma shift**, stitch only the face, and expose source-vs-result A/B. Do not transplant Krea denoise settings or template Turbo weights by habit. First inspect identity, eyes, lips, folds, blend boundaries, and preserved surroundings; defer whole-frame upscale until this isolated face pass is assessed.

This is a separate refinement candidate from latent contrast. The author targets small faces in video; superiority for our already-large female face or the man's car shot remains untested. User scope stays one quick run at a time.

## Proposed test order

These are proposed experiments, not executed findings. Preserve the exact character/place references or RefMods, their ordering, prompts, seeds, dimensions, model, both sampling passes, and decode settings. Record filenames/hashes and actual prompt IDs; keep post-processing out of the initial comparison. This follows the project's requirement to preserve inputs, distinguish observations from hypotheses, and reconcile receipts before retries. [Production resume contract](../agent-production-resume.md)

1. **Decode-only contrast A/B:** decode one retained final sampled latent unchanged, at 0.90/false, and at 0.85/true. Compare at identical scale with explicit labels. This isolates the screenshot intervention without rerunning generation.
2. **Sampler A/B:** hold adapters and contrast fixed. Compare the current sampler against `res_2s_stable`, first near the same model-call budget, then increase only if needed. Preserve scheduler family and endpoints; record the changed sigma grid caused by the new step count.
3. **Adapter A/B:** test one exact compatible candidate at a time. Larry's documented Turbo sampler is a combined adapter/sampler condition; label it accordingly rather than pretending only the weights changed. Keep Turbo strength 1.0 as requested.
4. **Light post-process:** only after selecting the generation condition, compare the accepted frame against a restrained upscale/refinement. Judge identity, age, pores, freckles, folds, lips, eye shape/light, tears, color, and background at matching display size. Stronger texture alone is not acceptance.

Stop expanding the test matrix once the preferred condition is clear; retain the original image and settings alongside the chosen result. No source reviewed here proves these interventions will fix identity errors already present in the original keyframe.

## Latest decision: generation quality first

**This supersedes the proposed test order above.** The user now prioritizes the original generation quality with **Turbo off**, a **0.4 MP** run followed by **0.8 MP**, not 1 MP. Latent contrast at 0.90/0.85, SAM masks, and face fixes are deferred. Do not combine these interventions into the first comparison.

The operator has opened the official `video_minimax_h3_i2v` template. A read-only inspection of the [installed template JSON](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/python_embeded/Lib/site-packages/comfyui_workflow_templates_json/templates/video_minimax_h3_i2v.json) confirmed one `SamplerCustomAdvanced` (14), `KSamplerSelect` (17) set to **`res_multistep`**, and `BasicScheduler` (9) using **`simple` / denoise 1**. The RAW branch is `ComfySwitchNode` 123 false → `PrimitiveInt` 124 = **20 steps**; its Turbo branch exposes primitive 125. Model switch 122 false selects UNETLoader 6 (FL2VA), whereas true selects LoRA loader 121. The stored scheduler widget alone is not the effective step count because steps are wired. This template is a single-pass I2V route, distinct from IR-099's two-pass Ref2VA still route. The operator found no explicit shift node; do not infer an effective shift from that absence.

The reported visible UI condition is square **0.4 MP**, **5 seconds**, **Turbo false**. Its screenshot still showed unresolved input/model selections, so it is not yet a ready-to-run or completed condition. Preserve the intended input/identity and verify effective settings in the submitted receipt before drawing quality conclusions.

FaceRefine installation has since changed: the operator installed its dependencies, including scenedetect 0.7.2, and restarted through ComfyUI Manager. This research then independently confirmed **`H3FaceTrackCrop` is exposed in the active server catalog**. That establishes node availability, not a successful FaceRefine render or accepted output. [Live node catalog](http://127.0.0.1:8188/object_info/H3FaceTrackCrop)
