# Existing VRGDG integration evidence

Inspected 2026-09-25. Read-only source and model-file inspection; no services started, models loaded, generations queued, or ComfyUI files changed. Capabilities below are implementation evidence, not a successful runtime test.

## Located installation

The supplied path resolves to:

`D:\ComfyUI-Easy-Install_v3122\ComfyUI-Easy-Install\ComfyUI\custom_nodes\comfyui-vrgamedevgirl`

Git HEAD reported `73c9bad4d21e7addbe1d13bc92eee0f1431b017d`. The surrounding ComfyUI checkout has unrelated untracked directories; leave them untouched. Its applicable `ComfyUI/AGENTS.md` requires narrow changes, preserving node/workflow contracts, and keeping orchestration concerns out of model internals. Graft in the installation returned no matching nodes for this package; targeted file inspection supplied the evidence.

## What can inform this project

| Requirement | Existing implementation and evidence |
| --- | --- |
| Editable timeline | The guide documents base and overlay tracks, waveform, beat snapping, split/trim, notes, undo/redo, and global-audio duration bounds. This is a scene-oriented editor; it does not establish parity with a general-purpose NLE. [Guide, lines 400–469](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/Workflows/LTX-2_Workflows/Video_Builder/readme.md:400). Actual frontend functions include `undo`/`redo` at 11218/11230, `trimBaseSceneVideoAtPlayhead` at 18930 and `splitActiveSceneAtPlayhead` at 44924 in [Builder UI](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/web/VRGDG_MusicVideoBuilderUI.js:18930). |
| Timed still-image approval preview | `_render_image_slideshow` accepts ordered image paths/durations plus global audio, output dimensions, and FPS; subsequent code normalizes images and muxes the soundtrack. [Runner, lines 4083–4168](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_WorkflowRunnerNodes.py:4083). This directly matches part of the requested approval package; cost estimation remains separate. |
| Beat analysis | `_estimate_beats_from_audio` loads mono audio, uses librosa onset strength, beat tracking and onset backtracking, and falls back to RMS peaks. [Builder, lines 2900–2937](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MusicVideoBuilderNodes.py:2900). |
| Lyrics and timing | Prompt Creator builds a Whisper workflow, and contains explicit reference-lyric repair instructions. [Prompt Creator, lines 49–103](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MusicVideoPromptCreatorNodes.py:49), [workflow construction at 1815](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MusicVideoPromptCreatorNodes.py:1815). Accuracy on the user's songs is untested. |
| MiniMax H3 rendering | `_build_minimax_h3_api_prompt` selects source-audio or generated-audio workflow templates and accepts authoritative timeline bounds. `/vrgdg/workflow_runner/build_minimax_h3_prompt` exposes construction of the ComfyUI prompt. [Runner, lines 2613–2655](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_WorkflowRunnerNodes.py:2613), [route at 4306](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_WorkflowRunnerNodes.py:4306). The guide describes T2V, I2V, reference-to-video, and V2V modes; those were not rendered during inspection. |
| Exact H3 timing | The local adapter defines 24 FPS, a `17n+5` frame grid and a 362-frame cap; timing calculation keeps final scene trim distinct from generation duration. These are this adapter's constants, not a universal claim about all H3 versions. [Timing, lines 13–45 and 86–184](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MiniMaxH3Timing.py:13). |
| Preserve original music | Audio Drive encodes source audio into the joint AV latent, locks it with a zero denoise mask, and returns the original audio for final mux. [Audio Drive, lines 56–119](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MiniMaxH3AudioDrive.py:56). Final assembly accepts ordered clips, overlays, scene timing and soundtrack paths and uses FFmpeg. [Runner, lines 3707–3730 and 3976–4020](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_WorkflowRunnerNodes.py:3707). |
| Agent integration boundary | Builder Agent consumes active context plus recent messages, produces JSON `{reply, actions}`, and enumerates scene planning, prompt generation and render actions. Manual mode forbids actions; Auto Apply delegates action execution to the application. [Builder, lines 4153–4270](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MusicVideoBuilderNodes.py:4153). This suggests a useful action contract for evaluating Jcode; it does not establish durable jobs, budgeting, or Jcode compatibility. |
| Project persistence | Existing routes include save/load session, project creation/branching, ZIP import/export, and render logs. [Builder routes beginning at 9824](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_MusicVideoBuilderNodes.py:9824). |

## Browser providers and Qwen: distinguish present from planned

The explicit browser-provider table contains **Flow Nano Banana, GPT Image, and Meta AI**. It does not contain Higgsfield or Midjourney. Their requested browser integrations need separate investigation and adapters. [Provider table, lines 35–60](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/VRGDG_BrowserImageRoutes.py:35).

Targeted searches of this package did not identify a **Qwen Image Edit 2.1** Builder adapter. Qwen encoders referenced by MiniMax/Krea/Flux are not proof of Qwen image-edit support.

However, direct filesystem inspection found the following substantial local artifacts in `D:\models\diffusion_models`:

- `qwen_image_2.1_bf16.safetensors` — 14,230,280,616 bytes.
- `qwen_image_2.1_int8_convrot.safetensors` — 7,256,783,064 bytes.
- `qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors` — 9,471,072,252 bytes.
- A corresponding `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` file.
- Separately named Qwen Image Edit **2511** model files also exist.
- MiniMax H3 FL2VA and Ref2VA files in W4A8 and INT8 variants also exist.

These names support preserving the user's **2.1** terminology pending inspection of their intended workflow. File existence does not establish model integrity, successful loading, compatible node registration, VRAM fit, or performance. Do not silently replace their choice with 2511.

Subsequent read-only `nvidia-smi` inspection reported a GeForce RTX 5090 with 32,607 MiB total VRAM and driver 616.92. This is the local Windows GPU budget, not a model-load benchmark. Schedule model workloads and benchmark quantized/local candidates within that budget; do not assume simultaneous video generation and large multimodal review will fit.

## Planning implications, still proposals

1. Decide whether VRGDG is the initial production workspace, a provider behind our own editor, or only a reference implementation. Its existing timeline and timed preview could materially reduce initial work.
2. Keep the application's project/scene/asset records and production budget authoritative. An agent should issue explicit supported actions; worker code should execute and record them.
3. A short validation should eventually prove one audio-aligned H3 scene, one Qwen 2.1 image-edit workflow, and one storyboard preview before architecture is marked settled. No generation is authorized by this research note.
4. Retain browser generation as a separate provider capability. The inspected VRGDG browser implementation does not prove Higgsfield/Midjourney reliability or session access.
5. Source reuse needs a deliberate licensing choice: the installed [LICENSE, lines 1–7](D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/comfyui-vrgamedevgirl/LICENSE:1) declares **AGPL-3.0**. This note records the license rather than interpreting legal obligations.

Open interview questions: reuse vs independent editor; exact Qwen workflow; hosting/worker machine; browser provider priority; meaning of the user's budget answer “1”; spend cap and retry policy; Jcode identity and whether it is required or under evaluation.
