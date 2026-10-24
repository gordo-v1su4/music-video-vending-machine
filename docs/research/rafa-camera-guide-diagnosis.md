# Camera relocation near a timed guide

Inspected 2026-10-09 after the user reported the camera cutting back to another place. The visible browser video source was `D:/output/local/MVVM/rafa-single-guide-1mp/rafa-one-guide_00011_.mp4`, executed job `3186eb55-c4e5-4337-8940-152e448f8136`, seed 909770540717858. Its guide image was `hf_20261009_050008_fa8f12a7-1a9d-4d58-8cbd-274ce624123d.png` at frame 120 (5 seconds). This diagnosis is scoped to that artifact, not every preceding clip.

## Observed evidence

Ordered samples every 12 frames at 24 fps show a wider falling-body view before the 5-second guide, a close boot/earth view at 5 seconds, and a return to a wider body view afterward. The guide image has the close boot composition. The executed prompt asks the camera to move from face to boots, swing underneath Rafa, look upward and later approach his face. Its particular earlier negative-action list had already been removed by the user's revision, while some other negative wording remained. These observations do not establish exact cut-frame boundaries or independently prove natural motion.

Evidence: [executed graph](D:/output/local/MVVM/rafa-camera-diagnosis/clip11-executed-api.json), [ordered half-second samples](D:/output/local/MVVM/rafa-camera-diagnosis/clip11-half-second-contact.png). Read source metadata rather than mutable UI fields when reproducing.

## Likely explanation and next controlled test

The abrupt composition change coincides with the timed guide. The strongest current hypothesis is that the model fits that close boot anchor, then resumes the wider falling composition requested by surrounding text. The multi-position camera path increases the continuity demand. This is an inference from placement, input composition and observed samples; it is not a causal proof or proof that all timed guides create cuts.

For a continuous-camera test, use a guide whose camera side, scale, height and action state match the intended view at its target frame. Describe one connected positive camera path and persistent geography. Compare the same prompt and seed with the existing guide versus a matched-view guide or a guide-free version. If an intentional cut is desired, assign the changed framing to an explicit shot boundary and carry action/dust/momentum across it. Keep the camera diagnosis separate from the user's unwanted-action wording correction.

## Later guide placement and frame inspection

The user requested moving the guide to the earlier fall onset. The visible source at that time was `rafa-one-guide_00012_.mp4`; ordered samples at frames 48,54,…,96 show the support breaking and body leaving the ledge around frames 66–72. Root changed the existing Add Guide `frame_idx` from 120 to **72** through the browser UI, renamed its title accordingly and removed the stale frame-120 image-node label. The guide image itself was retained. No Run was pressed for this change; camera continuity at the new placement remains untested.

The embedded preview exposes browser-native elapsed-time controls. A derived [frame-numbered inspection copy](D:/output/local/MVVM/rafa-camera-diagnosis/clip12-frame-number-preview.mp4) overlays zero-based frame indices 0–293. It retains 294 frames at 24 fps, with frame 72 corresponding to 3 seconds. This is a review copy, not a new generation or accepted export. [Frame 72](D:/output/local/MVVM/rafa-camera-diagnosis/frame72-preview.png) and the [fall-onset samples](D:/output/local/MVVM/rafa-camera-diagnosis/clip12-fall-frames-48-to-96.png) preserve the placement evidence.

## Positive wording guidance

The user flagged negated lists of unwanted actions as confusing generation guidance. The saved next heel-ramp draft and prompt-writer handoff now express desired movement positively. Existing submitted prompts remain immutable historical evidence. This correction was not submitted to the browser or queued as a new render. A programmatic negated-action lint rule is guidance/planned work, not an implemented compiler capability.
