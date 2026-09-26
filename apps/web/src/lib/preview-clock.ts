/** Monotonic timeline clock, independent of animation-frame frequency. */
export class PreviewClock {
  private anchorMs = 0;
  private startedAt: number | null = null;

  play(positionMs: number, now: number) {
    this.anchorMs = positionMs;
    this.startedAt = now;
  }

  position(now: number, durationMs: number) {
    const elapsed =
      this.startedAt === null ? 0 : Math.max(0, now - this.startedAt);
    return Math.min(durationMs, Math.max(0, this.anchorMs + elapsed));
  }

  pause(now: number, durationMs: number) {
    this.anchorMs = this.position(now, durationMs);
    this.startedAt = null;
    return this.anchorMs;
  }

  seek(positionMs: number, now: number) {
    this.anchorMs = positionMs;
    if (this.startedAt !== null) this.startedAt = now;
  }
}
