<script lang="ts">
  import type { AnalysisJob, Asset, StudioApi, TranscriptionJob } from './api';
  let { client, projectId, assets, available, upload, onError }: {
    client: StudioApi; projectId: string; assets: Asset[]; available: boolean;
    upload: { name: string; index: number; total: number; phase: string; failed: boolean } | null;
    onError: (error: unknown) => void;
  } = $props();
  let jobs = $state<Record<string, AnalysisJob | null>>({});
  let transcripts = $state<Record<string, TranscriptionJob | null>>({});
  let problem = $state('');
  let loading = $state(true);
  const audio = $derived(assets.filter(a => a.mediaType.startsWith('audio/')));
  const active = $derived([...Object.values(jobs), ...Object.values(transcripts)].some(j => j && ['queued','submitting','running'].includes(j.status)));
  const labels: Record<string,string> = { queued:'Queued for analysis', submitting:'Sending to Essentia', running:'Analyzing beats, energy and sections', completed:'Analysis ready', failed:'Analysis failed', reconciliation_required:'Analysis needs recovery' };
  $effect(() => {
    const api = client, id = projectId, sources = audio, enabled = available;
    let disposed = false, timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const entries = await Promise.all(sources.map(async asset => {
          const [job, transcript] = await Promise.all([api.analysis(id,asset.id), api.transcription(id,asset.id)]);
          if (job && (job.assetId !== asset.id || job.sha256 !== asset.sha256)) throw new Error('Analysis source does not match this file.');
          if (transcript && (transcript.assetId !== asset.id || transcript.sha256 !== asset.sha256)) throw new Error('Transcript source does not match this file.');
          return [asset.id,job,transcript] as const;
        }));
        if (disposed) return;
        jobs = Object.fromEntries(entries.map(([id,job]) => [id,job]));
        transcripts = Object.fromEntries(entries.map(([id,,transcript]) => [id,transcript]));
        problem = ''; loading = false;
        timer = setTimeout(poll,3000);
      } catch (error) {
        if (disposed) return;
        loading = false; problem = 'Cannot refresh processing status. Reconnecting…'; onError(error);
        timer = setTimeout(poll,5000);
      }
    }
    if (enabled) void poll();
    return () => { disposed = true; clearTimeout(timer); };
  });
</script>

<section class="processing-stack" aria-labelledby="processing-title">
  <div class="stack-heading"><h2 id="processing-title">Processing</h2><span class="subtle">{!available ? 'Connection paused' : upload && !upload.failed || active ? 'In progress' : loading ? 'Checking…' : 'Up to date'}</span></div>
  <p class="small-note">Each file has its own analysis and transcription results.</p>
  {#if upload}
    <div class="upload-status" role="status" aria-live="polite">
      <strong>{upload.failed ? 'Upload needs attention' : upload.phase} · file {upload.index} of {upload.total}</strong>
      <span>{upload.name}</span>
      {#if !upload.failed}<progress aria-label={`${upload.phase}: ${upload.name}`}></progress>{/if}
    </div>
  {/if}
  {#if problem}<p role="status">{problem}</p>{/if}
  {#each audio as asset (asset.id)}
    {@const job = jobs[asset.id]}
    {@const transcript = transcripts[asset.id]}
    <div class="file-process">
      <strong class="file-name">{asset.name}</strong>
      <ol aria-label={`Processing steps for ${asset.name}`}>
        <li class="done"><span class="step-mark" aria-hidden="true"></span><span>Audio uploaded and saved</span></li>
        <li class:done={job?.status === 'completed'} class:working={job && ['queued','submitting','running'].includes(job.status)}>
          <span class="step-mark" aria-hidden="true"></span><span>{!available ? 'Status paused — reconnect to refresh' : loading ? 'Checking analysis…' : job ? labels[job.status] ?? job.status : 'Analysis not started'}</span>
        </li>
        {#if job?.status === 'completed' && job.result}<li class="done"><span class="step-mark" aria-hidden="true"></span><span>{job.result.sections.length} sections · {job.result.beatsMs.length} beats ready to review</span></li>{/if}
        {#if transcript}<li class:done={transcript.status === 'completed' && (transcript.result?.wordCount ?? 0) > 0} class:working={['queued','running'].includes(transcript.status)}><span class="step-mark" aria-hidden="true"></span><span>{transcript.status === 'queued' ? 'Lyrics queued for Deepgram' : transcript.status === 'running' ? 'Extracting lyrics & story context' : transcript.status === 'completed' ? transcript.result?.wordCount ? `${transcript.result.wordCount} words ready to review` : 'No words recovered from this file' : 'Lyrics extraction needs attention'}</span></li>{/if}
      </ol>
      {#if job && ['queued','submitting','running'].includes(job.status)}<progress aria-label={`Analyzing ${asset.name}`}></progress><p class="small-note">{job.stage.replaceAll('_',' ')} · Progress is saved on the server.</p>{/if}
      {#if job?.message}<p class="small-note">{job.message}</p>{/if}
      {#if transcript && ['queued','running'].includes(transcript.status)}<progress aria-label={`Transcribing ${asset.name}`}></progress>{/if}
    </div>
  {:else}<p class="small-note">Import audio to see its upload and analysis stages here.</p>{/each}
</section>

<style>
  .processing-stack { margin-bottom:24px; border-block:1px solid var(--line); padding-block:18px; }
  .stack-heading { display:flex; justify-content:space-between; align-items:baseline; gap:12px; } h2 { margin:0; font-size:16px; }
  .file-process { margin-top:18px; } .file-name, .upload-status span { display:block; overflow-wrap:anywhere; font-size:13px; }
  ol { list-style:none; margin:12px 0; padding:0; display:grid; gap:10px; } li { display:flex; gap:10px; align-items:center; font-size:13px; color:var(--muted); }
  .step-mark { width:12px; height:12px; border:1px solid currentColor; flex-shrink:0; } .done .step-mark { background:var(--mint); border-color:var(--mint); box-shadow:inset 0 0 0 3px var(--panel); }
  .working { color:#f4f4f5; font-weight:600; } .working .step-mark { background:var(--accent); border-color:var(--accent); }
  .upload-status { display:grid; gap:8px; margin-top:16px; } progress { display:block; width:100%; height:6px; accent-color:var(--accent); margin-top:12px; }
</style>
