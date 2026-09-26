import { describe, expect, test } from "bun:test";
import type { AudioBreak } from "./api";
import {
  PreviewPlayback,
  type PlaybackState,
  type PreviewMedia,
} from "./preview-playback";
import { videoDuration, videoPosition } from "./timing";

class DelayedMedia implements PreviewMedia {
  currentTime = 0;
  ended = false;
  paused = true;
  pauses = 0;
  private resolvePlay!: () => void;
  private listeners = new Map<string, Set<() => void>>();
  play() {
    return new Promise<void>((resolve) => {
      this.resolvePlay = resolve;
    });
  }
  ready() {
    this.paused = false;
    this.emit("playing");
    this.resolvePlay();
  }
  advance(ms: number) {
    if (!this.paused) this.currentTime += ms / 1000;
  }
  pause() {
    this.paused = true;
    this.pauses++;
  }
  addEventListener(type: string, listener: () => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(listener);
  }
  removeEventListener(type: string, listener: () => void) {
    this.listeners.get(type)?.delete(listener);
  }
  emit(type: string) {
    for (const listener of this.listeners.get(type) ?? []) listener();
  }
}

function harness(breaks: AudioBreak[] = []) {
  let now = 0;
  const media: DelayedMedia[] = [];
  const sources: string[] = [];
  let state: PlaybackState = {
    positionMs: 0,
    playing: false,
    waiting: false,
    error: "",
  };
  const playback = new PreviewPlayback(
    () => ({
      durationMs: videoDuration(30000, breaks),
      breaks,
      masterUrl: "master",
      urls: { dialogue: "dialogue" },
    }),
    (source) => {
      const item = new DelayedMedia();
      media.push(item);
      sources.push(source);
      return item;
    },
    () => now,
    (next) => {
      state = next;
    },
  );
  return {
    playback,
    media,
    sources,
    state: () => state,
    elapsed: (ms: number) => {
      now += ms;
    },
  };
}

describe("preview playback with delayed real media operations", () => {
  test("startup and resume exclude pending play time and never seek over the song opening", async () => {
    const h = harness();
    const starting = h.playback.play(0);
    h.elapsed(8000);
    await h.playback.tick();
    expect(h.state()).toMatchObject({
      positionMs: 0,
      waiting: true,
      playing: true,
    });
    expect(h.media[0].currentTime).toBe(0);
    h.media[0].ready();
    await starting;
    await h.playback.tick();
    expect(h.state().positionMs).toBe(0);
    h.elapsed(1000);
    h.media[0].advance(1000);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(1000);
    h.playback.pause();
    const resuming = h.playback.play(h.state().positionMs);
    h.elapsed(15000);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(1000);
    expect(h.media[1].currentTime).toBe(1);
    h.media[1].ready();
    await resuming;
    h.elapsed(500);
    h.media[1].advance(500);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(1500);
  });

  for (const kind of ["insertion", "cutout"] as const) {
    test(`${kind} waits for dialogue and master restart without skipping their starts`, async () => {
      const breaks: AudioBreak[] = [
        {
          id: "break",
          kind,
          songStartMs: 5000,
          durationMs: 3000,
          assetId: "dialogue",
        },
      ];
      const h = harness(breaks);
      const start = h.playback.play(0);
      h.media[0].ready();
      await start;
      h.elapsed(5000);
      h.media[0].advance(5000);
      const entering = h.playback.tick();
      expect(h.sources).toEqual(["master", "dialogue"]);
      expect(h.media[0].paused).toBe(true);
      h.elapsed(20000);
      await h.playback.tick();
      expect(h.state()).toMatchObject({ positionMs: 5000, waiting: true });
      expect(h.media[1].currentTime).toBe(0);
      h.media[1].ready();
      await entering;
      h.elapsed(1000);
      h.media[1].advance(1000);
      await h.playback.tick();
      expect(videoPosition(h.state().positionMs, breaks)).toMatchObject({
        songMs: kind === "insertion" ? 5000 : 6000,
        breakMs: 1000,
        muted: true,
      });
      h.elapsed(2000);
      h.media[1].advance(2000);
      const leaving = h.playback.tick();
      expect(h.sources).toEqual(["master", "dialogue", "master"]);
      expect(h.media[2].currentTime).toBe(kind === "insertion" ? 5 : 8);
      h.elapsed(12000);
      await h.playback.tick();
      expect(h.state().positionMs).toBe(8000);
      h.media[2].ready();
      await leaving;
      h.media[2].advance(250);
      h.elapsed(250);
      await h.playback.tick();
      expect(h.state().positionMs).toBe(8250);
    });
  }

  test("buffering freezes the timeline at actual media time until audio advances", async () => {
    const h = harness();
    const start = h.playback.play(0);
    h.media[0].ready();
    await start;
    h.media[0].advance(2000);
    h.elapsed(2000);
    await h.playback.tick();
    h.media[0].emit("waiting");
    h.elapsed(90000);
    await h.playback.tick();
    expect(h.state()).toMatchObject({ positionMs: 2000, waiting: true });
    expect(h.media[0].currentTime).toBe(2);
    h.media[0].emit("playing");
    h.media[0].advance(500);
    h.elapsed(500);
    await h.playback.tick();
    expect(h.state()).toMatchObject({ positionMs: 2500, waiting: false });
  });

  test("hiding during pending play cancels it; late completion cannot revive playback", async () => {
    const h = harness();
    const start = h.playback.play(0);
    h.elapsed(10000);
    h.playback.pause();
    h.media[0].ready();
    await start;
    h.elapsed(10000);
    await h.playback.tick();
    expect(h.state()).toMatchObject({
      positionMs: 0,
      playing: false,
      waiting: false,
    });
    expect(h.media[0].paused).toBe(true);
  });

  test("an old pending completion cannot pause a new session after seek or quick resume", async () => {
    const h = harness();
    const oldPlay = h.playback.play(0);
    const sought = h.playback.seek(12000);
    h.media[1].ready();
    await sought;
    h.media[0].ready();
    await oldPlay;
    expect(h.media[0].paused).toBe(true);
    expect(h.media[1].paused).toBe(false);
    h.media[1].advance(1000);
    h.elapsed(1000);
    await h.playback.tick();
    expect(h.state()).toMatchObject({ positionMs: 13000, playing: true });
  });

  test("a silent inserted interval uses elapsed time, then waits at the exact master resume point", async () => {
    const breaks: AudioBreak[] = [
      {
        id: "silence",
        kind: "insertion",
        songStartMs: 5000,
        durationMs: 3000,
        assetId: null,
      },
    ];
    const h = harness(breaks);
    const start = h.playback.play(5000);
    await start;
    expect(h.media.length).toBe(0);
    h.elapsed(1500);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(6500);
    h.playback.pause();
    h.elapsed(60000);
    await h.playback.play(h.state().positionMs);
    h.elapsed(1500);
    const ending = h.playback.tick();
    expect(h.state()).toMatchObject({ positionMs: 8000, waiting: true });
    expect(h.media[0].currentTime).toBe(5);
    h.elapsed(20000);
    h.media[0].ready();
    await ending;
    await h.playback.tick();
    expect(h.state().positionMs).toBe(8000);
  });

  test("resume inside dialogue waits without losing its saved offset, then preserves a silent tail", async () => {
    const h = harness([
      {
        id: "dialogue-break",
        kind: "insertion",
        songStartMs: 5000,
        durationMs: 3000,
        assetId: "dialogue",
      },
    ]);
    const start = h.playback.play(6500);
    expect(h.media[0].currentTime).toBe(1.5);
    h.elapsed(20000);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(6500);
    h.media[0].ready();
    await start;
    h.media[0].advance(500);
    h.elapsed(500);
    h.media[0].ended = true;
    h.media[0].emit("ended");
    expect(h.state().positionMs).toBe(7000);
    h.elapsed(500);
    await h.playback.tick();
    expect(h.state().positionMs).toBe(7500);
    h.playback.pause();
  });

  test("a delayed frame cannot skip an entire dialogue interval", async () => {
    const h = harness([
      {
        id: "dialogue-break",
        kind: "insertion",
        songStartMs: 5000,
        durationMs: 3000,
        assetId: "dialogue",
      },
    ]);
    const start = h.playback.play(0);
    h.media[0].ready();
    await start;
    h.media[0].advance(10000);
    h.elapsed(10000);
    const transition = h.playback.tick();
    expect(h.state().positionMs).toBe(5000);
    expect(h.media[1].currentTime).toBe(0);
    h.media[1].ready();
    await transition;
    expect(h.state()).toMatchObject({ positionMs: 5000, waiting: false });
    h.playback.pause();
  });

  test("disposing a replaced project stops pending media without publishing its stale playhead", async () => {
    const h = harness();
    const pending = h.playback.play(12000);
    const lastPublished = h.state();
    h.playback.dispose();
    h.media[0].ready();
    await pending;
    expect(h.media[0].paused).toBe(true);
    expect(h.state()).toBe(lastPublished);
    await h.playback.play(15000);
    expect(h.media.length).toBe(1);
  });

  test("natural end stops at the final frame without resetting the playhead", async () => {
    const h = harness();
    const start = h.playback.play(29000);
    h.media[0].ready();
    await start;
    h.media[0].advance(1000);
    h.elapsed(1000);
    await h.playback.tick();
    expect(h.state()).toMatchObject({ positionMs: 30000, playing: false });
    expect(h.media[0].paused).toBe(true);
  });
});
