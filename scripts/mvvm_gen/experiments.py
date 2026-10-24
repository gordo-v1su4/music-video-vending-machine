"""Audio-reactive cut/language experiments across the pilot window (chunks 23-29), one generation each.

Each experiment uses the user's music-video template (graphs.h3_music_prompt) with anchors from the studio's edit
plan, named reference panels (Lune; Rafa where he is on screen; the stranger stays text-only so he can never become
Rafa), the song slice as H3 reference audio + locked output, and the v4 SLA settings. All jobs are submitted to the
7821 queue up front, then collected; each render is face-checked (Lune) and spliced into the cut at its song time.

Usage (repo root): python -m scripts.mvvm_gen.experiments scripts/mvvm_gen/plans/i-ran-pilot.json [--only E4 ...]
"""

import argparse
import json
import os
import sys

from . import comfy, graphs, pk_v11
from .identity_audio_test import COMFY_PY, SLA, face_score, stamp
from .run import Run, scene_cuts, seed_for

STRANGER = "a stranger: a lean man with a bleached-blond buzz cut, clean-shaven, pale blue eyes, in a white mesh tank"

# chunk -> (title, shot texts (one per cut slot), shots Lune is in, shots Rafa is in, extra timeline lines)
EXPERIMENTS = {
    "E1": (23, "breakdown: long takes, stable camera, gentle laser flicker on the hi-hats", [
        "<Subject 1> stands still in the dense festival crowd, searching over the heads, face half-lit by warm firelight, "
        "breathing slowly; locked-off camera, one long take.",
        "Medium close-up of <Subject 1> turning slowly; thin green lasers flicker softly in the atmospheric haze, the flicker "
        "glitching exactly on the hi-hat onsets of <Audio 1>; only the light moves on the beat.",
        "Over <Subject 1>'s shoulder: far across the crowd, <Subject 2> in his open olive shirt is there for a moment, then "
        "lost behind dancers.",
        "Flash insert, a memory: <Subject 2>'s face in moonlight, smiling at her.",
    ], [1, 2, 3], [3, 4], ["Sparse musical passage: minimal motion, long shots, stable camera; lights react, bodies stay calm."]),
    "E2": (24, "the reach: dolly zoom on the hit, bullet-time freeze", [
        "<Subject 1> glimpses <Subject 2> across the crowd and pushes toward him through the dancers, reaching one hand toward "
        "the camera, mouthing 'wait... let me through'; handheld, pressing forward.",
        "Close-up of two hands in laser light: <Subject 1>'s fingers reaching for <Subject 2>'s hand; they stop a finger-width "
        "apart and hang there.",
        "Whip pan: the crowd swallows <Subject 1>, bodies closing over the lens.",
    ], [1, 2, 3], [1, 2], ["At 00:07.30, exactly on the hit in <Audio 1>, a dolly zoom (Vertigo effect): the camera pulls "
                           "back while the lens zooms in, so <Subject 1> holds her size while the crowd behind her stretches "
                           "and warps; the moment freezes into a bullet-time slow-motion beat before the crowd closes in."]),
    "E3": (26, "the rope-bridge dream: bullet-time orbit, slow-mo into the build", [
        "Dream: on the edge of a swaying rope bridge high above the jungle canopy under a huge full moon, <Subject 1> and "
        "<Subject 2> kiss; bullet-time slow motion, the camera orbits them in one smooth arc, mist drifting through the ropes.",
        "Slow-motion close-up: <Subject 1>'s boot slips off a wet wooden plank.",
        "Slow motion: <Subject 2>'s hand grabs for hers and misses by an inch.",
        "<Subject 1> tips backward off the bridge into the mist, eyes on the moon.",
    ], [1, 2, 4], [1, 3], ["Slow-motion moment throughout the kiss; as <Audio 1> starts to build, the slow motion snaps back "
                           "toward real speed with the slip."]),
    "E4": (27, "the fall: FFT beat-synced jump cuts, laser flicker glitching on every onset", [
        "Freefall: <Subject 1> falls backward through mist and green lasers, hair streaming upward.",
        "Top-down: <Subject 1> spinning down through the canopy, strobing light pulsing on every beat.",
        "Extreme close-up of <Subject 1>'s face, between terror and bliss, lit by one laser strobe per beat.",
        "Jump cut: the same fall, tighter and closer.",
        "Jump cut: <Subject 1>'s outstretched hand slicing through a laser beam.",
        "Wide: <Subject 1>'s silhouette falling toward a sea of festival lights far below.",
    ], [1, 2, 3, 4, 5, 6], [], ["FFT beat-synced jump cuts: every cut and every laser flicker in the atmospheric haze glitches "
                                "exactly on a kick onset from <Audio 1>, one strobe per beat; nothing moves off the beat."]),
    "E5": (28, "the landing: stutter on the drum rolls, the festival on fire", [
        f"<Subject 1> crashes down into the festival crowd and stumbles; behind her the stage rigging has caught fire, flames "
        f"climbing the palm trunks, lasers cutting through the smoke.",
        "The crowd flees the fire in panic; <Subject 1> runs with them through embers and smoke.",
        f"Smash cut: <Subject 1> collides into a man's arms, {STRANGER}, seen only from behind; relief on her face.",
        "Slow-motion moment: <Subject 1> clings to him, eyes closed, burning palms behind them.",
    ], [1, 2, 3, 4], [], ["At 00:02.19, 00:02.87 and 00:04.62, stutters: the same half-second of <Subject 1>'s stumble repeats "
                          "in a jittering loop exactly on the drum-roll onsets of <Audio 1>, then releases on the next downbeat."]),
    "E6": (29, "the reveal: slow push, smash cut to the stranger, slow-mo reaction", [
        f"Slow push-in: <Subject 1> in the arms of {STRANGER}, seen from behind; her face buried in his shoulder, smiling, "
        "eyes closed.",
        "He begins to turn his head toward her; <Subject 1> lifts her face, still smiling, eyes still closed.",
        "Smash cut on the hit: full-frame close-up of the stranger's face, bleached-blond buzz cut, clean-shaven, pale blue "
        "eyes: clearly not the man she loves.",
        "Slow-motion reaction: <Subject 1> opens her eyes; her smile collapses into confusion, then hurt; lips part; she pulls back.",
    ], [1, 2, 4], [], ["Hold the reaction long enough to read; the camera stays close on <Subject 1>'s face."]),
}


def timeline(chunk, texts, extra):
    off = lambda ms: (ms - chunk["startMs"]) / 1000
    cuts = [off(x["startMs"]) for x in chunk["shots"]]
    ends = [off(x["endMs"]) for x in chunk["shots"]]
    hits = [off(x["ms"]) for x in chunk["impacts"]]
    near = lambda t: any(abs(h - t) <= 0.08 for h in hits)
    lines = []
    for i, (t, text) in enumerate(zip(cuts, texts)):
        if i == 0:
            lines.append(f"[Shot 1]\n{text}")
            continue
        if near(t) and i == len(cuts) - 1:
            cue = "exactly on the major hit, smash cut to a completely different composition. Strong sudden visual energy."
        elif near(t):
            cue = "on the strong downbeat, hard cut to a dramatically different camera angle, landing precisely with the transient."
        elif ends[i] - t < 0.9:
            cue = "on the sharp transient, abrupt framing change; a very fast cut."
        else:
            cue = "synchronized to the transient, hard cut; the motion begins just before the hit and resolves just after it."
        lines.append(f"[Shot {i + 1}] At {stamp(t)}, {cue}\n{text}")
    for b in chunk["builds"]:
        a, z = max(0.0, off(b["startMs"])), min(ends[-1], off(b["endMs"]))
        if z - a > 0.5:
            lines.append(f"From {stamp(a)} to {stamp(z)}, as <Audio 1> builds, progressively increase camera velocity and "
                         f"subject movement; musically driven, not mechanically linear.")
    return "\n\n".join(lines + extra)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args(argv)
    run = Run(args.plan)
    with open(run.path("edit-plan.json"), encoding="utf-8") as fh:
        chunks = {c["index"]: c for c in json.load(fh)["chunks"]}
    print("preflight:", comfy.preflight(), flush=True)
    song_file = run.plan["song"]["audio"]
    song = comfy.upload_image(song_file)
    lune, rafa = run.plan["characters"]["lune"], run.plan["characters"]["rafa"]
    lune_refs = [run.upload(run.named_panel("lune", p)) for p in ("anchor", "closeup")]
    rafa_refs = [run.upload(run.named_panel("rafa", p)) for p in rafa.get("ref_panels", ["front", "side"])]
    w, h = run.plan["frame_size"]
    sla = {**run.plan.get("clip_overrides", {}).get(SLA, {}), "reference_protection": "Heavy Enforcement",
           "protect_audio": True, "dense_last_steps": 1, "dense_steps": "0-2"}
    jobs = []
    for eid, (ci, title, texts, lune_shots, rafa_shots, extra) in EXPERIMENTS.items():
        if args.only and eid not in args.only:
            continue
        chunk = chunks[ci]
        if len(texts) != len(chunk["shots"]):
            raise SystemExit(f"{eid}: {len(texts)} shot texts for {len(chunk['shots'])} cut slots in chunk {ci}")
        subjects = [(f"{lune['identity']} Outfit: {lune['look']}", [1, 2], run.full_name("lune"), lune_shots)]
        refs = list(lune_refs)
        if rafa_shots:
            subjects.append((f"{rafa['identity']} Outfit: {rafa['look']}", list(range(3, 3 + len(rafa_refs))),
                             run.full_name("rafa"), rafa_shots))
            refs += rafa_refs
        prompt = graphs.h3_music_prompt(subjects, f"Experiment {eid}: {title}.", run.plan["style"], timeline(chunk, texts, extra))
        start, seconds = chunk["startMs"] / 1000, (chunk["endMs"] - chunk["startMs"]) / 1000
        seed = seed_for(run.name, "experiment", eid)
        graph = pk_v11.build("pk_v11_ref2v", prompt, seed, f"mvvm/{run.name}/exp-{eid}-c{ci}", w, h, seconds, images=refs,
                             unet=run.plan.get("clip_unet"), overrides={SLA: sla},
                             song_audio=(song, start), reference_audio=(song_file, start, seconds))
        dest = run.path("experiments", f"{eid}-c{ci}.mp4")
        os.makedirs(run.path("experiments"), exist_ok=True)
        with open(dest.replace(".mp4", ".prompt.txt"), "w", encoding="utf-8") as fh:
            fh.write(prompt)
        pid = comfy.submit(graph)
        print(f"[{eid}] chunk {ci} ({title}) queued as {pid}, {len(prompt)} chars", flush=True)
        jobs.append((eid, ci, pid, dest, chunk))
    identity = lune.get("master_ref", lune["identity_ref"])
    for eid, ci, pid, dest, chunk in jobs:
        record = comfy.wait(pid, timeout=run.plan.get("job_timeout_s", 1200))
        comfy.download(comfy.output_files(record)[0], dest)
        planned = [round((x["startMs"] - chunk["startMs"]) / 1000, 2) for x in chunk["shots"][1:]]
        cuts = scene_cuts(dest)
        err = [round(min((abs(c - p) for c in cuts), default=99), 2) for p in planned]
        face = face_score(identity, dest)
        print(f"[{eid}] done -> {dest} | cuts {cuts} err {err} | Lune face median {face.get('median')} per shot "
              f"{[x.get('median') for x in face.get('shots', [])]}", flush=True)
        run.splice(ci, dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
