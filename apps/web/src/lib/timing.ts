import type { AudioBreak } from "./api";
export const time = (ms: number) =>
  `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
export function videoDuration(
  songDurationMs: number,
  breaks: AudioBreak[],
): number {
  return (
    songDurationMs +
    breaks
      .filter((b) => b.kind === "insertion")
      .reduce((sum, b) => sum + b.durationMs, 0)
  );
}
// Video time at a song position: song time plus every insertion break that starts at or before it.
export function songToVideo(songMs: number, breaks: AudioBreak[]): number {
  return (
    songMs +
    breaks
      .filter((b) => b.kind === "insertion" && b.songStartMs <= songMs)
      .reduce((sum, b) => sum + b.durationMs, 0)
  );
}
export function videoPosition(videoMs: number, breaks: AudioBreak[]) {
  let offset = 0;
  for (const item of [...breaks]
    .filter((b) => b.kind === "insertion")
    .sort((a, b) => a.songStartMs - b.songStartMs)) {
    const start = item.songStartMs + offset;
    if (videoMs < start) break;
    if (videoMs < start + item.durationMs)
      return {
        songMs: item.songStartMs,
        muted: true,
        breakId: item.id,
        breakMs: videoMs - start,
      };
    offset += item.durationMs;
  }
  const songMs = Math.max(0, videoMs - offset);
  const cutout = breaks.find(
    (b) =>
      b.kind === "cutout" &&
      songMs >= b.songStartMs &&
      songMs < b.songStartMs + b.durationMs,
  );
  return {
    songMs,
    muted: !!cutout,
    breakId: cutout?.id ?? null,
    breakMs: cutout ? songMs - cutout.songStartMs : 0,
  };
}
