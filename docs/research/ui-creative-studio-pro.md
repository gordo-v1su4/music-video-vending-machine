# Creative Studio Pro as a UI donor

Inspected 2026-09-25. Source review only; no servers started, dependencies installed, or UI interactions verified. Local checkout: `donor-repo/creative-studio-pro`, branch `feat/s0-s1-creative-room-m3`, HEAD `8c2e2e18f89cd7c2338368412e21f616fd7125b8`. The checkout contains extensive unrelated changes, including removed/added skill files and untracked planning files; none were edited. Reading Graft refreshed its local cache automatically.

## Useful existing pieces

- Svelte 5 / SvelteKit, Tailwind 4, `@xyflow/svelte`, AI SDK, and Zod are declared in [package.json](donor-repo/creative-studio-pro/package.json).
- The main route defines Board, Story, Cards, Media, Preview, and Export views; its SvelteFlow canvas projects server-owned project state. [Main route](donor-repo/creative-studio-pro/src/routes/+page.svelte:23).
- Editable story/card views include story beats, purposes, image/video prompts, and approval status. [Production workspace](donor-repo/creative-studio-pro/src/lib/ui/ProductionWorkspace.svelte:116).
- Agent chat has a pending-question state, selectable options, custom text, and explicit submission. Useful for the requested guided decision workflow. [AgentChat](donor-repo/creative-studio-pro/src/lib/ui/chat/AgentChat.svelte:120).
- Brief approval checks match the current brief ID, version, and content hash, rather than treating a past approval as permission for changed content. [Gates](donor-repo/creative-studio-pro/src/lib/domain/gates.ts:117).

## Do not mistake these for a complete editor

- Media intake currently includes image/video URL fields. The inspected UI does not prove automated model generation. [Media view](donor-repo/creative-studio-pro/src/lib/ui/ProductionWorkspace.svelte:154).
- Preview shows a selected card's video/image. The row styled as timeline cards is a card selector, not evidence of multitrack editing, frame-accurate trimming, or continuous source-song playback. [Preview](donor-repo/creative-studio-pro/src/lib/ui/ProductionWorkspace.svelte:173).
- Export downloads a project JSON manifest, not an assembled movie. [Export](donor-repo/creative-studio-pro/src/lib/ui/ProductionWorkspace.svelte:186).
- No WebGPU renderer or Tauri configuration was found in the targeted source/file searches. No root LICENSE file was found. Inspect provenance when extracting implementation; this is not a license conclusion.

## Proposed role

Use this as the strongest directly compatible Svelte donor for workspace structure, story cards, guided decisions, and approval UI. Adapt music-specific planning and GPU rendering patterns from the other candidates. A full timeline, song synchronization, reliable production jobs, media export, and desktop packaging remain explicit work rather than inherited capabilities.

The donor's README describes a larger intended pipeline. Its product roadmap and reuse rules are not proof those capabilities are implemented, nor do they override the decisions for Music Vending Machine.

## Web and desktop constraints to test

User selected Svelte, WebGPU, and both web/Tauri delivery. Tauri uses platform webviews: WebView2 on Windows and WebKit on macOS/Linux, so support must be tested on the selected actual runtime. [Official Tauri webview documentation](https://v2.tauri.app/reference/webview-versions/).

WebGPU requires a secure context and exposes GPU rendering/compute; it is not by itself a video decode/encode or durable media-production system. Validate GPU capability and device-loss recovery independently from playback and export. [MDN WebGPU documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API).

Desktop offline behavior, OS targets, preview fallback, and the exact role of WebGPU remain interview decisions.
