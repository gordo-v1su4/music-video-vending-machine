# H3 skin realism LoRA discovery — 2026-10-12

Scope: discover skin/photorealism LoRAs first, followed by documented settings and a proposed controlled test. No weights downloaded and no generations queued during this research. Creator claims and personal reports are distinguished below.

## Shortlist

| Candidate | Creator guidance | Reference / quantization evidence | Priority |
| --- | --- | --- | --- |
| [fal Realism People](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA) | Trigger `r34l1sm` at prompt start. Intended strength 1.0; lighter 0.6–0.8. File `h3-realism-people-t2v-i2v-r2v.safetensors`. | Creator card claims T2V, I2V and R2V support through shared attention projections. Author separately says it was made normally for FP16/FP8; pruned INT8 ConvRot reliability remains uncertain. | Retest already installed file at lower strengths, with corrected trigger. |
| [JonXL Photorealistic Image Generator](https://civitai.com/models/2884206?modelVersionId=3260165) | Trigger `ph0t0r34l`. Default strength 1.0; one-frame workflow 1.5. Two variants: step3780 and step3990; author says 3990 has more contrast/sharpness. | Creator describes reference support in default workflow; one-frame workflow has no reference support in this description. No explicit INT8 ConvRot guarantee. | Strongest new discovery for still-image testing; begin conservatively with step3780. |
| [TuTu_1018 Authentic cinematic texture](https://civitai.com/models/2890588?modelVersionId=3267949) | Trigger `DY`; strength 0.7, or 0.5 for high motion. File `Minimax H3真实电影质感.safetensors` (BF16 weights). | Creator claims improved skin, lighting, color depth and less plastic appearance. No declared FL2VA/Ref2VA training family, sampler, steps or quantized-checkpoint support. | Additional candidate; verify adapter keys/family before using local Ref2VA. |

The public Civitai API was retrieved directly on 2026-10-12 when web-rendered model pages failed: [JonXL model API](https://civitai.com/api/v1/models/2884206), [TuTu model API](https://civitai.com/api/v1/models/2890588). These provide creator descriptions, version/file identity and hashes. Discovery mirrors were used only to locate the original listings, then claims were checked against the APIs. In particular, one mirror says TuTu has no trigger, contradicting the creator's explicit `DY` instruction; use the creator's instruction.

JonXL's creator description compares default workflow strength 0.9 / CFG 1 with one-frame strength 1.5 / CFG 1.5; it recommends default workflow quality up to 2560×1440 and one-frame up to 3840×2176. The 40-step recommendation specifically concerns one-frame generation. These are separate workflow recipes, not settings proven transferable to our existing reference still graph. Exact sampler/scheduler are not exposed in the model description. The optional workflow package is `JXL_H3_TIR2V_V7G.zip`; inspecting it later would resolve that question. [Creator API](https://civitai.com/api/v1/models/2884206)

The People card identifies it as a successor to [fal's older Realism LoRA](https://huggingface.co/fal/MiniMax-H3-Realism-LoRA). That older public card was unavailable during this pass, so it is not treated as a verified separate test candidate. [People creator card](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA)

## Compatibility caveat from a primary author discussion

On August 12, Lovis Odin (`lovis93`, fal organization member and credited creator) said the People LoRA was normally made for FP16/FP8. On August 19 he said he would work on an updated version. Participants specifically reported glitches with `minimax_h3_ref2va_pruned_int8_convrot`, W4A8 and pruned models; some found 0.5 helpful while others did not. The discussion does not establish a shipped fix or controlled proof that every INT8 setup fails. The broad R2V support claim therefore should not be read as a guarantee for the local quantized checkpoint. [Author and user discussion](https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA/discussions/4)

## First-person Reddit reports

- A People test reports a useful strength range of 0.3–0.8; commenters report 0.4, and 0.33 with six turbo steps. The poster also reports artifacts and failures with particular quantized/reference configurations. These are anecdotes with incomplete reproducibility, not a universal preset. [Personal test](https://www.reddit.com/r/StableDiffusion/comments/1vpj4r8/minimaxh3realismpeoplelora_personal_test_video/)
- A user reports half strength for skin/lighting and `res_multistep` + `simple`; another reports 0.35–0.45. Full strength reportedly changes camera-facing behavior. [Realism People usage discussion](https://www.reddit.com/r/StableDiffusion/comments/1vpcgga/anyone_tried_the_realism_h3_lora_if_so_any_samples/)
- Other reports disagree about turbo stacking; some attribute plastic skin to turbo and prefer 20-step baseline generation. Resolution and initial reference quality are also reported variables. [Community realism discussion](https://www.reddit.com/r/StableDiffusion/comments/1vw7e5u/need_realism_loras_for_minimax_h3/)

Additional sampler leads supplied by the coordinating agent: an artifacts thread points to a `res2s_stable` / `beta57` / 24-step workflow, while a separate fast FL2VA comparison uses Euler/simple at 6–8 steps and strength 1.0. Neither demonstrates better skin while retaining this female's identity in our two-pass Ref2VA still workflow. Treat them as later experiments, not interchangeable recipes. [Artifacts discussion](https://www.reddit.com/r/StableDiffusion/comments/1vo855c/how_to_fix_artifacts_generated_by_h3/) · [Fast comparison](https://www.reddit.com/r/StableDiffusion/comments/1wmtora/)

## Proposed first controlled comparison — not run

User follow-up supplied [WarmBloodAban Singularity](https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity/tree/main). This is a full fine-tuned/fused checkpoint, with a separate LoRA also distributed; they are different test interventions. The primary card claims less oily skin, improved distant faces and Ref2V support. Its recommended `minimax_h3_ref2v_turbo_4step_v0.1` is an acceleration recipe, not controlled proof of the best skin quality or preservation of this character. No universal quality sampler recipe is documented. [Creator card](https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity)

The coordinating agent verified the local UNETLoader catalog contains `Minimax-h3_Singularity_ref2va_v1.3_Pruned_w4a8.safetensors`, while the LoRA catalog also contains `Minimax-h3_Singularity_128spect-fro95_lora.safetensors`. The creator's native repository also offers pruned INT8 (~21 GB), full INT8 (~34 GB), and pruned W4A8 (~11.8 GB) variants. Test the already installed checkpoint alone against the current model, holding references and sampling fixed, before stacking People. There is no evidence here that W4A8 necessarily loses identity; there is also no guaranteed identity preservation from the author's claims. [Files](https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity/tree/main)

The coordinating agent inspected the earlier local A/B: the no-LoRA output reproduced IR-099, but the 1.0 LoRA render changed framing/identity; the prompt lacked `r34l1sm`. This is local session evidence, separate from web research.

For the first test, keep seed 4102, exact reference images/order, prompt, dimensions, model, reference strength and current two-pass sampling fixed (`er_sde`/`simple`, 50-step base plus 10-step refinement at 0.20 denoise). Put `r34l1sm` in every arm, including strength 0, to isolate the weight change. Compare People strengths 0, 0.25, 0.4 and 0.6 before changing sampler, introducing another adapter, or changing references.

Inspect face shape, eyes, nose, mouth and hairstyle first, then cheek/forehead pores, fine hairs, skin gradients and halos in matching crops. A texture gain does not pass if her likeness regresses. If no strength preserves her, test an adapter only in the low-denoise refinement as a separate experiment; this is a hypothesis, not a demonstrated identity-preservation technique.

For JonXL or TuTu later, record file/hash and check model-family/tensor compatibility before loading. Keep each adapter's trigger identical in its own on/off pair. Do not compare different prompts or many simultaneous model/sampler/step changes and attribute the result solely to skin quality.

## Follow-up: dedicated postprocessing of IR-099

The user's latest requirement is to enhance the existing image's skin without changing the female's face. SeedVR2 and the NVIDIA upscaler are excluded by explicit user preference. These candidates operate on the saved original rather than resampling the H3 scene; none guarantees unchanged facial detail.

| Candidate | Evidence and purpose | Conservative test |
| --- | --- | --- |
| [4xFaceUpDAT / SharpDAT](https://github.com/Phhofm/models/releases/tag/4xFaceUpDAT_Series) | Philip Hofmann's face-specific DAT super-resolution model, trained on 10,000 FaceUp images. Standard/sharp variants target good input; L variants additionally denoise poor input. Non-diffusion processing, no text prompt. It refines/sharpens rather than supplying a dedicated pores-generation pipeline. | Standard model first as a fidelity baseline; inspect matching crops and resize the result back for a fair same-size comparison. The installed sharp variant is also testable, but may emphasize edges/artifacts. |
| [1x ITF SkinDiffDetail Lite v1](https://openmodeldb.info/models/1x-ITF-SkinDiffDetail-Lite-v1) | Author-attributed OpenModelDB description names `intheflesh#3116`, ESRGAN 1×, 19.2 MB: adds plausible high-frequency detail/removes slight blur. Originally designed for 3D character skin diffuse textures, with faces/eyes/hair in its dataset; may amplify compression artifacts. Despite the name, this is not a diffusion model. Original author page not independently recovered. | Strongest specifically skin-oriented discovery for same-resolution texture-only testing. Start one pass on clean PNG; inspect skin and consider blending only cheeks/forehead while preserving eyes, lips and face silhouette. Mask/blend is our test proposal, not a creator recipe. |
| [SUPIR](https://github.com/Fanghua-Yu/SUPIR) | Primary restoration project uses diffusion with SDXL. `v0F` targets light degradation/high fidelity, `v0Q` generalizes more broadly. Official fidelity parameters: stage2=1.0, CFG4/startCFG1, noise1.01; default50 EDM steps. Author explicitly contrasts fidelity with quality-oriented settings. | Later generative-detail option if deterministic passes are inadequate. May invent/change details, so it must pass identity review and should be tested separately. |

Credible Civitai SUPIR workflow IDs were verified directly: [524740](https://civitai.com/models/524740) (`Aschente723`, version583009) is a straightforward standalone restoration workflow; creator prefers HelloWorldXLv7 plus 4xRealWebPhotoDAT2 or UltraSharp. [364115](https://civitai.com/models/364115) (`denrakeiw`, versions413897/406878) is SUPIR with automated captioning via Moondream/WD14. These are workflow packages, not distinct skin-trained SUPIR weights. [Primary API524740](https://civitai.com/api/v1/models/524740) · [Primary API364115](https://civitai.com/api/v1/models/364115)

An optional masked low-denoise Krea2 pass remains a generative experiment rather than a dedicated skin upscaler, with no guaranteed identity protection. The current next step is the coordinating agent's installed FaceUpDAT comparison, not a large stack of interventions. This research agent downloaded no models and rendered nothing. ITF catalog lists CC-BY-NC-SA-4.0 and SUPIR's primary project states noncommercial usage restrictions; record these before adopting either for production deliverables.

## Authorized recipe test — executed after discovery

The user subsequently requested Singularity + EMA-600 at 1.0 + People at 1.0, eight steps. This superseded the proposed research-first hold for that specific test.

- Browser Run submitted prompt `a753b3ad-2474-454f-9cf1-ebc83b3769c2`; ComfyUI history reports success in 29.56 seconds.
- Checkpoint: `Minimax-h3_Singularity_ref2va_v1.3_Pruned_w4a8.safetensors`.
- Stack: `MiniMaxH3TurboLoRA`, `mini/minimax_h3_turbo_v4_step600_ema.safetensors`, strength 1.0, low_vram false; then `LoraLoaderModelOnly`, `mini/h3-realism-people-t2v-i2v-r2v.safetensors`, strength 1.0.
- Sampling: installed `MiniMaxH3TurboSampler`, simple, eight steps, denoise 1.0, shifts 12/3; one pass at 2560×1440, resized to 2048×1152. No latent-upscale/refinement in this recipe test.
- Seed 4102; original IR-099 close-up prompt and reference order retained, prefixed with the documented `r34l1sm` trigger. Same raw courtyard/Rafa/Lune images, no RefMods.
- Author guidance for EMA-600 recommends six to eight steps, strength 1.0, simple scheduler, custom Turbo LoRA and Turbo Sampler nodes. [EMA-600 creator card](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora)
- Output: `D:/output/mvvm/i-ran-20261012/singularity-ema600-people-099/IR-099_Singularity_EMA600_People1_8steps_00001_.png`; exact history and API graph are in the same folder. Saved viewer workflow: `D:/user/default/workflows/IR-099_Singularity_EMA600_People_8steps.json`.
- Visual observation: more apparent cheek/forehead texture, but framing and facial appearance changed. This combined intervention cannot isolate the checkpoint, adapter, sampler, trigger, or single-pass effects; preserving Lune likeness is not accepted or proven.
