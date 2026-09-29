# Qwen Image 2.1 edit: prompt formulas and workflow techniques (research, 2026-09-28)

Web research only. Nothing here has been run on our stack yet. Our locked call is described in
`docs/qwen-image-edit.md` (2.1 bf16, 40 steps, euler/simple, cfg 1, PE on, scene = `<image1>` at 1344x768). Treat
every item below as a candidate A/B test against that baseline. Do not change the locked call without the user.

Credibility tags:

- **verified-official**: Qwen, Comfy-Org or diffusers docs, model cards or code.
- **multiple-users**: the same claim from two or more independent community sources.
- **single-report**: one blog, post, workflow or LoRA author.
- **unverified**: my inference from the sources. Nobody reported testing it.

2.1-specific community material is thin: the model is 8 days old. Much of the list below comes from 2509/2511 and
says so.

---

## Try first for our cases

Common to all five cases:

- **A. Restore the panel before inserting anyone.** The edit model copies the quality of `<image1>` and only redraws
  what it is told to change.
  - Two sources: the PE rule "only what was asked" (verified-official), and 2511 users reporting that the model is
    "very sensitive to the quality of your input image" (single-report).
  - That is why our output has a sharp new face on a soft upscaled frame.
  - Pass 0: send only the panel, with no tags, and prompt "Keep colors exactly the same, upscale the image"
    (NextDiffusion 2.1 upscaler prompt). Then insert the character into the restored panel.
- **B. A/B test guidance.** cfg 1 against cfg 2.5–3.5 with a short negative prompt, for example "yellow tint,
  washed-out colors, extra limbs, extra fingers, duplicate person".
  - Several 2.1 users say the default cfg 1 causes the yellow cast, grain and anatomy slips, and that cfg around 3
    plus a negative prompt fixes them. Cost: about 2x time.
  - The negative prompt does nothing at cfg 1.
  - Tag: multiple-users.
- **C. Name defects to fix and occluders to keep, by position.** The official enhancer does not fix unmentioned
  defects, and it keeps untargeted content "by type, position and role" (verified-official). Extra limbs and
  bubbles both have to be stated.
- **D. One character per pass for two-person shots.** Composite the passes. Two-character edits cross-talk:
  expressions and identity bleed between people (single-report, lilting.ch; see §4).

Per case:

1. **Underwater face, bubbles in front.**
   - Run pass 0 first.
   - Prompt: "Replace the woman in `<image1>` with Lune from `<image2>`. The bubbles in the foreground stay in front
     of her face and body. Match the underwater light and grade of `<image1>`."
   - If the bubbles still vanish, composite the original bubble layer back over the result (luma or difference mask).
     This is safe because a 2.1 edit at matched resolution is aligned to about 0.1 px (single-report, measured; §3).
   - Fallback: a 2.1 separate-mask edit, where the mask covers the skin but leaves out the bubbles (§1d; unverified
     in ComfyUI).
2. **Person falling through mist.**
   - Chain the edits: (1) "Remove all the people from the image, leaving only the mist" (already in our doc).
     (2) Insert the character.
   - Say "mist drifts in front of and around her" and "motion blur on her limbs".
   - Add one relight clause: "match the lighting and colour grade of `<image1>`".
3. **Two people on a breaking bridge.**
   - Pass 1 (cleanup): "Remove the extra arm on the left figure and the duplicated figure behind her". Name each
     defect.
   - Pass 2: insert character A.
   - Pass 3: insert character B, with the pass 2 output as `<image1>`.
   - Crop each reference to one clean face or body on a plain background. Give each reference an exclusive role:
     "use `<image3>` only for his face" (single-report, HF forum; §4).
4. **Two hands reaching.**
   - Hands are too small at 1344x768.
   - Crop and stitch the hands region: crop, upscale to about 1 MP, edit, and stitch back.
   - Prompt with count, contact and view, not "fix the hands": "left hand, five fingers, index finger extended
     toward the other hand, back of the hand toward camera".
   - Or draw a red circle on the panel: "fix the hand in the red circle … remove the red circle" (2.1 official circle
     editing; §1h).
5. **Two faces kissing in water.**
   - One face per pass, each head cropped and stitched at higher resolution.
   - Name "the water surface and droplets in front of their faces" as kept.
   - Composite back. Face-check each pass.

---

## 1. Prompt formulas

### (a) Replace a whole person, full-body re-render

- **Official 2.1 edit template shape**:
  - Keep X from `<image1>`, put Y from `<image2>` on the character, preserve face, hair, body shape and pose.
  - The template's example is a clothing transfer. For a person transfer, flip it: keep the scene and pose of
    `<image1>`, and take the identity from `<image2>`.
  - Source: <https://raw.githubusercontent.com/Comfy-Org/docs/9d133794aad002b82e8336dacf5b896be55676d3/tutorials/image/qwen/qwen-image-2-1.mdx>
    (verified-official).
- **Canvas rules** from the PE-I2I system prompt (`system_prompt.txt`):
  - Compositing, meaning a subject moved into a scene: the canvas is the target scene.
  - Face or head swap: the canvas is the **body** image.
  - `ratio_follow` is set to the canvas tag.
  - This confirms our order: scene `<image1>`, refs after.
  - Source: <https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I/commit/72927bc08afc99b7888ceb7d7d51a12db3700bbd>
    (verified-official).
- **2509/2511 community "person swap" formulas:**
  - "replace character in image1 with character in image2". This is the trigger phrase of a 2511 manga
    character-change LoRA:
    <https://civitai.com/models/2290840/qwen-image-edit-2511-monochrome-charachange> (single-report).
  - "Make the character from image2 to be in the scene of image1 at the exact pose and position of image3", where
    image3 is an OpenPose skeleton. It worked in 2509 and broke in 2511. This is the closest formula to our storyboard
    use: <https://huggingface.co/Qwen/Qwen-Image-Edit-2511/discussions/23> (single-report; regression unconfirmed by
    Qwen).
  - Role-declaration style: "Role A is the person. Role B is the outfit reference. Keep from A the face, hair …".
    <https://aistudynow.com/qwen-image-edit-2509-in-comfyui-3-image-compose-q5-gguf/> (single-report).
- **Known failure (2511):** a benchmark judge found that "use Image 1 as pose, Image 2 as character" layered both
  people instead of replacing one. <https://lumenfall.ai/arena/compare/flux.2-dev-turbo/qwen-image-edit-2511>
  (single-report).
  - Mitigation, if 2.1 does the same: chain the edits. Remove the source person first, then insert (unverified for
    2.1; our p23 chain is the same idea).

### (b) Face-only or head swap

- **BFS "Best Face Swap" LoRA prompts** (2509/2511, not 2.1). The V5 head-swap base prompt:
  - Take Picture 1 as the base, keeping its lighting, environment and background.
  - Remove the head completely and replace it with the head from Picture 2.
  - Preserve Picture 2's hair, eye colour and nose.
  - Copy the eye direction, head rotation and micro-expressions from Picture 1.
  - Input order: body first, then face.
  - The Face V1 variant adds: "swap only the face (not the hair), match the skin tone … keep … pose and lighting".
  - <https://huggingface.co/Alissonerdx/BFS-Best-Face-Swap/blob/d30573013a503436962bd0a2b07a171bb14a7c8d/README.md>
    (single-report, widely used on Civitai, so close to multiple-users).
  - The author also warns that Lightning LoRAs give "plastic-like skin" (not our problem).
- **"Change Head and Face" LoRA (2509)**:
  - Face-only template: replace the face with the one in Figure 2, keep Figure 1's hairstyle and colour, then a
    closing "check that the final face is Figure 2's" sentence.
  - The author says the Chinese prompt works best (it is the training prompt) and recommends 20 steps, CFG 2.5, no
    Lightning.
  - **Head-size fix:** the FAQ says the swapped head grows. The fix is to inpaint with a mask drawn along the
    *original* head outline.
  - <https://huggingface.co/Sentinel7/qwen-image/commit/f93d7ae03413cebd1dc7bab3f58aaeabf13ffd01> (single-report).
- **Seamless Head Swap Master (2511)**:
  - The prompt spells out head size, face-to-body ratio, neck thickness, gaze, shadow contact and sharpness
    consistency.
  - Structure: InpaintCrop → edit → InpaintStitch.
  - <https://civarchive.com/models/2612581?modelVersionId=2933471> (single-report).
- **2.1 rule:** point identity at the reference and don't describe the face in words. Already in our doc; it
  matches the YOLO LAB guide <https://yololab.net/archives/qwen-image-2-1-prompt-guide> (single-report, consistent
  with the PE rules).

### (c) Subject into a scene with matched lighting and grade

- **2509 multi-reference**: "lighting adjusted to blend naturally" at the end of a compose prompt.
  <https://wiki.monai.art/en/tutorials/qwen-reference-images> (single-report).
- **2511 has a built-in relight LoRA**: start the prompt with "Relight", then describe the light.
  <https://myaiforce.com/qwen-image-edit-2511-relighting/> (single-report; Qwen's 2511 card confirms the built-in
  lighting LoRA, verified-official).
- **Light-Migration LoRA (2509)**: "Refer to the color tone, remove the original lighting from Image 1, and relight
  Image 1 based on … Image 2".
  <https://github.com/PRITHIVSAKTHIUR/Qwen-Image-Edit-2511-LoRAs-Fast-Lazy-Load/blob/main/app.py> (single-report).
- **2.1 PE rule:** relight and blend adjustments apply only to the targeted subject; the environment stays.
  - So "match the lighting and colour grade of `<image1>`" is the right direction: a subject-to-scene match.
  - (verified-official, system_prompt.txt)
- **Composite-then-harmonise (2509 Fusion LoRA)**:
  - Paste the subject manually, mask the subject and shadow area, then let the model re-light only the mask.
  - It keeps the plate untouched.
  - <https://github.com/rik-python/QWEN-AI-Compositing> (single-report).
- **Role restriction for a lighting ref**: "use `<imageN>` only for lighting, colour temperature and contrast; do
  not transfer its subjects". YOLO LAB (single-report).

### (d) Keep foreground occluders (water, bubbles, hair, smoke) in front

No source addresses this directly. The best-supported pieces:

- **Name what stays by type, position and role, without redescribing it.**
  - This is the PE-I2I "say what stays, without repainting it" rule (verified-official).
  - Formula (unverified): "… keep the bubbles in the foreground in front of her face and body".
  - Our current prompt already does this, and the enhancer still dropped them sometimes.
- **Alignment makes compositing possible.**
  - At matched resolution, 2.1 edits hold position to about 0.1 px. The prompt's keep clause made about 0%
    difference; grid alignment was what held the untouched regions.
  - So a post-composite of the original occluders is viable.
  - <https://lilting.ch/en/articles/qwen-image-2-1-edit-pixel-perfect-output-resolution> (single-report, measured).
- **2.1 separate-mask editing.**
  - The original image and a separate black/white mask go in as two inputs, and the model edits only the mask
    region.
  - <https://www.alibabacloud.com/blog/603586> (verified-official capability).
  - A hosted API documents the same: white = change, exactly one reference image.
    <https://muapi.ai/playground/qwen2-1-image-to-image> (single-report).
  - In ComfyUI this would be the mask as an extra `image_N` slot plus a prompt naming it. Nobody has published it.
    Our earlier failed masks were masked inpaint and partial denoise, which is a different mechanism (unverified).
- **Layer route**: Qwen-Image-Layered decomposes a frame into RGBA layers in occlusion order, so only the subject
  layer is edited. <https://github.com/QwenLM/Qwen-Image-Layered> (verified-official; separate model, heavy).

### (e) Remove people or extra limbs for a clean plate

- **Formula (deAPI):**
  - "Remove the person in the blue shirt standing in the middle of the frame."
  - "Fill the empty area with matching sand, waves and sky."
  - Then preserve lighting, shadows and composition.
  - The rule is to name the exposed region. The PE rule says the same: removals must describe the newly exposed
    area (verified-official).
  - <https://deapi.ai/blog/qwen-image-edit-plus-prompting-guide-how-to-write-edit-instructions-that-actually-work>
    (single-report + official rule).
- **Identify the target by position or clothing** ("the second person from the left"). Same source.
- **Extra limbs are "unmentioned defects"** that the PE deliberately does not fix. Name them: "remove the extra left
  arm of the woman on the right" (verified-official rule; formula unverified).
- **Circle-guided removal (2.1 official example):** "Remove the metal watch in the blue circle, …". Multiple
  circled regions can be fixed in one call.
  <https://github.com/QwenLM/Qwen-Image-2.1> (verified-official).

### (f) Upscale or restore a low-res image, keeping composition

- **2.1 upscaler prompt**: "Keep colors exactly the same, upscale the image". Uses `TextEncodeQwenImage21` with the
  upscale factor on the canvas.
  <https://www.nextdiffusion.ai/tutorials/how-to-upscale-images-with-qwen-image-2.1-in-comfyui> (single-report).
- **2.1 2K upscale workflow**:
  - Canvas at about 4.2 MP (16:9 comes out near 2730x1536), with a generic enhance prompt.
  - The author warns that the longer "rich fine details" prompt adds grain and artifacts on some images.
  - <https://civitai.com/models/2952715/qwen-21-2k-upscale-workflow> (single-report).
- **2511 restore prompt (Andrew Zhu)**:
  - "Restore and upscale this image", remove noise, blur and JPEG artifacts, "No content changes".
  - The long negative prompt includes "plastic skin", "color shift" and "different person".
  - The source goes through a VAE-encoded reference latent.
  - <https://xhinker.medium.com/qwen-image-edit-2511-is-the-best-image-upscaler-in-jan-2026-bbeb8f24f490>
    (single-report).
- **Community verdict:** 2.1 is strong at upscaling and restoration once cfg is raised to about 3.5 (r/StableDiffusion
  "Qwen Image 2.1 Not Bad",
  <https://reddit.sentinel-team.org/posts/1wnr5u8/snapshots/2026-09-25T23%3A30%3A13.377351Z>). An HF tester said
  "works quite well as an upscaler" (<https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/27>). Tag:
  multiple-users.
- **Official Qwen hosted template** for old photos: "Restore the old photo, remove scratches, reduce noise, enhance
  details …". <https://docs.qwencloud.com/developer-guides/image-generation/image-editing> (verified-official, hosted
  model).

### (g) Pose-preserving swaps (skeleton or pose control)

- **2509 accepted keypoint maps natively** as an extra image ("Native Support for ControlNet").
  <https://github.com/qwenlm/qwen-image/blob/main/Qwen-Image-Edit-2509.md> (verified-official).
  - Formula: "The girl in image1 changes her pose to image3. she is standing on the rock in image2".
    <https://www.kombitz.com/2025/10/03/how-to-use-controlnet-with-qwen-image-edit-2509-in-comfyui/> (single-report).
- **2511 lost this**, per <https://huggingface.co/Qwen/Qwen-Image-Edit-2511/discussions/23> (single-report,
  unanswered). **2.1 has no documented skeleton-as-reference support** (unverified either way; worth one test).
- **Three-image pose method (2511)**:
  - Inputs: `<image1>` identity, `<image2>` a *cleaned* photo pose reference, `<image3>` its DWPose skeleton.
  - Prompt: "copy the pose using Image 2 and Image 3".
  - Clean `<image2>` first: mask its head, remove the background and stray objects, so its identity doesn't leak.
  - Finish with FaceDetailer.
  - <https://myaiforce.com/qwen-image-edit-pose-transfer/> (single-report).
- **Qwen-Image-2.1-Fun-Controlnet-Union** (alibaba-pai):
  - Supports Pose (DWPose), Depth and Canny, plus inpainting with a mask in one branch, and control plus mask
    together.
  - It targets the 2.1 T2I and inpaint path through VideoX-Fun scripts; ComfyUI support is unclear.
  - It could redraw a masked person to a skeleton, but not with a reference identity.
  - <https://huggingface.co/alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union> (verified-official for alibaba-pai;
    untested).
- **Two-stage pose-to-photoreal**: Qwen-Edit 2511 on a DWPose skeleton, then Krea 2 Turbo img2img at about 0.42
  denoise. <https://huggingface.co/JahJedi/Qwen-Edit-Krea2-Turbo-Workflow> (single-report).

### (h) Fixing hands

- **Circle or box the region**, then "fix the hand inside the …, remove the marking". This is the 2.1 circle mechanism
  (verified-official). The SpicyAPI test found the edit stayed inside the mark and asked for the mark to be removed
  in the same prompt. <https://spicyapi.ai/blog/qwen-image-2-1-api-guide> (single-report).
  - Kontext-era equivalent trigger: "Remove the green block. Fix the hand inside the green block." (LiblibAI hand-fix
    LoRA for Flux Kontext; single-report, different model).
- **Describe pose geometry, not "fix the hand"**:
  - State the finger count, contact points and camera view of the hand.
  - Crop in so the hand fills the frame, then composite back.
  - <https://www.versely.studio/blog/fixing-hands-without-regenerating-the-image> (single-report, model-agnostic).
- **cfg > 1 with a hands negative** ("missing fingers, badly drawn hands, wrong number of fingers") is part of the
  2.1 Fix workflow. <https://comfyui-wiki.com/en/news/2026-09-23-qwen-image-2-1-fix> (single-report; the LoRA itself
  is disputed).

---

## 2. Tagging, image order, canvas, prompt length

| Rule | Detail | Source | Tag |
|---|---|---|---|
| 2.1 tag syntax | Use `<image1>`, `<image2>`. PE output **must** use tags when N≥2, never "the first image". With one image, use no tags ("the image"). | PE-I2I system_prompt.txt (link in §1a) | verified-official |
| 2509/2511 syntax | "image 1" / "Picture 1" / "Figure 1". Hosted docs allow "[image 1]". The 2511 encoder's internal template labels images "Picture N"; BFS prompts use that. | <https://www.modellix.ai/blog/qwen-image-edit-prompt-guide/>, BFS README | multiple-users |
| Order = slot order | Refs are spliced into the encoder in slot order; attention reads them sequentially. | Comfy 2.1 doc; <https://www.qwe.edu.pl/tutorial/qwen-image-2-1-compact-unified-tutorial/> | verified-official |
| Canvas = first image (ComfyUI 2.1) | Output follows `<image1>`'s aspect at about `resolution`². Set `resolution` 0 to keep native sizes. `custom_size` far from the resized ref shifts the edit. | Comfy 2.1 doc | verified-official |
| Canvas = last image (hosted 2.0 API, vLLM) | Hosted Qwen API and vLLM derive output size from the *last* image. Don't port prompts or order blindly. | <https://recipes.vllm.ai/Qwen/Qwen-Image-2.1>, Alibaba API doc | verified-official |
| Exact-fit resolution | Set `resolution` = round(√(w·h)) with w and h multiples of 32, so the ref isn't stretched. That cut drift from about 7 px at the edges to about 0.1 px. At 1344x768, the default 1024 already maps exactly: we're fine. | lilting.ch 2.1 article | single-report (measured) |
| Node renumbering gotcha | In the T8 PE node, empty ports are skipped and later images renumber, so `<image1>` may be your `image_9`. | <https://comfy.icu/node/QwenPERewriteT8> | single-report |
| Ref count | 2.1 supports 10, but identity is strongest with 1–4 refs; more refs blend secondary details. 2509 optimum is 1–3. | Qwen 2509 card; <https://saascity.io/blog/qwen-image-2-1-local-text-to-image-editing-guide>; SpicyAPI | multiple-users |
| Prompt length | Official edit examples are one short sentence. The PE writes one paragraph without line breaks. Hosted limits are 800 tokens (edit-plus) and 1,300 tokens (2.0). One HF tester found long prompts "slightly better", so opinions are mixed. Our measurement favoured short prompts plus PE. | PE system prompt; Alibaba API doc; HF discussion 27 | mixed |
| One action per call | Split multi-attribute edits. Warning: every re-edit degrades the image a little (issue #88; our chains should stay at 2–3 steps). | <https://github.com/QwenLM/Qwen-Image/issues/88> | multiple-users |
| Aspect words | Never put a ratio or "4K" in the edit prompt; the PE strips them. | PE system prompt | verified-official |

---

## 3. Sampler and settings for 2.1 edit (full bf16, no turbo)

| Setting | Reported | Source | Tag |
|---|---|---|---|
| Steps / cfg | Diffusers reference: 40 steps, `true_cfg_scale` 1.0, no negative. Comfy templates ship 25 / cfg 1 / euler / simple. | Qwen-Image-2.1 README; Comfy doc; vLLM recipe | verified-official |
| cfg > 1 | CFG about 3–3.5 plus a negative prompt fixes the yellow cast, extra limbs and finger distortion, and "improves … editing". It doubles time. cfg > 1 only engages with a negative prompt. | r/StableDiffusion "Not Bad" thread; HF Comfy-Org discussion 10; vLLM recipe | multiple-users |
| Shift | One user runs ModelSamplingAuraFlow shift about 16 with RES4LYF abnorsett_3m / beta_57 / 30 steps / 2.5 MP (t2i). A reply says higher shift cuts hallucinations; the official scheduler uses dynamic shifting. | same thread | single-report |
| "Fix" workflow | Settings: 20 steps, cfg 3, seeds_2 / sgm_uniform, APG + FreSca guidance nodes. Negative: "artifacts, gpt-image, washed-out colors, … missing fingers, badly drawn hands, wrong number of fingers". Commenters doubt whether the LoRA or the cfg does the work. | <https://comfyui-wiki.com/en/news/2026-09-23-qwen-image-2-1-fix> | single-report |
| Yellow tint | Fix with a post white-balance node (ComfyUI-Bleachery), or cfg plus a negative ("yellow tint, warm cast"). | HF Comfy-Org/Qwen-Image-2.1 discussion 10; saascity guide | multiple-users |
| Resolution | 2.1 is native 2K: 16:9 is 2752x1536. Our 1344x768 is about 1 MP. Editing at about 2 MP then downscaling is untested for us. 2511 users note gen time grows non-linearly above 2–3 MP. | Qwen README; Civitai 2659067 | verified-official / single-report |
| Denoise < 1 | Only meaningful when the latent is a VAE encode of the source; with an empty latent it gives flat mush. RunComfy's 2.1 workflow suggests "reference latent + lower denoise" for tighter structure. Our own test of partial denoise failed. | comfyui-mcp skill doc; RunComfy 2.1 multi-image workflow | single-report |
| Double reference | 2511: feeding the input image twice improves adherence and clarity for single-image edits at about +50% time. Untested on 2.1. | <https://civitai.com/models/2659067> | single-report |
| KV cache / TaylorSeer | Barely changes output (about 0.1% diff) and cuts time about 2.5x. | lilting.ch | single-report |

---

## 4. Failure modes and fixes

| Failure | Cause / fix | Source | Tag |
|---|---|---|---|
| Rest of frame stays low-res | The model preserves untargeted content at input fidelity and copies input grain or blur. Fix: restore-upscale pass first, as a separate call. | PE rules; Civitai 2659067 | verified-official + single-report |
| Zoom / crop / face-size shift | The reference latent grid ≠ the output grid. Fix: match `resolution` to the source; in 2511, use the VAE Encode → ReferenceLatent path or LockPixel padding. | lilting.ch (2511 and 2.1); <https://github.com/tori29umai0123/ComfyUI-QwenImageEdit-LockPixel>; <https://myaiforce.com/fix-pixel-drift-for-qwen-edit/> | multiple-users |
| Head grows in swaps | Mask along the original head outline, or crop-and-stitch the head region. The prompt should name head size and face-to-body ratio. | Change-Head LoRA FAQ; Seamless Head Swap Master | single-report |
| "Pasted" face, wrong scale or colour | A 2.1 tester saw pasted-looking inserts and mismatched scale and colour, and found pose and angle changes hard. Multi-view character refs duplicated the character; a single ref pulled the output toward its angle and light. | <https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/27> | single-report |
| Identity drift with several refs | Crop refs to face and shoulders, remove busy backgrounds, and lightly denoise or de-sharpen synthetic refs. Give each ref an exclusive role ("use Picture 3 only for …; do not use it to change the face"). Stage it: composition first, then an identity pass with the face ref only. | <https://discuss.huggingface.co/t/multi-image-edit-3-refs-artifacts-at-true-cfg-fine-on-lightning-reference-content-dependent/175726> | single-report (detailed) |
| Features copied from refs (freckles, outfit, background) | Refs leak through the VAE/reference-latent path. Fix: role clauses, cropping, and never naming the unwanted feature (our "no freckles" finding). Pose refs: mask the head and remove the background first. | HF forum; MyAIForce pose article; our doc | multiple-users |
| Two-character cross-talk | Expressions or identity pulled between characters in one pass. Process one character at a time and composite. Prompt aid: "preserve each person's identity independently; do not merge facial features". | lilting.ch 2511 article; YOLO LAB | single-report |
| Plastic skin | Mostly blamed on Lightning LoRAs (not us). For 2.1, the grain and "GPT-soft" look is reduced by higher cfg plus a negative. The restore prompt negative includes "plastic skin, over-smooth, waxy". | BFS README; qwe.edu.pl; Andrew Zhu | multiple-users |
| Colour shift / yellow cast | See §3. Also post-white-balance, or grade-match to the original panel. | HF discussion 10 | multiple-users |
| Diamond grid / halftone | Caused by the Qwen VAE (a plain VAE round-trip reproduces it). Fix: downscale about 0.75x, then upscale (SeedVR2 or a DAT model), or apply a moiré-workaround node. | <https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/12>; Civitai 2659067 | multiple-users |
| Grids or text leaking from sheets | Multi-view sheets make the character duplicate; turnaround LoRAs output narrow characters. Fix: crop single views and remove labels (unverified for label text specifically). | HF discussion 27; tarn59 turnaround LoRA card | single-report |
| Edits land on the wrong subject | The mapping is implicit. Use "the X in image 1", "the Y from image 2", or position words. | Modellix guide | single-report |

---

## 5. Published workflows for character replacement in frames

| Workflow | Model | What it does differently | Tag |
|---|---|---|---|
| Comfy official "Qwen Image 2.1 Image Edit" template | 2.1 | Baseline: two refs, 25 steps, cfg 1, cache node, first image sets the canvas. <https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_image_edit.json> | verified-official |
| RunComfy "Qwen Image 2.1 Edit" | 2.1 | Marketed for "character storyboards". Uses the encoder's init latent anchored on the base image. Prompt pattern: base scene + role per tag + "no extra objects". <https://www.runcomfy.com/comfyui-workflows/qwen-image-2-1-edit-in-comfyui-reference-guided-editing> | single-report |
| RunComfy "Multi-image Editing" (PE) | 2.1 | PE-I2I rewrites first. A switch picks an empty latent (free layout) or the reference latent plus lower denoise (locked layout). Negative "no duplicates, no collage". <https://www.runcomfy.com/comfyui-workflows/qwen-image-2-1-multi-image-editing> | single-report |
| Seamless Head Swap Master | 2511 | Inpaint crop/stitch around the head, ReferenceLatent, BiRefNet subject mask, comparison output. Prompt spells out head size, neck and shadow contact. <https://civarchive.com/models/2612581?modelVersionId=2933471> | single-report |
| Swap Anything (SAM3.1) | 2509/2511 | SAM3 text-prompted mask ("woman's head") with crop-and-stitch, so only the masked part changes. Separate "person swap" mode. <https://civitai.com/models/2287824> | single-report |
| Segment Inpaint / swap / local edit | 2511 | Crop-and-stitch for huge frames, so edits keep the source quality outside the region. <https://civitai.com/models/2257259> | single-report |
| Face Swap SX CU | 2511 + BFS | For cinematic frames: it keeps expression and head angle plus dirt and water on the face. Gemma writes the prompt; couple mode swaps two faces with two refs. <https://civarchive.com/models/2780755?modelVersionId=3131767> | single-report |
| Pose transfer (3-image + DWPose) | 2511 | Cleaned pose ref + skeleton + FaceDetailer finish. <https://myaiforce.com/qwen-image-edit-pose-transfer/> | single-report |
| Qwen-Edit → Krea 2 Turbo | 2511 | Qwen gets the pose right; Krea img2img at about 0.42 denoise adds photoreal detail. <https://huggingface.co/JahJedi/Qwen-Edit-Krea2-Turbo-Workflow> | single-report |
| Qwen 2.1 2K Upscale | 2.1 | Pure restore/upscale pass at about 4.2 MP; a candidate for our "pass 0". <https://civitai.com/models/2952715> | single-report |

The recurring differences from our call:

1. **Crop and stitch.** The edited region is cropped and upscaled to about 1 MP, so faces and hands get real pixels.
   Then it is stitched back, which keeps everything else pixel-identical.
2. **Explicit masks, or a SAM segment.**
3. **Pre-cleaned references.** Cropped, background removed, head masked on pose refs.
4. **Two-stage finish.** A detailer or a low-denoise refiner, not one pass.

We rejected masked inpaint and partial denoise. That is not the same as crop-and-stitch at full denoise with the
unmasked crop as `<image1>`, which is untested for us.

---

Sources not reachable or not found: Benji's AI Playground has 2509/2511 Patreon posts (multi-angle, relight LoRA
prompts) but no 2.1 video description turned up. No X/Twitter posts with 2.1 edit formulas were found beyond Qwen's
launch thread (circle-edit example, "three-view reference → storyboard" claim).
