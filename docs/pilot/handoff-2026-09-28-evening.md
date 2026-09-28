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

### Identity test result (finished after this note was first written)

| Variant | Face median (same person >= 0.45) | Cut error vs prompt (s) |
|---|---|---|
| v2 s0 (anchor+closeup, Heavy, protect_audio, ref audio) | 0.24 | 0.09 / 0.31 / 0.28 / 0.31 |
| v2 s1 | 0.17 | 0.04 / 0.48 / 0.30 / 0.22 |
| v2dense s1 (sparsity 0) | 0.26 | 0.04 / 0.48 / 0.30 / 0.22 |

**Likely root cause (prompt bug, fix first):** `graphs.h3_ref2v_prompt` always writes the retention line as
`<Subject 1> (appears in [Shot 1]): fully_preserved ...`. True for the old one-shot clips; in the c25 montage Shot 1
is the POV with no Lune, and she is in Shots 2-5, which the prompt never marks as preserved. The montage shots also
say "Lune"/"her" instead of the `<Subject 1>` tag the H3 format uses in every shot (see
`multicut-reference-prompt.md`). And the plan `look` now starts with wardrobe text saying the headwrap is optional
while every reference picture has it. Fix: retention lists the shots she actually appears in; every shot with her
uses `<Subject 1>`; keep the headwrap in text when the refs have it. Re-test with face_check.py (old one-shot clips
scored 0.31-0.40; montage 0.11-0.26).

Protection settings, better panels and dense attention do **not** fix identity: H3 ref2v does not hold Lune (old
single-shot clips were only 0.31-0.40). This time later cuts landed 0.2-0.5 s after the prompt, so the splice step is
essential. Options to try next (measure each with face_check.py):
- first/last-frame route (`pk_v11_fl2v_refs`): a Qwen 2.1 keyframe with her face as the first frame of each shot;
- a face-swap / face-restore pass on rendered takes against her identity image (common production fix);
- shorter, image-first identity text (long text descriptions can outweigh the reference pictures);
- fewer shots per generation when she is on screen (the montage format scored worst).

## Next

1. Fix identity first (options above); make the winner the plan default. Face score >= 0.45 before any batch.
2. Write the v2 chunk prompts for the pilot window (chunks 23-30) from `story-v2-beats.md`: crowd reach and
   almost-touch on the 3:47 hit, rope-bridge dream, the fall (strobe on the beat), the stutter landing, the stranger
   reveal that reads, fire / escape; movement hits at impact times; ramp shots generated slow.
3. Render (song on every clip), face-check, splice each chunk, watch in Review -> First cut.
4. Later: stacked alternates (layers) to swap takes in the cut; camera re-render from a clip (ReCamMaster-style);
   Wan Dancer for danced phrases; Linear updates V1S-102/105/106/107/111; PR when the user asks.

References: `seedance-reference-cuts.md` (target cut grammar), `story-v2-beats.md`, `multicut-reference-prompt.md`.

User check of the c25 renders (confirms the diagnosis): the headwrap drops out and the eyes close-up does not look
like her. Plan `look` now requires the silver headwrap in every shot (fixed in the plan); the `<Subject 1>` tagging
and retention-line fix in `graphs.h3_ref2v_prompt` / the chunk prompts are still to do.
