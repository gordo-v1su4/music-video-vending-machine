# Ableton MCP for audio preparation

Research snapshot: 2026-09-25. Primary documentation/source review only. No installation, DAW operation, audio upload, or paid request. The user's exact Ableton MCP implementation, installed Live version/edition, and source format are not yet confirmed. No Ableton tool was callable in the parent task's current tool inventory.

## Proposed place in the product

An optional audio-preparation stage can precede video planning: inspect the source, propose arrangement/mix changes, compare revisions, then approve and freeze an audio version. All lyric timing, beat/section analysis, shot planning, and video edits refer to that immutable approved render. Later changes to song structure or timing invalidate the affected video timing data.

Source format matters. An existing Live Set or aligned stems permits individual-track decisions; a stereo mix permits global processing and section edits but does not expose its original instruments. Source separation would be an additional, potentially artifact-producing process, not a capability implied by audio import. These are design implications, not a settled workflow.

## Exact candidate implementations

| Implementation | Documented useful surface | Material gap |
| --- | --- | --- |
| [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp), MIT, Python MCP + MIDI Remote Script | Tracks, transport, Session clips, browser device loading; current code adds device parameter read/write, audio import, Arrangement inspection and Session-to-Arrangement duplication. | Import source requires Live 12.0.5+, despite the README's broader Live 10+ prerequisite. No export or undo tool found in inspected `MCP_Server/server.py`; a state snapshot is not a restore mechanism. |
| [adamjmurray/producer-pal](https://github.com/adamjmurray/producer-pal), GPL-3.0, Max for Live device + MCP/REST | Detailed Arrangement and Session clip operations, audio clip gain/pitch/warp, device and mixer control. Current installation requires Live 12.3+ and Max for Live, recommending 12.4+. | Cannot itself hear/analyze audio. Static parameter changes are supported, but its documented surface cannot edit automation/envelope curves. Its companion render helper is macOS UI automation, not a Windows export solution. |
| [ulm0/ableton-live-mcp](https://github.com/ulm0/ableton-live-mcp), Live Extension implementation | Arrangement/Session audio and MIDI creation, device/mixer parameters, file import, grouped undoable parameter writes. | Its `render_track_audio` is **pre-FX audio-track output**, not a processed master render. No transport, clip launch, browser, or automation curves in the documented Extensions API surface. |
| [idx3d/ableton-mcp-extension](https://github.com/idx3d/ableton-mcp-extension), MIT, another Live Extension | Named undo steps, validated batch writes, arrangement/clip/device/mixer operations; localhost HTTP with bearer token. | Repository distinguishes macOS in-Live validation from fake-Live tests and says Windows validation remains. Not evidence of an operational Windows pipeline. |

Sources for the first two rows: [original server source](https://raw.githubusercontent.com/ahujasid/ableton-mcp/main/MCP_Server/server.py), [Producer Pal installation](https://producer-pal.org/installation), [tool reference](https://producer-pal.org/features/tools), [limitations](https://producer-pal.org/features/limitations).

The official [Ableton Extensions SDK page](https://ableton.github.io/extensions-sdk/) currently says **Live 12.4.5 public beta only**. Do not interpret a third-party README's “12.4.5 or newer” wording as evidence that the user's stable installation supports extensions. No variant is selected here.

## What the underlying APIs really expose

**Arrangement versus Session:** the current official Live Object Model exposes `Track.arrangement_clips` (since Live 11), Arrangement audio creation from a file, Arrangement MIDI creation, and clip duplication to Arrangement in beats. Session slots have their own methods. A bridge can expose only part of that surface; inspect actual tools and version capabilities. [Track API](https://docs.cycling74.com/apiref/lom/track/)

**EQ/compression:** native devices can be controlled through exposed parameters. Discover parameter names, enabled state, ranges, quantization, and displayed units before writing values; read them back afterward. Parameters controlled by macros or automation may not behave like freely editable knobs. The LOM's native-device insertion method is available since Live 12.3 and does not insert third-party plug-ins. [DeviceParameter API](https://docs.cycling74.com/apiref/lom/deviceparameter/), [Track insertion API](https://docs.cycling74.com/apiref/lom/track/#insert_device)

For Producer Pal, third-party plug-in internals require manually configured Live parameter mappings; store those mappings in racks. Changing a visible parameter is not proof of an audible improvement. Use level-matched listening and measured audio evidence, not arbitrary gain increases or the presence of a compressor, to judge a revision. [Documented plug-in boundary](https://producer-pal.org/features/limitations)

**Runtime:** these candidates operate on an open Live instance with the Remote Script, Max device, or extension active. A headless MCP process does not make Live a headless render service. Proposed deployment is a homelab coordinator controlling a Windows DAW worker with an available desktop session, local media paths, installed instruments, and a working audio engine. Server-only rendering is unverified.

## Export is the critical validation gap

The inspected ordinary Live API/bridges do not establish a universal offline post-effects master export call. One other implementation, [jterratsdev/ableton-live-mcp](https://github.com/jterratsdev/ableton-live-mcp/blob/main/docs/ableton-python-remote-script.md), explicitly returns `501` for real Remote Script render/bounce routes; its development WAV artifacts must not be confused with Live-rendered music.

Producer Pal's [render helper source](https://raw.githubusercontent.com/adamjmurray/producer-pal/main/examples/skills/ableton-analyze-audio/render.mjs) drives the Export dialog through AppleScript on macOS, assumes English/default shortcuts, and produces MP3 review output. Windows would need a separately validated UI path or custom recording bridge. Real-time resampling is a possible engineering alternative, but requires routing, transport, start/end/tail alignment, and dropout checks; it is not equivalent to proven offline export.

Ableton's Export dialog supports Main output and selected/all-track exports, with explicit return/Main-effects options. Active Session clips can affect what is rendered. Establish the intended Arrangement playback state and verify the exported audio itself. [Live export manual](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/#exporting-audio-and-video)

## Undo and durable versions

The LOM provides undo/redo, but MCP exposure varies. Use grouped reversible edits where supported. Keep a separately saved baseline `.als` and a revision Set with required media collected; tool state snapshots are supplementary. Live's manual says undo history is not retained after closing a Set, and Save As/Save a Copy produce named versions. [Song API](https://docs.cycling74.com/apiref/lom/song/), [Set saving and history](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/#live-sets)

## Short validation before integration

1. Identify installed Live edition/version, Max availability, exact intended MCP, source format, and required third-party devices. Inspect the running tool/capability list before assuming compatibility.
2. On a copied 20–30-second test Set, import one audio file or aligned stems; read back file references, positions, duration, warp settings, and Arrangement state.
3. Make one bounded arrangement change and one native EQ/compressor parameter change. Verify readback, audible result, and undo; save/reopen the revision and confirm persistence.
4. Prove Windows export of the actual processed mix to a unique lossless file. Confirm duration, channel/sample format, non-silence, effects audibility, tails, clipping/true peak, and loudness. Compare with a manual reference export, allowing for nondeterministic devices.
5. Let the user compare level-matched baseline/revision. Approve an audio version and hand its file/hash, duration, tempo-map assumptions, and provenance to video production.

Until that pass succeeds, describe the stage as proposed audio assistance with an export gap. Automation access alone does not establish mixing or mastering quality.

## Recommendation following user comparison request

Five relevant implementations were inspected (the four main candidates plus jterratsdev); this is a research shortlist, not an exhaustive ecosystem count. Prioritize Producer Pal for its broader Arrangement/MIDI/mixer control and direct REST integration, conditional on Max for Live availability. Keep ahujasid's Remote Script implementation as the simpler alternative. Avoid making the beta Extensions SDK a first production dependency before validation.

Local read-only executable inspection found `C:\ProgramData\Ableton\Live 12 Intro\Program\Ableton Live 12 Intro.exe` with product version `12.3.1`. A `Live 12 Suite` directory also exists but a corresponding executable was not found at its expected `Program` location in this bounded check. This does not establish the active license/edition or Max for Live availability. No Ableton MCP tools are callable in this task, and no candidate was installed or connected.

The user subsequently confirmed they currently have **Intro** and are getting version **12.4.6**. Ableton's [Buying Max for Live](https://help.ableton.com/hc/en-us/articles/206407124-Buying-Max-for-Live) explicitly excludes Intro/Lite; Suite includes it and Standard supports the paid add-on. The current [edition comparison](https://www.ableton.com/en/live/compare-editions/) agrees. Therefore Producer Pal is conditional on an edition change, not merely upgrading Intro's version. Evaluate the ahujasid Remote Script alternative against required operations before recommending an edition purchase. No upgrade or installation is authorized by this research decision.
