<script lang="ts">
  // First cut in context: the assembled pilot cut following the studio playhead, with its shots laid out
  // along the song. Click a shot to move the playhead there; rebuild when review picks change.
  import CutVideo from "./CutVideo.svelte";
  import { pilotCut } from "./pilot-cut.svelte";
  import { studioClock } from "./studio-clock.svelte";
  import { time } from "./timing";

  let { onReviewTakes }: { onReviewTakes?: () => void } = $props();

  const cut = $derived(pilotCut.info?.exists ? pilotCut.info : null);
  const current = $derived(
    cut?.shots.findIndex((s) => studioClock.songMs >= s.startMs && studioClock.songMs < s.endMs) ?? -1,
  );
  const changed = $derived(cut?.shots.filter((s) => s.take !== s.pickNow) ?? []);
  const progress = $derived(
    cut ? Math.max(0, Math.min(1, (studioClock.songMs - cut.songStartMs) / cut.durationMs)) : 0,
  );
</script>

<section class="first-cut" aria-labelledby="first-cut-title">
  <header class="cut-head">
    <div>
      <h2 id="first-cut-title">First cut</h2>
      {#if cut}
        <p class="cut-meta">
          {cut.plan} · song {time(cut.songStartMs)}–{time(cut.songStartMs + cut.durationMs)} · {cut.shots.length} shots
          {#if cut.builtAt}· built {new Date(cut.builtAt).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}{/if}
        </p>
      {/if}
    </div>
    <div class="cut-actions">
      {#if cut}
        <button class="primary" disabled={!studioClock.available} onclick={() => studioClock.playFrom(cut.songStartMs)}
          >Play the cut</button
        >
      {/if}
      <button class="quiet" onclick={() => pilotCut.build()} disabled={pilotCut.building || pilotCut.unavailable}
        >{pilotCut.building ? "Building… about a minute" : cut ? "Rebuild cut" : "Build first cut"}</button
      >
    </div>
  </header>

  {#if pilotCut.error}<p class="note error" role="alert">{pilotCut.error}</p>{/if}
  {#if pilotCut.unavailable}
    <p class="note">
      The local review server isn't running, so the pilot cut can't load. Start
      <code>python -m scripts.mvvm_gen.review_server &lt;plan&gt;</code> and reopen this tab.
    </p>
  {:else if cut}
    {#if changed.length}
      <p class="note warn" role="status">
        Your picks changed for {changed.map((s) => s.id.toUpperCase()).join(", ")} since this cut was built. Rebuild to
        see them.
      </p>
    {/if}
    {#if !studioClock.available}
      <p class="note">Choose a project with an approved song master to play the cut against the song.</p>
    {/if}
    <div class="cut-stage">
      <CutVideo url={cut.url} songStartMs={cut.songStartMs} durationMs={cut.durationMs} />
    </div>

    <div class="strip-wrap">
      <ol class="shot-strip" aria-label="Shots in the cut">
        {#each cut.shots as s, i (s.id)}
          <li style:flex-grow={s.endMs - s.startMs}>
            <button
              class:current={i === current}
              class:changed={s.take !== s.pickNow}
              aria-current={i === current ? "true" : undefined}
              title="{s.id.toUpperCase()} · take {s.take} · {time(s.startMs)} · {s.summary}"
              onclick={() => studioClock.seek(s.startMs)}
            >
              <strong>{s.id.toUpperCase()}</strong><span>t{s.take}</span>
            </button>
          </li>
        {/each}
      </ol>
      <span class="strip-head" style:left="{progress * 100}%" aria-hidden="true"></span>
    </div>
    <p class="strip-caption">
      {#if current >= 0}
        <strong>{cut.shots[current].id.toUpperCase()}</strong> · take {cut.shots[current].take} · {cut.shots[current].summary}
      {:else}
        Click a shot to move the playhead there. The song plays from the transport below.
      {/if}
    </p>
    {#if onReviewTakes}
      <p class="subtle">
        To swap a shot, change its pick in <button class="link" onclick={onReviewTakes}>Take review</button>, then rebuild.
      </p>
    {/if}
  {:else if pilotCut.info && !pilotCut.info.exists}
    <p class="note">No cut yet. Once every shot has a pick, build the first cut to watch it against the song.</p>
  {/if}
</section>

<style>
  .first-cut {
    display: grid;
    gap: 14px;
    margin-bottom: 28px;
  }
  .cut-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
  }
  .cut-head h2 {
    font-size: 17px;
  }
  .cut-meta {
    margin-top: 4px;
    font-size: 12px;
    color: #a1a1aa;
    font-variant-numeric: tabular-nums;
  }
  .cut-actions {
    display: flex;
    gap: 8px;
  }
  .note {
    font-size: 12.5px;
    line-height: 1.55;
    color: #d4d4d8;
    padding: 10px 12px;
    border: 1px solid #27272a;
    border-radius: 7px;
  }
  .note.warn {
    border-color: #6b5d42;
    background: #2a251b;
    color: #eadbbd;
  }
  .note.error {
    border-color: #7a3b3b;
    background: #2a1818;
    color: #f3c9c9;
  }
  .note code {
    font-size: 12px;
  }
  /* Keep picture, shot strip and the transport on one screen: 16:9 capped to 40% of the window height. */
  .cut-stage {
    width: min(100%, calc(40vh * 16 / 9));
  }
  .strip-wrap {
    position: relative;
  }
  .shot-strip {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    gap: 2px;
  }
  .shot-strip li {
    flex-basis: 0;
    min-width: 0;
  }
  .shot-strip button {
    width: 100%;
    height: 44px;
    display: grid;
    align-content: center;
    gap: 1px;
    padding: 0 4px;
    border: 1px solid #27272a;
    border-radius: 5px;
    background: #18181b;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: #a1a1aa;
    overflow: hidden;
    white-space: nowrap;
  }
  .shot-strip button strong {
    color: #e4e4e7;
    font-weight: 600;
  }
  .shot-strip button:hover {
    border-color: #52525b;
  }
  .shot-strip button.current {
    border-color: #a78bfa;
    background: #221f33;
  }
  .shot-strip button.changed {
    border-style: dashed;
    border-color: #6b5d42;
  }
  .strip-head {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 2px;
    margin-left: -1px;
    background: #e4e4e7;
    pointer-events: none;
  }
  .strip-caption {
    font-size: 12.5px;
    color: #d4d4d8;
    min-height: 1.6em;
  }
  .link {
    padding: 0;
    color: #c4b5fd;
    text-decoration: underline;
    text-underline-offset: 3px;
  }
</style>
