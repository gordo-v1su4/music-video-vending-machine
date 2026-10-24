"""Build SwarmUI preset-import JSON for the V1S-155 demo renders (Presets tab -> Import Presets).

Every preset targets the saved 'MVVM Demo Eros Two Pass' workflow, so a render is: click preset in the
Generate tab, press Generate. Swarm records the full parameter set in the output's metadata/history.

  uv run --python 3.12 python -m mvvm_gen.demo_presets trials <prompt.txt> <out.json>
"""

import json
import sys

WORKFLOW = "MVVM - I Ran Music Video/MVVM Demo Eros Two Pass"
FOLDER = "MVVM - I Ran Music Video/Demo"
RAW = "comfyrawworkflowinput"
LOW_RES = {  # lower-res, faster demo setting chosen by the user over the 0.4/0.8 MP x1.2 default
    RAW + "decimalselectorfirstlowrespassnodemegapixelsu": "0.25",
    RAW + "decimalfinaltargetmegapixelsndpassnodevaluex": "0.5",
    RAW + "decimalrtxvideosuperresolutionnoderesizetypescalebn": "1",
}
MASTER = r"D:\output\local\MVVM\song\master.mp3"


def base(prompt, seed, scene, audio_seek, duration, outpath, lune=False):
    p = {
        "images": "1",
        "model": "10Eros-Max-Turbo-Beta5-Q6_K.gguf",
        "comfyuicustomworkflow": WORKFLOW,
        "prompt": prompt,
        "rafacharacterrefmod": "Rafa_identity_full",
        RAW + "textrafarefmodonlystrengthonecopynodemodee": "Lune_identity_full" if lune else "(none)",
        RAW + "seedseedrgthreenodeseedch": str(seed),
        RAW + "textscenereferencepicturenodeimageec": scene,
        RAW + "textvhsloadaudionodeaudiofileeb": MASTER,
        RAW + "decimalvhsloadaudionodeseeksecondseb": f"{audio_seek:.3f}",
        RAW + "decimalvhsloadaudionodedurationeb": f"{duration:.3f}",
        RAW + "decimaldurationinsecsnodevaluer": f"{duration:.3f}",
        "useguidea": "false", "useguideb": "false", "guideaframe": "62", "guidebframe": "120",
        "overrideoutpathformat": outpath,
    }
    p.update(LOW_RES)
    return p


def preset(title, description, param_map):
    return {f"{FOLDER}/{title}": {"title": f"{FOLDER}/{title}", "description": description,
                                   "preview_image": "", "param_map": param_map}}


def trials(prompt):
    """V1S-229 controlled anchor-count comparison: prompt, seed, references, size identical; guides differ."""
    common = dict(prompt=prompt, seed=410071, scene="hf_20261007_142933_fe26c478-b4cc-478d-9b1a-9d5be5648b3c.png",
                  audio_seek=229.285, duration=14.0)
    out = {}
    for tag, a, b, note in (("T0 no guide", False, False, "zero guides"),
                            ("T1 guide B f120", False, True, "falling-boot guide at frame 120 only"),
                            ("T2 guides A f62 + B f120", True, True, "ground-contact f62 + falling-boot f120")):
        slug = tag.split()[0].lower()
        p = base(outpath=f"MVVM/demo-v1s155/renders/trial-{slug}_[number]", **common)
        p["useguidea"], p["useguideb"] = str(a).lower(), str(b).lower()
        out.update(preset(f"V1S-229 {tag}", f"Guide-count trial ({note}); fixed prompt/seed 410071/refs/size.", p))
    return out


if __name__ == "__main__":
    kind, src, dst = sys.argv[1:4]
    with open(src, encoding="utf-8") as fh:
        text = fh.read().strip()
    data = {"trials": trials}[kind](text)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
    print(dst, len(data), "presets")
