// Edit plan on top of the cut map: effects the edit can apply (stutters on tight onset runs such as rolls and
// triplets, flashes on the biggest impacts, speed ramps on builds) and prompt chunks. A chunk groups
// consecutive cut slots into one multi-cut generation (<= maxChunkMs), after the Seedance reference grammar
// (docs/pilot/seedance-reference-cuts.md): fast inserts where hits cluster, story beats, a hold, all timed
// from the music. Loose in the prompt, exact in the edit: each shot is prompted longer than its slot (a
// handle), and the edit splits the render at its real internal cuts and trims every shot to its exact slot,
// so shots can still slide, be re-chosen, stutter or ramp.
import { energyAt, hitCurve, hitNear, type Build, type CutMap, type EnergyCurve } from "./cut-map";

export type StutterKind = "triplet" | "roll" | "stutter";
/** A tight, regular run of strong onsets: repeat a sliver of the same clip in this rhythm. */
export type Stutter = { startMs: number; endMs: number; onsetsMs: number[]; intervalMs: number; kind: StutterKind };
/** One of the biggest hits in the song: flash / brightness pulse / shake in the edit. */
export type Impact = { ms: number; strength: number };

export type ShotRole = "flash" | "beat" | "hold";
export type ChunkShot = {
  /** Song time. */
  startMs: number;
  endMs: number;
  /** Exact slot length in the edit. */
  lengthMs: number;
  /** Where this shot starts inside the generation, handles included: the prompt's timestamp. */
  promptOffsetMs: number;
  /** Length asked of the model: slot plus handle. */
  promptLengthMs: number;
  /** Loudness under the shot (0..1), for the prompt's intensity wording. */
  energy: number;
  role: ShotRole;
  section: string;
};
export type PromptChunk = {
  index: number;
  /** Song span the chunk covers in the edit. */
  startMs: number;
  endMs: number;
  /** Length of the generation, handles included. */
  promptLengthMs: number;
  sections: string[];
  shots: ChunkShot[];
  stutters: Stutter[];
  impacts: Impact[];
  builds: Build[];
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export function beatMsFrom(beatsMs: number[], fallbackBpm = 120): number {
  const gaps = beatsMs.slice(1).map((b, i) => b - beatsMs[i]).filter((g) => g > 150 && g < 2000).sort((a, b) => a - b);
  return gaps.length ? gaps[Math.floor(gaps.length / 2)] : 60000 / fallbackBpm;
}

function stutterKind(intervalMs: number, beatMs: number): StutterKind {
  const r = intervalMs / beatMs;
  if (Math.abs(r - 1 / 3) < 0.05 || Math.abs(r - 2 / 3) < 0.07 || Math.abs(r - 1 / 6) < 0.025) return "triplet";
  if (Math.abs(r - 1 / 4) < 0.05 || Math.abs(r - 1 / 8) < 0.025 || Math.abs(r - 1 / 2) < 0.05) return "roll";
  return "stutter";
}

/** Runs of 3-8 strong onsets with near-equal spacing (<= 3/4 beat) that stand apart from what surrounds
 *  them, so steady hi-hats do not read as stutters. */
export function findStutters(onsetsMs: number[], energy: EnergyCurve, beatMs: number, hits = hitCurve(energy)): Stutter[] {
  const onsets = [...new Set(onsetsMs)].sort((a, b) => a - b);
  const strong = (ms: number) => hitNear(hits, energy, ms, 40) >= 0.35 || energyAt(energy, ms) >= 0.6;
  const maxGap = beatMs * 0.75;
  const out: Stutter[] = [];
  let i = 0;
  while (i < onsets.length - 2) {
    const first = onsets[i + 1] - onsets[i];
    if (first < 60 || first > maxGap) { i++; continue; }
    let j = i + 1;
    while (j + 1 < onsets.length && j - i < 7 && Math.abs(onsets[j + 1] - onsets[j] - first) <= first * 0.2) j++;
    const run = onsets.slice(i, j + 1);
    const interval = (run.at(-1)! - run[0]) / (run.length - 1);
    const before = i > 0 ? run[0] - onsets[i - 1] : Infinity;
    const after = j + 1 < onsets.length ? onsets[j + 1] - run.at(-1)! : Infinity;
    const standsApart = before > interval * 1.3 && after > interval * 1.3;
    if (run.length >= 3 && standsApart && run.filter(strong).length >= Math.ceil(run.length * 0.67)) {
      out.push({ startMs: run[0], endMs: run.at(-1)! + interval, onsetsMs: run, intervalMs: Math.round(interval), kind: stutterKind(interval, beatMs) });
      i = j + 1;
    } else i++;
  }
  return out;
}

/** The biggest hits: hit-curve peaks in the song's top 2% on loud material, at most one per beat. */
export function findImpacts(energy: EnergyCurve, beatMs: number, hits = hitCurve(energy)): Impact[] {
  const sorted = Array.from(hits).filter((h) => h > 0).sort((a, b) => a - b);
  const cutoff = Math.max(0.85, sorted[Math.floor(sorted.length * 0.98)] ?? 1);
  const rate = energy.sampleRateHz, spacing = Math.max(1, Math.round((beatMs / 1000) * rate));
  const out: Impact[] = [];
  for (let i = 1; i < hits.length - 1; i++) {
    if (hits[i] < cutoff || hits[i] < hits[i - 1] || hits[i] < hits[i + 1]) continue;
    const ms = Math.round(energy.startMs + (i * 1000) / rate);
    if (energyAt(energy, ms) < 0.55) continue;
    const last = out.at(-1);
    if (last && ms - last.ms < beatMs) {
      if (hits[i] > last.strength) out[out.length - 1] = { ms, strength: hits[i] };
      continue;
    }
    out.push({ ms, strength: hits[i] });
    i += spacing - 1;
  }
  return out;
}

/** Extra length asked of the model per shot: 35% of the slot, 250-600 ms. */
export function handleMs(lengthMs: number): number {
  return Math.round(clamp(lengthMs * 0.35, 250, 600));
}

function roleOf(lengthMs: number, energy: number): ShotRole {
  if (lengthMs < 800) return "flash";
  if (lengthMs >= 3000 && energy < 0.6) return "hold";
  return "beat";
}

/** Group consecutive cut slots into generation-sized chunks, preferring to break at section changes once a
 *  chunk is at least minChunkMs long. */
export function planChunks(
  map: CutMap,
  energy: EnergyCurve,
  fx: { stutters: Stutter[]; impacts: Impact[] },
  maxChunkMs = 11000,
  minChunkMs = 6000,
): PromptChunk[] {
  const chunks: PromptChunk[] = [];
  let current: typeof map.slots = [];
  const flush = () => {
    if (!current.length) return;
    const startMs = current[0].startMs, endMs = current.at(-1)!.endMs;
    const inside = <T extends { startMs: number; endMs: number }>(x: T) => x.startMs < endMs && x.endMs > startMs;
    let cursor = 0;
    const shots = current.map((s) => {
      const lengthMs = s.endMs - s.startMs;
      let sum = 0, n = 0;
      for (let t = s.startMs; t < s.endMs; t += 50) { sum += energyAt(energy, t); n++; }
      const e = clamp(n ? sum / n : energyAt(energy, s.startMs), 0, 1);
      const promptLengthMs = lengthMs + handleMs(lengthMs);
      const shot: ChunkShot = {
        startMs: s.startMs, endMs: s.endMs, lengthMs, promptOffsetMs: cursor, promptLengthMs,
        energy: Math.round(e * 100) / 100, role: roleOf(lengthMs, e), section: s.sectionLabel,
      };
      cursor += promptLengthMs;
      return shot;
    });
    chunks.push({
      index: chunks.length,
      startMs,
      endMs,
      promptLengthMs: cursor,
      sections: [...new Set(current.map((s) => s.sectionLabel))],
      shots,
      stutters: fx.stutters.filter((x) => x.startMs >= startMs && x.startMs < endMs),
      impacts: fx.impacts.filter((x) => x.ms >= startMs && x.ms < endMs),
      builds: map.builds.filter(inside),
    });
    current = [];
  };
  for (const slot of map.slots) {
    const start = current[0]?.startMs ?? slot.startMs;
    const length = slot.endMs - start;
    const sectionChange = current.length > 0 && current.at(-1)!.section !== slot.section;
    if (current.length && (length > maxChunkMs || (sectionChange && current.at(-1)!.endMs - start >= minChunkMs))) flush();
    current.push(slot);
  }
  flush();
  return chunks;
}
