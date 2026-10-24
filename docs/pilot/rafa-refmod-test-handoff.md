# Rafa RefMod + unseen scene image: quick agent test

## Mission

Test whether an image of Rafa in a new environment improves generation when combined with his existing RefMod. Prepare comparable videos and a timecoded review, using the local workflow already open. This is a small rendering experiment, not an application build.

## Starting point

- Workspace: C:/Users/Gordo/Documents/Github/music-video-vending-machine.
- ComfyUI: http://127.0.0.1:8188/#fb424b88-5a7d-4b4f-b077-05bde6195232.
- Open workflow: PlagueKind_Rafa_14s_RefMod_16x9_06MP_1Kref.
- Existing RefMod: Rafa_identity_full, visibly enabled at master/visual strength 1.00 and one copy. Reuse it; rebuilding it is outside this experiment.
- Its sole source, confirmed by the user: C:/Users/Gordo/Downloads/9d98d0d3-3b9a-43e1-9d8b-a217f4f4b0a5.png. SHA-256: CCDDE04998D35A5EE9A75F8D5F6313EFF38476D42A600BF04DEC8D610D547817.
- New scene image: C:/Users/Gordo/Downloads/hf_20261007_150905_29578d4f-909d-43c0-847d-d173e649fa95 (1).png. SHA-256: 60D632B3AC61FEFC0AE50B8434DFE49A6E2156E4400B7DA6FF6646D1146D8411.
- The user identifies the scene image as outside the RefMod source collection. It depicts Rafa beside a misty moonlit jungle gorge, with airborne debris and an alarmed expression; treat it as an in-action reference, not a pre-run pose.
- UI inspection showed 12.0 seconds, 16:9, 0.70 MP (1312 x 736), res_multistep/simple, 20 steps, and 1024 visual-language image resolution. The workflow title is not authoritative for settings. Read the actual exported graph before running.

## Roles and steps

1. **Orchestrator:** create a fresh experiment folder in the established working folder. Export a baseline workflow and record the actual model, RefMod, prompt, reference map and settings. Preserve the user's original workflow and existing outputs. Done when the baseline can be restored and the inputs are identified.
2. **Prompt writer:** compile the single shared brief below using this workflow's actual Ref2VA/mixed-input grammar and reference map. Use the same creative description for all conditions; only input/alignment declarations may differ. Done when every subject/picture/audio label resolves to a real input and the prompt agrees with the generation duration.
3. **Render operator:** use copies of the baseline workflow, explicitly fixed seeds 241137 and 241138, and unique output prefixes. For subsequent runs, enter the prompt/settings in the visible ComfyUI browser tab and press its top Run button so the user can follow progress and previews. APIs may collect histories and outputs. Reuse the loaded RefMod and existing checkpoint. Done when each output has its exact prompt, workflow/settings, seed, input roles and render duration recorded.
4. **Independent reviewer:** receive anonymous clips, the shared brief and reference images, without the condition key. Watch temporal video, not merely contact sheets. Record technical/filmmaking and story/performance judgments before the orchestrator reveals conditions. Done when findings have timestamps, severity and usable ranges.
5. **Orchestrator:** reveal conditions, compare matched seeds, and deliver playable results plus findings. Two seeds provide an initial indication, not proof that one approach always wins.

## Render conditions

| Condition | Identity conditioning | Scene image role | Seeds |
| --- | --- | --- | --- |
| A | Existing Rafa_identity_full | Absent | 241137, 241138 |
| B | Same RefMod | Additional visual reference; not fixed at frame zero | 241137, 241138 |
| C, follow-up | Same RefMod | Actual first-frame anchor | 241137, 241138 |

Run A/B first: four renders. C is an authorized optional follow-up if the active workflow supports first-frame anchoring together with RefMod. Record unsupported conditions rather than silently substituting another input mode.

Use the same model, sampler, steps, dimensions, duration, RefMod strengths/copies, enabled LoRAs, audio slice/settings and enhancement settings for each matched pair. Remove other identity/scene image conditioning from both A and B so the supplied scene image is the only added visual input. Preserve any required non-image conditioning equally. If a mode necessarily changes an additional setting, record the difference and qualify the comparison.

Keep the new image separate from the RefMod; adding it to the RefMod would invalidate this test. Hash both supplied files and record any resize/crop. Derive picture numbers from the actual reference map, including references injected by the RefMod. The base H3 prompt grammar is not a universal replacement for Ref2VA grammar.

## Shared creative brief

One uninterrupted 12-second cinematic shot. Rafa is already falling downward through the moonlit jungle gorge shown in the scene image. Preserve his curly dark hair, face, moustache/goatee, earrings, open olive shirt, gray bandana, beads and backpack straps. Mossy rock pillars, vines, teal moonbeams and mist establish the environment. The camera travels beside him during the fall, then approaches a clear face close-up. Debris moves coherently with gravity while his hair and loose clothing lift relative to his descent. His face shows alarm through widened eyes, raised brows and parted lips; he visibly reacts to nearby falling debris. The last portion settles into readable slow motion while he continues descending. Maintain the same identity and location through the middle of the shot. This experiment ends during the fall, without a landing or return to running.

This is a semantic brief, not a precompiled model prompt. It deliberately tests one continuous action first. Later multi-cut tests belong in a separate experiment.

## Review and deliverables

Score 1-5 separately for identity/wardrobe, environment/composition, motion/anatomy, image quality, camera/continuity and emotional clarity. Inspect opening, middle and ending; specifically test whether the scene image helps beyond initial composition. Flag reverse travel, twisted limbs, face drift, fuzzy/damaged areas, frozen motion, disconnected camera changes and deadpan performance.

Identify usable ranges: a broken opening does not reject a strong later segment. Record source in/out times, defects near trim boundaries, whether the retained action is understandable, and whether enough footage remains for an edit. Entirely technically broken footage is unusable. Mark uncertain observations as uncertain. If only frame sampling is available, disclose sampling and leave unobserved motion unverified.

Deliver:

- Original baseline and each executed workflow export, compiled prompt, input hashes/roles and complete settings manifest.
- Four playable A/B renders with unique paths; optional C renders clearly separated.
- Anonymous review report and a separate condition/seed key, revealed after review is recorded.
- A short conclusion: what improved, what failed, usable ranges, and one recommended next test. Link actual files; distinguish render completion from observed video quality.

Stop after this batch and report. Further prompt revisions or broad stress testing are subsequent experiments. Reference quality is the variable here; competing LLM prompt interpretations come later.
