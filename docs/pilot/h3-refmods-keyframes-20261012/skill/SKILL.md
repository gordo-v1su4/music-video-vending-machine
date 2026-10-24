---
name: minimax-h3-refmods-keyframes
description: Build, inspect, and troubleshoot MiniMax H3 RefMod image bundles and generate cinematic still keyframes in ComfyUI using the tested reference-image and two-pass latent refinement route. Use for H3 identity extraction, reference routing, or still quality comparisons; use the separate H3 prompt skill for general video prompt writing.
---

# MiniMax H3 RefMods and still keyframes

Reproduce a reviewed baseline before experimenting. Character sheets are identity and wardrobe truth; environment images establish the world and its lighting. Preserve the user's approved images, framing, dimensions, expressions and render holds.

Read [references/refmods.md](references/refmods.md) when building or inspecting RefMods. Read [references/still-route.md](references/still-route.md) for the tested image route, parameters, comparisons and local evidence. These describe the October 12, 2026 installation; verify current node schemas and actual wiring before applying them elsewhere.

## Operating rules for this installation

- Work in `D:/ComfyUI-Easy-Install_v3122`; ComfyUI lives in `ComfyUI-Easy-Install/ComfyUI`, port 8188. Saved workflows are under `D:/user/default/workflows`, inputs under `D:/input`, outputs under `D:/output`. Verify these paths live.
- Run generations through the visible workflow's **top Run button**. Read-only queue/history/schema APIs can verify execution; never submit `/prompt` in the background. Reconcile existing running/pending jobs before submitting anything.
- Preserve the entire existing workflow. Back up its current saved or executed JSON before narrow changes. Disable competing experimental outputs when needed; do not delete unrelated video routes or overwrite user edits with an old transfer file. Import edited JSON through the UI and verify the selected workflow and settings.
- If the user is editing, running options or says to wait, do not edit inputs, prompts, parameters, queue or cancel jobs. Continue only independent documentation if appropriate. A previous render request does not override a later hold.
- Inspect exact executed graphs and output files. Node presence, labels and a completed queue are not evidence that references were applied or that images look good.

## Decision path

1. Establish which references and checkpoint actually reach the guider and sampler. A RefModApply node that is disconnected or disabled is not active. A ReferenceToVideo node can legitimately condition Fizgig's single-frame image path.
2. For RefMods, audit container members, tensor shapes, presets, sources and token budgets. A filename containing “master” or “identity” is not verification. Use the read-only [scripts/inspect_refmod.py](scripts/inspect_refmod.py) for safetensors headers, then the installed loader for full semantic validation if needed.
3. For still quality, start from the preferred original Ref2VA baseline in the still reference. Keep the first-pass latent fixed while comparing second-pass denoise. Save before, after and the 4K master; compare before/after at identical dimensions. State the compared pair explicitly.
4. Review identity, body proportions, eyes, skin, hair, material detail, pose, lighting motivation and depth. More pixels or more references do not guarantee fidelity. Distinguish user acceptance, agent observations and untested hypotheses.
5. Once the user approves the route, create one prompt per shot and render the requested rows. Multiple prompt rows, a latent batch and Run's queue count are different mechanisms; verify prompt-list iteration before promising distinct frames.

## Moving into MVVM

Use `C:/Users/Gordo/Documents/Github/music-video-vending-machine` and its `AGENTS.md`, production resume and actual song/story assets. Retrieve the existing duration, song map and loose story beats before drafting. Keep a plain one-shot-per-line prompt file plus a separate timing/shot-ID manifest so text stays feedable and outputs stay traceable. Discuss candidates before an overnight batch. Creating this skill does not authorize a batch, model installation, repo changes or messaging other chats.
