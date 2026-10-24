import { describe, expect, test } from "bun:test";
import { songToVideo, videoDuration, videoPosition } from "./timing";
import type { AudioBreak } from "./api";
const breaks: AudioBreak[] = [
  {
    id: "insert",
    kind: "insertion",
    songStartMs: 10000,
    durationMs: 3000,
    assetId: null,
  },
  {
    id: "mute",
    kind: "cutout",
    songStartMs: 15000,
    durationMs: 2000,
    assetId: null,
  },
];
describe("preview time mapping", () => {
  test("song time maps to video time past earlier insertions only", () => {
    expect(songToVideo(5000, breaks)).toBe(5000);
    expect(songToVideo(10000, breaks)).toBe(13000);
    expect(songToVideo(16000, breaks)).toBe(19000);
    expect(videoPosition(songToVideo(16000, breaks), breaks).songMs).toBe(16000);
  });
  test("insertions lengthen video and hold song position", () => {
    expect(videoDuration(30000, breaks)).toBe(33000);
    expect(videoPosition(11500, breaks)).toEqual({
      songMs: 10000,
      muted: true,
      breakId: "insert",
      breakMs: 1500,
    });
    expect(videoPosition(13000, breaks).songMs).toBe(10000);
  });
  test("cutout mutes without pausing song", () => {
    expect(videoPosition(19000, breaks)).toEqual({
      songMs: 16000,
      muted: true,
      breakId: "mute",
      breakMs: 1000,
    });
    expect(videoPosition(20000, breaks).muted).toBe(false);
  });
  test("multiple insertions accumulate independent of source ordering", () => {
    const later: AudioBreak = {
      id: "later",
      kind: "insertion",
      songStartMs: 20000,
      durationMs: 4000,
      assetId: null,
    };
    expect(videoPosition(25000, [later, ...breaks]).songMs).toBe(20000);
    expect(videoPosition(28000, [later, ...breaks]).songMs).toBe(21000);
  });
});
