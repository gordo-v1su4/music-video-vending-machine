import { describe, expect, test } from "bun:test";
import { buildCutMap, candidatePoints, findBuilds, hitCurve, maxSlotMsFor } from "./cut-map";

const RATE = 100;
// 40 s song, two sections; quiet bed with hits every 500 ms and a big jump at 25 s that has no onset.
function song() {
  const values = Array.from({ length: 40 * RATE }, (_, i) => {
    const ms = (i * 1000) / RATE;
    const hit = ms % 500 < 40 ? 0.5 : 0;
    const jump = ms >= 25000 && ms < 25300 ? 0.9 : 0;
    const bed = ms < 20000 ? 0.1 : 0.4; // the chorus really is louder
    return Math.min(1, bed + hit + jump);
  });
  const beatsMs = Array.from({ length: 80 }, (_, i) => i * 500);
  const onsetsMs = beatsMs.filter((ms) => ms > 0 && ms !== 25000);
  return {
    durationMs: 40000,
    sections: [
      { startMs: 0, endMs: 20000, label: "verse", energy: 0.3 },
      { startMs: 20000, endMs: 40000, label: "chorus", energy: 0.9 },
    ],
    onsetsMs,
    beatsMs,
    energy: { values, sampleRateHz: RATE, startMs: 0 },
  };
}

describe("cut map", () => {
  test("section boundaries are always cuts", () => {
    const map = buildCutMap({ ...song(), density: 0.4 });
    const ms = map.cuts.map((c) => c.ms);
    for (const b of [0, 20000, 40000]) expect(ms).toContain(b);
  });

  test("slots stay within the min and the energy-scaled max length", () => {
    for (const density of [0.2, 0.5, 0.9]) {
      const map = buildCutMap({ ...song(), density });
      for (const s of map.slots) {
        expect(s.endMs - s.startMs).toBeGreaterThanOrEqual(500);
        expect(s.endMs - s.startMs).toBeLessThanOrEqual(maxSlotMsFor(density) * 1.45);
      }
    }
  });

  test("a sustained climb is reported as a build", () => {
    const values = Array.from({ length: 10 * RATE }, (_, i) => {
      const ms = (i * 1000) / RATE;
      return ms < 3000 ? 0.2 : ms < 6000 ? 0.2 + ((ms - 3000) / 3000) * 0.6 : 0.8;
    });
    const builds = findBuilds({ values, sampleRateHz: RATE, startMs: 0 });
    expect(builds.length).toBe(1);
    expect(builds[0].startMs).toBeLessThan(3500);
    expect(builds[0].endMs).toBeGreaterThan(5000);
    expect(findBuilds({ values: values.map(() => 0.5), sampleRateHz: RATE, startMs: 0 })).toEqual([]);
  });

  test("higher density cuts more, and the louder section more than the quieter one", () => {
    const sparse = buildCutMap({ ...song(), density: 0.2 });
    const dense = buildCutMap({ ...song(), density: 0.9 });
    expect(dense.slots.length).toBeGreaterThan(sparse.slots.length);
    const verse = dense.slots.filter((s) => s.section === 0).length;
    const chorus = dense.slots.filter((s) => s.section === 1).length;
    expect(chorus).toBeGreaterThanOrEqual(verse);
  });

  test("an energy jump with no onset is still a cut candidate", () => {
    const input = { ...song(), density: 0.5 };
    const jump = candidatePoints(input).find((c) => c.source === "energy" && Math.abs(c.ms - 25000) <= 100);
    expect(jump).toBeDefined();
  });

  test("hit curve measures rises, not level", () => {
    const hits = hitCurve(song().energy);
    // The rise into the jump (25.00-25.06 s) scores high; the flat top after it scores lower.
    const rise = Math.max(...hits.slice(Math.round(24.98 * RATE), Math.round(25.07 * RATE)));
    expect(rise).toBeGreaterThan(0.5);
    expect(rise).toBeGreaterThan(hits[Math.round(25.2 * RATE)]);
  });
});
