<script lang="ts">
  // The pilot cut as a silent picture that follows the one studio playhead: the Transport plays the song,
  // this video tracks song time while the playhead is inside the cut, and shows the frame when scrubbing.
  import { studioClock } from "./studio-clock.svelte";
  import { time } from "./timing";

  let {
    url,
    songStartMs,
    durationMs,
    compact = false,
  }: { url: string; songStartMs: number; durationMs: number; compact?: boolean } = $props();

  let video = $state<HTMLVideoElement>();
  const local = $derived(studioClock.songMs - songStartMs);
  const inRange = $derived(local >= 0 && local < durationMs);

  $effect(() => {
    const v = video;
    if (!v) return;
    const t = Math.max(0, Math.min(durationMs, local)) / 1000;
    // Hold the picture while the song buffers so it never runs ahead of the audio.
    if (studioClock.playing && !studioClock.waiting && inRange) {
      if (Math.abs(v.currentTime - t) > 0.15) v.currentTime = t;
      if (v.paused) v.play().catch(() => {});
      // Song time updates every frame while playing; if it stalls (hidden window, dropped frames), stop the
      // picture rather than let it run ahead. The next update re-runs this and resumes.
      const stall = setTimeout(() => v.pause(), 400);
      return () => clearTimeout(stall);
    } else {
      if (!v.paused) v.pause();
      if (Math.abs(v.currentTime - t) > 0.04) v.currentTime = t;
    }
  });
</script>

<div class="cut-video" class:compact class:outside={!inRange}>
  <video bind:this={video} src={url} muted playsinline preload="auto"></video>
  {#if !inRange}
    <div class="outside-note">
      <span>The pilot covers {time(songStartMs)}–{time(songStartMs + durationMs)} of the song</span>
      <button class="quiet" disabled={!studioClock.available} onclick={() => studioClock.playFrom(songStartMs)}
        >Play from {time(songStartMs)}</button
      >
    </div>
  {/if}
</div>

<style>
  .cut-video {
    position: relative;
    border-radius: 10px;
    overflow: hidden;
    background: #000;
    aspect-ratio: 16 / 9;
  }
  video {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .outside video {
    opacity: 0.35;
  }
  .outside-note {
    position: absolute;
    inset: auto 0 0 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 12px 14px;
    background: linear-gradient(transparent, rgb(0 0 0 / 80%));
    font-size: 12px;
    color: #e4e4e7;
    font-variant-numeric: tabular-nums;
  }
  .compact .outside-note {
    padding: 8px 10px;
    font-size: 11px;
  }
</style>
