# Review of Document 2

Reviewed 2026-10-17. [Submitted source](document-2-updated-chatgpt-prompt-skill.md) is preserved byte-for-byte. Recommendation: retain as a proposed revision; do not replace the installed compiler with this version.

## What improves

The revision drops unsupported causal stories about cloning and appearance prose. It focuses on observable actions, compatible camera states, current entry poses, and action complexity suited to available time. Distinguishing timestamped prose from frame schedules is also useful. These are writing safeguards to validate with renders, not guaranteed model behavior.

## Changes needed before adoption

- Separate requested duration (14 seconds), requested frame count from the saved expression (345), playback at 24 FPS (14.375 seconds), and last valid zero-based frame index (344). A schedule key of 345 is outside a 345-frame clip. If the creative action ends at 14 seconds, explicitly decide how the remaining 0.375 seconds is handled; do not silently extend a cut or trim audio/video. Verify actual decoded output after generation.
- Preserve frame 118 as a guide placement, not an automatic cut boundary. Align a cut there only when the shot plan calls for it and the guide matches the desired shot state. Guide conditioning and scheduling remain different mechanisms.
- Display frame 118 as approximately 4.916667 seconds or 00:04.917, with integer frames authoritative. A displayed 4.9 seconds does round back to frame 118 at 24 FPS, but it is not its exact timestamp. Define half-frame rounding explicitly rather than relying on language-specific round behavior.
- Retain the installed H3 encoder's required sections, reference identifiers, and shot syntax. Raw bracketed time intervals are a compiler representation, not universally valid native encoder input. Confirm scheduler compatibility and interpolation behavior before claiming frame-exact switches.
- Include the mandatory linter, strict final rerun, intentional exception reporting, guide/reference wiring checks, and adjacent-shot state audit. This proposal omits these safeguards even though they are central to the user's requested workflow.
- Keep the 14-second/345-frame/guide-118 values in a named recovered-baseline profile. General H3 defaults must follow the actual selected workflow, FPS, duration, and guides. A reference setup for one clip should not silently govern unrelated scenes.
- Define pacing for cuts shorter than 1 second, the gaps between stated ranges, and shots longer than 6 seconds. Treat the ranges as flexible editorial guidance.
- Retain concise reference-matching wardrobe details as an explicit, reviewable option when relevant. Avoid claims that their presence or absence reliably fixes identity.

The example also needs a prop-state audit: gripping a microphone stand in the first cut and holding a microphone close in the second may require a compatible visible starting state or deliberate cut. It is not automatically a contradiction, but it should be checked against the guide image.

The final readiness-only reply is source content, not an instruction to suppress a requested review or implementation report.

## Disposition

The installed `h3-ref2v-dynamic-compiler` remains unchanged. Its existing separation of guide frames, cut boundaries, native H3 grammar, and executable schedules is preferable. No new generation prompt was authored, no workflow settings were changed, and no render was submitted during this review.
