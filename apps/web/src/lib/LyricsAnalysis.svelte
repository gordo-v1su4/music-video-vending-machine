<script lang="ts">
  import type { Asset, StudioApi, TranscriptionJob } from './api';
  import { time } from './timing';
  let { client, projectId, asset, available, onError, onResult }: { client:StudioApi; projectId:string; asset:Asset; available:boolean; onError:(e:unknown)=>void; onResult:(result:TranscriptionJob['result'])=>void } = $props();
  let job = $state<TranscriptionJob | null>(null), loading = $state(true), starting = $state(false), problem = $state(''), refresh = $state(0);
  let recovering = $state(false);
  let recoveryFile = $state<File | null>(null), confirmedSource = $state(false);
  const result = $derived(job?.status === 'completed' && job.sha256 === asset.sha256 ? job.result : null);
  const active = $derived(starting || job?.status === 'queued' || job?.status === 'running');
  $effect(() => {
    const api=client, id=projectId, selected=asset, enabled=available; void refresh;
    let disposed=false, timer:ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next=await api.transcription(id,selected.id);
        if(disposed)return;
        if(next && (next.assetId!==selected.id || next.sha256!==selected.sha256))throw new Error('Transcript does not match this audio source.');
        job=next;loading=false;problem='';
        onResult(next?.status === 'completed' ? next.result : null);
        if(next && ['queued','running'].includes(next.status))timer=setTimeout(poll,2000);
      } catch(e){if(disposed)return;loading=false;problem=e instanceof Error?e.message:'Transcription status unavailable.';onError(e);timer=setTimeout(poll,5000);}
    }
    if(enabled)void poll();
    return()=>{disposed=true;clearTimeout(timer);};
  });
  async function start() {
    if(starting || recovering || !available)return;
    starting=true;problem='';
    try {job=await client.transcription(projectId,asset.id,true);refresh++;}
    catch(e){problem=e instanceof Error?e.message:'Could not queue transcription.';onError(e);}
    finally{starting=false;}
  }
  async function recover() {
    if (!job || starting || recovering || !available || (recoveryFile && !confirmedSource)) return;
    const current = job;
    recovering = true; problem = '';
    try {
      let providerResponse = null;
      if (recoveryFile) {
        if (recoveryFile.size > 2 * 1024 * 1024) throw new Error('Provider response must be at most 2 MiB.');
        try { providerResponse = JSON.parse(await recoveryFile.text()); }
        catch { throw new Error('Choose a valid provider JSON response.'); }
      }
      job = await client.recoverTranscription(projectId, asset.id, {
        jobId: current.id, expectedUpdatedAt: current.updatedAt, sourceSha256: asset.sha256,
        providerResponse, confirmedSource,
      });
      recoveryFile = null; confirmedSource = false; refresh++;
    } catch (error) {
      problem = error instanceof Error ? error.message : 'Recovery could not finish.';
      onError(error);
    } finally { recovering = false; }
  }
</script>

<section class="lyrics-analysis" aria-labelledby="lyrics-title">
  <div class="heading"><h2 id="lyrics-title">Lyrics &amp; story context</h2><span role="status">{!available?'Connection paused':loading?'Checking transcript…':starting?'Queuing transcription…':job?.status==='queued'?'Queued for Deepgram':job?.status==='running'?'Transcribing & analyzing language':result?.wordCount?'Transcript ready':result?'No lyrics detected':job?'Needs attention':'Not started'}</span></div>
  <p class="small-note">{asset.name} · {result?.model ?? 'Deepgram Nova-3 / Whisper'} · English</p>
  {#if problem}<p role="alert">{problem}</p>{/if}
  {#if active}<progress aria-label="Deepgram transcription in progress"></progress><p>Extracting timed lyrics and checking for early dropout. Sentiment is disabled. Each completed pass is saved with your project.</p>{/if}
  {#if job?.message}<p role="status">{job.message}</p>{/if}
  {#if job && ['failed','reconciliation_required'].includes(job.status)}
    <div class="recovery">
      <h3>Recover an interrupted transcript</h3>
      <p>Use responses already saved on the server. If none are usable, obtain the completed JSON response from the provider and select it below. Recovery makes no new paid call and retains the original receipts.</p>
      <label>Completed provider response (optional)<input type="file" accept=".json,application/json" disabled={!available || starting || recovering} onchange={(event) => { recoveryFile = event.currentTarget.files?.[0] ?? null; confirmedSource = false; }} /></label>
      {#if recoveryFile}<label><input type="checkbox" bind:checked={confirmedSource} disabled={!available || starting || recovering} />I verified this response belongs to {asset.name}.</label>{/if}
      <button disabled={!available || starting || recovering || (!!recoveryFile && !confirmedSource)} onclick={recover}>{starting ? 'Recovering saved responses…' : recoveryFile ? 'Recover from provider response' : 'Recover saved responses'}</button>
      <p class="small-note">If the provider has no completed response, leave the request unresolved. A new paid attempt requires a separate approved quote.</p>
    </div>
  {/if}
  {#if !loading && (!job || job.profile === 'legacy-nova-3')}<p>Use Project Stack Structure’s full-song flow: Nova-3 with sentiment off, a Whisper pass if words stop early, then one remaining-audio pass if needed. Up to three billable requests for this {time(asset.durationMs ?? 0)} source; no automatic replay after an interrupted call.</p><button class="primary" disabled={!available || active || recovering} onclick={start}>{job ? 'Run full-song lyric recovery' : 'Extract lyrics & context'}</button>{/if}
  {#if result}
    {#if !result.wordCount}<p role="status">Deepgram returned no words from this source. Use an aligned isolated vocal stem and review the result before using it for your story.</p>{/if}
    <p><strong>{result.wordCount} words · {result.chunks.length} timed lyric chunks</strong></p>
    <dl>
      <dt>Deepgram summary</dt><dd>{result.summary || (result.model.includes('whisper') ? 'The recovery pass returned words without a story summary. Develop the interpretation in Treatment above.' : 'No summary returned. Develop the interpretation in Treatment above.')}</dd>
      <dt>Topics</dt><dd>{result.topics.join(' · ') || 'No topics returned.'}</dd>
      <dt>Intent</dt><dd>{result.intents.join(' · ') || 'No intent labels returned.'}</dd>
      <dt>Sentiment</dt><dd>{job?.profile === 'stack-structure-v1' ? 'Disabled for sung-lyric extraction' : result.sentiment || 'No sentiment returned.'}</dd>
    </dl>
    <p class="small-note">These are language cues for your story, not a finished treatment or an approval.</p>
    <details open><summary>Timed lyrics</summary><ol class="lyric-lines">{#each result.chunks as chunk, i (i)}<li><span>{time(chunk.startMs)}–{time(chunk.endMs)}</span><p>{chunk.text}</p>{#if chunk.confidence !== null && chunk.confidence !== undefined && chunk.confidence < 0.75}<small>Check wording</small>{/if}</li>{/each}</ol></details>
    <details><summary>Transcription notes</summary>{#each result.warnings as warning,i(i)}<p>{warning}</p>{/each}</details>
  {/if}
</section>

<style>
  .lyrics-analysis { padding-block:24px; border-bottom:1px solid var(--line); margin-bottom:24px; min-width:0; }
  .heading { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:baseline; gap:12px; } h2 { margin:0; } .heading span { color:var(--muted); font-size:13px; }
  p,dd { line-height:1.6; overflow-wrap:anywhere; } dl { display:grid; grid-template-columns:140px 1fr; gap:10px 16px; } dt { color:var(--muted); } dd { margin:0; }
  progress { width:100%; height:6px; accent-color:var(--accent); } summary { cursor:pointer; padding:12px 0; } summary:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
  .lyric-lines { list-style:none; padding:0; max-height:360px; overflow:auto; } li { display:grid; grid-template-columns:120px 1fr; gap:8px; border-bottom:1px solid var(--line); padding:12px 0; } li span,li small { color:var(--muted); font-size:12px; font-variant-numeric:tabular-nums; } li p { margin:0; } li small { grid-column:2; }
  @media(max-width:520px){dl{grid-template-columns:1fr;gap:6px;}dd{margin-bottom:12px;}li{grid-template-columns:90px 1fr;}}
</style>
