# Storyception UI reuse assessment

Source inspection: 2026-09-25. Repository: `donor-repo/storyception`. This is a bounded source review, not a browser, runtime, generation-quality, or test verification.

## Recommendation

Use Storyception as the design and domain reference for concept selection, reference intake, character sheets, and shot/storyboard choices. Reimplement selected interfaces in the user's chosen Svelte stack. Do not treat its bottom timeline as the requested full video editor or transplant the whole React application. WebGPU preview/compositing is a separate new capability; none was established in the reviewed Storyception UI.

## Concrete reuse candidates

| Area | Existing evidence | Proposed use |
| --- | --- | --- |
| Concept and story planning | The mounted entry panel uploads references, detects characters, requests concept pitches, then generates a story. [entry sequence](donor-repo/storyception/components/storyception/story-opening-panel.tsx:511), lines 511–592; [pitch request](donor-repo/storyception/components/storyception/story-opening-panel.tsx:360), lines 360–381; [story request](donor-repo/storyception/components/storyception/story-opening-panel.tsx:258), lines 258–316. | Reuse the staged selection pattern for song → direction → approved concept. Replace the hardcoded `totalDuration: 90` with actual song duration and measured musical structure. |
| Character/reference preparation | Detection has an actual API request and normalizes character candidates. Character generation separately requests annotated sheets and clean look sheets with visible progress phases. [detection and sheets](donor-repo/storyception/components/storyception/story-opening-panel.tsx:318), lines 318–463. | Port reference classification, editable character identity, and visible per-character generation status. Persist approved identity/style references as production constraints. |
| Character presentation | Character cards show source and sheet imagery, descriptor, kind, and default look label. [CharacterCard](donor-repo/storyception/components/storyception/character-card.tsx:15), lines 15–76. | Useful compact identity/reference card for continuity review. `+ Add look` is explicitly disabled/planned, so wardrobe/look editing requires implementation. |
| Storyboard choices | Flow canvas requests four image options; a selected option is added to the reference set when requesting the expanded storyboard. [option generation](donor-repo/storyception/components/storyception/flow-canvas.tsx:183), lines 183–245; [storyboard expansion](donor-repo/storyception/components/storyception/flow-canvas.tsx:247), lines 247–306. | Port candidate selection and approved-frame guidance; adapt to provider-neutral image/video jobs and revision records. This is relevant to vision-assisted prompt and continuity work. |
| Planning workspace | Main page switches between a flow canvas and story cards, supplies references/characters to the flow view, and mounts the bottom timeline. [workspace composition](donor-repo/storyception/app/page.tsx:285), lines 285–337. | Consider optional graph/story-card views of one shared scene plan. Keep the main music edit in a true timeline. |

## Implemented versus incomplete

- The active opening UI and flow canvas contain real API wiring for references, concept pitches, character detection/sheets, and image options. This establishes implementation, not successful current execution. The underlying image helper calls Gemini generation with reference images and errors if no image is returned: [image helper](donor-repo/storyception/lib/gemini-storyboard-image.ts:59), lines 59–86.
- The bottom timeline supports beat selection, zoomed button widths, skip controls, and elapsed/total displays: [timeline](donor-repo/storyception/components/storyception/timeline.tsx:19), lines 19–218. Playback is a `setTimeout` advancing the selected story beat, not an audio/video transport: [playback effect](donor-repo/storyception/app/page.tsx:232), lines 232–251. There is no trimming, multitrack compositing, waveform, or frame-accurate media playback in this component.
- Some card-view generation remains template/random based. Its action waits 800 ms and calls `generateBeatIdea`: [card action](donor-repo/storyception/components/storyception/story-canvas.tsx:30), lines 30–36. That helper randomly selects canned text: [idea helper](donor-repo/storyception/lib/story-generator.ts:186), lines 186–204. Do not mistake this for the API-connected flow-view path.
- Local page updates merge changes into React state: [beat updates](donor-repo/storyception/app/page.tsx:198), lines 198–207. Durable persistence for every UI edit is not established by this review; require revision persistence when porting.
- Story beat data already carries frames, selected visual options, status, prompts, and keyframes, but uses string durations. [StoryBeat schema](donor-repo/storyception/lib/types.ts:1), lines 1–31. Useful vocabulary, not a sufficient editing/render schema. Add song time, clip source ranges, tracks, revisions, and approval constraints independently.

## Svelte and WebGPU implications

The source uses Next.js 15.5.9, React/React DOM 19.2.0, `@xyflow/react`, Framer Motion, React Radix controls, and Tailwind 4.2.4. [package dependencies](donor-repo/storyception/package.json:14), lines 14–87. Therefore:

1. Port interactions, visual hierarchy, data contracts, and appropriate CSS; TSX, hooks, React Flow components, and Framer Motion components are not directly reusable as Svelte components.
2. Keep provider job execution outside UI components. Adapt the existing request/response ideas to the new homelab coordinator and local GPU worker.
3. Establish the Svelte timeline/media model before adding WebGPU effects. Storyception supplies planning UI ideas, not an existing WebGPU rendering foundation.
4. Do not copy build-validation settings unchanged: [Next config](donor-repo/storyception/next.config.mjs:7), lines 7–14, sets `typescript.ignoreBuildErrors: true` and unoptimized images.

## Checkout and reuse status

- Branch inspected: `main`.
- Existing uncommitted work before and after inspection: modified `.gitignore`; untracked `.ignore`. No application source edits, installs, servers, commits, or paid generation were performed.
- No repository `AGENTS.md`, LICENSE, or COPYING file was found in this checkout. `package.json` marks the project private. The user has authorized UI reuse across their repositories; this review does not establish third-party asset ownership or redistribution rights.
- Graft map/query/skeleton were used first. Graft reported an automatic graph refresh; Git status remained unchanged from the initial snapshot.

## Suggested scope for the combined app

Take Storyception's **reference intake → concept alternatives → character confirmation → storyboard option selection** flow. Add the approved timed preview, estimated production cost, musical alignment, vision review annotations, and full Svelte timeline as new integrated capabilities. Preserve an explicit approval boundary between changing the story/style and repairing clips or pacing within approved direction.
