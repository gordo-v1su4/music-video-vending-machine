# Automatic editing: Project Stack source evidence

Focused read-only inspection, 2026-09-25. Source root: `C:/Users/Gordo/Documents/Github/project-stack-structure`, local `main` at `0e8c45c`. No execution, visual review, or quality benchmark performed. These findings describe examined algorithms, not every editing path in that repository.

## Main finding

There is useful attribute-based ranking to reuse, but the examined selection flow does **not** implement the user's rule to leave a shot missing when every candidate is unsuitable. It generally selects the best available candidate, warns about weak matches, and favors filling coverage. Our product needs an explicit acceptance gate before ranking can commit a clip.

## Existing evidence

| Capability | Source evidence | Interpretation |
| --- | --- | --- |
| Clip attributes | `src/components/studio/types.ts:36-90` includes motion angle/magnitude/coherence, camera type/strength, residual motion, entropy, acceleration, confidence/provenance, and first/middle/last color palettes. | Useful metadata model. Presence of fields does not prove every uploaded clip has reliable measurements. |
| Suitability ranking | `semanticEditPlanner.ts:216-262` under `src/components/studio/` combines semantic text (0.30), lyrics (0.14), action intent (0.26), duration fit (0.12), motion continuity (0.10), motion energy (0.08), color continuity (0.04), minus repetition. `200-214` sorts by score. | Deterministic heuristic score, not calibrated probability or confidence of a good edit. Weights sum to 1.04 before penalties/clamping. Text similarity is keyword-based in `264-285`; this is not a multimodal critic. |
| Motion compatibility | `motionRanking.ts:4-19,37-58` compares dominant angle, magnitude, coherence and camera-motion type, multiplied by minimum descriptor confidence. | One descriptor per moment in the scorer, not explicit motion at the selected out-point and in-point; no next-neighbor argument. No measured guarantee of screen-direction or cinematic continuity. |
| Color and energy | `semanticEditPlanner.ts:376-418` compares prior exit/current entry color using numeric distance, and section energy to motion descriptors or text heuristics. `musicVideoProject.ts:437-452` wires caption, action, subjects, setting, shot type, motion and palette into semantic moments. | Good cheap signals. Similar palettes or movement can still produce a narratively wrong or jarring cut. |
| Sequence choice | `musicVideoProject.ts:743-764` walks sections using previous selected moment and use counts. `777-796` starts with the first ranked candidate. `1061-1117` selects preview candidates using readable duration, repetition, shot-family/source diversity, duration coverage and original rank. | Sequential heuristics and section reservations, not demonstrated global sequence optimization. Preview selection does not recompute exact adjacent-cut motion/color compatibility. |
| Duration fitting | `fitPolicy.ts:27-128` supports accept, trim, bounded speed adjustment (default maximum delta 0.15), overlap, or reject. Its callers include coverage classification and manifest candidate ranking. `panels/RampTab.tsx:168-223` derives curve anchors from section energy and presets. | Duration policy and curve UI exist. No evidence here that scoring evaluates actual retimed motion at both cut boundaries, optical-flow artifacts, lip-sync constraints or rendered ramp smoothness. Do not infer rendered speed-ramp support from the curve alone. |
| Missing-slot machinery | `editPlanCoverage.ts:80-118` separates missing/short/weak/filled and proposes replacement needs. `185-218` blocks only missing slots. `storyTreatments.ts:457-502` can classify an anchor as missing and leave its selected candidate null. | Reusable gap vocabulary and narrower story-anchor rejection already exist. Main edit acceptance remains permissive. |

## Conflicts with the requested behavior

- `semanticEditPlanner.ts:102-113` assigns the top candidate before recording a weak-match informational finding.
- `musicVideoProject.ts:1073` falls back to all candidates when none pass its readable-duration preference; `1116` always returns the first remaining candidate. `818-825` explicitly reuses reserved material to keep coverage complete.
- `editPlanCoverage.ts:266-274` labels below-45% matches optional review; weakness does not block Join. An approved generated replacement is given score 1 and full required duration in `161-170`, rather than being freshly scored against neighboring edits.
- `panels/matchModes.ts:23-39` implements the displayed color mode score using semantic/motion scores, not the color-continuity field. Do not reuse that label as evidence of actual color ranking.

## Proposed product rule and next interview choice

Store separate **observed attributes**, **measurement confidence**, **suitability score**, **neighbor-transition scores**, and **accept/reject reasons**. Hard constraints run before ranking; rejected candidates remain inspectable but unassigned. Evaluate source trims and speed transforms in the context of both neighbors. A slot with no acceptable candidate becomes a visible missing-shot request with duration, action, framing, entry/exit motion and references. Vision review then checks the proposed sequence against the approved direction; technical scores do not replace viewing it.

Suggested short interview question: **When no clip fits, what should happen next?** Choices: automatically generate a replacement within the approved budget; prepare a replacement request for approval; leave the slot for manual work. Preserve the user's existing rule that unsuitable material must not be silently inserted.
