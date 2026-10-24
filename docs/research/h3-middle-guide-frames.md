# H3 intermediate guide frames and causal shot continuity

Checked 2026-10-09 against the running local ComfyUI at `127.0.0.1:8188`. Initial findings are capability/source inspection. A later authorized workflow copy adds the two native guides; render/quality evidence is tracked separately below. No runtime code or models were changed.

## Verified local controls

| Control | Installed node/input | What it does |
| --- | --- | --- |
| Untimed scene/identity references | `PK_MiniMaxH3Combined.reference_images.reference_image_N`, `mods` | Encodes images/RefMods as ordinary reference blocks. No target frame index is attached. Picture labels and prompt shot assignments provide semantic guidance. |
| Opening/ending anchors | `PK_MiniMaxH3Combined.first_frame`, `last_frame` | Encodes keyframes at frame zero and the last generated frame. The active Combined node has no middle-frame socket. |
| Intermediate timed image or clip | Native **`MiniMaxH3AddGuide`**, display name **Add Guide for MiniMax H3** | Appends a guide to conditioning at an explicit `frame_idx`; chain multiple nodes for multiple guide positions. Live `/object_info/MiniMaxH3AddGuide` confirms registration. |
| Untimed motion-reference video | `PK_MiniMaxH3Combined.video` | Supplies a frame batch as a reference video; this is separate from inserting those frames at a particular target position. |

Local sources: [`pk_minimax_h3_combined.py:361`](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/plaguekind-nodes/ltx_lora_loader/pk_minimax_h3_combined.py:361), lines 361–393, 395–435 and 494–501; [`nodes_minimax_h3.py:166`](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/comfy_extras/nodes_minimax_h3.py:166), lines 166–240. Snapshot: `.runtime/gen/rafa-refmod-ab/add-guide-object-info.json`. Upstream primary source: [ComfyUI native H3 nodes](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_extras/nodes_minimax_h3.py).

`MiniMaxH3AddGuide` requires `positive`, the **H3 AV `latent`**, and `frame_idx`; image guides also require the video `vae`. It returns updated `positive` conditioning. Connect Combined conditioning → first Add Guide → second Add Guide → BasicGuider, with the original Combined latent supplied to each guide and the sampler. This preserves the existing reference metadata; implementation appends `minimax_keyframes` rather than replacing `minimax_refs`. Do this in a saved workflow copy.

At 24 fps, frame 72 is 3 seconds. Negative indices count from the actual generated end; `-1` anchors the last frame. Our 12-second setting generates 294 frames/12.25 seconds. An out-of-range guide fails validation. Images are **center-cropped/resized to output dimensions**. A batch below five frames uses only its first image; longer batches are shortened to the valid 5/22/39/… (`17k+5`) lengths and must fit in the remaining timeline. There is no exposed guide-strength input. These are source contracts, not a promise of exact pixel reproduction or successful motion between anchors. [Local native implementation, lines 191–240](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/comfy_extras/nodes_minimax_h3.py:191).

## Prompt roles and motion context

MiniMax's official Ref2VA guide distinguishes concrete frame/shot anchors from reusable subject references and whole-video motion/edit structure. Define each picture's purpose and shots consistently, then describe visible action and state changes in playback order. The six fields are `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`; later cuts use `[Shot N] At MM:SS.mmm`. A textual timestamp alone does not create an installed timed guide. [Official MiniMax prompt guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md).

[H3 Motion Context MultiRef](https://github.com/seitanism/ComfyUI-H3-Motion-Context-MultiRef/blob/main/TECHNICAL_ARCHITECTURE.md) describes guide-based continuation, interior placement via `target_start`, and compatibility with ordinary references. However, **`MiniMaxH3MotionContext` is not registered in this running installation**: live object_info returns `{}`. Original Motion Context source copies exist nested under `JLC-Flux2-ControlNet` and `H3Studio2-LD`; that does not make their nodes active. Installed `ComfyUI-MiniMaxH3-Contex-Loop` documents an optional adapter to MultiRef, not an embedded copy of that pack: [local attribution lines 42–57](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/ComfyUI-MiniMaxH3-Contex-Loop/THIRD_PARTY_NOTICES.md:42). No installation is needed to test the already-live native Add Guide.

Another maintainer's [Combined Image and Reference node](https://github.com/entropicnoise/MiniMax-H3-Combined-Image-And-Reference-to-Video) exposes a midpoint anchor, but it is different from the active PlagueKind Combined node. Do not substitute online socket names into the current graph.

## Narrow next tests

1. Keep Rafa's existing RefMod, model, seed and generation settings. Compare identical boot/ground and falling-boot images used as ordinary scene references against the same images as two explicit interior guides. Recompute picture labels when reference inputs change; Add Guide does not itself tokenize new picture labels, so images needing prompt labels should also appear in the declared reference map.
2. Anchor only within one causal action first: planted boot → earth fractures and drops → unsupported boot/body descends. Keep screen direction, camera side, clothes and environment consistent. Inspect whether the ground has actually changed state, whether the boot's support is gone and whether downward motion continues between anchors.
3. If still anchors reproduce poses but miss physical motion, test a short motion clip as a timed guide versus an untimed video reference. Record crop, actual shortened guide length and placement. For multi-shot production, also test separate shots joined through a matched last/first frame; a matching boundary alone does not establish causal continuity.

These controlled comparisons remain proposals. A later exploratory trial completed through the visible UI: job `ab692d87-4bfe-40bb-a103-f8e016e802c8`, two native guides at frames 62/120, seed 241139, 1 MP / 1312 x 736. Execution took 337.06 seconds; output decodes at 24 fps, 294 frames / 12.25 seconds. The executed graph confirms both guides. The prompt also incorporates the user's continuous-momentum correction, so this is not an isolated guide/no-guide comparison. Visual acceptance remains pending; see [experiment results](../pilot/rafa-render-experiment-results.md).

## Workflow metadata from the actual browser run

History `050932e1-f172-4699-9527-4853d0559cac` lists one media output: **`D:/output/local/MVVM/rafa-next-prompt-1mp/rafa-next_00001_.mp4`**. Node 5612 also emits the text `Resized to: 1312 × 736`. There is no companion PNG in this job's output receipts; the receipt's `images` field contains an animated MP4.

The actual MP4 has embedded **`workflow`** (168,955 characters) and **`prompt`** (19,139 characters) tags. Native `SaveVideo` writes hidden workflow/extra metadata and the executed prompt into the video container unless metadata is disabled. [Local SaveVideo implementation lines 185–203](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/comfy_extras/nodes_video.py:185). Extracted evidence is saved under `.runtime/gen/rafa-next-prompt-1mp/{container-metadata.json,embedded-workflow.json,embedded-prompt.api.json}`. This job supports recovery from video metadata; it does not prove that every workflow emits a separate workflow-bearing still image.
