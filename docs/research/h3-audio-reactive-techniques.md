# MiniMax H3: audio-reactive / beat-synced techniques (research, 2026-09-28)

Collected by a research agent across GitHub, MiniMax docs, Comfy blog, Civitai and write-ups (Reddit/X only via
secondary sources). Unverified items are marked.

## Prompt language
- Per-accent vocabulary (official MiniMax MV skill, `MiniMax-AI/MiniMax-H3/skills/music-video-subtitle-generator`):
  hi-hat roll -> micro-shake / frame skips; snare -> scale-up / hard cut / shoulder drop; 808 -> compression /
  stretch / offset; hard cuts only, no fades; cuts on the 1/4 or 1/8 grid, never inside a sung vowel; 0.3-1.2 s shots
  with "stop dead" on the hit.
- Trap MV recipe (minimax-h3.wiki): "Sync hard cuts ... to bass hits, snares, and hi-hat rolls".
- Name one or two major accents per chunk and forbid the rest: "Do not cut or shake the camera on minor beats."
- Timestamp syntax: no timestamp on the first shot, then `[Shot 2] At 00:04.167, the camera cuts to ...`, strictly
  increasing.
- Name physical camera moves precisely ("truck left plus pan right"); avoid contradictions (one take + cuts).
- A vocal in reference audio makes the performer sing; use an instrumental / percussion slice for silent performers.
- No sourced phrasings found for stutter, speed ramps or laser flicker (unverified; do them in the edit).

## Graph / workflow
- filliptm/ComfyUI-FL-MiniMaxH3: Audio Beat Prompt Schedule -> Beat Shot Planner -> Shot Motion Context (5 video /
  22 audio frames, trimmed at assembly) -> Beat KSampler -> Shot Assembler; audio-reactive prompt envelopes.
  Whether per-segment prompts truly switch inside one H3 generation is unverified (single packed sequence).
- Percussion stem as its own reference audio drives in-time motion (Comfy H3 Sync Sound Challenge, "Feel It");
  never feed several stems of one mix (phase-cancel).
- Sigma shift 12 (video) / 3 (audio) are coupled; claims that raising audio shift tightens rhythm are unverified.
- Edit rhythm from a reference video: "Follow Video 1 strictly for shot rhythm, transition style, cut order, and music
  timing." (minimax-h3.wiki reference-edit-rhythm-transfer). H3 video editing can also replace a person in a clip.
- Reference audio of exactly 15.075 s duplicated frames; 15.070 s did not (ethanfel/ComfyUI-MiniMaxH3-Contex-Loop).
- seitanism/ComfyUI-H3-Motion-Context-MultiRef (installed here): keyframes at arbitrary positions, master-song
  latent masking.

## Identity
- Restate the full look in every [Shot N]; a bare label or "the same man" drifts (ai-muninn two-character test).
- res_multistep + beta/normal beats simple for reference-heavy prompts (ComfyUI docs).
- ref_image_size max: 22% slower, no visible identity gain in one test.
- Stay >= 864x480 in reference mode; flat neutral light in references (H3 carries reference lighting).

## Try first (for 8-15 s chunks with the song slice as reference audio)
1. Per-accent vocabulary + name 1-2 major hits + "no cuts or shake on minor beats".
2. Percussion stem as a second reference audio for dance/B-roll chunks.
3. FL Beat Prompt Schedule / Shot Planner / Motion Context.
4. res_multistep + beta, shifts 12/3, restate wardrobe per shot.
5. Keep reference audio a few ms short of generation length at 15 s.
