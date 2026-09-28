// Music-driven cut map. Section budgeting after Project Stack Structure's adaptiveCueMap (cuts per section
// from bars x density x energy, oversized gaps split); hit detection after Beatsmaxxer Pro's onset triggers
// (a hit is a rise in energy against a decaying running peak, not the energy level itself).
// Candidates: onsets scored by the hit under them, energy jumps with no onset, lyric phrase starts.
// Cuts always include section boundaries and never leave a slot shorter than minSlotMs.
// Energy drives pace locally: each bar's energy weights how many cuts a section gets, loud accents win
// selection, and quiet stretches may hold a shot longer than loud ones. Sustained energy climbs are
// reported as builds (speed-ramp candidates).

export type CutSection = { startMs: number; endMs: number; label: string; energy?: number };
export type EnergyCurve = { values: number[]; sampleRateHz: number; startMs: number };
export type CutSource = "onset" | "energy" | "lyric" | "section" | "split";

export type CutPoint = { ms: number; source: CutSource; score: number };

export type CutSlot = {
  startMs: number;
  endMs: number;
  section: number;
  sectionLabel: string;
  /** Mean hit score inside the slot (0..1); how hard the music is pushing there. */
  strength: number;
};

/** A sustained energy climb (riser, build-up): a candidate for a speed ramp in the edit. */
export type Build = { startMs: number; endMs: number; rise: number };

export type CutMap = {
  /** Every cut, section boundaries included, sorted by time. */
  cuts: CutPoint[];
  slots: CutSlot[];
  builds: Build[];
  maxSlotMs: number;
};

export type CutMapInput = {
  durationMs: number;
  sections: CutSection[];
  onsetsMs: number[];
  beatsMs: number[];
  energy: EnergyCurve;
  /** 0.1 (sparse, long shots) .. 1 (dense, fast cutting). */
  density: number;
  lyricStartsMs?: number[];
  /** Share of lyric phrase starts that also become cuts (0 = none). */
  lyricBlend?: number;
  /** Cuts closer than this are not placed; keeps flash frames out. */
  minSlotMs?: number;
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function index(energy: EnergyCurve, ms: number) {
  return clamp(Math.round(((ms - energy.startMs) * energy.sampleRateHz) / 1000), 0, energy.values.length - 1);
}

export function energyAt(energy: EnergyCurve, ms: number): number {
  return clamp(energy.values[index(energy, ms)] ?? 0, 0, 1);
}

function meanEnergy(energy: EnergyCurve, startMs: number, endMs: number): number {
  const a = index(energy, startMs), b = index(energy, endMs);
  if (b <= a) return energyAt(energy, startMs);
  let sum = 0;
  for (let i = a; i < b; i++) sum += energy.values[i];
  return clamp(sum / (b - a), 0, 1);
}

/** Loudness of a stretch as its 75th-percentile energy: spiky bars read as loud, not averaged away. */
function loudEnergy(energy: EnergyCurve, startMs: number, endMs: number): number {
  const a = index(energy, startMs), b = index(energy, endMs);
  if (b <= a) return energyAt(energy, startMs);
  const window = energy.values.slice(a, b).sort((x, y) => x - y);
  return clamp(window[Math.floor(window.length * 0.75)] ?? 0, 0, 1);
}

function percentile(values: number[], p: number) {
  const sorted = values.filter((v) => v > 0).sort((a, b) => a - b);
  return sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))] : 1;
}

/** Per-sample hit strength 0..1: rise of energy over ~60 ms against a running peak (~4 s half-life),
 *  scaled by the song's own 95th-percentile rise so quiet and loud mixes read the same. */
export function hitCurve(energy: EnergyCurve): Float32Array {
  const n = energy.values.length, rate = energy.sampleRateHz;
  const decay = Math.pow(0.5, 1 / (4 * rate));
  const lag = Math.max(1, Math.round(0.06 * rate));
  const norm = new Float32Array(n);
  let peak = 0.01;
  for (let i = 0; i < n; i++) {
    const smooth = (energy.values[Math.max(0, i - 1)] + energy.values[i] + energy.values[Math.min(n - 1, i + 1)]) / 3;
    peak = Math.max(peak * decay, smooth, 0.01);
    norm[i] = smooth / peak;
  }
  const rise = new Float32Array(n);
  for (let i = lag; i < n; i++) rise[i] = Math.max(0, norm[i] - norm[i - lag]);
  const scale = percentile(Array.from(rise), 0.95) || 1;
  for (let i = 0; i < n; i++) rise[i] = clamp(rise[i] / scale, 0, 1);
  return rise;
}

function hitNear(hits: Float32Array, energy: EnergyCurve, ms: number, windowMs = 50) {
  const a = index(energy, ms - windowMs), b = index(energy, ms + windowMs);
  let best = 0;
  for (let i = a; i <= b; i++) best = Math.max(best, hits[i]);
  return best;
}

export function maxSlotMsFor(density: number): number {
  return Math.max(1200, 6500 - clamp(density, 0.1, 1) * 4600);
}

/** Longest slot allowed over a stretch: quiet can hold up to 1.45x the density maximum, loud down to 0.55x. */
export function allowedSlotMs(maxSlotMs: number, meanEnergyValue: number, minSlotMs: number): number {
  return Math.max(minSlotMs * 2, maxSlotMs * (1.45 - 0.9 * clamp(meanEnergyValue, 0, 1)));
}

/** Sustained climbs: energy smoothed over ~1 s (spiky mixes read as their envelope) rising for at least minMs by at least minRise. */
export function findBuilds(energy: EnergyCurve, minMs = 1500, minRise = 0.15): Build[] {
  const rate = energy.sampleRateHz, n = energy.values.length;
  const half = Math.max(1, Math.round(0.5 * rate));
  const smooth = new Float32Array(n);
  let acc = 0;
  for (let i = 0; i < n + half; i++) {
    if (i < n) acc += energy.values[i];
    if (i - 2 * half - 1 >= 0) acc -= energy.values[i - 2 * half - 1];
    const c = i - half;
    if (c >= 0 && c < n) smooth[c] = acc / Math.min(2 * half + 1, i + 1, n - (c - half));
  }
  const step = Math.max(1, Math.round(0.1 * rate)); // judge slope every 100 ms
  const builds: Build[] = [];
  let start = -1, dips = 0;
  const toMs = (i: number) => Math.round(energy.startMs + (i * 1000) / rate);
  const close = (end: number) => {
    const rise = smooth[end] - smooth[start];
    if (toMs(end) - toMs(start) >= minMs && rise >= minRise) builds.push({ startMs: toMs(start), endMs: toMs(end), rise: clamp(rise, 0, 1) });
    start = -1;
    dips = 0;
  };
  let last = 0;
  for (let i = step; i < n; i += step) {
    last = i;
    const rising = smooth[i] > smooth[i - step] + 0.002;
    if (rising) { if (start < 0) start = i - step; dips = 0; }
    else if (start >= 0 && ++dips > 4) close(i - step * dips); // tolerate brief dips of up to 400 ms
  }
  if (start >= 0) close(last);
  return builds;
}

export function candidatePoints(input: CutMapInput, hits = hitCurve(input.energy)): CutPoint[] {
  const { energy, durationMs } = input;
  const inSong = (t: number) => t > 0 && t < durationMs;
  const onsets = [...new Set(input.onsetsMs)].filter(inSong).sort((a, b) => a - b);
  const points: CutPoint[] = onsets.map((ms) => ({
    ms,
    source: "onset",
    score: clamp(0.6 * hitNear(hits, energy, ms) + 0.4 * energyAt(energy, ms), 0.02, 1),
  }));
  // Energy jumps with no onset nearby: local maxima of the hit curve in the top decile.
  const strong = percentile(Array.from(hits), 0.9);
  const rate = energy.sampleRateHz, spacing = Math.round(0.12 * rate);
  for (let i = spacing; i < hits.length - spacing; i++) {
    if (hits[i] < strong || hits[i] < 0.5) continue;
    let isPeak = true;
    for (let j = i - spacing; j <= i + spacing && isPeak; j++) if (hits[j] > hits[i]) isPeak = false;
    if (!isPeak) continue;
    const ms = Math.round(energy.startMs + (i * 1000) / rate);
    if (!inSong(ms) || onsets.some((o) => Math.abs(o - ms) < 80)) continue;
    points.push({ ms, source: "energy", score: clamp(0.9 * hits[i], 0.02, 1) });
  }
  for (const ms of input.lyricStartsMs ?? [])
    if (inSong(ms)) points.push({ ms, source: "lyric", score: 0.55 + 0.35 * energyAt(energy, ms) });
  return points.sort((a, b) => a.ms - b.ms);
}

export function buildCutMap(input: CutMapInput): CutMap {
  const { energy } = input;
  const density = clamp(input.density, 0.1, 1);
  const lyricBlend = clamp(input.lyricBlend ?? 0, 0, 1);
  const minSlot = input.minSlotMs ?? 500;
  const maxSlotMs = maxSlotMsFor(density);
  const hits = hitCurve(energy);
  const candidates = candidatePoints(input, hits);
  const sections = [...input.sections].filter((s) => s.endMs > s.startMs + 50).sort((a, b) => a.startMs - b.startMs);

  const cuts: CutPoint[] = [];
  const slots: CutSlot[] = [];

  sections.forEach((section, si) => {
    const { startMs: start, endMs: end } = section;
    const inside = candidates.filter((c) => c.ms > start + 50 && c.ms < end - 50);
    const musical = inside.filter((c) => c.source !== "lyric");
    const lyrics = inside.filter((c) => c.source === "lyric");
    const beats = input.beatsMs.filter((b) => b >= start && b < end);
    const bars = Math.max(1, beats.length / 4);
    // Each bar counts by its own loudness: quiet ~0.3, loud ~1.85. Loud bars pull in more cuts; at 45%
    // density a loud bar gets about one cut, a quiet one about one per three to four bars.
    let weight = 0;
    for (let b = 0; b < beats.length; b += 4) {
      const e = loudEnergy(energy, beats[b], beats[b + 4] ?? end);
      weight += 0.25 + 1.6 * Math.pow(e, 1.5);
    }
    if (!beats.length) weight = 0.25 + 1.6 * Math.pow(section.energy ?? loudEnergy(energy, start, end), 1.5);
    const target = Math.max(Math.max(1, Math.floor(bars / 8)), Math.round(weight * (0.12 + density * 1.3)));

    const chosen: CutPoint[] = [{ ms: start, source: "section", score: 1 }];
    const fits = (ms: number) => chosen.every((c) => Math.abs(c.ms - ms) >= minSlot) && end - ms >= minSlot;
    let placed = 0;
    const weighted = (c: CutPoint) => c.score * (0.55 + 0.9 * energyAt(energy, c.ms));
    for (const c of [...musical].sort((a, b) => weighted(b) - weighted(a))) {
      if (placed >= target) break;
      if (fits(c.ms)) { chosen.push(c); placed++; }
    }
    const lyricTake = Math.round(lyrics.length * lyricBlend);
    for (const c of [...lyrics].sort((a, b) => b.score - a.score).slice(0, lyricTake)) if (fits(c.ms)) chosen.push(c);
    chosen.sort((a, b) => a.ms - b.ms);

    // Split oversized gaps at the strongest unused candidate (midpoint when none) until every slot fits.
    const bounds = [...chosen.map((c) => c.ms), end];
    for (let i = 0, guard = 512; i < bounds.length - 1 && guard > 0; guard--) {
      const a = bounds[i], b = bounds[i + 1];
      if (b - a <= allowedSlotMs(maxSlotMs, loudEnergy(energy, a, b), minSlot)) { i++; continue; }
      const margin = Math.max(minSlot, Math.min(400, (b - a) / 4));
      const pick = musical
        .filter((c) => c.ms > a + margin && c.ms < b - margin && !bounds.includes(c.ms))
        .sort((x, y) => y.score - x.score)[0];
      const point: CutPoint = pick ?? { ms: Math.round((a + b) / 2), source: "split", score: 0 };
      bounds.splice(i + 1, 0, point.ms);
      chosen.push(point);
    }
    chosen.sort((a, b) => a.ms - b.ms);
    cuts.push(...chosen);

    for (let i = 0; i < bounds.length - 1; i++) {
      const a = bounds[i], b = bounds[i + 1];
      const within = musical.filter((c) => c.ms >= a && c.ms < b);
      slots.push({
        startMs: a,
        endMs: b,
        section: si,
        sectionLabel: section.label,
        strength: within.length ? Math.max(...within.map((c) => c.score)) : meanEnergy(energy, a, b),
      });
    }
  });
  const last = sections.at(-1);
  if (last) cuts.push({ ms: last.endMs, source: "section", score: 1 });

  return { cuts, slots, builds: findBuilds(energy), maxSlotMs };
}
