<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';
  import { type AnalysisJob, type Asset, type SongAnalysis, type StudioApi, type TranscriptionJob } from './api';
  import { time } from './timing';
  import { sampledWaveform } from './waveform';
  import { studioClock } from './studio-clock.svelte';

  let { client, projectId, asset, source, lyrics = [], available, locked, hasSections, onUse, onError }: {
    client: StudioApi; projectId: string; asset: Asset; source?: string;
    available: boolean; locked: boolean; hasSections: boolean;
    lyrics?: NonNullable<TranscriptionJob['result']>['chunks'];
    onUse: (result: SongAnalysis) => void; onError: (error: unknown) => void;
  } = $props();
  let job = $state<AnalysisJob | null>(null);
  let problem = $state('');
  let loading = $state(true);
  let starting = $state(false);
  let refresh = $state(0);
  // The studio Transport is the only player; this map shows its playhead and seeks through it.
  const playing = $derived(studioClock.playing);
  const positionMs = $derived(studioClock.songMs);
  let waveform = $state('');
  let waveformProblem = $state('');
  $effect(() => {
    const url = source, ready = job?.status === 'completed', durationMs = asset.durationMs ?? 0, sizeBytes = asset.sizeBytes;
    let disposed = false;
    const abort = new AbortController();
    let context: AudioContext | undefined;
    async function decode() {
      waveform = ''; waveformProblem = '';
      if (!url || !ready) return;
      // Bound decoded memory; measured energy remains available for larger media.
      if (durationMs <= 0 || durationMs > 600_000 || sizeBytes > 32 * 1024 * 1024) {
        waveformProblem = 'Showing measured energy. Waveform sampling is limited to files up to 10 minutes and 32 MiB.';
        return;
      }
      try {
        const response = await fetch(url, { signal: abort.signal });
        if (!response.ok) throw new Error('Waveform source unavailable');
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 32 * 1024 * 1024) throw new Error('Waveform source too large');
        if (disposed) return;
        context = new AudioContext({ sampleRate: 8000 });
        const buffer = await context.decodeAudioData(bytes);
        if (disposed) return;
        const channels = Array.from({ length: Math.min(2, buffer.numberOfChannels) }, (_, i) => buffer.getChannelData(i));
        waveform = sampledWaveform(channels);
      } catch { if (!disposed) waveformProblem = 'Waveform could not load. The measured energy and section timing are still available.'; }
      finally { if (context?.state !== 'closed') await context?.close(); }
    }
    void decode();
    return () => { disposed = true; abort.abort(); };
  });
  const result = $derived(job?.status === 'completed' && job.sha256 === asset.sha256 ? job.result : null);
  const currentCue = $derived(result?.sections.findIndex(s => positionMs >= s.startMs && positionMs < s.endMs) ?? -1);
  const stage = $derived(({ queued: 'Waiting for analysis', submitting: 'Sending audio', running: 'Analyzing song', completed: 'Analysis ready', failed: 'Analysis failed', reconciliation_required: 'Analysis needs recovery' } as Record<string, string>)[job?.status ?? ''] ?? 'Song analysis');
  const uid = $props.id();

  // Zoomable song map: a window [viewStart, viewStart + span] over the song, in milliseconds.
  const MIN_SPAN_MS = 4000;
  let viewStart = $state(0);
  let viewSpan = $state(0); // 0 = whole song
  let mapEl = $state<SVGSVGElement>();
  let drag: { x: number; start: number; moved: boolean } | null = null;
  const durationMs = $derived(result?.durationMs ?? 1);
  const span = $derived(viewSpan ? Math.min(viewSpan, durationMs) : durationMs);
  const zoomed = $derived(span < durationMs);
  const viewBox = $derived(`${(viewStart / durationMs) * 1000} 0 ${(span / durationMs) * 1000} 100`);
  function setView(start: number, nextSpan: number) {
    const width = Math.max(MIN_SPAN_MS, Math.min(durationMs, nextSpan));
    viewSpan = width >= durationMs ? 0 : width;
    viewStart = Math.max(0, Math.min(durationMs - width, start));
  }
  function zoomBy(factor: number, anchorMs = viewStart + span / 2) {
    const next = Math.max(MIN_SPAN_MS, Math.min(durationMs, span * factor));
    setView(anchorMs - ((anchorMs - viewStart) * next) / span, next);
  }
  function msAt(clientX: number) {
    const box = mapEl!.getBoundingClientRect();
    return viewStart + ((clientX - box.left) / box.width) * span;
  }
  function seek(ms: number) {
    studioClock.seek(Math.min(durationMs, ms));
  }
  function onMapWheel(e: WheelEvent) {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      zoomBy(Math.exp(e.deltaY * 0.002), msAt(e.clientX));
    } else if (zoomed && (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY))) {
      e.preventDefault();
      const px = e.shiftKey ? e.deltaY : e.deltaX;
      setView(viewStart + (px / mapEl!.getBoundingClientRect().width) * span, span);
    }
  }
  function onMapDown(e: PointerEvent) {
    drag = { x: e.clientX, start: viewStart, moved: false };
    mapEl?.setPointerCapture(e.pointerId);
  }
  function onMapMove(e: PointerEvent) {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    if (Math.abs(dx) > 4) drag.moved = true;
    if (drag.moved && zoomed) setView(drag.start - (dx / mapEl!.getBoundingClientRect().width) * span, span);
  }
  function onMapUp(e: PointerEvent) {
    if (drag && !drag.moved) seek(msAt(e.clientX));
    drag = null;
  }
  function onMapKey(e: KeyboardEvent) {
    const step = span / 10;
    const keys: Record<string, () => void> = {
      "+": () => zoomBy(0.5, positionMs),
      "=": () => zoomBy(0.5, positionMs),
      "-": () => zoomBy(2, positionMs),
      "0": () => setView(0, durationMs),
      ArrowLeft: () => seek(positionMs - step),
      ArrowRight: () => seek(positionMs + step),
    };
    const run = keys[e.key];
    if (run) {
      e.preventDefault();
      run();
    }
  }
  // While playing, the zoomed view scrolls with the Transport's playhead (updated every frame), holding it a
  // third of the way in; dragging the map pauses the follow.
  $effect(() => {
    if (playing && zoomed && !drag) setView(positionMs - span / 3, span);
  });
  const visibleSections = $derived(
    (result?.sections ?? [])
      .map((section) => ({
        section,
        left: ((section.startMs - viewStart) / span) * 100,
        width: ((section.endMs - section.startMs) / span) * 100,
      }))
      .filter((v) => v.left < 100 && v.left + v.width > 0 && v.width > 4),
  );
  // The energy curve leads: at whole-song scale it shows builds and drops; the waveform is faint texture behind it.
  const energyArea = $derived.by(() => {
    const points = energyPath.split(' ').filter(Boolean);
    if (!points.length) return '';
    return `${points[0].split(',')[0]},90 ${energyPath} ${points.at(-1)!.split(',')[0]},90`;
  });
  const energyPath = $derived.by(() => {
    if (!result) return '';
    const { values, sampleRateHz, startMs } = result.energy;
    const first = Math.max(0, Math.floor(((viewStart - startMs) * sampleRateHz) / 1000) - 1);
    const last = Math.min(values.length, Math.ceil(((viewStart + span - startMs) * sampleRateHz) / 1000) + 2);
    const stride = Math.max(1, Math.ceil((last - first) / 500));
    const points: string[] = [];
    for (let i = first; i < last; i += stride) {
      const x = (startMs + i * 1000 / sampleRateHz) / result.durationMs * 1000;
      if (x > 1000) break;
      let peak = 0;
      for (let j = i; j < Math.min(values.length, i + stride); j++) peak = Math.max(peak, values[j]);
      points.push(`${x.toFixed(2)},${(90 - Math.min(1, peak) * 80).toFixed(2)}`);
    }
    return points.join(' ');
  });

  $effect(() => {
    const currentClient = client;
    const id = projectId;
    const selected = asset;
    const enabled = available;
    void refresh;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await currentClient.analysis(id, selected.id);
        if (disposed) return;
        if (next && (next.assetId !== selected.id || next.sha256 !== selected.sha256)) throw new Error('Analysis does not belong to this audio file.');
        job = next;
        loading = false;
        problem = '';
        if (next && ['queued', 'submitting', 'running'].includes(next.status)) timer = setTimeout(poll, 3000);
      } catch (error) {
        if (disposed) return;
        loading = false;
        problem = error instanceof Error ? error.message : 'Analysis progress is unavailable.';
        onError(error);
        timer = setTimeout(poll, 5000);
      }
    }
    if (enabled) void poll();
    return () => { disposed = true; clearTimeout(timer); };
  });

  async function start() {
    if (starting || !available) return;
    starting = true;
    problem = '';
    try { await client.analysis(projectId, asset.id, true); refresh++; }
    catch (error) { problem = error instanceof Error ? error.message : 'Could not start analysis.'; onError(error); }
    finally { starting = false; }
  }
  function audition(startMs: number) {
    studioClock.playFrom(startMs);
  }
</script>

<section class="song-analysis" aria-labelledby="analysis-heading">
  <div class="analysis-heading"><h2 id="analysis-heading">Song analysis</h2><span class="subtle" role="status">{!available ? 'Connection paused' : loading ? 'Loading analysis…' : stage}</span></div>
  <p class="source-name">{asset.name}</p>
  {#if problem}<p class="analysis-error" role="alert">{problem}</p>{/if}
  {#if !loading && !job}
    <p>Find beats, energy changes, and musical sections in this recording.</p>
    <button class="primary" disabled={!available || starting} onclick={start}>{starting ? 'Starting…' : 'Analyze song'}</button>
  {:else if job && !result}
    <p>{job.message ?? (job.status === 'queued' ? 'Your audio is saved. Analysis will begin when the worker is ready.' : job.status === 'running' || job.status === 'submitting' ? `Current stage: ${job.stage.replaceAll('_', ' ')}. You can leave and return; this job is saved.` : 'The analysis did not produce usable sections.')}</p>
  {/if}
  {#if result}
    <p class="analysis-facts"><strong>{result.bpm.toFixed(2)} BPM measured</strong><span>{result.beatsMs.length} beats</span><span>{result.sections.length} musical sections</span><span>{time(result.durationMs)}</span></p>
    <div class="map-tools">
      <span class="map-hint">{zoomed ? `Showing ${time(viewStart)}–${time(viewStart + span)}` : 'Whole song'} · Ctrl + scroll to zoom · drag to move · click to jump</span>
      <div class="map-buttons">
        <button class="quiet" onclick={() => zoomBy(2)} disabled={!zoomed} aria-label="Zoom out">−</button>
        <button class="quiet" onclick={() => zoomBy(0.5, positionMs > 0 ? positionMs : undefined)} disabled={span <= MIN_SPAN_MS} aria-label="Zoom in">+</button>
        <button class="quiet" onclick={() => setView(0, durationMs)} disabled={!zoomed}>Fit song</button>
      </div>
    </div>
    <div class="map">
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <svg bind:this={mapEl} {viewBox} preserveAspectRatio="none" role="img" tabindex="0"
      aria-label="Song energy curve and waveform with detected sections shaded by duration. Plus and minus zoom; arrow keys move the playhead."
      class="energy-curve" class:zoomed onwheel={onMapWheel} onpointerdown={onMapDown} onpointermove={onMapMove} onpointerup={onMapUp} onpointercancel={() => (drag = null)} onkeydown={onMapKey}>
      {#each result.sections as section, i (i)}
        <!-- Sections tile edge to edge; boundaries are a 1px divider that stays thin at any zoom. -->
        <rect x={section.startMs / result.durationMs * 1000} y="0" width={Math.max(0, (section.endMs - section.startMs) / result.durationMs * 1000)} height="100" fill={section.endMs-section.startMs < 16000 ? '#3b82f6' : section.endMs-section.startMs < 28000 ? '#6366f1' : '#9333ea'} fill-opacity="0.12" />
        {#if i > 0}<line x1={section.startMs / result.durationMs * 1000} x2={section.startMs / result.durationMs * 1000} y1="0" y2="100" stroke="#101012" stroke-width="1" vector-effect="non-scaling-stroke" />{/if}
      {/each}
      <defs>
        <linearGradient id="energy-line-{uid}" gradientUnits="userSpaceOnUse" x1="0" y1="90" x2="0" y2="10">
          <stop offset="0" stop-color="#6366f1" /><stop offset="0.55" stop-color="#a78bfa" /><stop offset="1" stop-color="#f0abfc" />
        </linearGradient>
        <linearGradient id="energy-fill-{uid}" gradientUnits="userSpaceOnUse" x1="0" y1="90" x2="0" y2="10">
          <stop offset="0" stop-color="#6366f1" stop-opacity="0.02" /><stop offset="0.55" stop-color="#a78bfa" stop-opacity="0.16" /><stop offset="1" stop-color="#f0abfc" stop-opacity="0.34" />
        </linearGradient>
      </defs>
      {#if waveform}<polygon points={waveform} fill="#a1a1aa" fill-opacity="0.08" />{/if}
      <polygon points={energyArea} fill="url(#energy-fill-{uid})" />
      <polyline points={energyPath} fill="none" stroke="url(#energy-line-{uid})" stroke-width="1" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
      {#each result.onsetsMs as onset,i(i)}<line x1={onset / result.durationMs * 1000} x2={onset / result.durationMs * 1000} y1="88" y2="93" stroke="#a1a1aa" stroke-opacity={zoomed ? 0.6 : 0.3} stroke-width="1" vector-effect="non-scaling-stroke"/>{/each}
      {#each lyrics as chunk,i(i)}<rect x={chunk.startMs / result.durationMs * 1000} width={Math.max(1,(chunk.endMs-chunk.startMs)/result.durationMs*1000)} y="4" height="6" fill="#c4b5fd" fill-opacity="0.7" />{/each}
      {#each result.beatsMs as beat, i (i)}<line x1={beat / result.durationMs * 1000} x2={beat / result.durationMs * 1000} y1="94" y2="100" stroke="#d4d4d8" stroke-opacity="0.55" stroke-width="1" vector-effect="non-scaling-stroke" />{/each}
      <line x1={positionMs/result.durationMs*1000} x2={positionMs/result.durationMs*1000} y1="0" y2="100" stroke="#e4e4e7" stroke-width="1" vector-effect="non-scaling-stroke"/>
    </svg>
    <div class="map-labels" aria-hidden="true">
      {#each visibleSections as v (v.section.startMs)}<span style="left: {Math.max(0, v.left)}%">{v.section.originalLabel}</span>{/each}
    </div>
    </div>
    <div class="time-axis"><span>{time(viewStart)}</span><span>Energy{waveform ? ' · waveform' : ''} · onsets · beats{lyrics.length ? ' · lyric phrases' : ''}</span><span>{time(viewStart + span)}</span></div>
    {#if waveformProblem}<p class="small-note">{waveformProblem}</p>{/if}
    <div class="map-legend" aria-label="Section duration color legend"><span><i class="short"></i>Under 16s</span><span><i class="medium"></i>16–28s</span><span><i class="long"></i>28s and longer</span>{#if lyrics.length}<span><i class="lyrics"></i>Lyric phrase markers</span>{/if}</div>
    <div class="detected-sections" aria-label="Detected musical sections">
      {#each result.sections as section, i (`${section.startMs}:${section.endMs}`)}
        <button class="section-cue" class:current={currentCue === i} aria-current={currentCue === i ? 'true' : undefined} disabled={!studioClock.available} onclick={() => audition(section.startMs)} aria-label={`Play from ${section.originalLabel}, ${time(section.startMs)} to ${time(section.endMs)}`}>
          <span class="cue-number">{i + 1}</span><strong>{section.originalLabel}</strong><span>{time(section.startMs)}–{time(section.endMs)}</span>
        </button>
      {/each}
    </div>
    <details class="analysis-notes"><summary>How to read these suggestions</summary>
      <p>These are measured musical parts, not story decisions. Listen and adjust their names and boundaries. Tempo is an estimate; it does not override a known locked tempo.</p>
      {#each result.warnings as warning, i (i)}<p>{warning}</p>{/each}
      <p>Structure model: {result.method}. Native beat confidence: {result.nativeConfidence.toFixed(2)} (not a percentage).</p>
    </details>
    <button class="primary" disabled={!available || locked || !result.sections.length} onclick={() => { if (result) onUse(result); }}>{hasSections ? 'Replace draft with detected sections' : 'Use as editable story sections'}</button>
    {#if locked}<p class="small-note">Save your current edits first. Sections cannot be replaced after shots or edit revisions exist.</p>{:else}<p class="small-note">Creates an editable draft below. Save it when the boundaries look right.</p>{/if}
  {/if}
</section>

<style>
  .song-analysis { margin: 28px 0; padding: 24px 0; border-block: 1px solid var(--line); min-width: 0; }
  .analysis-heading, .analysis-facts, .time-axis { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  h2 { margin: 0; }
  p { line-height: 1.6; }
  .source-name { overflow-wrap: anywhere; color: var(--muted); margin: 8px 0 20px; }
  .analysis-facts { justify-content: flex-start; column-gap: 22px; font-variant-numeric: tabular-nums; }
  .map-tools { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
  .map-hint { font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .map-buttons { display: flex; gap: 6px; }
  .map-buttons button { min-width: 34px; }
  .map { position: relative; }
  .energy-curve { display: block; width: 100%; height: 130px; background: var(--surface); cursor: crosshair; touch-action: pan-y; }
  .energy-curve.zoomed { cursor: grab; }
  .energy-curve.zoomed:active { cursor: grabbing; }
  .energy-curve:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .map-labels { position: absolute; inset: 14px 0 auto 0; pointer-events: none; }
  .map-labels span { position: absolute; padding-left: 4px; font-size: 11px; color: #d4d4d8; white-space: nowrap; text-transform: capitalize; }
  .map-legend { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:20px; color:var(--muted); font-size:12px; }
  .map-legend span { display:flex; gap:6px; align-items:center; } .map-legend i { width:14px; height:10px; display:inline-block; }
  .short { background:rgb(59 130 246 / 20%); } .medium { background:rgb(99 102 241 / 20%); } .long { background:rgb(147 51 234 / 20%); } .lyrics { background:#a69bb8; }
  .time-axis { margin: 8px 0 20px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .section-cue.current { background:rgb(129 140 248 / 16%); }
  .detected-sections { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1px 18px; margin-block: 16px 24px; }
  .section-cue { display: flex; align-items: center; gap: 12px; text-align: left; padding: 12px 8px; border-bottom: 1px solid var(--line); min-width: 0; font-variant-numeric: tabular-nums; }
  .section-cue:hover:not(:disabled) { background: var(--panel); }
  .section-cue strong { flex: 1; text-transform: capitalize; overflow-wrap: anywhere; }
  .section-cue > span:last-child { white-space: nowrap; color: var(--muted); }
  .cue-number { color: var(--muted); min-width: 20px; }
  .analysis-notes { margin-block: 20px; }
  summary { cursor: pointer; padding-block: 8px; }
  summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
  .analysis-error { color: var(--amber); }
  @media (max-width: 520px) { .detected-sections { grid-template-columns: 1fr; } }
</style>
