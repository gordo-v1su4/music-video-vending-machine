<script lang="ts">
  // Side-by-side take review for locally rendered shots (scripts/mvvm_gen/review_server.py via /pilot-api).
  // Each setup's two seeds are judged as one pair; used standalone at /pilot-review and in the studio Review view.
  import Icon from "$lib/Icon.svelte";
  import { onMount, tick } from "svelte";

  type Choice = "a" | "b" | "neither";
  type Take = { take: number; setup: number; seed: number; url: string; gpu_s: number | null };
  type Setup = { label: string; framing: string; camera: string };
  type Decision = { a: number; b: number | null; choice: Choice; comment: string; at: string };
  type SetupResult = { setup: number; takes: number[]; done: boolean; winner: number | null };
  type BracketState = {
    pair: [number, number | null] | null;
    setup: number | null;
    setups: SetupResult[];
    setupCount: number;
    rejected: number[];
    done: boolean;
    winner: number | null;
  };
  type Shot = {
    id: string;
    summary: string;
    bars: number | null;
    location: string | null;
    characters: string[];
    setups: Setup[];
    takes: Take[];
    decisions: Decision[];
    state: BracketState | null;
    stale: boolean;
    planPick: number | null;
  };
  type Tone = "cut" | "kept" | "rejected" | "current" | "idle";

  let { embedded = false }: { embedded?: boolean } = $props();

  const START = "uv run --python 3.12 python -m scripts.mvvm_gen.review_server scripts/mvvm_gen/plans/i-ran-pilot.json";

  let plan = $state("");
  let shots = $state<Shot[]>([]);
  let selectedId = $state("");
  let loading = $state(true);
  let offline = $state(false);
  let error = $state("");
  let busy = $state(false);
  let comment = $state("");
  let flash = $state("");

  let videoA = $state<HTMLVideoElement>();
  let videoB = $state<HTMLVideoElement>();
  let playing = $state(false);
  let slow = $state(false);
  let sound = $state<"off" | "a" | "b">("off");
  let nextButton = $state<HTMLButtonElement>();
  let top = $state<HTMLElement>();

  const shot = $derived(shots.find((s) => s.id === selectedId));
  const pair = $derived(shot?.state?.pair ?? null);
  const takeA = $derived(pair ? takeOf(shot!, pair[0]) : undefined);
  const takeB = $derived(pair && pair[1] !== null ? takeOf(shot!, pair[1]) : undefined);
  const single = $derived(!!pair && pair[1] === null);
  const sides = $derived(
    [
      { letter: "A", take: takeA, side: "a" as const },
      { letter: "B", take: single ? undefined : takeB, side: "b" as const },
    ].filter((x) => x.take),
  );
  const winner = $derived(
    shot?.state?.done && shot.state.winner !== null ? takeOf(shot, shot.state.winner) : undefined,
  );
  const decidedCount = $derived(shots.filter((s) => s.state?.done).length);
  const noteCount = $derived(shots.reduce((n, s) => n + s.decisions.filter((d) => d.comment).length, 0));

  function takeOf(s: Shot, n: number) {
    return s.takes.find((t) => t.take === n);
  }

  function shotName(id: string) {
    return id.toUpperCase();
  }

  function setupLabel(s: Shot, setup: number) {
    return s.setups[setup]?.label ?? `Setup ${setup + 1}`;
  }

  function setupInitial(s: Shot, setup: number) {
    const label = setupLabel(s, setup);
    return label === "Main" ? "M" : label.replace(/^Alt\s*/, "");
  }

  function describe(s: Shot, t: Take) {
    return `${setupLabel(s, t.setup)} · seed ${t.seed + 1}`;
  }

  function setupDecisions(s: Shot, setup: number) {
    return s.decisions.filter((d) => takeOf(s, d.a)?.setup === setup);
  }

  function outcome(s: Shot, r: SetupResult): { text: string; short: string; tone: Tone } {
    if (r.done && r.winner === null) return { text: "Both seeds rejected", short: "rejected", tone: "rejected" };
    if (r.done && s.state?.done && r.winner === s.state.winner)
      return { text: `Take ${r.winner} · in the cut`, short: `take ${r.winner}, in the cut`, tone: "cut" };
    if (r.done)
      return {
        text: `Take ${r.winner} · ${s.state?.done ? "approved alternate angle" : "approved"}`,
        short: `take ${r.winner}`,
        tone: "kept",
      };
    if (s.state?.setup === r.setup)
      return {
        text: s.decisions.length ? "Comparing now" : "Up first",
        short: "not chosen yet",
        tone: "current",
      };
    return { text: "Not chosen yet", short: "not chosen yet", tone: "idle" };
  }

  async function load() {
    try {
      const res = await fetch("/pilot-api/review");
      if (!res.ok) throw new Error(`review server answered ${res.status}`);
      const data = await res.json();
      plan = data.plan;
      shots = data.shots;
      offline = false;
      const fromHash = embedded ? "" : location.hash.slice(1);
      if (!shots.some((s) => s.id === selectedId)) {
        selectedId = shots.some((s) => s.id === fromHash)
          ? fromHash
          : (shots.find((s) => !s.state?.done)?.id ?? shots[0]?.id ?? "");
      }
    } catch {
      offline = true;
    } finally {
      loading = false;
    }
  }

  async function act(action: "decide" | "undo" | "redo" | "reset", body: object = {}) {
    if (!shot || busy) return;
    busy = true;
    error = "";
    flash = "";
    try {
      const res = await fetch(`/pilot-api/review/${shot.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        error = `${data.error ?? "The review server rejected that."} Reloaded the latest state.`;
        await load();
        return;
      }
      shots = shots.map((s) => (s.id === data.id ? data : s));
      if (action === "decide") comment = "";
      if (action === "redo") top?.scrollIntoView({ block: "start" });
      if (action === "decide" && data.state?.done) {
        // Finishing a shot's last pair moves straight on to the next undecided shot.
        const w = data.state.winner;
        flash = `${shotName(data.id)} done: ${w !== null ? `take ${w} goes into the cut` : "every take rejected, needs a re-render"}.`;
        if (shots.some((s) => !s.state?.done)) nextOpen();
        else {
          flash += " All shots are decided.";
          await tick();
          nextButton?.focus();
        }
      }
    } catch {
      error = "Could not reach the review server. Your last choice was not saved.";
      offline = true;
    } finally {
      busy = false;
    }
  }

  function decide(choice: Choice) {
    if (!pair || (choice === "b" && single)) return;
    act("decide", { a: pair[0], b: pair[1], choice, comment });
  }

  function select(id: string) {
    selectedId = id;
    comment = "";
    error = "";
    if (!embedded) history.replaceState(null, "", `#${id}`);
  }

  function step(offset: number) {
    const i = shots.findIndex((s) => s.id === selectedId);
    const next = shots[i + offset];
    if (next) select(next.id);
  }

  function nextOpen() {
    const i = shots.findIndex((s) => s.id === selectedId);
    const next = [...shots.slice(i + 1), ...shots.slice(0, i)].find((s) => !s.state?.done);
    if (next) select(next.id);
    else step(1);
  }

  // Both players run as one: start together, correct drift from A, loop once both end.
  function players() {
    return [videoA, videoB].filter((v): v is HTMLVideoElement => !!v);
  }

  function play() {
    players().forEach((v) => v.play().catch(() => (playing = false)));
    playing = true;
  }

  function pause() {
    players().forEach((v) => v.pause());
    playing = false;
  }

  function restart() {
    players().forEach((v) => (v.currentTime = 0));
    if (playing) play();
  }

  function ended() {
    if (players().every((v) => v.ended || v.paused)) {
      players().forEach((v) => (v.currentTime = 0));
      if (playing) play();
    }
  }

  function syncB() {
    if (!videoA || !videoB || videoB.ended) return;
    if (videoA.currentTime < videoB.duration && Math.abs(videoB.currentTime - videoA.currentTime) > 0.08)
      videoB.currentTime = videoA.currentTime;
  }

  function cycleSound() {
    sound = sound === "off" ? "a" : sound === "a" && !single && takeB ? "b" : "off";
  }

  $effect(() => {
    const rate = slow ? 0.5 : 1;
    players().forEach((v) => (v.playbackRate = rate));
  });

  function onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (target.closest("textarea, input, select")) {
      if (e.key === "Escape") target.blur();
      return;
    }
    const keys: Record<string, () => void> = {
      "1": () => decide("a"),
      ArrowLeft: () => decide("a"),
      "2": () => decide("b"),
      ArrowRight: () => decide("b"),
      n: () => decide("neither"),
      ArrowDown: () => decide("neither"),
      " ": () => (playing ? pause() : play()),
      r: restart,
      s: () => (slow = !slow),
      m: cycleSound,
      z: () => shot?.decisions.length && act("undo"),
      c: () => document.getElementById("choice-comment")?.focus(),
      "[": () => step(-1),
      "]": () => step(1),
    };
    const run = keys[e.key.length === 1 ? e.key.toLowerCase() : e.key];
    if (!run) return;
    e.preventDefault();
    run();
  }

  function onHash() {
    if (embedded) return;
    const id = location.hash.slice(1);
    if (id !== selectedId && shots.some((s) => s.id === id)) select(id);
  }

  onMount(load);
</script>

<svelte:window onkeydown={onKey} onhashchange={onHash} />

<div class="take-review" class:embedded>
<div class="review-shell">
  <aside class="rail" aria-label="Shots">
    <div class="rail-head">
      <svelte:element this={embedded ? "h2" : "h1"} class="rail-title">Take review</svelte:element>
      {#if plan}
        <p class="rail-plan">{plan}</p>
        <div class="progress" aria-label="{decidedCount} of {shots.length} shots decided">
          <span style="transform: scaleX({shots.length ? decidedCount / shots.length : 0})"></span>
        </div>
        <p class="rail-count">
          <strong>{decidedCount}</strong> of {shots.length} shots decided{#if noteCount}<span class="rail-notes"
              ><Icon name="note" size={13} />{noteCount} note{noteCount === 1 ? "" : "s"}</span
            >{/if}
        </p>
      {/if}
    </div>
    <ol class="shot-list">
      {#each shots as s (s.id)}
        {@const notes = s.decisions.filter((d) => d.comment).length}
        <li>
          <button
            class:active={s.id === selectedId}
            aria-current={s.id === selectedId ? "true" : undefined}
            onclick={() => select(s.id)}
          >
            <span class="shot-id">{shotName(s.id)}</span>
            <span class="shot-line">{s.summary}</span>
            <span class="chips">
              {#if s.stale}
                <span class="chip rejected">Re-rendered, start over</span>
              {:else}
                {#each s.state?.setups ?? [] as r (r.setup)}
                  {@const o = outcome(s, r)}
                  <span class="chip {o.tone}" title="{setupLabel(s, r.setup)}: {o.text}"
                    ><span class="sr-only">{setupLabel(s, r.setup)}: {o.short}.</span><span aria-hidden="true"
                      >{setupInitial(s, r.setup)}{#if r.done && r.winner !== null}&nbsp;{r.winner}{:else if r.done}<Icon
                          name="close"
                          size={10}
                        />{/if}</span
                    ></span
                  >
                {/each}
                {#if notes}<span class="chip note" title="{notes} note{notes === 1 ? '' : 's'}"
                    ><Icon name="note" size={12} /><span class="sr-only">{notes} note{notes === 1 ? "" : "s"}.</span
                    ><span aria-hidden="true">{notes}</span></span
                  >{/if}
              {/if}
            </span>
          </button>
        </li>
      {/each}
    </ol>
  </aside>

  <div class="review-main" id="review-content" bind:this={top}>
    {#if loading}
      <p class="empty-state" aria-live="polite">Loading renders…</p>
    {:else if offline && !shots.length}
      <section class="offline">
        <h2>The review server isn't running</h2>
        <p>Start it from the repository root, then reload.</p>
        <code>{START}</code>
        <button class="primary" onclick={load}>Retry</button>
      </section>
    {:else if shot}
      <header class="shot-head">
        <div>
          <p class="shot-meta">
            <span>{shotName(shot.id)}</span>
            {#if shot.bars}<span>{shot.bars} bars</span>{/if}
            {#if shot.characters.length}<span>{shot.characters.join(", ")}</span>{/if}
            {#if shot.location}<span>{shot.location.replaceAll("_", " ")}</span>{/if}
          </p>
          <h2 class="shot-title">{shot.summary}</h2>
        </div>
        <div class="head-actions">
          <button class="quiet" onclick={() => step(-1)} disabled={shots[0]?.id === shot.id}
            >Previous <kbd>[</kbd></button
          >
          <button class="quiet" onclick={() => step(1)} disabled={shots.at(-1)?.id === shot.id}
            >Next <kbd>]</kbd></button
          >
        </div>
      </header>

      {#if error}<p class="notice error" role="alert">{error}</p>{/if}
      {#if flash}<p class="notice done" role="status">{flash}</p>{/if}
      {#if shot.stale}
        <div class="notice warn" role="status">
          <span>Some takes were re-rendered after you reviewed them, so these choices no longer apply.</span>
          <button class="quiet" onclick={() => act("reset")} disabled={busy}>Start this shot over</button>
        </div>
      {/if}

      {#if pair && takeA}
        <section class="compare" class:single aria-label="Comparison">
          {#each sides as { letter, take: t, side } (letter)}
            {#if t}
              {@const setup = shot.setups[t.setup]}
              <figure class="take-card">
                <figcaption>
                  <span class="letter" aria-hidden="true">{single ? "" : letter}</span>
                  <span class="take-name">
                    <strong>{shotName(shot.id)} · Take {t.take}</strong>
                    <span>{describe(shot, t)}</span>
                  </span>
                  {#if sound === side}<span class="listening"><Icon name="volume" size={14} /> Sound</span>{/if}
                </figcaption>
                {#key t.url}
                  <!-- svelte-ignore a11y_media_has_caption -->
                  {#if side === "a"}
                    <video
                      bind:this={videoA}
                      src={t.url}
                      muted={sound !== "a"}
                      playsinline
                      autoplay
                      preload="auto"
                      onplay={() => (playing = true)}
                      ontimeupdate={syncB}
                      onended={ended}
                    ></video>
                  {:else}
                    <!-- svelte-ignore a11y_media_has_caption -->
                    <video
                      bind:this={videoB}
                      src={t.url}
                      muted={sound !== "b"}
                      playsinline
                      autoplay
                      preload="auto"
                      onended={ended}
                    ></video>
                  {/if}
                {/key}
                {#if setup}<p class="setup-text">{setup.framing} {setup.camera}</p>{/if}
              </figure>
            {/if}
          {/each}
        </section>

        <div class="playback" role="group" aria-label="Playback">
          <button class="quiet icon-text" onclick={() => (playing ? pause() : play())}>
            <Icon name={playing ? "pause" : "play"} size={15} />{playing ? "Pause" : "Play"} <kbd>Space</kbd>
          </button>
          <button class="quiet icon-text" onclick={restart}><Icon name="restart" size={15} />Restart <kbd>R</kbd></button>
          <button class="quiet" aria-pressed={slow} onclick={() => (slow = !slow)}>Half speed <kbd>S</kbd></button>
          <button class="quiet icon-text" onclick={cycleSound}>
            <Icon name={sound === "off" ? "mute" : "volume"} size={15} />Sound: {sound === "off"
              ? "off"
              : sound.toUpperCase()}
            <kbd>M</kbd>
          </button>
          <span class="pair-count">
            <strong>{setupLabel(shot, takeA.setup)}</strong>{single ? " · only one seed rendered" : " · seed vs seed"}
            · setup {takeA.setup + 1} of {shot.state?.setupCount ?? 1}
          </span>
        </div>

        <section class="decide" aria-label="Your choice">
          <label for="choice-comment"
            >What should change? <span>Optional · saved with this choice <kbd>C</kbd></span></label
          >
          <textarea
            id="choice-comment"
            rows="2"
            bind:value={comment}
            placeholder={single
              ? "e.g. her stride looks weightless, keep the palms but make the run heavier"
              : "e.g. B's face holds, but the camera drifts; A's laser light is better"}
          ></textarea>
          <div class="choices" class:single>
            <button class="choice" onclick={() => decide("a")} disabled={busy}>
              {single ? `Keep take ${takeA.take}` : "A is better"} <kbd>1</kbd>
            </button>
            <button class="choice neither" onclick={() => decide("neither")} disabled={busy}>
              {single ? "Reject" : "Neither"} <kbd>N</kbd>
            </button>
            {#if !single}
              <button class="choice" onclick={() => decide("b")} disabled={busy}>B is better <kbd>2</kbd></button>
            {/if}
          </div>
        </section>
      {:else if shot.state?.done}
        <section class="verdict" aria-live="polite">
          {#if winner}
            <figure class="take-card winner">
              <figcaption>
                <span class="letter kept" aria-hidden="true"><Icon name="check" size={18} /></span>
                <span class="take-name">
                  <strong>{shotName(shot.id)} · Take {winner.take} goes into the cut</strong>
                  <span>{describe(shot, winner)}</span>
                </span>
              </figcaption>
              <!-- svelte-ignore a11y_media_has_caption -->
              <video src={winner.url} muted loop autoplay playsinline controls></video>
            </figure>
          {:else}
            <div class="all-rejected">
              <h3>All {shot.takes.length} takes rejected</h3>
              <p>
                This shot needs a new render. Your notes go into the next plan revision; until then the cut uses
                {shot.planPick !== null ? `the plan's take ${shot.planPick}` : "take 0"}.
              </p>
            </div>
          {/if}
          <div class="verdict-actions">
            <button class="primary" bind:this={nextButton} onclick={nextOpen} disabled={shots.length < 2}
              >{decidedCount === shots.length ? "Next shot" : "Next undecided shot"}</button
            >
            <button class="quiet" onclick={() => act("reset")} disabled={busy}>Redo the whole shot</button>
          </div>
        </section>
      {:else if !shot.takes.length}
        <p class="empty-state">No takes rendered for this shot yet.</p>
      {/if}

      {#if shot.state && !shot.stale}
        <section class="setups" aria-label="Setups for {shotName(shot.id)}">
          <div class="setups-head">
            <h3>Setups</h3>
            {#if shot.decisions.length}
              <button class="quiet icon-text" onclick={() => act("undo")} disabled={busy}
                ><Icon name="undo" size={15} />Undo last <kbd>Z</kbd></button
              >
            {/if}
          </div>
          <ol>
            {#each shot.state.setups as r (r.setup)}
              {@const o = outcome(shot, r)}
              {@const notes = setupDecisions(shot, r.setup).filter((d) => d.comment)}
              <li class:current={o.tone === "current"}>
                <span class="setup-name">{setupLabel(shot, r.setup)}</span>
                <span class="setup-outcome {o.tone}">
                  {#if o.tone === "rejected"}<Icon name="close" size={13} />{:else if o.tone === "cut" || o.tone === "kept"}<Icon
                      name="check"
                      size={13}
                    />{/if}{o.text}
                </span>
                {#if r.done}
                  <button class="quiet redo" onclick={() => act("redo", { setup: r.setup })} disabled={busy}
                    >Redo {setupLabel(shot, r.setup)}</button
                  >
                {/if}
                {#each notes as d, i (i)}
                  <p class="setup-note"><Icon name="note" size={13} /><span>{d.comment}</span></p>
                {/each}
              </li>
            {/each}
          </ol>
          {#if shot.state.done && shot.state.setups.filter((r) => r.winner !== null).length > 1}
            <p class="subtle">The cut uses the first approved setup, Main first. Other approved angles stay available for the edit.</p>
          {/if}
        </section>
      {/if}
    {/if}
  </div>
</div>
</div>

<style>
  .take-review {
    container-type: inline-size;
  }
  .review-shell {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 272px minmax(0, 1fr);
  }
  .embedded .review-shell {
    min-height: 0;
    border: 1px solid #27272a;
    border-radius: 12px;
    overflow: clip;
    background: #101012;
  }
  .rail {
    background: var(--surface);
    border-right: 1px solid #202023;
    position: sticky;
    top: 0;
    align-self: start;
    max-height: 100vh;
    overflow-y: auto;
    padding: 28px 14px 20px;
  }
  .rail-head {
    padding: 0 8px 22px;
  }
  .rail-title {
    font-family: "Manrope", "Segoe UI", sans-serif;
    font-size: 21px;
    font-weight: 650;
    letter-spacing: -0.03em;
  }
  .embedded .rail-title {
    font-size: 17px;
  }
  .rail-plan {
    margin-top: 4px;
    font-size: 12px;
    color: #a1a1aa;
  }
  .progress {
    margin-top: 18px;
    height: 3px;
    border-radius: 3px;
    background: #27272a;
    overflow: hidden;
  }
  .progress span {
    display: block;
    height: 100%;
    background: var(--mint);
    transform-origin: left;
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .rail-count {
    margin-top: 8px;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 12px;
  }
  .rail-count strong {
    color: #f4f4f5;
    font-weight: 600;
  }
  .rail-notes {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--amber);
  }
  .shot-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  .shot-list button {
    width: 100%;
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    column-gap: 8px;
    row-gap: 6px;
    text-align: left;
    padding: 10px 10px;
    border-radius: 7px;
    color: #d4d4d8;
  }
  .shot-list button:hover {
    background: #202023;
  }
  .shot-list button.active {
    background: #27272a;
    color: #f4f4f5;
  }
  .shot-id {
    grid-row: span 2;
    font-size: 12px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: #a1a1aa;
    padding-top: 1px;
  }
  .active .shot-id {
    color: #f4f4f5;
  }
  .shot-line {
    font-size: 12px;
    line-height: 1.45;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    min-height: 20px;
    padding: 0 6px;
    border-radius: 5px;
    border: 1px solid #3f3f46;
    font-size: 11px;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    color: #a1a1aa;
  }
  .chip.cut {
    border-color: #456659;
    background: #1f2e2a;
    color: var(--mint);
  }
  .chip.kept {
    color: #e4e4e7;
  }
  .chip.rejected {
    border-color: #6b5d42;
    background: #2a251b;
    color: var(--amber);
  }
  .chip.current {
    border-color: #a1a1aa;
    color: #f4f4f5;
  }
  .chip.idle {
    border-style: dashed;
  }
  .chip.note {
    border-color: transparent;
    color: var(--amber);
    font-weight: 500;
  }

  .review-main {
    min-width: 0;
    display: flex;
    flex-direction: column;
    padding: 30px 32px 48px;
    gap: 22px;
    scroll-margin-top: 16px;
  }
  .embedded .review-main {
    padding: 24px 24px 32px;
  }
  .shot-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 20px;
  }
  .shot-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    font-size: 12px;
    color: #a1a1aa;
    text-transform: capitalize;
  }
  .shot-meta span:first-child {
    color: #f4f4f5;
    font-weight: 600;
    text-transform: none;
  }
  .shot-title {
    margin-top: 6px;
    font-family: "Manrope", "Segoe UI", sans-serif;
    font-size: 22px;
    font-weight: 650;
    letter-spacing: -0.02em;
    line-height: 1.3;
    max-width: 62ch;
    text-wrap: balance;
  }
  .head-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .notice {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 10px 14px;
    border-radius: 7px;
    font-size: 12px;
    line-height: 1.5;
  }
  .notice.warn {
    border: 1px solid #6b5d42;
    background: #2a251b;
    color: #eadbbd;
  }
  .notice.done {
    border: 1px solid #456659;
    background: #1f2e2a;
    color: #c0decd;
  }
  .notice.error {
    border: 1px solid #7a3b3b;
    background: #2a1818;
    color: #f3c9c9;
  }

  .compare {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .compare.single {
    grid-template-columns: minmax(0, 760px);
  }
  .take-card {
    margin: 0;
    background: var(--panel);
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 12px;
    display: grid;
    gap: 10px;
    align-content: start;
  }
  .take-card figcaption {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 34px;
  }
  .letter {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: #27272a;
    font-family: "Manrope", "Segoe UI", sans-serif;
    font-size: 17px;
    font-weight: 700;
    color: #f4f4f5;
    flex-shrink: 0;
  }
  .single .letter {
    display: none;
  }
  .letter.kept {
    background: #2b403b;
    color: var(--mint);
  }
  .take-name {
    display: grid;
    gap: 1px;
    min-width: 0;
  }
  .take-name strong {
    font-size: 13px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .take-name span {
    font-size: 12px;
    color: #a1a1aa;
  }
  .listening {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--mint);
  }
  video {
    display: block;
    width: 100%;
    aspect-ratio: 1344 / 768;
    border-radius: 8px;
    background: #000;
  }
  .setup-text {
    font-size: 12px;
    line-height: 1.55;
    color: #a1a1aa;
  }

  .playback {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .icon-text {
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }
  .playback [aria-pressed="true"] {
    background: #27272a;
    border-color: #d4d4d8;
  }
  .pair-count {
    margin-left: auto;
    font-size: 12px;
    color: #a1a1aa;
    font-variant-numeric: tabular-nums;
  }
  .pair-count strong {
    color: #f4f4f5;
    font-weight: 600;
  }

  kbd {
    display: inline-block;
    min-width: 18px;
    margin-left: 6px;
    padding: 1px 5px;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    font: 500 10.5px/1.5 "DM Sans", sans-serif;
    color: #a1a1aa;
    text-align: center;
    vertical-align: 1px;
  }

  .decide {
    display: grid;
    gap: 8px;
    padding-top: 4px;
  }
  .decide label {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-size: 13px;
    font-weight: 500;
  }
  .decide label span {
    font-size: 12px;
    font-weight: 400;
    color: #a1a1aa;
  }
  .decide label kbd {
    margin-left: 4px;
  }
  .choices {
    margin-top: 6px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(140px, 0.45fr) minmax(0, 1fr);
    gap: 12px;
  }
  .choices.single {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    max-width: 760px;
  }
  .choice {
    min-height: 50px;
    border-radius: 9px;
    font-size: 14px;
    font-weight: 600;
    background: var(--accent);
    color: var(--ink);
    border: 1px solid var(--accent);
    transition:
      background 0.15s ease-out,
      transform 0.15s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .choice:hover:not(:disabled) {
    background: #f4f4f5;
  }
  .choice:active:not(:disabled) {
    transform: translateY(1px);
  }
  .choice kbd {
    border-color: #71717a;
    color: #3f3f46;
  }
  .choice.neither {
    background: #18181b;
    color: #f4f4f5;
    border-color: var(--line);
  }
  .choice.neither:hover:not(:disabled) {
    background: #202023;
    border-color: #a1a1aa;
  }
  .choice.neither kbd {
    border-color: #3f3f46;
    color: #a1a1aa;
  }

  .verdict {
    display: grid;
    gap: 16px;
    max-width: 760px;
  }
  .all-rejected {
    border: 1px solid #6b5d42;
    background: #2a251b;
    border-radius: 12px;
    padding: 20px 22px;
  }
  .all-rejected h3 {
    margin: 0 0 6px;
    font-size: 16px;
    color: #eadbbd;
  }
  .all-rejected p {
    color: #e4d8bf;
    max-width: 65ch;
  }
  .verdict-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .verdict-actions .primary {
    padding: 12px 18px;
    font-size: 13px;
  }

  .setups {
    border-top: 1px solid #27272a;
    padding-top: 18px;
    max-width: 900px;
    display: grid;
    gap: 10px;
  }
  .setups-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 34px;
  }
  .setups h3 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
  }
  .setups ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
  }
  .setups li {
    display: grid;
    grid-template-columns: 70px minmax(0, 1fr) auto;
    align-items: center;
    gap: 6px 16px;
    padding: 10px 0;
    border-bottom: 1px solid #202023;
    font-size: 12.5px;
    font-variant-numeric: tabular-nums;
  }
  .setup-name {
    color: #a1a1aa;
  }
  .current .setup-name {
    color: #f4f4f5;
    font-weight: 600;
  }
  .setup-outcome {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #d4d4d8;
  }
  .setup-outcome.cut {
    color: var(--mint);
  }
  .setup-outcome.rejected {
    color: var(--amber);
  }
  .setup-outcome.idle {
    color: #a1a1aa;
  }
  .redo {
    grid-column: 3;
    padding: 6px 10px;
  }
  .setup-note {
    grid-column: 2 / 4;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    font-size: 12.5px;
    line-height: 1.55;
    color: #eadbbd;
    max-width: 70ch;
  }
  .setup-note :global(svg) {
    flex-shrink: 0;
    margin-top: 3px;
    color: var(--amber);
  }

  .offline {
    max-width: 640px;
    margin-top: 12vh;
    display: grid;
    gap: 12px;
    justify-items: start;
  }
  .embedded .offline {
    margin-top: 24px;
  }
  .offline h2 {
    font-size: 20px;
  }
  .offline code {
    display: block;
    width: 100%;
    padding: 12px 14px;
    border: 1px solid #27272a;
    border-radius: 7px;
    background: var(--surface);
    font-size: 12px;
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
  .empty-state {
    margin-top: 12vh;
    color: #a1a1aa;
  }

  @container (max-width: 1000px) {
    .review-shell {
      grid-template-columns: minmax(0, 1fr);
    }
    .rail {
      position: static;
      max-height: none;
      border-right: 0;
      border-bottom: 1px solid #202023;
      padding: 18px 16px 12px;
    }
    .rail-head {
      padding: 0 0 12px;
    }
    .shot-list {
      grid-auto-flow: column;
      grid-auto-columns: minmax(170px, 200px);
      overflow-x: auto;
      padding-bottom: 6px;
    }
    .review-main {
      padding: 22px 16px 40px;
    }
  }
  @container (max-width: 700px) {
    .compare {
      grid-template-columns: minmax(0, 1fr);
    }
    .shot-head {
      flex-direction: column;
    }
    .choices {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
    .choices .neither {
      grid-column: span 2;
      order: 3;
    }
    .choices.single .neither {
      grid-column: auto;
    }
    .pair-count {
      margin-left: 0;
      width: 100%;
    }
    .setups li {
      grid-template-columns: minmax(0, 1fr) auto;
    }
    .setup-name {
      grid-column: 1 / -1;
    }
    .redo {
      grid-column: 2;
      grid-row: 2;
    }
    .setup-note {
      grid-column: 1 / -1;
    }
    kbd {
      display: none;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .progress span,
    .choice {
      transition: none;
    }
  }
</style>
