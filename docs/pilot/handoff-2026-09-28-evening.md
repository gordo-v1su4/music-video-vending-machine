# I Ran pilot: handoff, 2026-09-28 evening

Branch `feat/local-gen-pipeline`, pushed; no PR yet (user: not yet). Earlier notes: `handoff-2026-09-28.md`.

## Where things stand

- **Studio** (`bun run --cwd=apps/web dev`, 127.0.0.1:5198) with a local coordinator (`pwsh scripts/dev-coordinator.ps1`,
  reads the gitignored `.env.local`) and the review server
  (`python -m scripts.mvvm_gen.review_server scripts/mvvm_gen/plans/i-ran-pilot.json`, 127.0.0.1:5197).
- **Song map** (Story tab): energy curve, zoom, one playhead (studio-clock), music-driven **cut map** with density
  slider (`apps/web/src/lib/cut-map.ts`), stutters / impacts / builds / prompt chunks (`edit-plan.ts`),
  "Export edit plan" -> `.runtime/gen/i-ran-pilot/edit-plan.json` (39 chunks at 45%).
- **Review tab**: First cut (synced to the transport), Take review (per-setup seed pairs), Revisions.
- **Splice**: `python -m scripts.mvvm_gen.run splice <plan> --chunk N --render PATH` splits a chunk render at its real
  cuts and places each shot on its exact music slot; measured within 10 ms. Chunk 25 (chorus 3:49.3-3:58.1) is
  spliced from `audio-test/c25-song-s0.mp4`.

## Findings (measured)

- **Cut timing** comes from the prompt's timestamps: PK V11 cuts within 0.03-0.25 s of the prompted time (no early
  offset). The splice makes the delivered cut exact.
- **Song conditioning**: locking the song into the output latent alone did not change pictures or timing. H3's
  **reference audio** path (PK combined `audio` input, `<Audio 1>`) is what the model reads; community tests show
  it drives rhythm. Now on for every clip: `run clips` feeds each shot's slice as reference audio + locked output
  (`song_conditioning: false` turns it off). The prompt must say the audio drives cuts and movement.
- **`protect_audio` was off** in our V11 SLA settings, so sparse attention dropped parts of the prompt and audio
  tokens. Now on in the plan's `clip_overrides`.
- **Identity** (ArcFace vs `refs/lune-identity.png`, `scripts/mvvm_gen/face_check.py`, run with ComfyUI's venv
  python): sheets are good (anchor 0.77, front 0.65, closeup 0.60, portrait 0.58); old single-shot clips 0.31-0.40;
  the five-shot montage 0.26 (seed 0) and 0.11-0.17 (seed 1). Same person is >= 0.45. We fed portrait + front;
  the anchor panel was unused.

## Running when this was written

`python -m scripts.mvvm_gen.identity_audio_test scripts/mvvm_gen/plans/i-ran-pilot.json` (log
`.runtime/gen/identity-test.log`, results `audio-test/c25-idtest-results.json`): chunk 25 with anchor + closeup refs,
Heavy Enforcement, protect_audio, reference audio + lock, audio-driving prompt; variants v2 s0, v2 s1, v2dense s1
(sparsity 0). Re-running the command skips renders that already exist and re-scores them.

## Next

1. Read the identity test results; pick refs + protection settings that score >= 0.45; make them the plan default.
2. Write the v2 chunk prompts for the pilot window (chunks 23-30) from `story-v2-beats.md`: crowd reach and
   almost-touch on the 3:47 hit, rope-bridge dream, the fall (strobe on the beat), the stutter landing, the stranger
   reveal that reads, fire / escape; movement hits at impact times; ramp shots generated slow.
3. Render (song on every clip), face-check, splice each chunk, watch in Review -> First cut.
4. Later: stacked alternates (layers) to swap takes in the cut; camera re-render from a clip (ReCamMaster-style);
   Wan Dancer for danced phrases; Linear updates V1S-102/105/106/107/111; PR when the user asks.

References: `seedance-reference-cuts.md` (target cut grammar), `story-v2-beats.md`, `multicut-reference-prompt.md`.
