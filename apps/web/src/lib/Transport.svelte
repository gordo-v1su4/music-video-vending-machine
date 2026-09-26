<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import type { Project } from "./api";
  import { time, videoDuration, videoPosition } from "./timing";
  import { PreviewClock } from "./preview-clock";
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
  let playbackError = $state("");
  let playbackNotice = $state("");
  let frame = 0;
  let masterAudio: HTMLAudioElement | undefined;
  let breakAudio: HTMLAudioElement | undefined;
  let lastSource = "";
  let activeBreak = "";
  const previewClock = new PreviewClock();
  const duration = $derived(
    videoDuration(project.master?.durationMs ?? 0, project.breaks),
  );
  const position = $derived(videoPosition(videoMs, project.breaks));
  const masterUrl = $derived(
    project.master ? urls[project.master.assetId] : "",
  );

  function stop() {
    // Capture time between the last painted frame and the actual pause.
    if (playing) videoMs = previewClock.pause(performance.now(), duration);
    playing = false;
    cancelAnimationFrame(frame);
    masterAudio?.pause();
    breakAudio?.pause();
  }
  async function synchronize() {
    if (!masterUrl) return;
    if (!masterAudio || lastSource !== masterUrl) {
      masterAudio?.pause();
      masterAudio = new Audio(masterUrl);
      lastSource = masterUrl;
    }
    const now = videoPosition(videoMs, project.breaks);
    const inserted =
      project.breaks.find((b) => b.id === now.breakId)?.kind === "insertion";
    if (Math.abs(masterAudio.currentTime - now.songMs / 1000) > 0.12)
      masterAudio.currentTime = now.songMs / 1000;
    masterAudio.muted = now.muted;
    if (inserted || !playing) masterAudio.pause();
    else if (masterAudio.paused) await masterAudio.play();
    // A visibility change may pause while play() is still pending.
    if (!playing) masterAudio.pause();
    const selected = project.breaks.find((b) => b.id === now.breakId);
    const breakUrl = selected?.assetId ? urls[selected.assetId] : undefined;
    if (activeBreak !== (breakUrl ?? "")) {
      breakAudio?.pause();
      breakAudio = breakUrl ? new Audio(breakUrl) : undefined;
      activeBreak = breakUrl ?? "";
    }
    if (breakAudio) {
      if (Math.abs(breakAudio.currentTime - now.breakMs / 1000) > 0.12)
        breakAudio.currentTime = now.breakMs / 1000;
      if (playing && breakAudio.paused && !breakAudio.ended)
        await breakAudio.play();
      if (!playing) breakAudio.pause();
    }
  }
  async function tick(timestamp: number) {
    if (!playing) return;
    videoMs = previewClock.position(timestamp, duration);
    try {
      await synchronize();
    } catch {
      playbackError = "Audio playback failed. Pause and try again.";
      stop();
      return;
    }
    if (videoMs >= duration) stop();
    else if (playing) frame = requestAnimationFrame(tick);
  }
  async function toggle() {
    if (playing) {
      stop();
      return;
    }
    if (document.hidden) return;
    playbackError = "";
    playbackNotice = "";
    if (videoMs >= duration) videoMs = 0;
    playing = true;
    previewClock.play(videoMs, performance.now());
    try {
      await synchronize();
      if (playing) frame = requestAnimationFrame(tick);
    } catch {
      playbackError = "Audio could not play. Check the imported master.";
      stop();
    }
  }
  function seek(value: number) {
    videoMs = Math.min(duration, Math.max(0, value));
    previewClock.seek(videoMs, performance.now());
    void synchronize().catch(() => {
      playbackError = "Could not seek the audio.";
      stop();
    });
  }
  onMount(() => {
    const pauseWhenHidden = () => {
      if (document.hidden && playing) {
        stop();
        playbackNotice =
          "Preview paused while this window was hidden. Press Play to continue.";
      }
    };
    // HTML audio can continue while rAF is suspended. Pause both media tracks
    // immediately rather than miss an insertion or mute boundary offscreen.
    document.addEventListener("visibilitychange", pauseWhenHidden);
    return () =>
      document.removeEventListener("visibilitychange", pauseWhenHidden);
  });
  onDestroy(stop);
</script>

<footer class="transport">
  <div class="transport-top">
    <div class="transport-controls">
      <button
        class="play"
        onclick={toggle}
        disabled={!masterUrl || !duration}
        aria-label={playing ? "Pause preview" : "Play preview"}
        >{playing ? "Ⅱ" : "▶"}</button
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
    step="41.6667"
    value={videoMs}
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
  {#if playbackNotice}<p role="status" class="small-note">
      {playbackNotice}
    </p>{/if}
</footer>
