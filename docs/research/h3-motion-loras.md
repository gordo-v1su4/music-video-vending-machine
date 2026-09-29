# MiniMax H3: motion / camera LoRAs and motion techniques (research, 2026-09-28)

Web research only. Nothing was downloaded or installed. Figures such as download counts, file sizes and
recommended strengths come from the model pages and have not been checked locally. "Evidence" means what the page
or community shows. None of it has been tested in this repo.

Context from our pilot (`docs/evidence/2026-09-28-local-ref2v-pilot.md`): Ref2VA int8, 20 steps, res_multistep, sigma
shift 12/3, 1344x768 @ 24 fps; some clips used `minimax_h3_turbo_v4_step600_ema` at 8 steps (euler).

**Variant warning:** an FL2VA LoRA (t2v / i2v / first-last frame) and a Ref2VA LoRA are not interchangeable
([minimax3.org guide](https://minimax3.org/minimax-h3-lora)). Most motion LoRAs below were trained on FL2VA. Only
the items marked **Ref2VA** were trained for our main route.

---

## Best candidates to try (ranked, sizes for download approval)

| # | Candidate | Size | Variant | Why | Identity risk |
|---|-----------|------|---------|-----|---------------|
| 1 | **Motion speed slider for H3** (FrogOnStilts, Civitai) | **9.6 MB** | H3 (checkpoint not stated) | Bipolar slider: negative = slow motion, positive = faster. Cheap to test for speed ramps / beat-snaps | Low (tiny rank); untested on Ref2VA |
| 2 | **Faster! Harder! Shake Harder! H3 Motion Booster**, V0.2 REF2VA / V2 (FourBunny) | **148 MB** | **Ref2VA-native** file exists; also FL2VA | Boosts action amplitude, recoil and secondary motion. The only general motion booster trained on Ref2VA | Medium. Hosted in Civitai's mature section, so it may lean NSFW. Test with neutral prompts |
| 3 | **Better Human Motion** (AdaptiveVision / vpakarinen) | **296 MB** | FL2VA (t2v + i2v) | More natural, consistent body movement; most-reviewed H3 motion LoRA | Unknown; FL2VA only |
| 4 | **Jojocodex Camera Motion LoRA** v1_3000 | **155 MB** (each of 2 files) | FL2VA / t2v | Push-in, pull-back, orbit, handheld tracking, crane, aerial. Ships a 55-prompt library | Low for camera moves; t2v only |
| 5 | **[MMH3] Bullet Time** (alcaitiff) | **96 MB** | H3 (checkpoint not stated) | Freeze-frame orbit plus a return to normal speed. Loop Forge found bullet time impossible with prompts alone | Unknown |
| 6 | **H3 Combat BASE V2** (FourBunny) | **148 MB** | FL2VA only | Momentum, recoil, balance loss, falls and follow-through; useful for falling and impact beats | Unknown |
| 7 | **Wushu Action v7 R2V** (Jojocodex) `wushu_h3_r2v_v7_2000` | **310 MB** (FL2VA files 596 MB) | **Ref2VA** + FL2VA | Force dynamics for martial arts; one of the few Ref2VA action LoRAs | Trained on a single person; multi-person is unstable |
| 8 | **Viggle Meridian** (camera re-shoot of an existing clip) | **2 x 2.5 GiB** LoRAs + VGGT-Omega | v2v on H3 | Re-renders a finished clip along a new camera path, and can slow down or freeze the action (bullet time or speed ramp after the fact) | Low (geometry-guided). **VGGT-Omega uses a non-commercial licence** |
| 9 | **MiniMax-H3 Fun ControlNet Union 2.0** (Alibaba PAI) | **~6.8 GB** | FL2VA + Ref2VA paths | Pose/depth control video, so you can drive exact dance choreography from a real dancer clip | Low with Ref2VA path + `ref_image_size max` |
| 10 | **Spatial Physics LoRA** (Jojocodex) | 148 MB | t2v | Object collisions and bounce only, not human motion. Low priority | n/a |

Recommendation order for our pipeline: test #1 (tiny) and #2 Ref2VA at 0.6–0.7 on one existing Ref2VA shot,
comparing face against the named-character refs. Then try #4 and #5 on FL2V/t2v inserts. Keep #8 and #9 for when
we need exact camera paths or choreography, because both are heavy.

**Quickest free wins (no download):** keep 20–25 steps for any dynamic or camera shot, render ≥124 frames for camera
moves, drop the background reference plate on camera-move shots, and write camera moves with MiniMax's
amplitude/speed vocabulary (see "Techniques").

---

## Candidate details

### 1. Motion speed slider for H3 MiniMax (FoS)
- Link: https://civitai.com/models/2951265/motion-speed-slider-for-h3-minimax-by-fos
- Does: a speed slider. Negative weights slow motion down and positive weights speed it up. The optional words
  `slow` / `fast` help.
- File: fp32 safetensors, 9.63 MB, v1.0 (published 2026-09-20).
- Strength: the author suggests -10 to +10 before prompt adherence drops (tested to about ±16). These are slider
  units, not 0–1.
- License: MiniMax H3 Community License, per the page.
- Evidence: high download count and many positive reviews on Civitai. No sample videos were visible in the fetched
  page. The page also notes it works with adult content.
- Identity: not addressed. At this size it is unlikely to carry appearance, but that is unverified.
- Use for us: slow-motion or fast-snap beats generated natively rather than retimed in the edit.

### 2. Faster! Harder! Shake Harder! H3 Motion Booster (FourBunny)
- Link: https://civitai.com/models/2840146 (details via archive: https://civitaiarchive.com/models/2840146?modelVersionId=3246346)
- Does: raises action amplitude, fluidity, body recoil and secondary motion. Aimed at two-person interaction.
- Versions: V0.2 (FL2VA-trained), **V0.2 REF2VA** (Ref2VA-native), V2 (wider motion coverage, audio-aware), and an
  anime edition. The file `ref2VA_Motion_v2.safetensors` is 147.92 MB.
- Strength 0.6–0.8 (start 0.7). Trigger `dynv2`. The author says i2v works best and t2v needs more rerolls.
- Training: proof of concept, 20 clips, 1,600 steps.
- License: not stated on the archive page.
- Caveat: Civitai redirects it to its mature site. Captions avoid explicit wording, but the training material is
  probably adult. Expect bias toward bouncing body motion. Good for dance energy, but review outputs.
- Evidence: moderate downloads (thousands). Unverified by us.

### 3. Better Human Motion (MiniMax H3)
- Links: https://civitai.com/models/2734359/better-human-motion-minimax-h3 · https://huggingface.co/vpakarinen/better-human-motion-h3-lora
  · demo Space: https://huggingface.co/spaces/hugging-apps/better-human-motion-h3-lora-demo
- Does: more natural, temporally consistent human body movement.
- Variant: t2v + i2v (FL2VA). Ref2VA not mentioned.
- File: 295.8 MB bf16.
- Strength 0.4–0.8. 20–30 steps (the HF card prefers 30). 720x1280. No trigger. The author advises short prompt
  sentences to avoid prompt bleed.
- License: the HF card says Apache 2.0 and Civitai lists the H3 Community License. The LoRA weights sit on the H3
  base licence either way.
- Evidence: the most-reviewed H3 motion LoRA on Civitai (roughly 24k downloads, hundreds of positive reviews). A demo
  Space exists. We saw no side-by-side comparisons.

### 4. Jojocodex Camera Motion LoRA
- Link: https://huggingface.co/Jojocodex/minimax-h3-Camera-Motion-lora
- Does: adds camera moves the base model underplays. It covers push-in, pull-back, push-pull combinations, orbit,
  handheld tracking, aerial, crane, pan and macro.
- Files: `camera_motion_h3_lora_v1_1000_pruned.safetensors` and `..._3000_pruned.safetensors`, 155 MB each, plus
  `camera_motion_Prompt Library.md`.
- Strength 0.8–1.0 (higher values risk instability). Start the prompt with `camera motion`, then subject, scene,
  move, light and quality.
- Variant: t2v only. License Apache 2.0.
- Evidence: the author rates push-in, pull-back and handheld tracking as most stable and pan as weakest (few training
  samples). Dolly zoom, crash zoom and whip pan are not trained classes.
- Identity: t2v only, so it doesn't apply to Ref2VA character shots unless it transfers (untested).

### 5. [MMH3] Bullet Time (alcaitiff)
- Link: https://civitai.com/models/2934116/mmh3-bullet-time
- Does: fast action, then a frozen impact with an orbiting camera, then back to normal speed.
- File: 96.28 MB fp32. Trigger `bullet-time`.
- Strength 1.0 without speedups. Drop to about 0.5 with turbo LoRAs or attention optimisations, where artefacts appear.
- Ships a long prompt "skill" for structuring bullet-time prompts.
- License: H3 Community License. Evidence: very high download count, a top-ranked H3 creator, many positive reviews.
- Why it matters: Loop Forge could not get bullet time from prompts alone (see Techniques).

### 6. MiniMax H3 Combat BASE V2 (FourBunny)
- Link: https://civarchive.com/models/2853878?modelVersionId=3246572 (Civitai id 2853878)
- Does: replaces attack-then-reset loops with continuous physical chains. Momentum carries, blocks redirect, limbs
  separate cleanly, balance shifts and falls read physically.
- File `H3_Combat_V2.safetensors`, 147.92 MB. Strength 0.85–1.0. Triggers `prfight2` (general) and `prfin1`
  (finisher/knockout). The slow-motion trigger was removed in V2.
- Variant: tested only on FL2VA. License not stated. About 7k downloads. Some commenters report motion blur.
- Use for us: falling, stumbling and impact beats. It isn't a dance LoRA.

### 7. Wushu Action v7 / v8 (Jojocodex)
- Links: https://huggingface.co/Jojocodex/wushu-action-v7-minimax-h3-fl2va-ref2va-lora · older https://huggingface.co/Jojocodex/minimax-h3-wushu-action-lora
- Does: learns force dynamics for martial arts (strikes, kicks, swordplay) rather than looks.
- Files: `wushu_h3_r2v_v7_2000.safetensors` **310 MB (Ref2VA)**. FL2VA v7 1000/2000-step files are 596 MB each
  (trained on the int8-convrot FL2VA DiT). The v8 files (596 MB) render untextured grey 3D models on black, so avoid
  them.
- Settings: trigger `wushu_action` at the start. Strength 0.6–0.8. 25 steps, euler/simple, **CFG 1.0** (the card
  says values above 1 cause artefacts). Frame counts on the 17n+5 grid. Ships a ComfyUI workflow and move-tag lists
  (Chinese).
- Training: 924 clips at 832x480, 24 fps. License listed as "other". Multi-person scenes are less stable.

### 8. Viggle Meridian (camera re-control / time manipulation)
- Links: https://huggingface.co/Viggle/Meridian · node: https://github.com/NyckM/3d-Camera-control-H3-Minimax
  · INT8 build: https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX
- Does: estimates depth and camera from an input video, renders the point cloud along a new camera path, then
  Meridian (H3 adapters) fills in and refines the result. The card says it can slow the action or hold a moment still,
  which covers bullet time, speed ramps, orbits and dollies on a clip we already like.
- Files: two LoRA adapters (teacher and turbo), 2.5 GiB each, plus VGGT-Omega.
- Licence: weights use the H3 Community License and code is Apache 2.0. **VGGT-Omega is FAIR non-commercial**, which
  matters if the product ships commercially.
- Output: 24 fps, clips of about 3–10 s.

### 9. MiniMax-H3 Fun ControlNet Union (Alibaba PAI)
- Links: https://huggingface.co/alibaba-pai/MiniMax-H3-Fun-Controlnet-Union-2.0 · ComfyUI workflow write-up:
  https://www.runcomfy.com/comfyui-workflows/minimax-h3-fun-control-in-comfyui-depth-and-pose-video
- Does: conditions H3 on pose, depth, canny, HED or MLSD control videos, and can also inpaint. One ~6.8 GB checkpoint
  covers all of them. Runs at guidance 1.0.
- Suggested settings from the write-up: control strength 0.6–1.0, with an end percent around 0.6 so motion locks early
  and texture recovers late. The Ref2VA path keeps identity and `ref_image_size max` strengthens it.
- Use for us: exact choreography (lyrical/pedestrian dance, beat-snap poses) from a real reference performance, with
  our named characters' identity.

### 10. Others (lower priority)
- **Spatial Physics LoRA** (Jojocodex, https://huggingface.co/Jojocodex/minimax-h3-spatial-physics-lora): 148 MB
  pruned files. Trained on object-physics datasets (CLEVRER/PhyCo). Strength 0.3–0.5, rising to 0.8–1.0 in later
  notes. t2v, Apache 2.0, early release, and not trained on human motion.
- **360 Orbit LoRA** (pablodawson, https://huggingface.co/pablodawson/MiniMax-H3-360-Orbit-LoRA):
  `minimax_h3_flf2v_lora_v1.safetensors` 155 MB. FL2V with the same first and last frame gives a frozen-time 360°
  orbit. Strength 1.0, 28 steps, fixed long prompt. Trained on only 28 human splat orbits. Sample MP4s are on the
  card.
- **Third-person view** (WarmBloodAban, https://huggingface.co/WarmBloodAban/Minimax_H3_LoRAs · Civitai 2945172):
  over-the-shoulder spring-arm camera, whip pans and impact camera shake, with a game-cutscene look. Strength 0.6–0.85.
  Apache 2.0. Size not listed.
- **Anime Motion I2V** (prithivMLmods): loop motion with subtle, minimal movement. Wrong direction for us.
- **VFX-Edit** (NRDX, Civitai 2954203): 1.16 GB. Edits a clip while keeping its timing, motion and camera. Useful for
  relighting a good-motion take, but it doesn't add motion.
- Not found: no dedicated H3 dance, dolly-zoom/Vertigo, crash-zoom, whip-pan or audio-reactive LoRA turned up on
  Civitai or HF as of 2026-09-28. (Wan has Vertigo and dance LoRAs, but they are not H3-compatible.)

---

## Turbo / distill LoRAs and motion

The evidence is mixed. It points to **4 steps hurting large motion and camera moves**, while 8 steps is mostly fine.

- **larryvrh Turbo** (https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora, Apache 2.0, about 744 MB bf16 each).
  v4 step600 is recommended and improves static and small-motion shots. The card admits 4-step renders of large, fast
  motion can smear and ghost. Fixes are 6–8 steps, or the older v1 ckpt850 for "4-step + heavy motion" (over-sharpens).
  Keep strength at 1.0 and don't go past 8 steps. larryvrh's own sampler node steps audio and video on separate
  schedules (https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo).
- **LightX2V / ModelTC Turbo** (https://huggingface.co/lightx2v/Minimax-h3-Turbo; ComfyUI conversions at
  https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI). FL2V 8-step is about 312 MiB; the FL2V 4-step
  dynamic-rank files are 284–891 MiB; Ref2V 4-step is about 312 MiB. Suggested 8-step settings: euler/beta, video
  shift 12, audio shift 4–6. The HyperFlow 8-step variant claims better motion consistency (unverified).
- **Alibaba PAI Acc LoRAs** (https://huggingface.co/alibaba-pai/MiniMax-H3-Acc-LoRAs): FL2VA and Ref2VA 8-step
  versions, rank 64. The Kijai comfy conversions are about 1.72 GB each
  (https://huggingface.co/Kijai/MiniMax-H3-experimental/tree/main/loras). H3 Community License.
- **Against turbo:**
  - Loop Forge found that a 4-step turbo render all but removes camera motion regardless of the prompt
    (https://loopforge.cc/projects/h3-camera-shots/).
  - PlagueKind V11 dropped turbo because it "was ruining video and audio", and the V11 default is 9 steps with step
    skips (https://civitai.com/models/2663838).
  - A Kijai-repo tester said the 3-4 step LoRAs are fine for simple shots, but hands blur in dancing
    (https://huggingface.co/Kijai/MiniMax-H3-experimental/discussions/44).
  - TaoMate 3-step streaming works better on static or slow scenes than on rapid motion
    (https://comfyui-wiki.com/en/news/2026-09-14-taomate-h3).
  - MindStudio saw face and hand degradation at about 6 steps
    (https://www.mindstudio.ai/blog/minimax-h3-turbo-lora-comfyui-local).
- **For turbo:** StableYogi saw no smear or face loss at 8 or 4 steps in its tests
  (https://stableyogi.com/blog/minimax-h3-turbo-and-reference). Our own s10 test matched 20 steps at 8.
- **Stacking:** the Bullet Time author says to lower motion LoRAs to about 0.5 when combined with turbo. The Spatial
  Physics author says it stacks with turbo.
- **Takeaway for us:** use base 20–25 steps (no turbo) for camera-move, dance and fall shots. Turbo v4 at 8 steps is
  fine for low-motion or performance shots. Never use 4 steps for motion shots.

---

## Techniques that reportedly increase motion (no download)

**Sampler / schedule**
- **Steps:** Comfy's docs suggest raising base steps to about 25 for better motion
  (https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native). Loop Forge says 20 steps is the minimum for
  camera moves.
- **Frame count:** render at least 124 frames for a camera move to develop, and 192 for three-phase moves (Loop
  Forge). Stay on the 17n+5 grid.
- **Sigma shift:** higher video shift puts steps in the high-noise region where motion and composition are set.
  - RunningHub's docs suggest 14–16 when motion or large structure is unstable, and 8–10 when detail is lost
    (https://github.com/HM-RunningHub/ComfyUI_RH_MinMaxH3/blob/main/docs/sampling.md).
  - Low video shift makes motion stiff
    (https://www.seedance.tv/blog/best-minimax-h3-settings).
  - **Move audio shift with video shift.** The audio schedule is derived from the video one.
- **CFG:** keep it at 1. H3 is guidance-distilled and higher CFG destabilises motion (Seedance settings guide, Wushu
  card). The minimax3.org advice of CFG 5–7 with DPM++ conflicts with this and looks wrong for H3.
- **Sampler:** res_multistep + simple (Seedance guide, RunningHub). We already use res_multistep.
- **NAG-Lite and FETA** (Enhance-A-Video) in **H3Forge** (https://github.com/RationallyPrime/ComfyUI-H3Forge):
  - NAG-Lite adds negative-prompt guidance without a second pass. Suggested `nag_scale` is 3, not Wan's 11. It could
    carry negatives such as "static, frozen, stiff".
  - FETA suggested values: strength 2.0, max gain 1.10.
  - The **Timeline Prompt** node splits the prompt on `|` across the timeline, which is useful for beat-snapped action
    changes.
  - The author calls all defaults starting points, not tuned values (experimental).
- **Motion-amplitude node:** no H3-specific one found (unverified gap).

**Prompting**
- **Camera vocabulary:** use MiniMax's camera vocabulary with explicit amplitude and speed, written into the sentence
  as an action, e.g. "the camera pushes in with large amplitude at fast speed"
  (https://civitai.com/articles/35774/minimax-h3-prompt-guide).
  - Motion types: Zoom, Push/Pull, Pan, Truck, Tilt, Pedestal, Arc, Tracking, Shake slightly/strongly, POV, Roll.
- **Named shots** from Loop Forge (MIT prompts + agent skills,
  https://github.com/loopforge0/minimaxh3-shots-skills):
  - Built from primitives: dolly zoom (two recipes), crash zoom (as a super dolly in), whip pan, yo-yo zoom (imperfect
    proportions), snorricam, orbit, crane rise and Dutch angle.
  - Bullet time failed from prompts alone.
  - Lens names (8 mm vs 50 mm) changed nothing.
  - **Reference plates damp the camera.** A character plate alone gave about 0.47x the background movement and adding
    a background plate gave about 0.81x (their measure), so for camera-move shots drop the background plate.
- **Pacing:** write exact body-part actions and spread beats across the whole duration. Use `[At MM:SS.mmm]`
  timestamps inside a shot for continuous dance instead of cuts, and end the last beat at least 1 s before the end
  (Civitai prompt guide).
- **Ref2V video reference drives motion:** a reference video can own motion, timing and camera while images own
  identity. Broad motion transfers well, but fine choreography, fingers and facial acting drift. The performer's face
  can bleed through, so avoid strong faces in the motion reference
  (https://digitalzoomstudio.net/2026/09/minimax-h3s-motion-transfer/). The official Ref2V guidance is to state which
  reference drives which part of the shot.
- **Audio-reactive:** see `docs/research/h3-audio-reactive-techniques.md` (percussion stem as reference audio,
  per-accent vocabulary). seitanism's MultiRef nodes add music-video mode, v2v motion transfer at fractional denoise
  of about 0.9995, and keyframes (https://github.com/seitanism/ComfyUI-H3-Motion-Context-MultiRef, GPL-3.0).

**Post / second pass (speed-ramp friendly)**
- **Temporal Upsampling 2nd Pass** (de-rope) in the Advanced Filmmaking workflow. Its author says it greatly improves
  action scenes and fixes fast-motion blur and smudge. It also uses the FILM VFI node for 24→48 fps
  (https://civitai.com/models/2834514).
- **filliptm FL MiniMax H3 Motion Refine:**
  - How it works: decodes the render, stretches motion-heavy intervals, re-denoises partially, then keeps the
    original-timing frames.
  - Status: needs an `H3TimeSmear` dependency that isn't published, so it's unusable for now
    (https://github.com/filliptm/ComfyUI-FL-MiniMaxH3/issues/2).
- **Speed ramps:** Meridian (#8) can slow down or freeze an existing clip. Otherwise, generate a slow take with the
  speed slider (#1) and retime in the edit with interpolation.

---

## Licence notes
- Most Civitai pages restate the MiniMax H3 Community License, including territorial exclusions (the pages list EU,
  UK, South Korea and USA for some self-hosted uses). Check this against the base-model licence we already run under
  before any commercial use.
- Apache 2.0: Jojocodex camera/physics, larryvrh and LightX2V turbo, WarmBloodAban.
- Non-commercial dependency: VGGT-Omega (Meridian).
- "Other" or unstated: Wushu, FourBunny LoRAs.

## Sources (primary)
Civitai: 2951265, 2840146 (and civitaiarchive), 2734359, 2934116, 2853878 (civarchive), 2663838 (PlagueKind V11),
2834514, 2928691, 2954203, articles/35774 · HF: Jojocodex (camera, physics, wushu v7), vpakarinen, pablodawson,
WarmBloodAban, prithivMLmods, larryvrh, lightx2v, drbaph, alibaba-pai (Acc, Fun ControlNet Union 2.0),
Kijai/MiniMax-H3-experimental, Viggle/Meridian · GitHub: loopforge0/minimaxh3-shots-skills, RationallyPrime/
ComfyUI-H3Forge, seitanism/ComfyUI-H3-Motion-Context-MultiRef, filliptm/ComfyUI-FL-MiniMaxH3,
HM-RunningHub/ComfyUI_RH_MinMaxH3, NyckM/3d-Camera-control-H3-Minimax · Other: loopforge.cc, docs.comfy.org,
comfyui-wiki.com, seedance.tv, minimax3.org, artrealmai.com, stableyogi.com, mindstudio.ai, digitalzoomstudio.net,
runcomfy.com. Reddit, X and Banodoco were only reachable through secondary sources.
