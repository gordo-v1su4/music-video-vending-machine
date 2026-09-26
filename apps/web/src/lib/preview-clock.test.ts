import { describe, expect, test } from "bun:test";
import { PreviewClock } from "./preview-clock";
import { videoPosition } from "./timing";
import type { AudioBreak } from "./api";

const breaks: AudioBreak[] = [
  {
    id: "pause",
    kind: "insertion",
    songStartMs: 5000,
    durationMs: 3000,
    assetId: null,
  },
  {
    id: "mute",
    kind: "cutout",
    songStartMs: 12000,
    durationMs: 2000,
    assetId: null,
  },
];
const duration = 33000;

describe("preview clock during delayed frames and background pauses", () => {
  test("uses all elapsed time after a delayed frame instead of rewinding advancing audio", () => {
    const clock = new PreviewClock();
    clock.play(1000, 100);
    expect(clock.position(116, duration)).toBe(1016);
    // Audio has advanced five seconds while the main thread did not paint.
    expect(clock.position(5100, duration)).toBe(6000);
    expect(clock.position(5200, duration)).toBe(6100);
  });

  test("captures sub-frame progress on hide and excludes the entire hidden interval", () => {
    const clock = new PreviewClock();
    clock.play(1000, 100);
    expect(clock.position(116, duration)).toBe(1016);
    const paused = clock.pause(125, duration);
    expect(paused).toBe(1025);
    expect(clock.position(60125, duration)).toBe(paused);
    clock.play(paused, 60125);
    expect(clock.position(61125, duration)).toBe(2025);
  });

  test("a delayed frame crossing a whole insertion resumes at the correct song offset", () => {
    const clock = new PreviewClock();
    clock.play(4900, 0);
    const afterDelayedFrame = clock.position(3600, duration);
    expect(afterDelayedFrame).toBe(8500);
    expect(videoPosition(afterDelayedFrame, breaks)).toEqual({
      songMs: 5500,
      muted: false,
      breakId: null,
      breakMs: 0,
    });
  });

  test("a delayed frame crossing an entire cutout does not lose song time or remain muted", () => {
    const clock = new PreviewClock();
    clock.play(14900, 0);
    const afterDelayedFrame = clock.position(2600, duration);
    expect(afterDelayedFrame).toBe(17500);
    expect(videoPosition(afterDelayedFrame, breaks)).toEqual({
      songMs: 14500,
      muted: false,
      breakId: null,
      breakMs: 0,
    });
  });

  test("preserves inserted pause progress across hide and resumes song after its remaining duration", () => {
    const clock = new PreviewClock();
    clock.play(4900, 0);
    // A long frame lands 1.5 seconds into the insertion, holding song time.
    const paused = clock.pause(1600, duration);
    expect(videoPosition(paused, breaks)).toEqual({
      songMs: 5000,
      muted: true,
      breakId: "pause",
      breakMs: 1500,
    });
    expect(videoPosition(clock.position(61600, duration), breaks).breakMs).toBe(
      1500,
    );
    clock.play(paused, 61600);
    expect(videoPosition(clock.position(63100, duration), breaks)).toEqual({
      songMs: 5000,
      muted: false,
      breakId: null,
      breakMs: 0,
    });
    expect(videoPosition(clock.position(64100, duration), breaks).songMs).toBe(
      6000,
    );
  });

  test("cutouts keep advancing song time and preserve remaining mute duration after hide", () => {
    const clock = new PreviewClock();
    clock.play(14900, 0);
    const paused = clock.pause(600, duration);
    expect(videoPosition(paused, breaks)).toEqual({
      songMs: 12500,
      muted: true,
      breakId: "mute",
      breakMs: 500,
    });
    clock.play(paused, 60600);
    expect(videoPosition(clock.position(61600, duration), breaks).songMs).toBe(
      13500,
    );
    expect(videoPosition(clock.position(62100, duration), breaks).muted).toBe(
      false,
    );
  });

  test("seeking reanchors active playback and a long final frame stops at duration", () => {
    const clock = new PreviewClock();
    clock.play(1000, 0);
    clock.seek(10000, 500);
    expect(clock.position(1500, duration)).toBe(11000);
    expect(clock.pause(100000, duration)).toBe(duration);
    expect(clock.position(200000, duration)).toBe(duration);
  });
});
