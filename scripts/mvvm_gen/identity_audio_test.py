"""Identity + audio-following test on one edit-plan chunk (follow-up to audio_test.py).

Changes against the first test (where Lune's face scored 0.11-0.26 against her identity image and the song only
sat in the output audio):
  - references: the sheet's anchor + close-up panels (0.77 / 0.60 likeness) instead of portrait + front;
  - SLA attention: protect_audio on (prompt tokens, target audio and audio refs always attended),
    reference_protection "Heavy Enforcement", dense first steps and last step;
  - the song twice: as H3 reference audio (<Audio 1>, what the model reads for rhythm) and locked as the output;
  - the prompt says the music drives cuts and movement, with movement hits at the chunk's impact times.
Variant "v2dense" additionally turns sparse attention off, to see whether sparsity is what costs the face.

Every render is scored for cut timing (scene detection vs the cut map) and identity (face_check.py, ArcFace).
Usage (repo root): python -m scripts.mvvm_gen.identity_audio_test scripts/mvvm_gen/plans/i-ran-pilot.json
"""

import argparse
import json
import subprocess
import sys

from . import comfy, graphs, pk_v11
from .run import Run, scene_cuts, seed_for

COMFY_PY = r"D:\ComfyUI_V89\ComfyUI\venv\Scripts\python.exe"
SLA = "5310:5603"


def stamp(s):
    return f"{int(s // 60):02d}:{s % 60:05.2f}"


def prompt_for(run, chunk):
    char = run.plan["characters"]["lune"]
    # She is in shots 2-5 (shot 1 is the POV); retention and <Subject 1> tags follow that.
    subjects = [(f"{char['identity']} Outfit: {char['look']}", [1, 2], run.full_name("lune"), [2, 3, 4, 5])]
    off = lambda ms: (ms - chunk["startMs"]) / 1000
    s = [off(x["startMs"]) for x in chunk["shots"]]
    hits = [off(x["ms"]) for x in chunk["impacts"]]
    drive = ("<Audio 1> is the song and it drives this whole generation: every hard cut lands on a hit in <Audio 1>, "
             "and her body, the camera and the light move on its accents. The pace follows its energy"
             + (f", building from {stamp(max(0.0, off(chunk['builds'][0]['startMs'])))}" if chunk["builds"] else "") + ".")
    body = (
        f"First-person POV sprinting through dense moonlit jungle palms at night, fronds whipping past the lens, heavy "
        f"realistic footfalls. At {stamp(hits[1])}, on the hit, a palm frond smacks across the lens.\n\n"
        f"[Shot 2] At {stamp(s[1])}, HARD CUT on the beat. <Subject 1> runs straight toward the camera through the "
        f"palms, silver headwrap and silver halter top catching green laser light, real weight in every stride; the camera tracks backward at her "
        f"running speed. At {stamp(hits[3])}, on the accent, she snaps her head back over her shoulder in fear.\n\n"
        f"[Shot 3] At {stamp(s[2])}, HARD CUT on the beat. Extreme close-up of <Subject 1>'s face and eyes, her silver "
        f"headwrap across her forehead, eyes wide and wet with sweat, a green laser sweeping across her face.\n\n"
        f"[Shot 4] At {stamp(s[3])}, HARD CUT on the beat. Low angle at ground level: <Subject 1>'s tan suede boots slam "
        f"into wet roots, mud spraying toward the lens.\n\n"
        f"[Shot 5] At {stamp(s[4])}, HARD CUT on the hit. The palms part and <Subject 1> bursts out onto a ridge above "
        f"the festival crowd under a huge full moon; the camera surges forward past her shoulder into the lasers.\n\n"
        "Camera and transitions: unmistakable HARD CUTS exactly on the music's hits; no dissolves, morphs or split "
        "screens. Her face is identical to <Picture 1> and <Picture 2> in every shot.")
    return graphs.h3_ref2v_prompt(subjects, "A fast-cut chorus montage in five shots, from the jungle run to the festival "
                                  "ridge. " + drive, run.plan["style"], body,
                                  "<Audio 1>, the song itself, exactly as supplied.")


# Shot content for the chorus chunk, one per cut slot; <Subject 1> wherever Lune is on screen.
V4_SHOTS = [
    "Opening shot: first-person POV sprinting through dense moonlit jungle palms at night, fronds whipping past the lens, "
    "heavy realistic footfalls; movement follows the pulse of <Audio 1>, camera restrained through the opening phrase.",
    "<Subject 1> runs straight toward the camera through the palms, silver headwrap and silver halter top catching green "
    "laser light, real weight in every stride; the camera tracks backward at her running speed.",
    "Extreme close-up of <Subject 1>'s face and eyes, her silver headwrap across her forehead, eyes wide and wet with "
    "sweat, a green laser sweeping across her face.",
    "Low angle at ground level: <Subject 1>'s tan suede boots slam into wet roots, mud spraying toward the lens.",
    "The palms part and <Subject 1> bursts out onto a ridge above the festival crowd under a huge full moon; the camera "
    "surges forward past her shoulder into the lasers.",
]


def music_timeline(chunk, shots_text):
    """The template's TIMELINE, anchored on the edit plan: cuts named by what the music does there."""
    off = lambda ms: (ms - chunk["startMs"]) / 1000
    cuts = [off(x["startMs"]) for x in chunk["shots"]]
    ends = [off(x["endMs"]) for x in chunk["shots"]]
    hits = [off(x["ms"]) for x in chunk["impacts"]]
    near_hit = lambda t: any(abs(h - t) <= 0.08 for h in hits)
    lines = []
    for i, (t, text) in enumerate(zip(cuts, shots_text)):
        if i == 0:
            lines.append(f"[Shot 1]\n{text}")
        else:
            last = i == len(cuts) - 1
            if near_hit(t) and last:
                cue = "exactly on the major hit, smash cut to a completely different composition and camera position. Strong sudden visual energy."
            elif near_hit(t):
                cue = "on the strong downbeat, hard cut to a dramatically different camera angle. The cut lands precisely with the musical transient."
            elif ends[i] - t < 0.9:
                cue = "on the sharp transient, abrupt framing change; a very fast cut that resolves immediately."
            else:
                cue = "synchronized to the transient, a very fast whip-pan into a closer framing; the motion begins just before the hit and resolves just after it."
            lines.append(f"[Shot {i + 1}] At {stamp(t)}, {cue}\n{text}")
        for h in hits:
            if t + 0.1 < h < ends[i] - 0.1:
                lines.append(f"At {stamp(h)}, on the kick transient inside this shot, a hard physical accent: a push-in impact "
                             f"and a sharp movement from the subject.")
    for b in chunk["builds"]:
        a, z = max(0.0, off(b["startMs"])), min(ends[-1], off(b["endMs"]))
        lines.append(f"From {stamp(a)} to {stamp(z)}, as <Audio 1> builds in intensity, progressively increase camera "
                     f"velocity and subject movement. The acceleration should feel musically driven rather than mechanically linear.")
    lines.append(f"From {stamp(cuts[-1] + 0.6)} to {stamp(ends[-1])}, allow the shot to breathe; camera movement follows the "
                 f"groove without cutting on every beat.")
    return "\n\n".join(lines)


def music_prompt_for(run, chunk):
    char = run.plan["characters"]["lune"]
    subjects = [(f"{char['identity']} Outfit: {char['look']}", [1, 2], run.full_name("lune"), [2, 3, 4, 5])]
    return graphs.h3_music_prompt(subjects, "A fast-cut chorus montage in five shots, from the jungle run to the festival ridge.",
                                  run.plan["style"], music_timeline(chunk, V4_SHOTS))


def face_score(ref, video):
    out = subprocess.run([COMFY_PY, "scripts/mvvm_gen/face_check.py", ref, video], capture_output=True, text=True)
    line = next((l for l in out.stdout.splitlines() if l.startswith("{")), None)
    return json.loads(line) if line else {"error": out.stderr[-400:]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--at", type=float, default=230.0)
    ap.add_argument("--variant", choices=("v3", "v4"), default="v4",
                    help="v3: fixed ref2v prompt; v4: the user's audio-reactive music-video template")
    args = ap.parse_args(argv)
    run = Run(args.plan)
    with open(run.path("edit-plan.json"), encoding="utf-8") as fh:
        chunk = next(c for c in json.load(fh)["chunks"] if c["startMs"] <= args.at * 1000 < c["endMs"])
    start, seconds = chunk["startMs"] / 1000, (chunk["endMs"] - chunk["startMs"]) / 1000
    planned = [round((x["startMs"] - chunk["startMs"]) / 1000, 2) for x in chunk["shots"][1:]]
    print(f"chunk {chunk['index']} {stamp(start)} +{seconds:.2f}s planned cuts {planned}", flush=True)
    print("preflight:", comfy.preflight(), flush=True)
    prompt = music_prompt_for(run, chunk) if args.variant == "v4" else prompt_for(run, chunk)
    print("--- prompt ---\n" + prompt + "\n---", flush=True)
    refs = [run.upload(run.named_panel("lune", p)) for p in ("anchor", "closeup")]
    song_file = run.plan["song"]["audio"]
    song = comfy.upload_image(song_file)
    identity = run.plan["characters"]["lune"]["identity_ref"]
    w, h = run.plan["frame_size"]
    base = seed_for(run.name, "audiotest", str(chunk["index"]))
    sla = {**run.plan.get("clip_overrides", {}).get(SLA, {}),
           "reference_protection": "Heavy Enforcement", "protect_audio": True, "dense_last_steps": 1, "dense_steps": "0-2"}
    variants = [(args.variant, 0, sla), (args.variant, 1, sla)]  # v3: named refs, <Subject 1> in shots 2-5, retention on those shots, headwrap required
    results = []
    for name, k, overrides in variants:
        key = f"idtest:c{chunk['index']}:{name}:s{k}"
        dest = run.path("audio-test", f"c{chunk['index']}-{name}-s{k}.mp4")
        graph = pk_v11.build("pk_v11_ref2v", prompt, base + k, f"mvvm/{run.name}/idtest-c{chunk['index']}-{name}-s{k}",
                             w, h, seconds, images=refs, unet=run.plan.get("clip_unet"), overrides={SLA: overrides},
                             song_audio=(song, start), reference_audio=(song_file, start, seconds))
        run.generate(key, graph, dest, base + k)
        cuts = scene_cuts(dest)
        timing = [round(min((abs(c - p) for c in cuts), default=99), 2) for p in planned]
        face = face_score(identity, dest)
        results.append({"variant": name, "seed": k, "cuts": cuts, "timing_err_s": timing, "face": face})
        print(f"[id-test] {name} s{k}: cuts {cuts} timing err {timing} | face median {face.get('median')} worst "
              f"{face.get('worst')} per shot {[x.get('median') for x in face.get('shots', [])]}", flush=True)
    with open(run.path("audio-test", f"c{chunk['index']}-idtest-results.json"), "w", encoding="utf-8") as fh:
        json.dump({"planned": planned, "prompt": prompt, "results": results}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
