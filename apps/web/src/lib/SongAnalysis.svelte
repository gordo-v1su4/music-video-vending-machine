<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';
  import { type AnalysisJob, type Asset, type SongAnalysis, type StudioApi, type TranscriptionJob } from './api';
  import { time } from './timing';
  import { sampledWaveform } from './waveform';

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
  let audio: HTMLAudioElement | undefined = $state();
  let stopAt = $state<number | null>(null);
  let playing = $state(false);
  let positionMs = $state(0);
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
  onMount(() => {
    const pauseForPreview = (event: Event) => { if ((event as CustomEvent).detail === 'preview') audio?.pause(); };
    window.addEventListener('studio-playback', pauseForPreview);
    return () => { window.removeEventListener('studio-playback', pauseForPreview); audio?.pause(); };
  });
  async function toggleAudio() {
    if (!audio) return;
    if (!audio.paused) { audio.pause(); return; }
    stopAt = null;
    try { await audio.play(); } catch { problem = 'Playback could not start. Try again.'; }
  }
  const stage = $derived(({ queued: 'Waiting for analysis', submitting: 'Sending audio', running: 'Analyzing song', completed: 'Analysis ready', failed: 'Analysis failed', reconciliation_required: 'Analysis needs recovery' } as Record<string, string>)[job?.status ?? ''] ?? 'Song analysis');
  const energyPath = $derived.by(() => {
    if (!result) return '';
    const { values, sampleRateHz, startMs } = result.energy;
    const stride = Math.max(1, Math.ceil(values.length / 500));
    const points: string[] = [];
    for (let i = 0; i < values.length; i += stride) {
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
  async function audition(startMs: number, endMs: number) {
    if (!audio) return;
    audio.currentTime = startMs / 1000;
    positionMs = startMs;
    stopAt = endMs / 1000;
    try { await audio.play(); }
    catch { problem = 'Playback could not start. Use the audio controls to try again.'; }
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
    <svg viewBox="0 0 1000 100" preserveAspectRatio="none" role="img" aria-label="Song waveform with detected sections shaded by duration" class="energy-curve">
      {#each result.sections as section, i (i)}
        <rect x={section.startMs / result.durationMs * 1000} y="0" width={Math.max(0,(section.endMs - section.startMs) / result.durationMs * 1000 - 1)} height="100" fill={section.endMs-section.startMs < 16000 ? '#3b82f6' : section.endMs-section.startMs < 28000 ? '#6366f1' : '#9333ea'} fill-opacity="0.12" />
        {#if section.endMs-section.startMs > 7000}<text x={section.startMs / result.durationMs * 1000 + 3} y="17" fill="#d4d4d8" font-size="9">{section.originalLabel}</text>{/if}
      {/each}
      {#if waveform}<polygon points={waveform} fill="#a5afc1" fill-opacity="0.52" />{:else}<polyline points={energyPath} fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke" />{/if}
      {#each result.onsetsMs as onset,i(i)}<line x1={onset / result.durationMs * 1000} x2={onset / result.durationMs * 1000} y1="88" y2="93" stroke="#93a5bf" stroke-opacity="0.3" stroke-width="0.5"/>{/each}
      {#each lyrics as chunk,i(i)}<rect x={chunk.startMs / result.durationMs * 1000} width={Math.max(1,(chunk.endMs-chunk.startMs)/result.durationMs*1000)} y="4" height="6" fill="#c4b5fd" fill-opacity="0.7" />{/each}
      {#each result.beatsMs as beat, i (i)}<line x1={beat / result.durationMs * 1000} x2={beat / result.durationMs * 1000} y1="94" y2="100" stroke="currentColor" stroke-width="0.5" />{/each}
      <line x1={positionMs/result.durationMs*1000} x2={positionMs/result.durationMs*1000} y1="0" y2="100" stroke="#e4e4e7" stroke-width="1" vector-effect="non-scaling-stroke"/>
    </svg>
    <div class="time-axis"><span>0:00</span><span>{waveform ? 'Waveform' : 'Measured energy · loading waveform'} · onsets · beats{lyrics.length ? ' · lyric phrases' : ''}</span><span>{time(result.durationMs)}</span></div>
    {#if waveformProblem}<p class="small-note">{waveformProblem}</p>{/if}
    <div class="map-legend" aria-label="Section duration color legend"><span><i class="short"></i>Under 16s</span><span><i class="medium"></i>16–28s</span><span><i class="long"></i>28s and longer</span>{#if lyrics.length}<span><i class="lyrics"></i>Lyric phrase markers</span>{/if}</div>
    {#if source}
      <audio bind:this={audio} src={source} preload="metadata"
        onplay={() => { playing = true; window.dispatchEvent(new CustomEvent('studio-playback', { detail: 'audition' })); }}
        onpause={() => { playing = false; }} onended={() => { playing = false; stopAt = null; }}
        ontimeupdate={() => { if (audio) { positionMs = audio.currentTime * 1000; if (stopAt !== null && audio.currentTime >= stopAt) { audio.pause(); stopAt = null; } } }}></audio>
      <div class="audition-controls">
        <button class="play" onclick={toggleAudio} aria-label={playing ? 'Pause section audio' : 'Play section audio'}><Icon name={playing ? 'pause' : 'play'} size={16} /></button>
        <span>{time(positionMs)} / {time(result.durationMs)}</span>
        <strong role="status">{playing ? 'Playing' : 'Paused'}{currentCue >= 0 ? ` · ${result.sections[currentCue].originalLabel} · section ${currentCue + 1} of ${result.sections.length}` : ''}</strong>
      </div>
      <label class="sr-only" for="section-seek">Section audio position</label>
      <input id="section-seek" class="playhead" type="range" min="0" max={result.durationMs} step="1" value={positionMs} aria-valuetext={`${time(positionMs)} of ${time(result.durationMs)}`} oninput={(e) => { if (audio) { stopAt = null; positionMs = Number(e.currentTarget.value); audio.currentTime = positionMs / 1000; } }} />
    {/if}
    <div class="detected-sections" aria-label="Detected musical sections">
      {#each result.sections as section, i (`${section.startMs}:${section.endMs}`)}
        <button class="section-cue" class:current={currentCue === i} aria-current={currentCue === i ? 'true' : undefined} disabled={!source} onclick={() => audition(section.startMs, section.endMs)} aria-label={`Listen to ${section.originalLabel}, ${time(section.startMs)} to ${time(section.endMs)}`}>
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
  .energy-curve { display: block; width: 100%; height: 110px; color: #93c5fd; background: var(--surface); }
  .map-legend { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:20px; color:var(--muted); font-size:12px; }
  .map-legend span { display:flex; gap:6px; align-items:center; } .map-legend i { width:14px; height:10px; display:inline-block; }
  .short { background:rgb(59 130 246 / 20%); } .medium { background:rgb(99 102 241 / 20%); } .long { background:rgb(147 51 234 / 20%); } .lyrics { background:#a69bb8; }
  .time-axis { margin: 8px 0 20px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .audition-controls { display:flex; align-items:center; gap:12px; flex-wrap:wrap; font-size:13px; font-variant-numeric:tabular-nums; }
  .audition-controls strong { color:var(--mint); text-transform:capitalize; }
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
