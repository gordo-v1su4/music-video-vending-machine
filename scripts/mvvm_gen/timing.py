"""Beat-grid timing for shot cuts and pilot passage selection (standard library only)."""

import array
import math
import subprocess

FPS = 24


def bar_seconds(bpm, beats_per_bar=4):
    return 60.0 / bpm * beats_per_bar


def shot_frames(bars_per_shot, bpm, start_frame=0):
    """Frame counts per shot using cumulative rounding so the cut never drifts off the grid."""
    frames, bar, elapsed = [], bar_seconds(bpm), 0.0
    prev = start_frame
    for bars in bars_per_shot:
        elapsed += bars * bar
        edge = start_frame + round(elapsed * FPS)
        frames.append(edge - prev)
        prev = edge
    return frames


def load_envelope(path, rate=200):
    """Mono 16-bit PCM at `rate` Hz via ffmpeg, as a list of absolute sample values."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        check=True, capture_output=True).stdout
    return [abs(v) for v in array.array("h", raw)], rate


def downbeat_phase(env, rate, bpm):
    """Offset (s) within one beat whose grid lands on the strongest onsets."""
    flux = [max(0, env[i] - env[i - 1]) for i in range(1, len(env))]
    beat = 60.0 / bpm
    best, best_offset = -1.0, 0.0
    for step in range(int(beat * rate)):
        offset = step / rate
        score, t = 0.0, offset
        while t * rate < len(flux):
            score += flux[int(t * rate)]
            t += beat
        if score > best:
            best, best_offset = score, offset
    return best_offset


def loudest_window(env, rate, bpm, bars, phase, step_bars=4):
    """Start time of the `bars`-long, bar-aligned window with the highest RMS."""
    bar = bar_seconds(bpm)
    total = len(env) / rate
    best, best_start = -1.0, phase
    start = phase
    while start + bars * bar <= total:
        a, b = int(start * rate), int((start + bars * bar) * rate)
        rms = math.sqrt(sum(v * v for v in env[a:b]) / max(1, b - a))
        if rms > best:
            best, best_start = rms, start
        start += step_bars * bar
    return best_start
