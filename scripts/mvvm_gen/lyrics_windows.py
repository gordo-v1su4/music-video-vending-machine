"""Full-song timed lyrics from the vocal stem, transcribed in short overlapping windows.

Why (proven in project-stack-structure, commits 5b757a4 and e6d78d4): nova-3, a speech model, stops recognising sung
vocals partway into a long file, and even whisper drops sung content deep into a long file, yet both transcribe the
same audio when it arrives as its own short clip. The coordinator's single tail pass is still minutes long on a
5:53 song, so this slices the whole stem.

Each window goes to nova-3. If the stem is clearly singing in that window but few words came back, the window is
retried with whisper-large, and the result with more words is kept. Words are shifted onto the song timeline and
kept only from each window's core, so overlaps are not duplicated. The output is one Deepgram-shaped response for
the whole song, which the coordinator's transcription recovery endpoint accepts.

  python -m scripts.mvvm_gen.lyrics_windows .runtime/gen/song/lead-vocal.mp3 --out .runtime/gen/song/lyrics-windows

Paid: about $0.0043/min for nova-3 (whisper-large is similar); the total is printed. The Deepgram key is read from
Bitwarden Secrets Manager (DEEPGRAM_API_KEY) into this process only and is never printed.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

BWS = os.path.expanduser("~/.local/bin/bws")
DEEPGRAM_SECRET = "DEEPGRAM_API_KEY"
PRICE_PER_MIN = 0.0043


def deepgram_key():
    key = os.environ.get("DEEPGRAM_API_KEY")
    if key:
        return key
    out = subprocess.run([BWS, "secret", "list", "-o", "json"], capture_output=True, text=True, check=True).stdout
    hits = [s for s in json.loads(out) if s["key"] == DEEPGRAM_SECRET]
    if len(hits) != 1:
        raise SystemExit(f"{DEEPGRAM_SECRET}: {len(hits)} matches in BWS (need exactly 1)")
    return hits[0]["value"]


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout)


def voiced_seconds(path):
    """Seconds of the clip louder than -35 dB (a sung stem is near-silent between phrases)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    silent = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err))
    return max(0.0, duration(path) - silent)


def listen(key, audio_path, model):
    params = {"model": model, "punctuate": "true", "smart_format": "true"}
    if model.startswith("nova"):
        params["filler_words"] = "true"
    query = "&".join(f"{k}={v}" for k, v in params.items())
    with open(audio_path, "rb") as fh:
        data = fh.read()
    req = urllib.request.Request(f"https://api.deepgram.com/v1/listen?{query}", data=data, method="POST",
                                 headers={"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def words_of(response):
    alts = response.get("results", {}).get("channels", [{}])[0].get("alternatives") or [{}]
    return alts[0].get("words", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stem")
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--overlap", type=float, default=12.0)
    ap.add_argument("--start", type=float, default=0.0, help="only transcribe from here (seconds)")
    ap.add_argument("--end", type=float, default=None, help="only transcribe to here (seconds)")
    ap.add_argument("--merge-into", help="an earlier merged.json: in [start, end) keep whichever pass has more words")
    ap.add_argument("--min-words-per-voiced-min", type=float, default=20.0,
                    help="below this, a singing window is retried with whisper-large")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    total = duration(args.stem)
    key = deepgram_key()
    stop = min(total, args.end or total)
    starts, t = [], args.start
    while t < stop:
        starts.append(t)
        if t + args.window >= stop:
            break
        t += args.window - args.overlap
    billed = 0.0
    merged, report = [], []
    for i, start in enumerate(starts):
        end = min(stop, start + args.window)
        clip = os.path.join(args.out, f"w{i:02d}.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i",
                        args.stem, "-ac", "1", "-b:a", "128k", clip], check=True)
        voiced = voiced_seconds(clip)
        cache = os.path.join(args.out, f"w{i:02d}-nova-3.json")
        if os.path.exists(cache):
            best, model = json.load(open(cache, encoding="utf-8")), "nova-3"
        else:
            best, model = listen(key, clip, "nova-3"), "nova-3"
            billed += end - start
            json.dump(best, open(cache, "w", encoding="utf-8"))
        rate = len(words_of(best)) / max(voiced / 60, 1e-6)
        if voiced > 8 and rate < args.min_words_per_voiced_min:
            wcache = os.path.join(args.out, f"w{i:02d}-whisper-large.json")
            if os.path.exists(wcache):
                alt = json.load(open(wcache, encoding="utf-8"))
            else:
                alt = listen(key, clip, "whisper-large")
                billed += end - start
                json.dump(alt, open(wcache, "w", encoding="utf-8"))
            if len(words_of(alt)) > len(words_of(best)):
                best, model = alt, "whisper-large"
        # Core of this window: half the overlap trimmed from each inner edge.
        core_lo = args.start if i == 0 else start + args.overlap / 2
        core_hi = stop if i == len(starts) - 1 else end - args.overlap / 2
        kept = 0
        for w in words_of(best):
            s, e = w["start"] + start, w["end"] + start
            # Letterless tokens ("0000", music marks) are junk (project-stack-structure e6d78d4).
            if core_lo <= (s + e) / 2 < core_hi and re.search(r"[^\W\d_]", w.get("word", "")):
                merged.append({**w, "start": round(s, 3), "end": round(min(e, total), 3)})
                kept += 1
        report.append({"window": i, "from": round(start, 1), "to": round(end, 1), "voiced_s": round(voiced, 1),
                       "model": model, "words": len(words_of(best)), "kept": kept})
        print(f"[lyrics] w{i:02d} {start:6.1f}-{end:6.1f}s voiced {voiced:5.1f}s {model:13s} "
              f"{len(words_of(best)):3d} words, kept {kept}", flush=True)
    if args.merge_into:
        old = words_of(json.load(open(args.merge_into, encoding="utf-8")))
        inside = [w for w in old if args.start <= w["start"] < stop]
        keep_new = len(merged) > len(inside)
        print(f"[lyrics] {args.start:.0f}-{stop:.0f}s: earlier pass {len(inside)} words, this pass {len(merged)}; "
              f"keeping {'this' if keep_new else 'the earlier'} pass", flush=True)
        outside = [w for w in old if not (args.start <= w["start"] < stop)
                   and re.search(r"[^\W\d_]", w.get("word", ""))]
        merged = outside + (merged if keep_new else inside)
    merged.sort(key=lambda w: w["start"])
    clean, last = [], -1.0
    for w in merged:  # the coordinator requires non-decreasing starts and end > start
        if w["start"] < last or w["end"] <= w["start"]:
            continue
        clean.append(w)
        last = w["start"]
    response = {"metadata": {"duration": total, "models": sorted({r["model"] for r in report}),
                             "mvvm_windows": report},
                "results": {"channels": [{"alternatives": [{
                    "transcript": " ".join(w.get("punctuated_word", w["word"]) for w in clean), "words": clean}]}]}}
    path = os.path.join(args.out, "merged.json")
    json.dump(response, open(path, "w", encoding="utf-8"), indent=1)
    print(f"[lyrics] {len(clean)} words, first {clean[0]['start'] if clean else '-'}s, last "
          f"{clean[-1]['end'] if clean else '-'}s of {total:.1f}s; billed audio {billed / 60:.2f} min "
          f"(~${billed / 60 * PRICE_PER_MIN:.3f}); wrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
