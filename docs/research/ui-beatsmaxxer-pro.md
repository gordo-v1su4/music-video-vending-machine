# Beatsmaxxer Pro: music-driven editing reference

Inspected 2026-09-25 at `C:/Users/Gordo/Documents/Github/beatsmaxxer-pro`, branch `codex/playback-and-arrangement-followup`. Source review only; no browser acceptance, playback measurement, generation, server startup, install, or source edit. Read the repository AGENTS.md and Svelte code-writer skill before component analysis. Graft was queried first; Svelte component text was inspected directly because the graph did not index those components.

## Recommended role

This is the strongest inspected reference for the user's clarified editing model: **change musical behavior and compare variations, while the timeline explains the result**. The relevant building blocks already use Svelte and WebGPU. Prioritize its Timing workspace and musical trigger controls over copying conventional clip dragging as the primary workflow.

Preserve music-vending-machine's independent story, character continuity, approvals, providers, and homelab production coordinator. Beatsmaxxer supplies a promising interactive timing/rendering layer, not the whole automated narrative generator.

## What the operator changes, and what it changes

| Operator control | Implemented behavior | Source |
| --- | --- | --- |
| Trigger source and instrument/channel | Choose beat grid, MIDI notes, mix/vocal/stem onsets, vocal phrase starts, RMS peaks, or continuous behavior. Select a channel or rotate channels by slot. Data availability still matters; selection alone does not create stem analysis. | [source definitions](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/timing/triggers.ts:4), lines 4–16; [trigger UI](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingTriggers.svelte:14), lines 14–39 |
| Every N beats/bars, threshold, effect chance, minimum gap | Control which musical events qualify, what percentage start a ramp/stutter, and how much normal playback remains between finite bursts. Threshold is onset strength/MIDI velocity; RMS is relative amplitude, not LUFS. | [trigger UI](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingTriggers.svelte:24), lines 24–34 |
| Seed | Repeatable trigger choices with a separate sequence per slot. Changing the seed yields another timing realization while the other rules can remain fixed. | [seed input](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingTriggers.svelte:34); [schedule compiler](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/timing/triggers.ts:38), lines 38–69 |
| Speed-ramp minimum/maximum, cycle, shape, curve points, presets | Change the source-time motion within musical cycles. UI exposes smooth/sine/linear/tension/hold interpolation, beat/bar cycle lengths, snapping, and presets including COSINE/SMASH. | [TimingPanel](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingPanel.svelte:79), lines 79–108 |
| Stutter groove, division, repeats, mode, slice count | Choose straight/swing/dotted timing; repeat/hold/jump-cut behavior; subdivision; repeat count; jump source slices. Swing is a 2:1 pair, dotted stretches note length by 1.5. | [stutter UI](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingPanel.svelte:94), lines 94–110; [boundary calculation](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/timing/triggers.ts:24), lines 24–29 |
| Clip order HOLD / LINEAR / RANDOM | Controls source progression; PGM scheduling receives available sources, queued source, interval in beats, and feel. This governs output-source choices separately from an individual clip's time effects. | [order selector](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/TopBar.svelte:408); [director schedule](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/pgm/PgmDirector.ts:86), lines 86–100 |
| Perform rack time-sampler controls | Forward/reverse/ping-pong/random sampling, jump subdivision, slice count, loops, playback rate, sensitivity, and accent mode. Useful optional detailed controls rather than the required initial user experience. | [ModuleControls](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/ModuleControls.svelte:314), lines 314–402 |

The timing compiler builds finite bursts on changes rather than rerolling each frame. It filters event strength, applies chance, skips events inside an existing burst or its minimum gap, uses beat-grid time for repeat boundaries, and records source/exit positions. This gives a concrete basis for stable preview and reusable edit recipes. [buildTimingSchedule](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/timing/triggers.ts:38), lines 38–69.

## Timeline and song structure

- Arrangement owns song sections, bars, colors, per-section FX banks, and cut patterns. The defaults distinguish relatively sparse intro/verse patterns from denser choruses. [ArrangementSection](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/stores/arrangement.ts:27), lines 27–54; [default patterns](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/stores/arrangement.ts:69), lines 69–145.
- Structure analysis maps labeled sections to bar-aligned spans and templates. [structure mapping](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/arrangement/seedFromStructure.ts:150), lines 150–177. This is a musical organization mechanism, not proof of narrative understanding.
- Timeline UI can record program-lane occupancy and effect fires, quantize recorded triggers into cuts, arm playback of the arrangement, and recall section FX banks. [ArrangeView controls](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/ArrangeView.svelte:588), lines 588–615. It also supports manual cut painting; that need not become music-vending-machine's primary interface.
- The runtime resolves cuts against absolute song steps and the active loop region, then selects the target rack source. It does not repeat every cut as though all bars were one bar. [runSequencer](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/runtime/AppLoop.ts:352), lines 352–394.

For the new app, use the timeline to show sections, resulting shots/cuts, trigger events, variation changes, and QC flags. Put high-level musical choices and preview comparison ahead of manual placement.

## Rhythm analysis and preview

Audio import can request hosted analysis or stay local. On the hosted path the current implementation fetches rhythm, applies returned beats/onsets/BPM, and applies structure if supplied; failures explicitly enter fallback and clear analysis beat/onset data. [audio loading](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/audio/AudioEngine.ts:360), lines 360–394; [fallback](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/audio/AudioEngine.ts:1230), lines 1230–1240. Do not describe fallback as equivalent to full verified structural analysis. The current UI also imports matching song/MIDI/analysis files: [import controls](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingTriggers.svelte:36), lines 36–39.

MainViewer mounts the program WebGPU canvas. [MainViewer](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/MainViewer.svelte:82). WebGpuCanvas binds to the shared engine; rack previews use 320×180, and the program canvas has a 1280-width cap plus device/render-budget scaling. [canvas sizing and attachment](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/WebGpuCanvas.svelte:39), lines 39–88. This is preview rendering, not evidence of final-resolution export.

Timing exposes output cadence 24/30/60 FPS, preload resolution, and memory capacity. [TimingFooter](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/timing/TimingFooter.svelte:7), lines 7–12. These are playback/resource controls; a reliable production export and preview/export equivalence still require separate verification.

## Variations, presets, persistence: distinguish the existing pieces

- **Repeatable timing variations exist as primitives:** the explicit trigger seed and chance controls feed a deterministic schedule compiler. They are appropriate donors for `Make another variation` with scope locks.
- **Rack-wide RANDOMIZE is different:** it assigns `Math.random()` values to numeric rack parameters. [randomize](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/stores/rack.ts:439), lines 439–453. It is not a named/reproducible version system or a continuity-aware creative editor.
- **Undo/redo exists:** top-bar dispatches to rack or timing history by workspace. [edit menu](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/components/TopBar.svelte:410), lines 410–433. Undo history is not equivalent to saved project revisions and alternate branches.
- **Timing settings persist locally:** timing.ts reads/writes localStorage and retains per-slot clip timing settings. [timing persistence](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/stores/timing.ts:65), lines 65–94. This is not the homelab-owned durable project, assets, and production history needed here.
- **Factory preset code exists:** names map to rack macros, which map to parameters. [preset store](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/stores/presets.ts:5), lines 5–113. A PresetBrowser component exists, but the inspected main page does not mount it; do not promise that preset browser as a current visible main-workspace feature.
- **Missing from this bounded review:** named saved music-video versions, A/B comparison, parent/child variant lineage, approval preservation, cost-aware regeneration, and a durable output artifact per revision. These should be new application features, even though timing randomness and undo offer useful lower-level mechanisms.

## Platform reuse

This checkout has Svelte 5.56, SvelteKit 2.63, adapter-static, WebGPU types, MediaBunny, SoundTouch audio worklet, and optional Tauri 2 bindings. [package](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/package.json:37), lines 37–77. It is directly aligned with the user's Svelte/WebGPU decision, unlike the React planning references.

Runtime detection distinguishes browser versus Tauri, and the platform video-source adapter currently selects the HTML video source. [runtime detection](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/platform/runtime.ts:1), lines 1–23; [video adapter](C:/Users/Gordo/Documents/Github/beatsmaxxer-pro/svelte/src/lib/platform/videoSource.ts:1), lines 1–18. Reuse browser rendering/interfaces first; the presence of a desktop shell does not replace homelab orchestration or local GPU generation-worker integration. AGENTS' branch-specific desktop guidance and continuity notes contain historical context; this assessment uses the current checkout source.

## Five questions the source resolves

1. **Must the user move and trim each clip to get musical changes?** No. Timing rules, curves, triggers, source ordering, and seeds already drive meaningful output changes; timeline cut painting is an optional existing control.
2. **Can changes follow actual musical events rather than only fixed BPM?** Yes, the interfaces and compiler accept analysis onsets and MIDI channels as well as the beat grid. Available validated source data remains a prerequisite.
3. **Can a variation be repeated?** Yes for the seeded timing scheduler with the same input/configuration. Rack RANDOMIZE and durable named versioning are separate concerns.
4. **Is Svelte/WebGPU only an aspiration here?** No. Mounted Svelte components attach real preview canvases to the WebGPU engine. Their current runtime quality was not tested in this pass.
5. **Does this already provide the generator's complete version/review workflow?** No. Add durable version snapshots, scoped variation commands, comparisons, story/style locks, QC evidence, and production artifacts.

## Checkout preservation

Six QA fixture JSONs were already modified under `svelte/tests/fixtures/qa-fixtures/` and remained unchanged by this review. No application changes or validation runs were made. Component source was analyzed for reuse, not modified/finalized; no autofixer or dependency installation was needed for this research note.
