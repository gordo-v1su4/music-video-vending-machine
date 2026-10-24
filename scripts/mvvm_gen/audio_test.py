"""A/B test: does conditioning H3 on the real song slice make its cuts land on the music?

One chunk of the studio's edit plan (.runtime/gen/<plan>/edit-plan.json) is rendered twice per seed with
the same multi-cut prompt: "plain" (no audio in) and "song" (the master song is loaded once and
MiniMaxH3SongMaskedAVContext isolates the chunk's slice inside ComfyUI and protects it in the audio
latent). Each render's real cuts (ffmpeg scene detection) are compared with the planned cuts.

Usage (repo root): python -m scripts.mvvm_gen.audio_test scripts/mvvm_gen/plans/i-ran-pilot.json [--at 230] [--seeds 2]
"""

import argparse
import json
import re
import subprocess
import sys

from . import comfy, graphs, pk_v11
from .run import Run, seed_for

EARLY_CUT_S = 0.0  # PK V11 lands hard cuts within ~0.1-0.2 s of the prompted time (c25 plain s0); the official graph cut 0.3-0.7 s early

# Content for the chorus chunk at 3:49.3-3:58.1 (five slots: beat, beat, flash, flash, beat).
CHORUS_SHOTS = [
    "First-person POV sprinting through dense moonlit jungle palms at night, fronds whipping past the lens, "
    "heavy realistic footfalls and breathing, thin green laser beams cutting through the canopy ahead.",
    "Lune runs straight toward the camera through the palms, glancing back over her shoulder in fear, hair "
    "flying, her silver halter top catching the laser light; the camera tracks backward at her running speed, "
    "real weight in every stride.",
    "Extreme close-up of her eyes, wide and wet with sweat, a green laser sweeping across her face.",
    "Low angle at ground level: her boots slam into wet roots, mud spraying toward the lens.",
    "The palms part and she bursts out onto a ridge above the festival crowd under a huge full moon; the camera "
    "surges forward past her shoulder into the sea of lasers.",
]


def stamp(seconds):
    return f"{int(seconds // 60):02d}:{seconds % 60:06.3f}"


def chunk_prompt(run, chunk, shots_text):
    char = run.plan["characters"]["lune"]
    subjects = [(f"{char['name']}. {char['identity']} Outfit: {char['look']}", [1, 2])]
    shots = chunk["shots"]
    if len(shots) != len(shots_text):
        raise SystemExit(f"chunk has {len(shots)} shots, content written for {len(shots_text)}")
    parts = [shots_text[0]]
    for i, (shot, text) in enumerate(zip(shots[1:], shots_text[1:]), start=2):
        at = (shot["startMs"] - chunk["startMs"]) / 1000 + EARLY_CUT_S
        parts.append(f"[Shot {i}] At {stamp(at)}, HARD CUT. {text}")
    body = "\n\n".join(parts) + (
        "\n\nCamera and transitions: every change between shots is an unmistakable HARD CUT timed to a hit in the "
        "music; no dissolves, morphs or split screens. Realistic running physics, no floaty or weightless motion.")
    summary = ("A fast-cut chorus montage in one generation: five shots separated by hard cuts that land on the "
               "song's hits, from the jungle run to the festival ridge.")
    return graphs.h3_ref2v_prompt(subjects, summary, run.plan["style"], body,
                                  "The soundtrack is the song itself: a driving chorus with heavy hits.")


def detected_cuts(path):
    # 0.12: these renders are dark; 0.28 missed every real cut in c25 plain s0.
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "select='gt(scene,0.12)',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [round(float(t), 2) for t in re.findall(r"pts_time:([0-9.]+)", out)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--at", type=float, default=230.0, help="song second inside the chunk to test")
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args(argv)
    run = Run(args.plan)
    with open(run.path("edit-plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    chunk = next(c for c in plan["chunks"] if c["startMs"] <= args.at * 1000 < c["endMs"])
    start, seconds = chunk["startMs"] / 1000, (chunk["endMs"] - chunk["startMs"]) / 1000
    planned = [round((s["startMs"] - chunk["startMs"]) / 1000, 2) for s in chunk["shots"][1:]]
    print(f"chunk {chunk['index']} {stamp(start)} +{seconds:.2f}s, planned cuts {planned}", flush=True)
    print("preflight:", comfy.preflight(), flush=True)

    prompt = chunk_prompt(run, chunk, CHORUS_SHOTS)
    refs = [run.upload(run.panel("lune", p)) for p in run.plan["characters"]["lune"].get("ref_panels", ["portrait", "front"])]
    song = comfy.upload_image(run.plan["song"]["audio"])  # generic ComfyUI input upload; LoadAudio reads it
    w, h = run.plan["frame_size"]
    base = seed_for(run.name, "audiotest", str(chunk["index"]))
    results = []
    for k in range(args.seeds):
        for variant in ("plain", "song"):
            key = f"audiotest:c{chunk['index']}:{variant}:s{k}"
            dest = run.path("audio-test", f"c{chunk['index']}-{variant}-s{k}.mp4")
            graph = pk_v11.build("pk_v11_ref2v", prompt, base + k, f"mvvm/{run.name}/audiotest-c{chunk['index']}-{variant}-s{k}",
                                 w, h, seconds, images=refs, unet=run.plan.get("clip_unet"),
                                 overrides=run.plan.get("clip_overrides"),
                                 song_audio=(song, start) if variant == "song" else None)
            run.generate(key, graph, dest, base + k)
            cuts = detected_cuts(dest)
            err = [min((abs(c - p) for c in cuts), default=None) for p in planned]
            results.append({"variant": variant, "seed": k, "cuts": cuts, "offsets_s": err})
            print(f"[audio-test] {variant} s{k}: cuts {cuts}; distance to each planned cut {err}", flush=True)
    with open(run.path("audio-test", f"c{chunk['index']}-results.json"), "w", encoding="utf-8") as fh:
        json.dump({"chunk": chunk["index"], "planned": planned, "prompt": prompt, "results": results}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
