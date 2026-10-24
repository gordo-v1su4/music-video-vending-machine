# Document 1: Grounded Technical Reference (MiniMax H3 Baseline)

Received 2026-10-17. The submitted document is preserved below, followed by review notes. This is a snapshot of the recovered workflow, not a universal H3 configuration. [Document 2](document-2-updated-chatgpt-prompt-skill.md) and its [review](document-2-review.md) are saved alongside it.

## Submitted document

### 1. Architecture & Resolution Constraints (MiniMax H3 Only)

- **Spatial Compression:** MiniMax H3 uses **16× spatial VAE compression** followed by **2× patchification** (**32× effective spatial downsampling**). Do not mix rules from other models (like LTX-2 or Wan).
- **Temporal Compression & Workflow Frame Math:**
  - H3 officially documents **4× temporal compression**.
  - Your saved workflow uses **24 FPS** for a requested **14-second duration**, with a custom rounding expression that outputs **345 total frames** (note: **`345 = 4 × 86 + 1`**).
  - **Guide Image Index:** Set at **Frame 118** (**`118 ÷ 24 ≈ 4.917 seconds`**). If you are designing a cut or major transition around the guide image, **Frame 118 (~4.9s)** is your actual anchor point, not Frame 120 (5.0s).
- **Resolution Pair for `7:4` (`1.75:1`) Aspect Ratio:**
  - **Current Baseline:** **`1344 × 768`** (**`42 × 24`** patched tokens at 32× downsampling).
  - **Matched 2-Pass Experiment Pair:** **`896 × 512` → `1344 × 768`** (**`28 × 16`** → **`42 × 24`** patched tokens). Both preserve the exact **`7:4`** aspect ratio and 32-pixel divisibility.

### 2. Installed SLA Node Specifics

- **Sparsity (`>60%`) & `tail_correction: false`:** In your installed SLA implementation, **`tail_correction`** is set to **`false`** (meaning the linear residual branch is disabled, running pure sparse block masking). Per the node's own tooltip, keep sparsity above **~60%** so sparse mask calculation overhead doesn't exceed dense attention runtime.
- **Testing Rule:** Keep **`1344 × 768`** and your original reference images as the control baseline. Test any change (such as dense warmup steps or the **`896 × 512 → 1344 × 768`** two-pass setup) one variable at a time on a locked seed.

### 3. Prompt Conditioning & Scheduling Reality

- **What Prompt Discipline Actually Fixes:** Preventing the LLM from contradicting camera/lighting states, restating already-completed actions in later cuts, or writing summary sentences at the end of a prompt are practical safeguards against conflicting text conditioning.
- **What Remains Hypothesis:** Rigid rules like "never repeat a subject noun or it will clone" or "never mention any wardrobe detail in Ref2V" are hypotheses, not proven H3 behavior. In fact, light wardrobe/context cues can sometimes help if they match your reference image.
- **Single Box vs. Scheduled Format:** Putting **`"0": ...`**, **`"118": ...`** into a standard text box will **not** automatically schedule conditioning—it will just read the numbers and quotes as literal text unless that string is wired into an actual scheduling/splitting node in ComfyUI. Use **Block 1** for standard single-text-encoder setups, and **Block 2** only if wired to a scheduler or multi-segment conditioning node.

## Review notes and operational qualifications

Agreement: the architecture arithmetic, matched resolution pair, guide timestamp, preservation of original references, and controlled comparison method are sound. Apply these qualifications when using this document:

1. **Requested frame count versus verified output.** The recovered graph's expression is `max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17`. At `a = 14`, it requests 345 frames. It rounds to a count congruent to 5 modulo 17; it is not a general `4n + 1` expression. The fact that 345 also equals `4 × 86 + 1` does not establish that every duration is valid. Verify downstream normalization and decoded frame count before promising a new duration. At 24 FPS, a 345-frame clip has a nominal playback duration of 14.375 seconds; its last zero-based frame index is 344.
2. **Spatial tokens per temporal slice.** `42 × 24 = 1008` and `28 × 16 = 448` describe the spatial video-token grid for each latent temporal slice, not the complete packed attention sequence. Temporal slices, text, audio, and reference inputs also contribute tokens.
3. **SLA implementation terminology.** Treat `tail_correction: false` as disabling this node's optional tail correction. Do not equate that option with the learned linear-attention branch of the original SLA research implementation without checking the installed code. Approximately 60% is the installed tooltip's reported performance break-even, not a mandatory validity threshold or a quality recommendation. The recovered baseline uses sparsity 0.70, block size 32, dense step `0`, and dense backend `comfy_kitchen`; it can still execute dense fallback paths.
4. **Guide timing and cut timing are distinct.** Frame 118 is the requested guide index; it does not itself create a cut, and it does not require every cut to move to that frame. Inspect guide-to-latent indexing before claiming frame-perfect anchoring.
5. **Encoder grammar precedes presentation format.** Block 1 is a drafting/presentation format, not a universal drop-in replacement for the installed H3 encoder's structured prompt grammar. Compile it into the actual encoder format and preserve reference identifiers and required sections. Block 2 needs a compatible, connected scheduler, and that scheduler may interpolate or blend rather than perform hard cuts. A multi-segment node also needs its actual timing behavior checked. Neither format guarantees sharp cuts or motion continuity.
6. **Prompt heuristics require render evidence.** Contradiction and repeated-action checks reduce avoidable prompt conflicts; they do not certify conditioning behavior. Matching wardrobe cues are an option to test when useful, not a proven improvement for every reference setup. Continue the required H3 linter and adjacent-shot review before delivering or submitting new or revised prompts. This archived document is not itself a generation prompt.

## Evidence

- [Official MiniMax H3 architecture and specifications](https://huggingface.co/MiniMaxAI/MiniMax-H3): spatial VAE 16×, temporal VAE 4×, patchification `1 × 2 × 2`, and default 24 FPS.
- Recovered working graph: `D:/output/local/MVVM/metadata-audit-20261017/Rafa_1908001_Working_1344x768.api.json`, nodes 15 (SLA), 32 (frame expression), 35 (combined conditioning), 38 (guide), 42 (FPS), and 46 (guide index).
- Installed node guidance: `D:/ComfyUI-Easy-Install_v3122/ComfyUI-Easy-Install/ComfyUI/custom_nodes/plaguekind-nodes/ComfyUI-H3-SLA-Attention/sla_node.py`.

No workflow parameters or render queue entries were changed when saving this document.
