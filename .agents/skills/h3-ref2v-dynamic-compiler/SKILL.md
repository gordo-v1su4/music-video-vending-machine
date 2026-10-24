---
name: h3-ref2v-dynamic-compiler
description: Preferred H3 Ref2V prompt skill for multi-cut scenes, audio-reactive timing, scoped prompt repairs, and contradiction checks. Compile timestamped cuts and matching frame schedules; lint before delivery. For base T2VA/I2VA/FL2VA/L2VA grammar use h3-prompt-writing.
---

# H3 Ref2V Dynamic Compiler

This is the user's preferred writing profile for H3 reference-conditioned video. Apply it first for Ref2V multi-cut and audio-reactive prompts, including prompts used through SwarmUI's ComfyUI backend. Keep the user's scene, approved references, timing, and working passages intact.

Read [the supplied source](references/user-source.md) for the full six laws and irregular-cut example. The source is preserved as supplied; its final readiness-only reply applies only to a bare initialization request, not to actual work.

## Establish the executable contract

Identify duration, FPS, actual conditioning node, reference map, guide frames, cut boundaries, and whether a prompt scheduler is connected. Use 24 FPS and five-second shot intervals only when the user supplies neither. Explicit timestamps and frame numbers take precedence. For supplied frame indices, retain the exact integers; derive display times from frame/FPS.

Separate three mechanisms: text describing a cut, an image wired as a timed guide, and a scheduler that changes conditioning. A timestamp in text does not create a guide. A JSON schedule is executable only when the installed scheduler and video sampler consume it correctly; do not promise zero bleed or exact cuts from a text prompt alone.

For this user's H3 render tests, default to explicit 1344 x 768 output dimensions unless they request another size. Verify the width/height reaching the latent constructor; an MP slider is not proof of the dimensions (different nodes use decimal or binary pixel units). Preserve archived baseline settings, and label a resized working copy as a variation. Check the prompt's pose, camera angle and background against each injected guide at its actual frame and the shot active there.

Use the actual node's supported duration/frame grid. The user's 15+ second scope does not establish a checkpoint's tested duration. Request-level frames use round(seconds * FPS); model latent-grid padding is a separate calculation. Use decimal round-half-up for fractional frames (4.2 * 24 = 101).

## Compile each cut

1. Start in its current physical state. State an action once, in present tense, rather than retelling prior cuts. Preserve continuity through compatible entry/exit states, camera side, props and rotation direction. “Amnesia” means independent wording, not permission for state jumps.
2. Start with one bracketed camera command and one shot size. Give each cut one primary camera vector; align framing with visible action. A close-up cannot simultaneously show the whole body.
3. Identify each principal once early in the cut, then use pronouns. Use references for appearance; omit appearance prose unless the user requests an override or the node's reference binding needs a minimal identifier.
4. Pace action to available time: 0.5–2s = one micro-action, at most 35 words; 2.5–5s = one fluid action or connected pair, roughly 40–65 words; 6s+ = sustained movement with gradual progression, roughly 60–85 words. Treat word ranges as editing heuristics, not token limits imposed by H3. For gaps between ranges, use the nearest simpler action budget.
5. For audio-reactive cuts, use observable accents: synchronized steps, sharp head snaps, rhythmic bounce, pulsing light or camera micro-shake. Keep calm/peaceful direction out of explicitly high-energy cuts, while preserving an intentional slow intro or a requested speed ramp.
6. End each cut with the same exact short environment/lighting suffix for shots sharing a location. Put intended visible actions in generation text. Keep negatives, failure lists, and interpretive wrap-ups in review notes.

For repairs, replace only the failing passage. Preserve untouched text, timings and reference labels. Audit the prior exit state and the repaired entry state before declaring it ready.

## Deliver two matching representations

**Block 1 — timestamped cuts:** one line per shot, e.g. `[00:00.000 - 00:03.500] [Slow orbit] Medium shot. The dancer ... jungle canopy, teal haze, warm torchlight.` Millisecond precision avoids losing exact frame timings at 24 FPS; one-decimal display is fine only when exact.

**Block 2 — frame schedule:** a valid JSON object whose string keys are exact starting frame numbers and whose values are the identical shot bodies from Block 1. Use JSON escaping for quotes and newlines. Supply a bare entry fragment only when the actual scheduler requires one; commas separate entries and the last entry has no trailing comma.

These blocks are the user's custom compiler format, not a replacement claim about H3's native grammar. If the positive encoder expects official Ref2VA text, use `h3-prompt-writing`'s six-field wrapper and `[Shot N] At MM:SS.mmm` cut grammar, keeping actions only in `detailed_description`; make the required summary a short task label, not a replay. Read `references/ref-en.txt` from that installed skill. For base modes read its `references/base-en.txt`. If unavailable, report that specific missing dependency rather than inventing headers.

## Lint and review

Run the bundled standard-library checker before delivering the two blocks:

```text
python scripts/lint_prompt.py cuts.txt --fps 24 --duration 15 --schedule schedule.json --context context.json
```

Paths above are relative to this skill folder. `--context` is optional JSON: `{"subject_anchors":["the dancer"],"environment_suffix":"jungle canopy, teal haze, warm torchlight.","high_energy_shots":[2,3],"appearance_override":false}`. Match context to the current shot plan; use `environment_suffixes` keyed by one-based shot number for multiple locations.

For every native H3 prompt, including a single-shot rewrite, run `python scripts/lint_prompt.py prompt.txt --format h3 --fps 24 --duration 15 --strict` with its actual FPS/duration. When this repo's production input map is available, also run its existing `scripts/mvvm_gen/h3lint.py` structural/reference checker. This skill's checker complements that checker; it does not replace actual reference-map validation.

Before delivering or submitting any newly written or revised H3 prompt, fix every error, resolve every warning (or record a concrete intentional exception), and rerun after edits. Use `--strict` for the final pass. Report the pass result and any exceptions. Existing archived prompts are audited read-only; never rewrite an archive just to make lint pass. Mechanical checks cover intervals, frame math, schedule equality, camera/framing conflicts, common typos, repeated words, likely prior-action replay, and likely violations of the user's writing profile. Warnings do not establish model causality, and a clean result does not certify physics, identity, motion continuity, or render quality. A separate continuity audit must compare each shot's entry/exit physical state, actor, camera side and rotation direction. This is an agent preflight; it does not intercept a human's Run button.

The supplied explanations about appearance prose, noun repetition, past tense, and conditioning are user hypotheses and writing heuristics, not verified internals of diffusion attention. Preserve useful rules as this profile; distinguish them from findings established by matched render comparisons. Workflow edits, installs, and renders require their own task authorization.
