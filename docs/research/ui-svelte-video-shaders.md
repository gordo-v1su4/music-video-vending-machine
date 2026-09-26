# Svelte Video Shaders donor audit

Source inspection on 2026-09-25 of `C:/Users/Gordo/Documents/Github/svelte-video-shaders`, local `main` at `893eedb`. Existing modified `.gitignore` and untracked `UI_UX_DESIGN_HANDOFF.md` preserved. `graft map` reports no graph; no graph was built during this read-only pass. Read AGENTS/CLAUDE and relevant local rules, plus the Svelte code-writer skill. No dependencies installed, components edited, servers started, generation requested, runtime tests or browser verification performed.

## Recommended role

Use it as a **Svelte music-arrangement, waveform, retiming and shader-controls donor**. Its section buckets can become the visual organization for story beats and planned shots, but the inspected application does not implement an agent director or a story/prompt/continuity bible. Combine these musical interactions with the narrative workflow from another donor.

Important renderer distinction: this is **WebCodecs + Three.js WebGL/GLSL**, not an existing WebGPU implementation. Reuse timing/data/UI concepts and selectively port shaders to the chosen renderer; do not silently change the project's chosen WebGPU direction.

## Current implementation

All paths below are relative to the donor root above.

| Area | Evidence | Reuse and limitation |
| --- | --- | --- |
| Active app | `src/routes/+page.svelte:1-5` imports and mounts VideoWorkbench. `package.json:20-58` lists Svelte `^5.55.2`, SvelteKit `^2.57.0`, Three `^0.178.0`, Peaks, mp4box, mediabunny and Tweakpane. `svelte.config.js:1-15` uses adapter-static with index fallback. | Actual Svelte browser app; no React migration required. The active workbench is a very large component, so extract domain and media services before reuse. |
| Song structure | `src/lib/VideoWorkbench.svelte:1781-1836` calls EssentiaService, applies BPM/beats/onsets/energy/sections and handles failure. `src/lib/essentia-service.js:49-86` checks the service and sends the audio for analysis. | Existing musical-analysis integration; external service availability and analysis accuracy were not tested. |
| Section-based arrangement | `src/lib/VideoWorkbench.svelte:319-321` stores section→video pools; `564-576` defaults first section to all clips and others to empty; `662-705` reorders section rows while remapping pools/focus/loop state. `src/lib/PeaksPlayer.svelte:5-41,99-117,753-767` exposes section bounds, rename and creation callbacks. | Useful song-section/shot-bucket UX. Row reorder retains section times; this is not evidence of a general multitrack editing model. Existing empty buckets can inform missing-shot UX. |
| Automatic cutting | `src/lib/VideoWorkbench.svelte:1890-1910` counts onset/MIDI markers and calls nextVideo. `2244-2270` advances sequentially through the current section's pool, or clears active video when the pool is empty. | Musical switching is implemented, but selection is round-robin rather than scored for story, motion, palette or neighbor compatibility. It does not establish the requested reject-unsuitable-candidates policy. |
| Speed remapping | `src/lib/VideoWorkbench.svelte:1272-1345` normalizes audio energy, smooths it, maps to a speed range and integrates a time-remap curve. `1402-1448` uses audio as master clock and applies remapping with continuity offsets. | More substantive than a decorative curve editor. Still not proof of frame-accurate rendered export, suitable ramps per shot, safe lip-sync handling or artifact-free interpolation. |
| Effects preview | `src/lib/ShaderPlayer.svelte:75-99` initializes Three.WebGLRenderer and shader uniforms. `src/lib/shaders/` contains bloom, glitch, VHS, CRT, chromatic aberration, color/tone and other GLSL modules. `src/lib/VideoWorkbench.svelte:1912-1933` triggers jump cuts, effect spikes and high-energy micro-jumps. | Useful creative effect controls and preset vocabulary; requires WebGPU adaptation. Random jumps are creative options, not QC-approved editing decisions. |
| Decode/cache | `src/lib/webcodecs-frame-buffer.js:97-129` keeps decoded ImageBitmap arrays with clip offsets; defaults to 24fps and 1280×720 with fixed 16:9 normalization. `src/lib/VideoWorkbench.svelte:2121-2128` preloads videos and assigns new clips to buckets. | Donor for decoder/frame-selection concepts. All-clip frame caching, preview resolution and fixed aspect ratio require redesign/measurement for full-song projects, large libraries and multiple output formats. |
| Asset state | `src/lib/stores.js:1-20` stores browser File/object URLs in writable stores. | Ephemeral UI data, not durable project assets, version history or a worker-safe asset contract. |

## Story, generation and production gaps

A targeted source search for story/agent/reference-asset/prompt-template, persistence (localStorage/IndexedDB), undo/redo, Tauri, WebGPU, VideoEncoder and MediaRecorder found no corresponding implementation in the active source. The broad `onsets` name causes false positives for `onset`-containing search text; it is musical timing, not story infrastructure. Treat this as a bounded absence finding, not proof about other branches or past versions.

The untracked `UI_UX_DESIGN_HANDOFF.md` describes this current workbench (including waveform/section bucket interactions); it is not evidence of implemented agent planning. `src/temp_backup/` is not the active route. No agent session, shot prompt/ref model, generation adapters, visual-continuity reviewer, durable edit revision history or finished-video export path was established in this pass.

Use section boundaries, waveforms, clip buckets, auditioning, master-clock playback and energy-shaped effects in our combined design. Add stable project/shot/asset-version IDs, accepted creative direction, missing-shot requests, suitability/neighbor evidence, reversible edit operations and durable render jobs in the new application model.

No tracked LICENSE file was found; package declares private with no license field. Preserve attribution for any third-party shader code that is selected later. Repository code was not modified or certified by Svelte autofixer during this source-only audit.
