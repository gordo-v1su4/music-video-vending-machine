# Paused handoff — I Ran hero keyframes — 2026-10-13

Paused at the user's explicit request. Do not submit, restore, or resume renders until the user resumes work.

ComfyUI queue verified empty after interrupting the final overhead repair (c63fd037-df17-45c8-9ae3-45b04fd8c811). The remaining read-only collector was stopped. ComfyUI itself remains available.

## Saved work

Output: D:/output/mvvm/i-ran-20261013/hero-action

18 distinct numbered shots were rendered, plus two running repair alternatives and one localized Z Image Turbo torso retouch: 21 image candidates, plus the separate torso mask. Files are preserved at original resolution. This is a render count, not a quality acceptance count.

Manual reviews cover primary HERO 01–14 in visual-reviews.json. Primary 15–18, the two running repairs, and torso retouch still require visual review. HERO 08 original is rejected for a duplicate female principal; its single-couple overhead repair was interrupted and has no finished output. Several originals need action/skin polish; HERO 03, 10, 13 have extra pendant variations.

Use shot-manifest.json, visual-reviews.json, extra-job-manifest.json, and pause-job-statuses.json for exact evidence. The pause-history files preserve final extra-job receipts; pause-queue-before/after preserve queue state. The contact sheet may predate extras.

## Resume priorities

1. Review unreviewed outputs and torso mask before accepting them.
2. Compare running repairs against HERO 01 and 04; assess matte skin and natural eyes, upper chest texture and anatomy, action, and light streaks.
3. Resume only the interrupted overhead single-couple repair if still needed. Its plan is overhead-repair-plan.json, workflow H3_Hero_Overhead_Single_Couple_Repair.json. Never restore the whole completed batch.
4. Select the strongest story keyframes; sequence assembly was deferred until tomorrow.

Prompts identify the female by silver headband, yellow flowers and silver clothing rather than a personal name. Pending repair plans use prompt revision 3 with exactly one round medallion for the male. Character references establish one individual per principal; world/action references are exploratory, not identity canon. Both-principal festival shots are memories. Present-day gorge shots must not invent a reunion. No crying.

## Protected workflow and references

Main completed workflow: D:/user/default/workflows/H3_I_Ran_Hero_Action_16_Refined.json

Protected original: D:/user/default/workflows/MVVM_I_Ran_H3_120_Keyframes_Resume.json; hash a4b536ec3caad177361048a23d37052402122c6fcc5e5ad50c56e22c0fda9fbd. Do not run the old 120-frame workflow or reset its counter.

Correct protected original SHA256: a4b536ec3caad177361048a23d37052402122c6fcc5e5ad50c56e22c0fda9fbd.

Native H3 route: 2560x1440, learned latent 2x, simple 10-step / 0.20 denoise refinement, Lanczos 2048x1152 output. Running/overhead repairs additionally use latent contrast 0.90 with preserve_norm false. Do not treat the unreviewed Z Image Turbo experiment as a proved improvement.

Archived references: docs/pilot/i-ran-reference-library-20261012 (43 source images). Motion guides and initial shot plan: docs/pilot/i-ran-hero-keyframes-20261013. Revised D:/input and D:/output prompt plans are authoritative over initial project copies.
