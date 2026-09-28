"""PlagueKind MiniMax H3 V11 workflow, as exported by ComfyUI's own frontend (graphToPrompt).

`workflows/plaguekind-h3-v11.api.json` is his V11 graph unchanged: sparse SLA attention (0.7),
H3 cache, chunked attention/feed-forward, AdaLN LoRA fix, res_multistep/simple 13 steps, no
turbo. Each mode below only fills his reference bundle and sets his first/last-frame switch,
exactly as the UI does; every other node and setting is his.

Bundle slots (his Extra Refs subgraph): slot 1 and 2 feed first/last frame when the switch is
off, or reference images 1 and 2 when it is on; slots 3-9 are always reference images 3-9.
"""

import copy
import json
import os

TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "..", "workflows", "plaguekind-h3-v11.api.json")
WORKFLOWS = ("pk_v11_t2v", "pk_v11_fl2v", "pk_v11_ref2v", "pk_v11_fl2v_refs")

SEED, SAVE, TARGET, DURATION = "5445", "5480", "5612", "5479:5476"
COMBINED, REF_SWITCH, BUNDLE = "5479:5961", "5479:5881", "5556:5570"


def template():
    with open(TEMPLATE, encoding="utf-8") as fh:
        return json.load(fh)


def build(workflow, prompt, seed, prefix, width=1344, height=768, seconds=5.0, images=(), unet=None, overrides=None):
    """Return an API prompt for one of WORKFLOWS.

    images: uploaded image names, one per bundle slot (None leaves a slot empty). fl2v takes
        [first] or [first, last]; ref2v takes up to 9 refs; fl2v_refs takes [first, last-or-None,
        ref, ...] with up to 7 refs in slots 3-9, which stay references in first/last-frame mode.
    overrides: {node_id: {input: value}} for deliberate deviations from his settings (e.g. identity).
    """
    if workflow not in WORKFLOWS:
        raise ValueError(f"unknown workflow {workflow}; expected one of {WORKFLOWS}")
    g = copy.deepcopy(template())
    g[SEED]["inputs"]["noise_seed"] = seed
    g[SAVE]["inputs"]["filename_prefix"] = prefix
    # His note: for generation from scratch set the Target Dimension node to explicit W x H.
    g[TARGET]["inputs"].update({"scale_mode": "Dimensions (W × H)", "aspect_ratio": "16:9 (Widescreen)",
                               "width": width, "height": height})
    g[DURATION]["inputs"]["value"] = seconds
    g[COMBINED]["inputs"]["prompt"] = prompt
    if unet:
        g["5310:5008"]["inputs"]["unet_name"] = unet
    for node_id, values in (overrides or {}).items():
        g[node_id]["inputs"].update(values)

    limit = {"pk_v11_t2v": 0, "pk_v11_fl2v": 2, "pk_v11_ref2v": 9, "pk_v11_fl2v_refs": 9}[workflow]
    if len(images) > limit:
        raise ValueError(f"{workflow} takes at most {limit} images, got {len(images)}")
    # Switch on = slots 1-2 are references (first/last frame disabled); off = first/last frame.
    g[REF_SWITCH]["inputs"]["value"] = workflow == "pk_v11_ref2v"
    for i, name in enumerate(images, start=1):
        if name is None:
            continue
        g[f"mvvm_image_{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        g[BUNDLE]["inputs"][f"input_{i}"] = [f"mvvm_image_{i}", 0]
    return g
