# Hybrid LoRA + RefMod Container Specification & ComfyUI Implementation Guide

> The pack is implemented. How to install it, run a file as a LoRA only or as a LoRA plus its RefMod, and build new files: **[`MINIMAX_H3_REFLORA_GUIDE.md`](MINIMAX_H3_REFLORA_GUIDE.md)**. The node is [ComfyUI-MiniMaxH3RefLoRA](https://github.com/malcolmamal/ComfyUI-MiniMaxH3RefLoRA) (`Load H3 RefLoRA`, `Apply H3 RefLoRA References`, `Pack H3 RefLoRA`). This page is the format notes.

_Version: 1.0.0_  
_Last Updated: September 2026_  
_Target Architecture: MiniMax-H3 (T2V, C2V, R2V), FLUX.2 / Klein9, and ComfyUI Model Pipeline_  
_Repository & Ecosystem: [huggingface.co/malcolmrey/minimaxh3](https://huggingface.co/malcolmrey/minimaxh3) & [huggingface.co/datasets/malcolmrey/various](https://huggingface.co/datasets/malcolmrey/various)_

---

## 1. Executive Summary & Core Answer

### The Core Questions:
1. **Is it possible to create a single `.safetensors` file that is read seamlessly by standard ComfyUI LoRA loaders (`Load LoRA`, `Power Lora Loader`, `LoraLoaderModelOnly`) and ALSO contains embedded RefMod latent data?**
2. **Can a specialized ComfyUI custom node load both the LoRA and RefMod from that single file—applying the LoRA weights to the model/CLIP while simultaneously extracting the RefMod latents for identity conditioning?**

### The Answer:
**YES, 100% natively and losslessly.**

Because of how the **Safetensors binary specification** and **ComfyUI model patching backend** are designed, you can pack:
- Low-Rank Adaptation weight matrices (`lora_down`, `lora_up`, `alpha`)
- Pre-encoded 3D Video VAE reference latent adapters (`refmod.latent` or `refmod.samples`)
- Full RefMod metadata (token budgets, concept type, facial geometry tags, source aspect ratios)

...into a **single unified `.safetensors` file**.

```
                           ┌────────────────────────────────────────────────────────┐
                           │   UNIFIED HYBRID CONTAINER (.safetensors, ~51.5 MB)    │
                           ├────────────────────────────────────────────────────────┤
                           │ • LoRA Weights: diffusion_model...lora_up/down (50 MB) │
                           │ • RefMod Latents: refmod.latent [1, 24, T, H, W] (1.5M)│
                           │ • JSON Header Metadata: token_budget, tags, alpha      │
                           └───────────────────────────┬────────────────────────────┘
                                                       │
                           ┌───────────────────────────┴────────────────────────────┐
                           ▼                                                        ▼
           ┌───────────────────────────────┐                        ┌───────────────────────────────┐
           │   Standard ComfyUI Loaders    │                        │  MiniMaxH3UnifiedLoader Node  │
           │ (Load LoRA / Power Lora Loader│                        │   (New Custom Dual Loader)    │
           ├───────────────────────────────┤                        ├───────────────────────────────┤
           │ • Reads LoRA keys             │                        │ • Reads LoRA keys -> MODEL/CLIP│
           │ • Patches MODEL & CLIP        │                        │ • Reads RefMod latents        │
           │ • Safely ignores refmod.* keys│                        │ • Outputs REFMODS conditioning│
           └───────────────────────────────┘                        └───────────────────────────────┘
```

---

## 2. Technical Mechanics: Why This Works Under the Hood

### 2.1 The Safetensors Binary Architecture
The Hugging Face `safetensors` format is a zero-copy, memory-mapped tensor serialization container with a straightforward binary layout:

```
┌─────────────────┬──────────────────────────────────┬──────────────────────────────────────┐
│ 8 Bytes (uint64)│ N Bytes UTF-8 JSON Header String │ M Bytes Contiguous Raw Tensor Buffer │
├─────────────────┼──────────────────────────────────┼──────────────────────────────────────┤
│ Header Size N   │ {"__metadata__": {...},          │ [Tensor Data 1][Tensor Data 2]...    │
│                 │  "tensor_a": {"dtype", "shape"}, │                                      │
│                 │  "tensor_b": {"dtype", "shape"}} │                                      │
└─────────────────┴──────────────────────────────────┴──────────────────────────────────────┘
```

- **Key Agnostic**: Safetensors does not enforce fixed naming schemas. Any string key can be associated with any arbitrary multi-dimensional tensor.
- **Selective Memory-Mapping**: Tensors are loaded via offset pointers. Reading one tensor key does not require decompressing or parsing unrelated keys.

### 2.2 How Standard ComfyUI LoRA Loaders Parse State Dicts
When ComfyUI (`comfy.sd.load_lora_for_models` or `Power Lora Loader`) loads a `.safetensors` file:
1. It opens the file and obtains a Python dictionary of key-value tensor pairs: `state_dict = comfy.utils.load_torch_file(lora_path)`.
2. It iterates through the target model's parameter names and looks for corresponding keys formatted like:
   - `diffusion_model.<layer>.lora_down.weight`
   - `lora_unet_<layer>.lora_up.weight`
   - `lora_te_<layer>.weight`
3. **Any tensor key not matching known model layers (e.g. `refmod.latent`, `refmod.samples`, `refmod.mask`) is silently discarded without throwing an error or disrupting weight patching.**

Therefore, existing workflows that use standard `LoraLoader` or rgthree's `Power Lora Loader` continue to function with 100% backward compatibility.

### 2.3 How the Unified Dual Loader Operates
The dedicated custom node (`MiniMaxH3UnifiedLoraRefModLoader`):
1. Loads the `.safetensors` file once into memory.
2. Partitions the dictionary into two distinct sets:
   - **`lora_state_dict`**: All keys beginning with `diffusion_model.`, `lora_unet_`, `lora_te_`, `text_encoder.`, or containing `.lora_`.
   - **`refmod_state_dict` / metadata**: Keys matching `refmod.latent`, `refmod.samples`, and metadata from the Safetensors header (`__metadata__`).
3. Passes `lora_state_dict` to `comfy.sd.load_lora_for_models(model, clip, lora_state_dict, lora_model_strength, lora_clip_strength)` $\to$ returns patched `(MODEL, CLIP)`.
4. Instantiates an `H3RefMod` object using the extracted latent tensor and header metadata $\to$ outputs `REFMODS` conditioning for `MiniMaxH3RefModApply`.

---

## 3. Hybrid Safetensors Key Schema Specification

To ensure interoperability across loaders and custom node ecosystems, the hybrid file should follow this standard key convention:

### 3.1 Tensor Payload Keys
| Key Name | Shape | Data Type | Purpose |
| :--- | :--- | :--- | :--- |
| `diffusion_model.<block>.lora_down.weight` | `[rank, dim, ...]` | `float16` / `bfloat16` | Standard LoRA down-projection weights |
| `diffusion_model.<block>.lora_up.weight` | `[dim, rank, ...]` | `float16` / `bfloat16` | Standard LoRA up-projection weights |
| `diffusion_model.<block>.alpha` | `[1]` or scalar | `float32` / `int64` | Standard LoRA scaling alpha |
| `refmod.latent` | `[1, 24, T, H, W]` | `float16` / `bfloat16` | MiniMax-H3 3D VAE reference latent stack |
| `refmod.samples` *(Klein9 / FLUX.2)* | `[B, 16, H, W]` | `bfloat16` / `float16` | 2D VAE spatial reference latents |
| `refmod.mask` *(Optional)* | `[1, 1, T, H, W]` | `float16` | Spatial focus / face isolation mask |

### 3.2 Safetensors Header Metadata (`__metadata__`)
```json
{
  "format": "pt",
  "ss_network_module": "networks.lora",
  "ss_network_dim": "32",
  "ss_network_alpha": "16",
  "h3_refmod_meta": {
    "name": "minimaxh3_billieeilish_hybrid_v1",
    "concept_type": "identity",
    "mode": "encode",
    "token_budget": 8192,
    "token_count": 6144,
    "source_shape": "1024x1024x8",
    "tags": ["billie eilish", "female", "singer", "green hair"],
    "created_by": "malcolmrey",
    "version": "1.0.0"
  }
}
```

---

## 4. Packaging Tool: Merging LoRA & RefMod into a Hybrid File

Use this Python script to combine an existing LoRA `.safetensors` and a RefMod `.safetensors` into a single hybrid container:

```python
#!/usr/bin/env python3
"""
merge_lora_refmod.py
Creates a unified hybrid .safetensors container holding both LoRA weights and RefMod latents.
"""

import argparse
import json
import os
from safetensors import safe_open
from safetensors.torch import save_file


def build_hybrid_safetensors(lora_path: str, refmod_path: str, output_path: str):
    print(f"[+] Reading LoRA: {lora_path}")
    lora_tensors = {}
    lora_metadata = {}
    with safe_open(lora_path, framework="pt", device="cpu") as f:
        lora_metadata = f.metadata() or {}
        for k in f.keys():
            lora_tensors[k] = f.get_tensor(k)

    print(f"[+] Reading RefMod: {refmod_path}")
    refmod_tensors = {}
    refmod_metadata = {}
    with safe_open(refmod_path, framework="pt", device="cpu") as f:
        refmod_metadata = f.metadata() or {}
        for k in f.keys():
            # Prefix refmod tensor keys to guarantee namespace separation
            target_key = k if k.startswith("refmod.") else f"refmod.{k}"
            refmod_tensors[target_key] = f.get_tensor(k)

    # Combine tensor dictionaries
    combined_tensors = {**lora_tensors, **refmod_tensors}

    # Merge metadata headers
    merged_metadata = dict(lora_metadata)
    if "minimax_h3_refmod_meta" in refmod_metadata:
        merged_metadata["minimax_h3_refmod_meta"] = refmod_metadata["minimax_h3_refmod_meta"]
    elif "h3_refmod_meta" in refmod_metadata:
        merged_metadata["h3_refmod_meta"] = refmod_metadata["h3_refmod_meta"]
    else:
        merged_metadata["h3_refmod_meta"] = json.dumps({
            "name": os.path.splitext(os.path.basename(refmod_path))[0],
            "type": "identity",
            "embedded_in_hybrid": True
        })

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    save_file(combined_tensors, output_path, metadata=merged_metadata)
    
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[✓] Hybrid container created successfully: {output_path} ({file_size_mb:.2f} MB)")
    print(f"    - LoRA Tensors: {len(lora_tensors)}")
    print(f"    - RefMod Tensors: {len(refmod_tensors)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pack LoRA and RefMod into a single .safetensors container")
    parser.add_argument("--lora", required=True, help="Path to source LoRA .safetensors file")
    parser.add_argument("--refmod", required=True, help="Path to source RefMod .safetensors file")
    parser.add_argument("--output", required=True, help="Output hybrid .safetensors path")
    args = parser.parse_args()

    build_hybrid_safetensors(args.lora, args.refmod, args.output)
```

---

## 5. Custom ComfyUI Node Implementation

Here is the complete Python code for a custom ComfyUI node (`MiniMaxH3UnifiedLoraRefModLoader`) that loads both the LoRA and RefMod from the single file.

Place this inside `ComfyUI/custom_nodes/ComfyUI-MiniMaxH3Mod/nodes.py` (or as a standalone custom node):

```python
import os
import json
import torch
import folder_paths
import comfy.sd
import comfy.utils
from safetensors import safe_open

class MiniMaxH3UnifiedLoraRefModLoader:
    """
    Unified Node: Loads a hybrid .safetensors container, applying LoRA weights
    to MODEL/CLIP and outputting the embedded RefMod for identity conditioning.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # Allow selecting from either models/loras/ or models/refmods/
        lora_files = folder_paths.get_filename_list("loras")
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "hybrid_name": (lora_files,),
                "lora_model_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "refmod_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05}),
                "refmod_copies": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "REFMODS")
    RETURN_NAMES = ("MODEL", "CLIP", "REFMODS")
    FUNCTION = "load_hybrid"
    CATEGORY = "MiniMaxH3/loaders"

    def load_hybrid(self, model, clip, hybrid_name, lora_model_strength, lora_clip_strength, refmod_strength, refmod_copies):
        hybrid_path = folder_paths.get_full_path("loras", hybrid_name)
        if not hybrid_path or not os.path.exists(hybrid_path):
            raise FileNotFoundError(f"Hybrid model file not found: {hybrid_name}")

        print(f"[MiniMaxH3UnifiedLoader] Loading container: {hybrid_path}")

        lora_sd = {}
        refmod_sd = {}
        metadata = {}

        # 1. Inspect and partition tensors
        with safe_open(hybrid_path, framework="pt", device="cpu") as f:
            metadata = f.metadata() or {}
            for key in f.keys():
                tensor = f.get_tensor(key)
                if key.startswith("refmod.") or key in ("latent", "samples"):
                    # Normalize key for RefMod engine
                    ref_key = key.replace("refmod.", "")
                    refmod_sd[ref_key] = tensor
                else:
                    lora_sd[key] = tensor

        # 2. Apply LoRA weights to MODEL and CLIP
        patched_model, patched_clip = model, clip
        if lora_sd and (lora_model_strength != 0 or lora_clip_strength != 0):
            patched_model, patched_clip = comfy.sd.load_lora_for_models(
                model, clip, lora_sd, lora_model_strength, lora_clip_strength
            )
            print(f"[MiniMaxH3UnifiedLoader] Applied LoRA weights ({len(lora_sd)} keys) to MODEL/CLIP")

        # 3. Construct RefMod conditioning structure
        refmods_list = []
        if refmod_sd:
            latent = refmod_sd.get("latent", refmod_sd.get("samples"))
            if latent is not None:
                mod_meta = {}
                if "h3_refmod_meta" in metadata:
                    try:
                        mod_meta = json.loads(metadata["h3_refmod_meta"])
                    except Exception:
                        pass

                # Build RefMod dictionary compatible with MiniMaxH3RefModApply
                refmod_entry = {
                    "name": mod_meta.get("name", os.path.splitext(hybrid_name)[0]),
                    "latent": latent,
                    "strength": refmod_strength,
                    "copies": refmod_copies,
                    "concept_type": mod_meta.get("concept_type", "identity"),
                    "token_count": mod_meta.get("token_count", latent.numel() // (24 * 16)),
                    "meta": mod_meta
                }
                refmods_list.append(refmod_entry)
                print(f"[MiniMaxH3UnifiedLoader] Extracted embedded RefMod '{refmod_entry['name']}' (latent shape: {latent.shape})")
        else:
            print("[MiniMaxH3UnifiedLoader] No embedded RefMod latents found in container; returning empty REFMODS list.")

        return (patched_model, patched_clip, refmods_list)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3UnifiedLoraRefModLoader": MiniMaxH3UnifiedLoraRefModLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3UnifiedLoraRefModLoader": "MiniMax-H3 Unified LoRA + RefMod Loader"
}
```

---

## 6. ComfyUI Graph Wiring Comparison

### Option A: Backward-Compatible Legacy Graph (Standard Loaders)
If using standard ComfyUI nodes or rgthree's `Power Lora Loader`, the hybrid file sits in `ComfyUI/models/loras/` and behaves identically to a standalone LoRA:

```
[ Load Checkpoint ] ──► (MODEL, CLIP) ──► [ Power Lora Loader ] ──► (MODEL, CLIP) ──► [ KSampler ]
                                            (loads hybrid .safetensors)
```

### Option B: Unified Dual Graph (Single Node for Weights + Latents)
Using the new `MiniMaxH3UnifiedLoraRefModLoader`, one single node loads both the weight adaptation and reference latents:

```
                                  ┌──────────────────────────────────────────────┐
                                  │    MiniMaxH3UnifiedLoraRefModLoader          │
[ Load Checkpoint ] ──(MODEL,CLIP)► (File: minimaxh3_billie_hybrid.safetensors)  │
                                  ├──────────────────────────────────────────────┤
                                  │ • MODEL  ────────────────────────────────────┼──► [ KSampler ]
                                  │ • CLIP   ──► [ CLIP Text Encode (Prompt) ] ──┼──► [ MiniMaxH3RefModApply ]
                                  │ • REFMODS ───────────────────────────────────┼──► [ MiniMaxH3RefModApply ]
                                  └──────────────────────────────────────────────┘
```

---

## 7. Comparative Benefits & Production Analysis

| Evaluation Metric | Standalone LoRA Only | Standalone RefMod Only | Separate LoRA + RefMod Files | Unified Hybrid Container (`.safetensors`) |
| :--- | :--- | :--- | :--- | :--- |
| **Model Weight Adaptation** | Full (Fine-tuned layers) | None (Zero weight changes) | Full | **Full** |
| **VAE Invariant Consensus** | None | Full (Biometric lock) | Full | **Full** |
| **Number of Files to Download** | 1 file (~50 MB) | 1 file (~1.5 MB) | 2 files (Sync issues) | **1 file (~51.5 MB)** |
| **ComfyUI Graph Cleanliness** | 1 loader node | 1 loader + apply node | 2 separate loader nodes | **1 unified loader node** |
| **Standard Loader Compatibility** | 100% | 0% (RefMods loader only) | Mixed | **100% Backward Compatible** |
| **Version Mismatch Risk** | None | None | High (v1 LoRA with v2 RefMod) | **Zero (Permanently Bundled)** |

---

## 8. Summary & Next Steps

1. **Format Validation**: Safetensors' non-restrictive key-value tensor model allows storing both PyTorch weight state dicts and latent tensors in the same file.
2. **Standard Loader Safety**: Existing ComfyUI LoRA loaders safely ignore non-weight keys without errors.
3. **Ecosystem Standardization**: Creating unified hybrid containers allows model creators to distribute single `.safetensors` files on Hugging Face that provide both fine-tuned transformer weights and high-fidelity reference latent consensus.

---

## 9. Related Documentation
- [MiniMax-H3 RefMod Creation & Extraction Guide](MINIMAX_H3_REFMOD_CREATION_GUIDE.md)
- [MiniMax-H3 RefMod Stacking & Multi-Subject Architecture Guide](MINIMAX_H3_REFMOD_STACKING_AND_MULTISUBJECT_GUIDE.md)
- [MiniMax-H3 RefMods Installation & Quickstart Guide](MINIMAX_H3_REFMODS_INSTALLATION_AND_USAGE_GUIDE.md)
- [MiniMax-H3 Prompting Guide](MINIMAX_H3_PROMPTING_GUIDE.md)
- [FLUX.2 Klein9 RefMod Architecture Guide](../../klein9/docs/FLUX2_KLEIN9_REFMODS_GUIDE.md)
- [Jinx identity LoRA epoch sweep & RefMod stack](lora/README.md) — running LoRA weights and RefMod latents as two files; combined stack wins
