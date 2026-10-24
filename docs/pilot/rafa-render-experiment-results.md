# Rafa rendering experiments

## Completed reference comparison

Four local renders compared the existing Rafa_identity_full RefMod alone (A) with the same RefMod plus the supplied new scene image as an untimed visual reference (B). Each condition used seeds 241137 and 241138, the same creative brief, actual 1088 x 608 output, 20 res_multistep/simple steps, and the same audio/model settings. The user sees provenance; reviewers received anonymous clips and stayed isolated until their reviews were saved.

| Clip | Condition | Seed | Execution seconds | Wall seconds | Playback |
| --- | --- | --- | ---: | ---: | --- |
| 03 | A: RefMod | 241137 | 180.57 | 185.50 | [video](D:/output/local/MVVM/rafa-refmod-ab/clip-03.mp4) |
| 01 | B: RefMod + scene image | 241137 | 219.38 | 220.56 | [video](D:/output/local/MVVM/rafa-refmod-ab/clip-01.mp4) |
| 04 | A: RefMod | 241138 | 198.90 | 200.41 | [video](D:/output/local/MVVM/rafa-refmod-ab/clip-04.mp4) |
| 02 | B: RefMod + scene image | 241138 | 194.89 | 195.55 | [video](D:/output/local/MVVM/rafa-refmod-ab/clip-02.mp4) |

All four decode successfully at 24 fps with 294 frames and 12.25-second video/audio streams. No black spans or freeze spans were detected using blackdetect d=0.1/pix_th=0.1 and freezedetect n=-50dB/d=0.5. These checks do not certify physical motion, identity, anatomy, storytelling or sound quality. The 12-second generation setting rounds to H3's 294-frame grid.

The additional image contributes an estimated 4,158 native visual-reference tokens, plus the library-reported 1,508 Rafa RefMod tokens. The image estimate comes from installed source, not a runtime token counter. Timing varies by seed and cache state; these four samples do not establish universal performance costs or quality superiority.

An initial attempt using the canvas preview's 1312 x 736 dimensions was interrupted and preserved separately. Only the four corrected successful renders appear above.

Evidence: [manifest](D:/output/local/MVVM/rafa-refmod-ab/manifest.json), [timings](D:/output/local/MVVM/rafa-refmod-ab/render-timings.json), [technical metrics](D:/output/local/MVVM/rafa-refmod-ab/technical-metrics.json), [reference cost evidence](D:/output/local/MVVM/rafa-refmod-ab/reference-cost-evidence.json). Each clip has an exact API graph, prompt, submission and history beside it.

## Independent reviewer models

| Selected model | Preferred clip | Report |
| --- | --- | --- |
| GPT-6 Luna (`gpt-6-luna`) | 02 | [review](D:/output/local/MVVM/rafa-refmod-ab/reviewer-comparison/luna/review.md), [scores](D:/output/local/MVVM/rafa-refmod-ab/reviewer-comparison/luna/scores.json) |
| GPT-6.1 Sol (`gpt-6.1-sol`) | 01 | [summary](D:/output/local/MVVM/rafa-refmod-ab/reviewer-comparison/sol/summary.md) |
| GPT-6 Astra (`gpt-6-astra`) | 02, conditionally | [comparison](D:/output/local/MVVM/rafa-refmod-ab/reviewer-comparison/astra/comparison-and-coverage.md) |

These are independent ordinal judgments, not ground truth or a statistical ranking. All three preferred a candidate made with the scene image, but disagree about the best candidate and score severity. Luna generally rates emotional impact higher; Sol and Astra emphasize missed causal acting and motion requirements. Sol/Astra identify shorts changing to trousers in clip 03. No review establishes an unmistakable debris-triggered reaction throughout the required action.

All three used ordered frame samples at 4 fps, supplemented by native-size details and tail checks. They did not ingest native temporal video or assess audio. Sampling can miss short defects and does not prove natural motion, exact gravity, camera cadence or slow-motion easing. Their usable ranges remain provisional until complete playback. Initial preliminary review files under blind-review are separate from this explicit three-model comparison.

## Higher-resolution prompt tests

The user requested subsequent renders through the visible ComfyUI tab, with prompt entry and the top Run button. APIs collect results and metadata only. Existing workflow copies and output snapshots preserve every submitted version; repeated manual workflow saving is unnecessary for collecting the actual executed state.

- Original user six-shot/trapdoor prompt: UI job 050932e1-f172-4699-9527-4853d0559cac, fixed seed 241139, 1.0 MP / 1312 x 736, completed in 329.29 execution seconds after clearing VRAM. [Video](D:/output/local/MVVM/rafa-next-prompt-1mp/rafa-next-1mp.mp4). Exact user text matched the queued graph's 4,356 characters. [Workflow metadata](D:/output/local/MVVM/rafa-next-prompt-1mp/embedded-workflow.json) and [executed prompt graph](D:/output/local/MVVM/rafa-next-prompt-1mp/embedded-prompt.api.json) were extracted from the actual MP4.
- User crumbling-ground replacements for Shots 2-4: UI job 658f7814-3cee-4735-a2fe-fc4f240df95b. Same seed/settings; summary and audio event wording aligned with crumbling instead of trapdoor. [Collected video](D:/output/local/MVVM/rafa-crumbling-prompt-1mp/collector-rafa-next_00002_.mp4), 353.82 execution seconds. Mechanical decode/black/freeze checks pass; causal and visual acceptance remains open.
- Closer match-on-action continuity revision: UI job f567822e-8c77-4742-80bc-9bb55d4e8129. Tight body-scale framing and persistent dust, advancing edge collapse, slipping boot and downward body motion carried between cuts. [Collected video](D:/output/local/MVVM/rafa-continuity-close-1mp/collector-rafa-next_00003_.mp4), 297.07 execution seconds, 1 MP / 1312 x 736. Mechanical checks passed; visual acceptance remains open.
- User continuous-camera/no-cuts prompt: UI job db8b2fdc-691c-42f5-a087-2a63f0e9dcbc. Exact user wording; same seed/settings. [Collected video](D:/output/local/MVVM/rafa-continuous-camera-1mp/collector-rafa-next_00004_.mp4), 333.13 execution seconds, 1 MP / 1312 x 736. Mechanical checks passed; visual acceptance remains open.
- User's separately queued two-shot/one-cut variation: UI job faf82a1c-db81-4cbd-8648-407d7a1eb0c8. [Collected video](D:/output/local/MVVM/rafa-two-shot-1mp/collector-rafa-next_00005_.mp4), 262.67 execution seconds. Actual executed resolution was 0.8 MP / 1184 x 640 despite the collection folder name. Prompt contained 3,725 characters; exact graph and metadata preserved. Mechanical checks passed; visual acceptance remains open.

Higher-resolution prompt versions are not the same experiment as the original reference comparison. Compare causal continuity and framing against each version's own intended camera path; retain usable segments instead of automatically rejecting an entire render for a defective portion.

## Guide-frame experiment

The user authorized testing the two supplied boot images as timed interior guides. [Capability research](../research/h3-middle-guide-frames.md) verifies an installed native MiniMaxH3AddGuide node, separate from untimed references. The copied graph contains guides at frame 62 (2.583 seconds) and frame 120 (5.0 seconds), Rafa's existing RefMod, seed 241139 and 1 MP output. The actual browser API export confirmed all 48 nodes' execution settings matched the candidate; only four node titles differed. A frontend tab-registration alert occurred after the graph loaded. Two orphan links were inherited from the source GUI; no runtime patch or installation was made. See [import diagnosis](D:/output/local/MVVM/rafa-guide-frame-1mp/import-diagnosis.txt).

After clearing model/cache memory in the visible UI, the top Run button started job **ab692d87-4bfe-40bb-a103-f8e016e802c8**. [Collected video](D:/output/local/MVVM/rafa-guide-frame-1mp/collector-rafa-guides_00001_.mp4): 337.06 execution seconds, 1312 x 736, 24 fps, 294 frames / 12.25 seconds. Decode passed, with zero detected black/freeze spans at the existing thresholds. The executed graph confirms both guides at frames 62/120; exact prompt, GUI/API workflow, history, original output and embedded metadata are preserved. Prompt: 4,479 characters, SHA256 `95dc67e2ac66022a36e457521ddb69bfdbc53d8c86a828805345324bd1c073eb`.

The user also corrected the motion brief: the collapse must continuously carry the running momentum into an immediate fast downward fall, without stopping or sitting, followed by a gradual playback ramp into slow motion while descent continues. This trial changes both the prompt and timed guides; it cannot isolate the contribution of guides. Visual/motion acceptance remains open. Automated reviewers remain paused at the user's request.

Review the entry into the fall, not only the final pose: support disintegrates under the loaded boot; downward translation begins before the knees fold; no seated/settled pause or second takeoff; dust and rubble continue through the transition. Evaluate the real-speed fall separately from the later speed ramp. Identity and wardrobe defects block the affected shot; inspect other shots for salvage before rejecting the whole clip.

### One-guide comparison

The user observed that both anchors appeared to be imposed and requested keeping only the downward-angled falling-boot image. The hypothesis is that the ground-contact anchor constrains the collapse into an unwanted pose; it is not yet a verified cause. The contact guide at frame 62 and its loader were removed, retaining the falling guide at frame 120. The exact 4,479-character executed prompt, seed 241139, references and 1 MP settings match the two-guide run. The previously stale unused prompt-note text was synchronized with the active prompt.

The browser's cached media list initially reported the retained image missing despite its visible preview and existing input file. Selecting/uploading the same `rafa-guide-2-frame-120.png` through the node's UI resolved that frontend validation. An actual UI API export confirmed exactly one native guide and the intended output prefix. After UI model/cache clearing (3,138 MiB GPU memory reported), top Run started **ee4f9fae-68e8-4956-a5cf-0c828c761c72**. [Collected video](D:/output/local/MVVM/rafa-single-guide-1mp/collector-rafa-one-guide_00001_.mp4): 300.18 execution seconds, 1312 x 736, 24 fps, 294 frames / 12.25 seconds. Decode passed with zero detected black/freeze spans; exact queued/executed/embedded graph, workflow and prompt, metadata and logs are preserved. `collector-executed-comparison.json` confirms identical Combined inputs and seed, 46 nodes and exactly one guide at frame 120. Visual acceptance and whether removing the contact anchor improves motion remain open; no subjective reviewer was dispatched.

Later creative variations are recorded separately: heel-led contact, the speed ramp beginning while the loaded heel digs and keeps sliding through the collapse, continuous camera travel over the boot, and motion blur that preserves readable contact detail. They were not added to this one-guide comparison. The user's later live edits apply to future submissions; queued execution settings are preserved for comparison.

The user supplied four new motion-blur image variants after this run. They are not the guide used in either completed comparison. The fourth (`hf_20261009_050057_e1fd9c3a-ca53-4900-8518-e62b3883abe1.png`) depicts an unsupported angled boot above the landslide; the second/third retain more of the ground-contact stage. Treat these as candidate alternate anchors with reviewed timing/camera roles, not four simultaneous guides by default.

### Second-image motion-blur trial

The user explicitly requested trying the second supplied variant despite its larger visible ground mass. The retained single guide's image was changed through the visible Upload control to `hf_20261009_045912_2c92a505-e709-4e13-b973-e4806af05a62.png`, SHA256 `0B8EF87E9249F7ADAAA82B1EAB5AF177406C3AB9472F68A2BBE4BE690DCF3B6A`. Root left guide timing, seed and prompt untouched; the actual queued/executed graph must establish whether independent user edits changed any other inputs. This tests the supplied image as a whole, not blur strength in isolation.

After UI cache/model clearing (2,729 MiB reported), top Run started **085e52b7-9bfe-47b5-b18d-ca9b66649ff3**. [Collected video](D:/output/local/MVVM/rafa-blur-guide-1mp/collector-rafa-one-guide_00002_.mp4): 316.54 execution seconds, 1312 x 736, 24 fps, 294 frames / 12.25 seconds. Decode passed with zero detected black/freeze spans. Actual queued/executed comparison confirms only the guide image changed relative to the preceding one-guide trial; prompt, seed, placement and other inputs match. The original output prefix remains `rafa-single-guide-1mp/rafa-one-guide`; the receipt identifies this distinct trial rather than inferring its condition from the filename. A still's apparent blur does not establish temporal movement.

The user subsequently reported that the alternate ground-contact/motion-blur picture brought back a stop, shoe movement and then a separate fall, and switched the next trials back toward the falling-angle image. This is a user-observed failure mode and preferred direction, not a universal proof that motion blur or all ground-contact guides fail. The user described the falling-angle result as useful/promising while speed-ramp timing remains awkward. Preserve the successful ranges and exact inputs before changing timing. The unqueued [next heel-ramp prompt](D:/output/local/MVVM/rafa-blur-guide-1mp/next-heel-ramp-prompt.txt) incorporates the latest heel-led slide and ramp-on-contact direction.

### User-operated randomized queue

The user enabled randomized seeds and queued takes directly in the visible UI. Root inspected the queue and did not add duplicates. Three initial captured IDs used the same one-guide blur-contact picture and exact 4,479-character prompt: `8db73d23-426f-4431-9f7e-41216c33efab` (seed 243885044649477), `bfc79b1d-97a0-42ac-84d6-7753ce4b7237` (529054502437983) and `33916772-71c6-44ab-995f-9b64faca3a84` (84954363620845). The latter two subsequently disappeared from both queue and history; cancellation is inferred, not confirmed. Their captured receipts remain preserved.

The first take completed in 357.09 seconds and was collected under `D:/output/local/MVVM/rafa-randomized-blur-guide-1mp/seed-243885044649477/collector-rafa-one-guide_00004_.mp4`. Later queue snapshots contained three new jobs using `hf_20261009_050057_e1fd9c3a-ca53-4900-8518-e62b3883abe1.png`, the fourth supplied falling-angle blur variant:

| Captured job ID | Seed | Status at handoff |
| --- | ---: | --- |
| 5c58b1bc-a31e-400b-ac24-92988398f265 | 388608669273415 | Collection pending |
| bcab3e2c-0fe5-4c77-9a1c-23fda292dc81 | 581137133127615 | Collection pending |
| 6b401e14-c830-49e3-ba28-654850ef2e7b | 987321352725476 | Collection pending |

Queue snapshots are historical, not live state. Consult collector receipts/history before reproducing, retrying or assigning a condition. The user requested wrapping up documentation without waiting for these renders. No new subjective reviewers were dispatched, and pending renders are not accepted outputs.

## Demo chain results (2026-10-10)

Evidence root `.runtime/gen/demo-v1s155/` and `.runtime/gen/i-ran-pilot/production/`. Eros two-pass demo workflow,
0.25/0.5 MP, seed 410071 on the rgthree node for every controlled render.

- **Story** (user, this day): they never reunite. C0 run → C1 ledge breaks, face-up drift into fog → C2 moonlit
  flashback of the night they met (Rafa POV) → C3 present day, Lune runs away along the same ledge. Direction for
  C2: mysterious, hazy, anamorphic fashion-film look, blue/green lasers only, no pink.
- **Guide-count trial** (prompt/seed/refs fixed): T0 no guide, T1 B f120, T2 A f62 + B f120. Blind frame-sheet
  reviewers rated T0 weakest; T2's break/tumble is used in cut 1. Motion between guides still needs playback review.
- **First C2 renders** followed the old "crashes into the festival" brief (cand-8eb4d2, cand-3d0eea): story-wrong,
  rejected. r10 C2/C3 from two isolated writer teams matched the new story; C2 Look drifted in the close-up.
- **C2 Look repair** (ArcFace median vs Lune portrait, uncalibrated, close-up range): original 0.408; RefMod only
  0.491; RefMod + portrait as `<Picture 1>` 0.576; RefMod + Qwen 2.1 last-frame guide f208 0.491; + early guide
  f110 0.488. PlagueKind V11 fl2v_refs (first/last + portrait, no RefMod) is the most polished visually.
- **Multi-view RefMod** `Lune_identity_multi` (8 views, 640 px, 5120 cap; sha256 9d10ecf8…) vs `Lune_identity_full`
  on the identical executed graph, ArcFace median vs the named master close-up: V2 graph 0.563 → **0.676**,
  V3 graph 0.491 → **0.602**. Built partly from drifted Qwen views; a rebuild from face-swap views is next.
- **Cut 1**: `production/edits/cut-v1.mp4`, 34.375 s (825 frames) on the song 3:49.3–4:23.7, timing within one
  frame; 4 joins valid with frame evidence; `cut-unsafe-demo` shows a rejected regressing join.
