<script lang="ts">
  import Icon from "./Icon.svelte";
  import { onDestroy, onMount } from "svelte";
  import type { Project } from "./api";
  import { time, videoDuration, videoPosition } from "./timing";
  import { PreviewPlayback } from "./preview-playback";
  let {
    project,
    urls,
    videoMs = $bindable(0),
  }: {
    project: Project;
    urls: Record<string, string>;
    videoMs?: number;
  } = $props();
  let playing = $state(false);
  let waiting = $state(false);
  let playbackError = $state("");
  let playbackNotice = $state("");
  let frame = 0;
  let loop = 0;
  const duration = $derived(
    videoDuration(project.master?.durationMs ?? 0, project.breaks),
  );
  const position = $derived(videoPosition(videoMs, project.breaks));
  const masterUrl = $derived(
    project.master ? urls[project.master.assetId] : "",
  );
  const playback = new PreviewPlayback(
    () => ({ durationMs: duration, breaks: project.breaks, masterUrl, urls }),
    (url) => new Audio(url),
    () => performance.now(),
    (state) => {
      videoMs = state.positionMs;
      playing = state.playing;
      waiting = state.waiting;
      playbackError = state.error;
    },
  );

  function stop() {
    loop++;
    cancelAnimationFrame(frame);
    playback.pause();
  }
  async function tick(generation: number) {
    if (!playing || generation !== loop) return;
    await playback.tick();
    if (playing && generation === loop)
      frame = requestAnimationFrame(() => tick(generation));
  }
  async function toggle() {
    if (playing) {
      stop();
      return;
    }
    if (document.hidden) return;
    playbackNotice = "";
    const generation = ++loop;
    await playback.play(videoMs >= duration ? 0 : videoMs);
    if (playing && generation === loop)
      frame = requestAnimationFrame(() => tick(generation));
  }
  async function seek(value: number) {
    const generation = ++loop;
    cancelAnimationFrame(frame);
    await playback.seek(value);
    if (playing && generation === loop)
      frame = requestAnimationFrame(() => tick(generation));
  }
  onMount(() => {
    const pauseWhenHidden = () => {
      if (document.hidden && playing) {
        stop();
        playbackNotice =
          "Preview paused while this window was hidden. Press Play to continue.";
      }
    };
    document.addEventListener("visibilitychange", pauseWhenHidden);
    return () =>
      document.removeEventListener("visibilitychange", pauseWhenHidden);
  });
  onDestroy(() => {
    loop++;
    cancelAnimationFrame(frame);
    playback.dispose();
  });
</script>

<footer class="transport">
  <div class="transport-top">
    <div class="transport-controls">
      <button
        class="play"
        onclick={toggle}
        disabled={!masterUrl || !duration}
        aria-label={playing ? "Pause preview" : "Play preview"}
        ><Icon name={playing ? "pause" : "play"} size={18} /></button
      >
      <div>
        <strong>{time(videoMs)} <span>/ {time(duration)}</span></strong><small
          >{position.breakId ? "Audio break" : "Song preview"} · {time(
            position.songMs,
          )} song time</small
        >
      </div>
    </div>
    <div class="timeline-description">
      <span class="dot amber"></span> Timed story preview
      <span class="subtle">720p / 24 fps target</span>
    </div>
    <span class="subtle">{project.sections.length} sections</span>
  </div>
  <label class="sr-only" for="playhead">Preview position</label>
  <input
    id="playhead"
    class="playhead"
    type="range"
    min="0"
    max={duration || 1}
    step="1"
    value={videoMs}
    aria-valuetext={`${time(videoMs)} of ${time(duration)} video time`}
    oninput={(e) => seek(Number(e.currentTarget.value))}
    disabled={!duration}
  />
  <div class="timeline" aria-label="Song sections">
    {#each project.sections as section (section.id)}
      <button
        style:flex={Math.max(1, section.endMs - section.startMs)}
        onclick={() =>
          seek(
            section.startMs +
              project.breaks
                .filter(
                  (b) =>
                    b.kind === "insertion" && b.songStartMs <= section.startMs,
                )
                .reduce((n, b) => n + b.durationMs, 0),
          )}
        title={`${section.name}: ${time(section.startMs)}–${time(section.endMs)}`}
        ><span>{section.name}</span><small>{time(section.startMs)}</small
        ></button
      >
    {:else}<div class="empty-track">
        Import your song and add story sections to build its timeline.
      </div>{/each}
  </div>
  {#if playbackError}<p role="alert" class="error">{playbackError}</p>{/if}
  {#if waiting}<p role="status" class="small-note">
      Waiting for audio. Preview time is paused.
    </p>{/if}
  {#if playbackNotice}<p role="status" class="small-note">
      {playbackNotice}
    </p>{/if}
</footer>
