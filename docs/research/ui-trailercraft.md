# TrailerCraft UI reuse assessment

Inspected 2026-09-25. Source review only; no service startup, provider calls, browser review, or visual/runtime acceptance. Target direction supplied during review: Svelte and WebGPU.

## Working copy

- Source: `donor-repo/trailercraft`, branch `main`, HEAD `b8ccc2cd259bf8c0953b6ea59ad8290b402f3a05`. Status reported `main...origin/main`, modified `src/utils/api.js` and `vite.config.js`, untracked `.claude/`. Those existing changes were preserved; remote freshness was not checked.
- No local AGENTS.md or Graft index was found. No tracked LICENSE file or package license declaration was found; code reuse requires confirming ownership/license before redistribution. User has authorized this repository as a design/code donor.
- React 18.3, Vite 5.4, Tailwind 3.4, Lucide React: [package.json](donor-repo/trailercraft/package.json:13), lines 13–23. Components must be rewritten for Svelte; plain algorithms and design patterns can be adapted independently.
- The actual entry loads the monolithic `App.jsx`: [main.jsx](donor-repo/trailercraft/src/main.jsx:3), lines 3–8. Its own story/timeline renderers are selected at [App.jsx](donor-repo/trailercraft/src/App.jsx:1614), lines 1614–1616. The separate `components/TimelineEditor.jsx`, `StoryBuilder.jsx`, and hooks are not the active implementation.

## Useful donors and limits

| Area | Source-backed implementation | Reuse recommendation |
|---|---|---|
| Story/reference planning | Up to eight uploaded references, vision analysis of the first reference, character descriptions, style and 15 story beats: [App.jsx](donor-repo/trailercraft/src/App.jsx:659), lines 659–750. | Adapt the reference/character/story inspector. Avoid hardcoding a trailer's 15-beat structure for every music video. |
| Prompt continuity and repair | Scene render combines stored character descriptions, scene prompt, visual style and corrective instructions; selected references accompany generation: [App.jsx](donor-repo/trailercraft/src/App.jsx:586), lines 586–617. | Good basis for an editable prompt inspector and per-shot repair action. This is prompt conditioning, not an implemented visual QC verdict. |
| Storyboard assets | Generates exactly 18 descriptions, renders two 3×3 grids, splits them into stills: [App.jsx](donor-repo/trailercraft/src/App.jsx:826), lines 826–911. Asset cards have editable prompts, rerender and add-to-timeline: [App.jsx](donor-repo/trailercraft/src/App.jsx:1340), lines 1340–1389. | Reuse interaction patterns; make shot count and layout song-dependent. Preserve generated versions rather than replacing an asset in place. |
| Audio/animatic | Web Audio decoding/playback and Canvas 2D waveform: [App.jsx](donor-repo/trailercraft/src/App.jsx:459), lines 459–574. Preview switches still images using cumulative durations: [App.jsx](donor-repo/trailercraft/src/App.jsx:1241), lines 1241–1301. | Useful reference for the approved timed preview. It is an audio-backed slideshow, not video compositing. |
| Music markers | Amplitude-energy threshold windows with sensitivity and spacing: [App.jsx](donor-repo/trailercraft/src/App.jsx:74), lines 74–108. Marker controls at [App.jsx](donor-repo/trailercraft/src/App.jsx:1418), lines 1418–1449. | Reuse marker UI; replace heuristic detection with measured beat/downbeat/section/lyric analysis. The current algorithm does not understand musical structure. |
| Timeline arrangement | Add/remove, move left/right, and set successive scene durations from detected markers: [App.jsx](donor-repo/trailercraft/src/App.jsx:1001), lines 1001–1032. | A sketch for arrangement controls only. No full timeline foundation: source review found no trim, split, scrubbing, transitions, multitrack, undo, or render/export path. |
| Production status | Local progress strings and event log: [App.jsx](donor-repo/trailercraft/src/App.jsx:1587), lines 1587–1612. | Adapt for durable job progress and evidence-backed QC findings; current messages are not a review system. |

## Gaps that affect architecture

- **Persistence excludes media.** Autosave strips image URLs and reference payloads, retaining metadata: [App.jsx](donor-repo/trailercraft/src/App.jsx:398), lines 398–450. Manual Save does the same at lines 288–298. Audio remains browser state. This cannot serve the required complete editable project archive.
- **Placeholder fallback exists.** Generation failure creates `mock_` scene cards without images: [App.jsx](donor-repo/trailercraft/src/App.jsx:915), lines 915–954. Those states must remain visibly distinct from completed generated assets.
- **Video API code is disconnected.** `callVeo` exists at [api.js](donor-repo/trailercraft/src/utils/api.js:135), lines 135–166, but the active App imports only Gemini/Imagen at [App.jsx](donor-repo/trailercraft/src/App.jsx:9). A helper does not establish an implemented video workflow.
- **Current config is broken.** Read-only `node --check vite.config.js` fails with `SyntaxError: Unexpected identifier 'VERTEX_PROJECT_ID'` at [vite.config.js](donor-repo/trailercraft/vite.config.js:20). The local modified file places declarations directly inside a plugin object (lines 17–25). `src/utils/api.js` passed syntax checking. No repair was attempted.
- **No WebGPU donor.** Inspected source/package contains no WebGPU/WebGL, WebCodecs or GPU compositor implementation. Rendering is DOM images and Canvas 2D. Svelte/WebGPU preview, video decode/synchronization, timeline editing and export need an independent implementation or a stronger donor.

## Recommended scope

Use TrailerCraft for the storyboard/reference workspace, character-aware prompt editing, single-shot regeneration and music-marker controls. Reimplement these as Svelte components over durable project/asset/job data. Treat the full editor, WebGPU renderer, automated review, approval/budget controls, and final export as separate missing systems. Do not adopt its React shell, fixed 18-frame workflow, browser-only persistence, or modified provider configuration wholesale.
