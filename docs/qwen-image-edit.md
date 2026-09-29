# Qwen Image 2.1 edit: the locked call

The one approved way to edit a still (put a character into a frame, fix a panel, swap a person). It rebuilds the
user's SwarmUI workflow `Data/Workflows/kim-ho-qwen/swarm-safe-qwen-2.1-pe-i2i.json` node for node. The user
approved it on 2026-09-28 ("that was solid"). Do not change it without the user.

| Piece | Where |
|---|---|
| Command | `python -m scripts.mvvm_gen.qwen_edit` (`scripts/mvvm_gen/qwen_edit.py`) |
| Graph builder | `graphs.qwen21_edit` |
| ComfyUI API JSON | `workflows/qwen-image-2.1-edit-pe.api.json` (regenerate with `--export-api`) |
| Batch use | `python -m scripts.mvvm_gen.board_fix PLAN board2 [--panels p31] [--seeds 2]` (storyboard panels) |
| Backend | Swarm-managed ComfyUI on 127.0.0.1:7821 only |

## Usage

```bash
python -m scripts.mvvm_gen.qwen_edit --scene panel.png --ref lune-identity.png --ref lune-front.png --prompt "Replace the woman in <image1> with Lune from <image2> and <image3> ..." --out out.png --seed 7
```

Output: `out.png` (always 1344x768) and `out.json`. The JSON records:

- the instruction
- the enhancer's rewritten prompt
- the seed, refs and prompt id

## The rules that make it work

1. **The scene is `<image1>`, conformed to 1344x768 first.**
   - The Qwen 2.1 encoder (`TextEncodeQwenImage21`) sizes the canvas from the *first* reference; its tooltip says
     "any other size shifts the edit". When a portrait came first, the shot was reframed and faces grew.
   - `qwen_edit.conform` fits the scene to `SIZE` (lanczos, centre trim of a few percent at most for near-16:9
     panels). At `resolution` 1024 that maps to exactly 1344x768.
   - So output size and framing never depend on the refs.
2. **Character refs come after the scene** (`<image2>`, `<image3>`, ...): the named masters (see below). Any size works. Use the close-up for the
   face and the full-body sheet panel for the outfit.
3. **Model and sampling:**
   - `qwen_image_2.1_bf16`, 40 steps, euler / simple, cfg 1, denoise 1.0
   - the canvas is the encoder's own latent output
   - **no LoRA** (no turbo or Lightning), **no masks, no img2img**. Masked face inpaints and partial denoise were
     tried and failed: mangled bodies, eyes opened underwater, pasted-on faces.
4. **Prompt enhancer on.**
   - The Benji enhancer: `benjiyaya/ComfyUI-Qwen-Image-2.1-Prompt-Enhancer`, node `QwenImage21_EditPromptRewrite`.
   - Model `qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot`, sampling 1.0 / 0.95 / 0 / 24000.
   - It looks at the images and rewrites the instruction. `--no-pe` skips it.
   - For text-to-image there is the sibling `QwenImage21_T2IPromptRewrite` with the `pe_t2i` model.
5. **Prompt content: short, in the user's format. The enhancer fills in the rest.**
   - Write one or two sentences, operation first, for example: "Replace the woman in `<image1>` with Lune from
     `<image2>` and `<image3>`, same face, smooth clear skin. She is underwater with her eyes closed; keep all the
     bubbles, with bubbles drifting in front of her face and body. Match the underwater lighting and colour grade of
     `<image1>`."
   - Its system prompt (`custom_nodes/ComfyUI-Qwen-Image-2.1-Prompt-Enhancer/prompts/system_prompt_edit.txt`)
     expects "a vague edit instruction + image(s)". It then writes the precise directive itself: image roles, the
     identity transfer, blending, and one blanket preservation clause.
   - **Point identity at the reference image, never describe the face in words.** In the enhancer's own rules:
     "verbal descriptions make the model regenerate and degrade the likeness." Describing what should stay also
     makes it drift.
   - Add only what matters for the shot: eyes closed, bubbles in front, motion blur on a fall, "he is not smiling",
     "match the lighting and colour grade of `<image1>`". Phrase each one affirmatively.
   - Measured on board2 p31: the long verbose prompt scored identity 0.46–0.50 with the face 14% small. The short
     prompt scored 0.63 with the face 0.99× and a 0.5% shift.
   - Name each character as on their reference. **Never name a feature the character lacks**, not even negated
     ("no freckles" paints freckles); say "smooth clear skin" instead.
   - For big changes, chain steps. Each step edits the previous output. Example (p23): 1. "Remove all the people
     from the image, leaving only the smoke and mist." 2. "Put Lune from `<image2>` into `<image1>` …".
   - The enhancer's rewritten prompt is saved in each output's `.json` sidecar. Read it when a result is off.
6. **Scoring:** face-check each result with `face_check.py` or `board_fix.face` (ArcFace, same person ≥ 0.45). Then
   look at it: the score does not see anatomy, eyes or framing.

## Character references

Use each character's **master**: the named sheet close-up `sheets/<cid>/closeup-named.png` (plan `master_ref`), with
copies in `D:\output\local\MVVM\i-ran-pilot\<cid>\<Name>-master.png`.

- Never use the old `refs/*-identity.png` photos. Lune's has a scarf and freckles, and both leaked into the edits.
- **A name goes in a prompt only when that name is printed on the reference being passed** (the named master). An
  unlabeled image plus a name confuses the model. The edit prompts say "the woman from `<image2>`".
- One master per character is enough. The enhancer transfers the costume from it, and says on its own to leave the
  caption text out of the image.

## Formula log (measured, board2 p31 underwater close-up)

The enhancer decides the operation from the verb. **"Replace the woman…" becomes a face swap** (everything else is
"kept unchanged" at the input's low quality). **"Put the woman from `<image2>` into the scene of `<image1>`…"
becomes compositing**: the whole person is re-rendered with the master's costume and relit, and the bubbles really
go in front of the face.

| Wording | Enhancer read it as | Identity | Face size / shift | Look |
|---|---|---|---|---|
| Long descriptive (identity in words, old ref) | face swap | 0.46–0.50 | 0.86× / 0.8% | eyes open or half open, bubbles dropped |
| Short "Replace the woman in `<image1>` with Lune from `<image2>`, same face…" (old ref) | face swap | 0.63 | 0.99× / 0.5% | good face; rest of the frame low-res; freckles from the ref |
| A "Recreate `<image1>` … a completely different woman: Lune…" (old ref) | face swap | 0.76 | 0.96× / 0.9% | same as above |
| D "Based on the environment of … use the woman in `<image2>` to recreate her…" (master) | face swap | 0.59 | 0.98× / 0.6% | rest of the frame low-res, freckles |
| **C "Put the woman from `<image2>` into the scene of `<image1>`, in the same position and pose… Match the exact lighting and environment of `<image1>`, with bubbles drifting in front of her face."** (master) | **compositing** | 0.36* | 0.82× / 3.4% | **whole frame re-rendered sharp, bubbles over her face, full costume, matched teal light** |
| **E = upscale first ("Keep colors exactly the same, upscale the image.") then C** (master) | compositing | 0.42 / 0.79 | 0.88× / 2.4% ; 0.82× / 11.5% | take 1: sharp everywhere, the panel's composition, bubbles on her face, faint freckles (the enhancer says "freckled skin tone", read off the master). Take 2: clearly her, but recomposed into a centred portrait (rejected by the proportion check) |

\* ArcFace is low when bubbles cover the face and the head is turned. Judge by eye.

Lessons:

- **Settled recipe (2026-09-28): upscale, then C**, one character per pass, with "with smooth clear skin" for Lune. The proportion check picks the takes that kept the panel's composition.
- Use **C's formula to replace a whole person** (the user's preferred look).
- Use "Replace … same face" only when the rest of the frame is already production quality.
- **Low-res source:** upscale the scene first (single image, no tags): "Keep colors exactly the same, upscale the
  image." Output quality follows input quality (research doc).
- Never write the character's name alone as a description ("a completely different woman: Lune"). Point at the
  image.
- Worth testing next (from research): cfg 3–3.5 with a negative prompt for limbs and fingers; one character per pass
  for two-person shots; a crop-edit-stitch pass for hands and small faces.

Research sources: [docs/research/qwen-image-edit-formulas.md](research/qwen-image-edit-formulas.md).
