import type { AudioBreak } from "./api";
import { PreviewClock } from "./preview-clock";
import { videoPosition } from "./timing";

export interface PreviewMedia {
  currentTime: number;
  readonly ended: boolean;
  play(): Promise<void>;
  pause(): void;
  addEventListener(type: string, listener: () => void): void;
  removeEventListener(type: string, listener: () => void): void;
}
export interface PlaybackState {
  positionMs: number;
  playing: boolean;
  waiting: boolean;
  error: string;
}
interface PlaybackInput {
  durationMs: number;
  breaks: AudioBreak[];
  masterUrl: string;
  urls: Record<string, string>;
}
interface MediaSession {
  media: PreviewMedia;
  videoStartMs: number;
  mediaStartMs: number;
  ended: boolean;
  cleanup: () => void;
}

/** Include every transition so a late painted frame cannot skip a whole break. */
function nextBoundary(positionMs: number, input: PlaybackInput) {
  let offset = 0;
  const boundaries = [input.durationMs];
  const insertions = input.breaks
    .filter((b) => b.kind === "insertion")
    .sort((a, b) => a.songStartMs - b.songStartMs);
  for (const item of insertions) {
    boundaries.push(
      item.songStartMs + offset,
      item.songStartMs + offset + item.durationMs,
    );
    offset += item.durationMs;
  }
  for (const item of input.breaks.filter((b) => b.kind === "cutout")) {
    for (const songMs of [
      item.songStartMs,
      item.songStartMs + item.durationMs,
    ]) {
      boundaries.push(
        songMs +
          insertions
            .filter((b) => b.songStartMs <= songMs)
            .reduce((sum, b) => sum + b.durationMs, 0),
      );
    }
  }
  return Math.min(...boundaries.filter((value) => value > positionMs));
}

/** Audible spans follow media time; only silence uses wall time. */
export class PreviewPlayback {
  private clock = new PreviewClock();
  private generation = 0;
  private session: MediaSession | null = null;
  private boundaryMs = 0;
  private pending = false;
  private disposed = false;
  private state: PlaybackState = {
    positionMs: 0,
    playing: false,
    waiting: false,
    error: "",
  };

  constructor(
    private input: () => PlaybackInput,
    private createMedia: (url: string) => PreviewMedia,
    private now: () => number,
    private publish: (state: PlaybackState) => void,
  ) {}

  private emit() {
    if (!this.disposed) this.publish({ ...this.state });
  }

  dispose() {
    // A replaced component must not write its old playhead into the new one.
    this.disposed = true;
    this.pause();
  }

  private sample() {
    if (!this.state.playing || this.pending) return this.state.positionMs;
    const session = this.session;
    const position =
      session && !session.ended
        ? session.videoStartMs +
          Math.max(0, session.media.currentTime * 1000 - session.mediaStartMs)
        : this.clock.position(this.now(), this.input().durationMs);
    return Math.min(this.boundaryMs, position);
  }

  private release() {
    if (!this.session) return;
    this.session.cleanup();
    this.session.media.pause();
    this.session = null;
  }

  pause() {
    this.state.positionMs = this.sample();
    this.generation++;
    this.release();
    this.clock.pause(this.now(), this.input().durationMs);
    this.clock.seek(this.state.positionMs, this.now());
    this.pending = false;
    this.state.playing = false;
    this.state.waiting = false;
    this.emit();
  }

  async play(positionMs: number) {
    if (this.disposed) return;
    this.pause();
    this.state.positionMs = Math.max(
      0,
      Math.min(positionMs, this.input().durationMs),
    );
    // The supplied seek/play target is authoritative until enter() establishes
    // its new segment. pause() must not sample the previous segment boundary.
    this.pending = true;
    this.state.playing = true;
    this.state.error = "";
    const generation = this.generation;
    await this.enter(generation);
  }

  async seek(positionMs: number) {
    const resume = this.state.playing;
    this.pause();
    this.state.positionMs = Math.max(
      0,
      Math.min(positionMs, this.input().durationMs),
    );
    if (resume) await this.play(this.state.positionMs);
    else this.emit();
  }

  private fail(generation: number) {
    if (generation !== this.generation) return;
    this.pause();
    this.state.error =
      "Audio playback failed. Check the imported media and try again.";
    this.emit();
  }

  private async enter(generation: number) {
    const input = this.input();
    if (this.state.positionMs >= input.durationMs) {
      this.pause();
      return;
    }
    const mapped = videoPosition(this.state.positionMs, input.breaks);
    const audioBreak = input.breaks.find((b) => b.id === mapped.breakId);
    const url = audioBreak
      ? audioBreak.assetId
        ? input.urls[audioBreak.assetId]
        : ""
      : input.masterUrl;
    if ((!audioBreak || audioBreak.assetId) && !url) {
      this.fail(generation);
      return;
    }
    this.boundaryMs = nextBoundary(this.state.positionMs, input);
    if (!url) {
      this.pending = false;
      this.state.waiting = false;
      this.clock.play(this.state.positionMs, this.now());
      this.emit();
      return;
    }

    // Each asynchronous play owns its media instance. A cancelled old promise
    // must never pause or restart a newer session using the same source URL.
    const media = this.createMedia(url);
    const session: MediaSession = {
      media,
      videoStartMs: this.state.positionMs,
      mediaStartMs: audioBreak ? mapped.breakMs : mapped.songMs,
      ended: false,
      cleanup: () => {},
    };
    const current = () =>
      generation === this.generation &&
      this.session === session &&
      this.state.playing;
    const waiting = () => {
      if (current()) {
        this.state.waiting = true;
        this.emit();
      }
    };
    const playing = () => {
      if (current() && !this.pending) {
        this.state.waiting = false;
        this.emit();
      }
    };
    const ended = () => {
      if (!current()) return;
      // A short dialogue/SFX file leaves silence for the rest of its break.
      this.state.positionMs = Math.min(
        this.boundaryMs,
        session.videoStartMs +
          Math.max(0, media.currentTime * 1000 - session.mediaStartMs),
      );
      session.ended = true;
      this.clock.play(this.state.positionMs, this.now());
      this.state.waiting = false;
      this.emit();
    };
    const error = () => {
      if (current()) this.fail(generation);
    };
    const events = { waiting, stalled: waiting, playing, ended, error };
    for (const [type, listener] of Object.entries(events))
      media.addEventListener(type, listener);
    session.cleanup = () => {
      for (const [type, listener] of Object.entries(events))
        media.removeEventListener(type, listener);
    };
    this.session = session;
    this.pending = true;
    this.state.waiting = true;
    this.emit();
    try {
      media.currentTime = session.mediaStartMs / 1000;
      await media.play();
      if (!current()) {
        media.pause();
        return;
      }
      this.pending = false;
      this.state.waiting = false;
      // No wall-clock time accrued during play(). Once audible, currentTime
      // is authoritative, including buffering and delayed playing events.
      this.emit();
    } catch {
      if (current()) this.fail(generation);
      else media.pause();
    }
  }

  async tick() {
    if (!this.state.playing || this.pending) return;
    this.state.positionMs = this.sample();
    if (this.state.positionMs >= this.boundaryMs) {
      this.pending = true;
      this.release();
      await this.enter(this.generation);
    } else this.emit();
  }
}
