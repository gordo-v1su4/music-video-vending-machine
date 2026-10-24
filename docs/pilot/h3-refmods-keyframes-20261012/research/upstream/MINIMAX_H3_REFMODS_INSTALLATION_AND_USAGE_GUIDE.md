# MiniMax-H3 RefMods: Installation & Quickstart Guide

_Version: 1.0.0_  
_Last Updated: September 2026_  
_Repository & Weights: [huggingface.co/malcolmrey](https://huggingface.co/malcolmrey)_

---

## 1. Overview

**RefMods (Reference Latent Adapters)** are pre-encoded conditioning-level adapters (`.safetensors`) for **MiniMax-H3**. They allow zero-training, instant-load facial likeness, anatomical consistency, and multi-character scaling without the live VAE encoding overhead or prompt syntax constraints of legacy reference image workflows.

---

## 2. Where to Get & How to Install ComfyUI Custom Nodes

The RefMod node system is powered by **`ComfyUI-MiniMaxH3Mod`**.

### Installation Steps

1. Navigate to your ComfyUI `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   ```

2. Clone the custom node repository:
   ```bash
   git clone https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod.git
   ```

3. (Optional / If needed) Install requirements in your ComfyUI virtual environment:
   ```bash
   pip install -r ComfyUI-MiniMaxH3Mod/requirements.txt
   ```

4. Restart **ComfyUI**.

---

## 3. Where to Get RefMod Weights (`.safetensors`)

All open-weight MiniMax-H3 RefMod models and sample benchmark datasets are created by **malcolmrey** as an open research and community project, available on Hugging Face:

- **Hugging Face Hub:** [https://huggingface.co/malcolmrey](https://huggingface.co/malcolmrey)
- **Model Files:** `minimaxh3_<name>_v1_refmod.safetensors` (approx. 1.1 MB – 1.6 MB per character/concept).

---

## 4. Where to Put Downloaded RefMods

Place all downloaded `.safetensors` files into the ComfyUI **`models/refmods/`** directory:

```text
ComfyUI/
├── models/
│   ├── checkpoints/
│   ├── loras/
│   ├── vae/
│   └── refmods/                  <── Place RefMod .safetensors files here
│       ├── minimaxh3_adamdriver_v1_refmod.safetensors
│       ├── minimaxh3_adrianalima_v1_refmod.safetensors
│       ├── minimaxh3_aarontaylorjohnson_v1_refmod.safetensors
│       ├── minimaxh3_adele_v1_refmod.safetensors
│       └── ...
```

> **Note:** If the `models/refmods/` folder does not exist yet in your ComfyUI installation, create it manually. The `MiniMaxH3RefModsLoader` node will automatically scan and populate dropdown menus with all `.safetensors` files located in this folder.

---

## 5. Workflow Node Wiring

In your MiniMax-H3 video workflow (Text-to-Video, Image-to-Video, or Clip-to-Video C2V), insert the two RefMod nodes between the conditioning loader and the guider / motion context:

```text
[ MiniMaxH3ImageToVideo / ReferenceToVideo ] (conditioning out)
                    │
                    ▼
          [ MiniMaxH3RefModApply ] ◄── [ MiniMaxH3RefModsLoader ] (loads mod_1 .. mod_8)
                    │ (conditioning out)
                    ▼
     [ BasicGuider ] / [ MiniMaxH3MotionContext ]
```

### Node Parameters

1. **`MiniMaxH3RefModsLoader`**:
   - **`mod_1` .. `mod_8`**: Select your target persona or anatomy RefMod `.safetensors` from the dropdown list.
   - **`strength_1` .. `strength_8`**: Adapter injection weight (default: `1.0`).
   - **`copies_1` .. `copies_8`**: Token repeat factor (default: `1`).

2. **`MiniMaxH3RefModApply`**:
   - **`conditioning`**: Connected to conditioning output of `MiniMaxH3ImageToVideo` or `MiniMaxH3ReferenceToVideo`.
   - **`mods`**: Connected to `mods` output of `MiniMaxH3RefModsLoader`.
   - **`retention`**: `1.0` (constant retention across sampling steps).
   - **`curve_direction`**: `constant`.

---

## 6. Prompting with RefMods

When using RefMods, you do **not** need positional image tags (such as `<Picture 1>`). Simply write standard multimodal prompts using subject tags and biometric descriptions:

```text
subject_definitions:
<Subject 1> Billie Eilish, natural authentic human appearance, expressive eyes, modern dark streetwear...

integrated_multimodal_description:
[Shot 1] Live-action, 35mm cinematic look, fine film grain. Continuous take. Medium close-up framing of <Subject 1> looking directly into the camera lens with clear facial expressions...
```

For multi-character scenes, assign `mod_1` and `mod_2` in the loader and define `<Subject 1>` and `<Subject 2>` in your prompt. MiniMax-H3 will automatically map the identity latents without token collisions.

---

## 7. RefLoRA: one file, LoRA or LoRA + RefMod

A **RefLoRA** is that pairing already packed into one `.safetensors`. A normal LoRA loader uses it as a LoRA and ignores the references. **Load H3 RefLoRA** uses both.

Install, wiring, and packing: **[`MINIMAX_H3_REFLORA_GUIDE.md`](MINIMAX_H3_REFLORA_GUIDE.md)**.

Format notes: **[`MINIMAX_H3_HYBRID_LORA_REFMOD_CONTAINERS_GUIDE.md`](MINIMAX_H3_HYBRID_LORA_REFMOD_CONTAINERS_GUIDE.md)**.

Separate LoRA and RefMod files still work. On the Jinx terrace test, RefMod plus the identity LoRA beat either alone, and epoch 60 was enough. Clips: **[`lora/README.md`](lora/README.md)**.
