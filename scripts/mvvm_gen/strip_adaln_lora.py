"""Write a copy of an H3 turbo LoRA without adaln_proj tensors, for the pruned H3 models.

Pruned H3 checkpoints shrink adaln_proj.linear to [96768, 8]; LoRAs trained on the full
model carry [96768, 2688] deltas there that ComfyUI cannot apply (it logs an error per block
and skips them). Dropping those keys gives the same result without the errors.
"""
import sys
from safetensors.torch import load_file, save_file
from safetensors import safe_open

src, dst = sys.argv[1], sys.argv[2]
with safe_open(src, "pt") as f:
    meta = f.metadata() or {}
tensors = load_file(src)
kept = {k: v for k, v in tensors.items() if "adaln_proj" not in k}
meta = dict(meta, mvvm_note="adaln_proj tensors removed for pruned H3 ([96768, 8]) models")
save_file(kept, dst, metadata=meta)
print(f"kept {len(kept)} of {len(tensors)} tensors; dropped {len(tensors) - len(kept)} adaln_proj tensors -> {dst}")
