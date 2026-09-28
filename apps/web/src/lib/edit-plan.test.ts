import { describe, expect, test } from "bun:test";
import { buildCutMap } from "./cut-map";
import { beatMsFrom, findStutters, handleMs, planChunks } from "./edit-plan";

const RATE = 100;
const flat = (seconds: number, level = 0.5) => ({ values: Array(seconds * RATE).fill(level), sampleRateHz: RATE, startMs: 0 });

describe("edit plan", () => {
  test("beat length is the median beat gap", () => {
    expect(beatMsFrom([0, 440, 880, 1320, 1765, 2200])).toBe(440);
  });

  test("a bounded run of tight, even onsets is a stutter; steady hats are not", () => {
    const energy = flat(10, 0.7);
    const roll = [1000, 1110, 1220, 1330, 1440];
    const stutters = findStutters([0, 500, ...roll, 2400, 3000], energy, 440);
    expect(stutters.length).toBe(1);
    expect(stutters[0].kind).toBe("roll");
    expect(stutters[0].onsetsMs).toEqual(roll);
    const hats = Array.from({ length: 40 }, (_, i) => i * 110);
    expect(findStutters(hats, energy, 440)).toEqual([]);
  });

  test("third-of-a-beat spacing reads as a triplet", () => {
    const stutters = findStutters([0, 800, 947, 1094, 1241, 2000], flat(4, 0.7), 440);
    expect(stutters[0]?.kind).toBe("triplet");
  });

  test("chunks stay generation-sized and every shot gets a handle", () => {
    const beatsMs = Array.from({ length: 160 }, (_, i) => i * 500);
    const onsetsMs = beatsMs.filter((b) => b > 0);
    const energy = flat(80, 0.6);
    const map = buildCutMap({
      durationMs: 80000,
      sections: [{ startMs: 0, endMs: 40000, label: "verse" }, { startMs: 40000, endMs: 80000, label: "chorus" }],
      onsetsMs, beatsMs, energy, density: 0.5,
    });
    const chunks = planChunks(map, energy, { stutters: [], impacts: [] });
    expect(chunks.map((c) => c.shots.length).reduce((a, b) => a + b)).toBe(map.slots.length);
    for (const c of chunks) {
      expect(c.endMs - c.startMs).toBeLessThanOrEqual(11000);
      let cursor = 0;
      for (const s of c.shots) {
        expect(s.promptOffsetMs).toBe(cursor);
        expect(s.promptLengthMs).toBe(s.lengthMs + handleMs(s.lengthMs));
        cursor += s.promptLengthMs;
      }
      expect(c.promptLengthMs).toBe(cursor);
    }
    // No chunk straddles the section change when it could break there.
    expect(chunks.some((c) => c.startMs === 40000)).toBe(true);
  });
});
