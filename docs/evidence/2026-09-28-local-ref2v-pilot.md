# Local reference-to-video pilot — 2026-09-28 (in progress)

Linear: V1S-102 (SwarmUI route), V1S-105 (Characters/Looks), V1S-106/107 (timed shots, generation).
Branch `feat/local-gen-pipeline`. Status: **partial** — 16 of 21 planned renders complete (11 base shots + 5 alternate takes); the
check stage, beat cut and user review of the assembled passage are still pending.

## What ran

Everything ran on the Windows workstation (RTX 5090, 32 GiB) through SwarmUI 7861 and its managed
ComfyUI 0.37.0 backend on 7821. `scripts/mvvm_gen` submits API-format graphs, downloads outputs and
keeps a resumable manifest at `.runtime/gen/i-ran-pilot/manifest.json`. Private media stays under
`.runtime/` and is mirrored to `D:\output\local\MVVM\i-ran-pilot` for Swarm history. No paid or
off-host calls were made. The 5:53 master was read from the private `mvvm` bucket through
`proxmox-home` agent-secrets. No credential values appear in commands or files.

| Stage | Model / route | Observed |
| --- | --- | --- |
| Character sheets | Qwen Image 2.1 int8 + qwen3vl_8b; one anchor render, then close-up, front, back and side panels, joined with FFmpeg | 12–24 s per panel; 3.8k×2k sheets; user reviewed and redirected wardrobe several times |
| Clips (s01–s10) | MiniMax H3 ref2va int8, 20 steps, res_multistep, sigma shift 12/3, 1344×768 at 24 fps | 150–223 s per clip |
| Clips (s10 t1–s12) | Same, plus `mini\minimax_h3_turbo_v4_step600_ema` LoRA, 8 steps, euler | 94 s (124 frames), 157 s (4-bar, 180 frames) |

Whole-device GPU memory after H3 jobs: 27–30 GiB, sampled with nvidia-smi. That figure includes
other processes and is not isolated model memory.

## Findings

- The user compared the options and chose reference-to-video straight from the character panels.
  Composited Qwen keyframes plus H3 image-to-video were rejected: copied backgrounds and pasted-in
  scale.
- On s10, the 8-step turbo matched the 20-step clip closely at about 2.3× the speed. The 4-step
  LoRA (`minimax_h3_turbo_4step_ema_ckpt500`) was visibly murkier.
- Qwen 2.1 limits: renders above ~1.6 MP break up; chained re-edits drift; two studio references
  at once degrade the result.
- The extras copied the leads' outfits until each location got an explicit crowd rule.
  Flashback and lagoon locations exclude crowds.
- Backend incidents:
  1. After a client-side interrupt, SwarmUI relaunched the backend on 7822. The user requires 7821
     only. SwarmUI was stopped and relaunched with its own launcher, and the client now refuses
     other ports.
  2. Later the backend and SwarmUI both disappeared while `s13` was marked running, and `wait()`
     blocked until its 60-minute timeout. Jobs now time out after 20 minutes, and a lost prompt is
     resubmitted once after 7821 returns.

## Not yet verified

Clips s13–s16, the mechanical check report, the assembled 34-bar passage (59.6 s from the loudest
bar-aligned window, currently 224.34 s), timing agreement within one frame, and the user's review
of the result. Identity consistency was judged from sampled frames, not by an automated reviewer.
