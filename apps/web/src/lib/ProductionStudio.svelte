<script lang="ts">
  // Production journey for one approved packet: references -> plan -> prompts -> visible Swarm runs ->
  // anonymous review -> salvage/Keep -> export. Data: scripts/mvvm_gen/production_api.py via /pilot-api/production.
  import Icon from "$lib/Icon.svelte";
  import { onMount } from "svelte";
  import {
    call, clock, hardBlocked, inputMap, pct, slotDuration,
    type Clip, type EditCandidate, type Finding, type Lint, type Reference, type Repair, type Slot, type State
  } from "$lib/production";

  const START = "uv run --python 3.12 python -m scripts.mvvm_gen.review_server scripts/mvvm_gen/plans/i-ran-pilot.json";
  const STEPS = [
    { id: "references", label: "References" },
    { id: "plan", label: "Sequence plan" },
    { id: "prompts", label: "Prompts" },
    { id: "runs", label: "Renders" },
    { id: "review", label: "Review" },
    { id: "edit", label: "Edit and Keep" },
    { id: "export", label: "Export" }
  ] as const;

  let { embedded = false }: { embedded?: boolean } = $props();

  let s = $state<State | null>(null);
  let offline = $state(false);
  let error = $state("");
  let busy = $state(false);
  let flash = $state("");
  let notes = $state<Record<string, string>>({});

  let promptSlot = $state("C1");
  let draft = $state("");
  let draftLint = $state<Lint | null>(null);
  let draftName = $state("");
  let lintTimer: ReturnType<typeof setTimeout> | undefined;

  let editingSlot = $state("");
  let slotForm = $state<Record<string, string>>({});
  let editingBrief = $state(false);
  let briefForm = $state("");

  let step = $state("");
  let candidateView = $state<string>("");
  let player = $state<HTMLVideoElement>();

  const packet = $derived(s?.packet);
  const seq = $derived(packet?.sequence);
  const slot = $derived(seq?.clips.find((c) => c.slot === promptSlot));
  const candidates = $derived(s?.edit.candidates ?? []);
  const shownCandidate = $derived(candidates.find((c) => c.id === candidateView) ?? candidates.find((c) => c.id === s?.edit.active) ?? candidates[0]);
  const activeCandidate = $derived(candidates.find((c) => c.id === s?.edit.active));
  const status = $derived(stepStatus());
  // Open on the first step that still needs action; the user can jump to any step.
  const current = $derived(step || (STEPS.find((x) => status[x.id] !== "done")?.id ?? "references"));

  function stepStatus(): Record<string, "done" | "open" | "blocked" | "idle"> {
    if (!s) return {};
    const p = s.packet;
    const done = (b: boolean) => (b ? "done" : "open");
    const anyRun = s.runs.length > 0;
    return {
      references: p.approved ? "done" : p.blocking.length ? "blocked" : "open",
      plan: done(s.clips.some((c) => c.shots.some((x) => x.status === "reviewed"))),
      prompts: done(Object.values(s.prompts).some((x) => x.lint.ok)),
      runs: anyRun ? done(s.runs.every((r) => r.status === "complete")) : "idle",
      review: s.findings.length ? "done" : "idle",
      edit: s.edit.active ? "done" : candidates.length ? "open" : "idle",
      export: s.edit.active ? "open" : "idle"
    };
  }

  async function load() {
    try {
      s = await call<State>("");
      offline = false;
      if (!draftName) loadDraft(promptSlot);
    } catch (e) {
      offline = true;
      error = String((e as Error).message ?? e);
    }
  }

  async function act<T>(label: string, fn: () => Promise<T>) {
    busy = true;
    error = "";
    try {
      await fn();
      flash = label;
      setTimeout(() => (flash = ""), 2400);
      await load();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  function decide(ref: Reference, decision: "approved" | "rejected" | "pending") {
    return act(`${ref.id} ${decision}`, () =>
      call(`/reference/${ref.id}/decide`, { decision, note: notes[ref.id] ?? ref.note ?? "", revision: packet!.revision })
    );
  }

  function approvePacket() {
    return act("Packet approved", () => call("/approve", { by: "director", revision: packet!.revision }));
  }

  const SLOT_FIELDS = [["title", "Title"], ["entry", "Starts"], ["exit", "Ends"], ["camera", "Camera"], ["action", "Action"]] as const;

  function startSlotEdit(c: Slot) {
    editingSlot = c.slot;
    slotForm = Object.fromEntries(SLOT_FIELDS.map(([k]) => [k, String((c as Record<string, unknown>)[k] ?? "")]));
  }

  function saveSlot(c: Slot) {
    const fields = Object.fromEntries(Object.entries(slotForm).filter(([k, v]) => v !== String((c as Record<string, unknown>)[k] ?? "")));
    return act(`${c.slot} plan saved; approval needed again`, async () => {
      await call("/plan", { slot: c.slot, fields, revision: packet!.revision });
      editingSlot = "";
    });
  }

  function saveBrief() {
    return act("Brief saved; approval needed again", async () => {
      await call("/plan", { brief: briefForm, revision: packet!.revision });
      editingBrief = false;
    });
  }

  function loadDraft(slotId: string) {
    promptSlot = slotId;
    const saved = Object.entries(s?.prompts ?? {}).find(([, p]) => p.slot === slotId);
    draftName = saved?.[0] ?? `${slotId} director`;
    draft = saved?.[1].text ?? "";
    draftLint = saved?.[1].lint ?? null;
  }

  function scheduleLint() {
    clearTimeout(lintTimer);
    lintTimer = setTimeout(runLint, 350);
  }

  async function runLint() {
    if (!slot || !packet) return;
    try {
      draftLint = await call<Lint>("/lint", {
        text: draft, input_map: inputMap(slot, packet.characters), duration: slotDuration(slot),
        cuts: slot.cuts, revision: packet.revision
      });
    } catch (e) {
      error = (e as Error).message;
    }
  }

  function savePrompt() {
    if (!slot || !packet) return;
    return act(`Saved ${draftName}`, () =>
      call("/prompt/save", {
        name: draftName, slot: slot.slot, text: draft, input_map: inputMap(slot, packet.characters),
        duration: slotDuration(slot), cuts: slot.cuts
      })
    );
  }

  function markShots(clip: Clip, reviewed: boolean) {
    const shots = clip.shots.map((x) => ({ in: x.in, out: x.out, note: x.note, status: reviewed ? "reviewed" : x.status }));
    return act(reviewed ? "Ranges marked reviewed" : "Ranges saved", () => call(`/clip/${clip.id}/shots`, { shots, by: "director" }));
  }

  async function proposeCuts(clip: Clip) {
    await act("Detector cuts proposed (unreviewed)", async () => {
      const r = await call<{ proposed: { in: number; out: number; status: string }[] }>(`/clip/${clip.id}/propose-cuts`, {});
      await call(`/clip/${clip.id}/shots`, { shots: r.proposed, by: "detector" });
    });
  }

  function editAction(c: EditCandidate, action: "keep" | "reject" | "restore") {
    const label = { keep: "Kept as active cut", reject: "Candidate rejected", restore: "Previous cut restored" }[action];
    return act(label, () => call(`/edit/${c.id}/${action}`, {}));
  }

  function decideRepair(r: Repair, decision: "approved" | "rejected") {
    return act(`Repair ${r.id} ${decision}`, () => call(`/repair/${r.id}/decide`, { decision, by: "director" }));
  }

  function findingsFor(candidate: string): Finding[] {
    return (s?.findings ?? []).filter((f) => f.candidate === candidate);
  }

  // Generated clips belong to the slot their reconciled run was rendered for (guide trials span C0+C1);
  // supplied clips to the slot their recorded song start falls in.
  function clipInSlot(k: Clip, c: Slot): boolean {
    const run = s?.runs.find((r) => r.clip_id === k.id);
    if (run) return run.slot === c.slot || (run.slot === "C0+C1" && (c.slot === "C0" || c.slot === "C1"));
    const t = (k.lineage as { song_start_s?: number }).song_start_s;
    return t !== undefined && t >= c.song_s[0] - 0.05 && t < c.song_s[1];
  }

  function slotOf(t: number): Slot | undefined {
    // Segment starts are frame-snapped, so allow one output frame (1/24 s) either side of a slot boundary.
    const at = t + 1 / 24;
    return seq?.clips.find((c) => at >= c.song_s[0] && at < c.song_s[1]);
  }

  onMount(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  });
</script>

<div class="studio" class:embedded>
  <aside class="rail" aria-label="Production steps">
    <div class="rail-head">
      <h1>{seq?.id === "seq-into-the-fog" ? "Into the fog" : "Production"}</h1>
      {#if packet}
        <p class="sub">Packet revision {packet.revision}, fingerprint <span class="num">{packet.fingerprint}</span></p>
        <p class="approval" class:ok={packet.approved}>
          <Icon name={packet.approved ? "check" : "note"} />
          {packet.approved ? `Approved by ${packet.approval?.by}` : "Not approved"}
        </p>
      {/if}
    </div>
    <nav>
      {#each STEPS as st (st.id)}
        <button class="step {status[st.id] ?? 'idle'}" class:current={current === st.id} aria-current={current === st.id ? "step" : undefined} onclick={() => (step = st.id)}>
          <span class="dot" aria-hidden="true"></span>{st.label}
          <span class="sr-only">{status[st.id] ?? "idle"}</span>
        </button>
      {/each}
    </nav>
    {#if packet && !packet.approved}
      <div class="gate">
        {#each packet.blocking as b}<p>{b}</p>{/each}
        <button class="primary" disabled={busy || packet.blocking.some((b) => !b.startsWith("packet changed"))} onclick={approvePacket}>
          Approve packet
        </button>
      </div>
    {/if}
    {#if flash}<p class="flash" role="status">{flash}</p>{/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
  </aside>

  <main>
    {#if offline && !s}
      <section class="empty">
        <h2>The production server isn't running</h2>
        <p>Start it from the repository root, then this page reconnects on its own.</p>
        <code>{START}</code>
      </section>
    {:else if s && packet && seq}
      <header class="spine" aria-label="Sequence on the song timeline">
        <div class="spine-meta">
          <span>Song <span class="num">{clock(seq.song_start_s)}</span> to <span class="num">{clock(seq.song_end_s)}</span></span>
          <span>{seq.clips.length} planned clips</span>
          {#if activeCandidate}<span class="ok-text">Active cut: {activeCandidate.label}</span>{:else}<span class="muted">No active cut yet</span>{/if}
        </div>
        {#if s.song.chunks.length && !embedded}
          <div class="lane song-lane" aria-label="Song analysis: edit-plan chunks and energy">
            {#each s.song.chunks as ch (ch.index)}
              <span class="chunk" style:left="{pct(ch.start_s, seq.song_start_s, seq.song_end_s)}%"
                style:width="{pct(ch.end_s, seq.song_start_s, seq.song_end_s) - pct(ch.start_s, seq.song_start_s, seq.song_end_s)}%"
                title="Chunk {ch.index}: {ch.sections.join(', ')}">
                {#each ch.shots as sh, i (i)}
                  <i class="beat {sh.role}" style:left="{((sh.start_s - ch.start_s) / (ch.end_s - ch.start_s)) * 100}%"
                    style:height="{Math.max(12, sh.energy * 100)}%"></i>
                {/each}
                <em>{ch.sections.join(" to ")}</em>
              </span>
            {/each}
          </div>
        {/if}
        <div class="lane plan-lane">
          {#each seq.clips as c (c.slot)}
            <button class="slot {c.kind}" class:selected={current === "prompts" && promptSlot === c.slot} style:left="{pct(c.song_s[0], seq.song_start_s, seq.song_end_s)}%"
              style:width="{pct(c.song_s[1], seq.song_start_s, seq.song_end_s) - pct(c.song_s[0], seq.song_start_s, seq.song_end_s)}%"
              onclick={() => { loadDraft(c.slot); step = "prompts"; }}>
              <strong>{c.slot}</strong><span>{c.title}</span>
            </button>
          {/each}
        </div>
        {#if shownCandidate}
          <div class="lane cut-lane" aria-label="Candidate cut segments">
            {#each shownCandidate.segments as g, i (i)}
              <span class="seg" style:left="{pct(g.song_s, seq.song_start_s, seq.song_end_s)}%"
                style:width="{pct(g.song_s + g.out_s - g.in_s, seq.song_start_s, seq.song_end_s) - pct(g.song_s, seq.song_start_s, seq.song_end_s)}%"
                title="{g.label} {clock(g.in_s)}-{clock(g.out_s)}">{g.label}</span>
            {/each}
            {#each shownCandidate.joins as j, i (i)}
              <span class="join {j.verdict}" style:left="{pct(j.at_s, seq.song_start_s, seq.song_end_s)}%" title={j.reasons.join("; ")}></span>
            {/each}
          </div>
        {/if}
      </header>

      <div class="stepbar" role="tablist" aria-label="Production steps">
        {#each STEPS as st (st.id)}
          <button role="tab" aria-selected={current === st.id} class="step {status[st.id] ?? 'idle'}" class:current={current === st.id}
            onclick={() => (step = st.id)}><span class="dot" aria-hidden="true"></span>{st.label}</button>
        {/each}
        {#if embedded && !packet.approved}
          <span class="bar-gate">{packet.blocking[0]}</span>
          <button class="primary small" disabled={busy || packet.blocking.some((b) => !b.startsWith("packet changed"))} onclick={approvePacket}>Approve packet</button>
        {/if}
      </div>
      {#if embedded && (flash || error)}<p class={error ? "error" : "flash"} role={error ? "alert" : "status"}>{error || flash}</p>{/if}

      {#if current === "references"}
      <section id="references">
        <h2>References</h2>
        {#if editingBrief}
          <label class="sr-only" for="brief">Brief</label>
          <textarea id="brief" rows="5" bind:value={briefForm}></textarea>
          <div class="clip-actions">
            <button class="primary" disabled={busy || briefForm === packet.brief} onclick={saveBrief}>Save brief</button>
            <button class="ghost" onclick={() => (editingBrief = false)}>Cancel</button>
          </div>
        {:else}
          <p class="lede">{packet.brief}</p>
          <button class="ghost small" onclick={() => { briefForm = packet.brief; editingBrief = true; }}><Icon name="note" />Edit brief</button>
        {/if}
        <div class="characters">
          {#each packet.characters as c (c.id)}
            <article class="character">
              <h3>{c.name}</h3>
              {#if c.refmod}
                <p class="kv"><span>RefMod</span>{c.refmod.name} <span class="num faint">{c.refmod.sha256.slice(0, 10)}</span></p>
                <p class="kv"><span>Mode</span>{c.refmod.mode}</p>
              {:else}
                <p class="warn-text">No RefMod: identity conditioning missing</p>
              {/if}
              <p class="look">{c.look}</p>
              {#if c.look_note}<p class="faint">{c.look_note}</p>{/if}
            </article>
          {/each}
        </div>
        <ul class="refs">
          {#each packet.references as r (r.id)}
            <li class="ref {r.decision}">
              {#if /\.(png|jpe?g|webp)$/i.test(r.path)}
                <img src="/pilot-api/production/ref-image/{r.id}" alt="{r.id} reference" loading="lazy" />
              {:else}
                <div class="noimg"><Icon name="production" /></div>
              {/if}
              <div class="ref-body">
                <div class="ref-top">
                  <h3>{r.id}</h3>
                  <span class="role">{r.role.replace("_", " ")}{r.frame !== undefined ? ` at frame ${r.frame}` : ""}</span>
                  <span class="chip {r.decision}">{r.decision}</span>
                </div>
                <details>
                  <summary>Details</summary>
                  {#if r.provenance}<p>{r.provenance}</p>{/if}
                  {#if r.transform}<p class="faint">Transform: {r.transform}</p>{/if}
                  {#if r.sha256}<p class="faint num">sha256 {r.sha256.slice(0, 16)}</p>{/if}
                </details>
                <div class="ref-actions">
                  <label class="sr-only" for="note-{r.id}">Note for {r.id}</label>
                  <input id="note-{r.id}" placeholder="Decision note" value={notes[r.id] ?? r.note ?? ""}
                    oninput={(e) => (notes[r.id] = (e.target as HTMLInputElement).value)} />
                  <button class="primary" disabled={busy || r.decision === "approved"} onclick={() => decide(r, "approved")}><Icon name="check" />Approve</button>
                  <button class="ghost" disabled={busy || r.decision === "rejected"} onclick={() => decide(r, "rejected")}><Icon name="close" />Reject</button>
                </div>
              </div>
            </li>
          {/each}
        </ul>
      </section>
      {/if}

      {#if current === "plan"}
      <section id="plan">
        <h2>Sequence plan</h2>
        <ol class="slots">
          {#each seq.clips as c (c.slot)}
            {@const clips = s.clips.filter((k) => clipInSlot(k, c))}
            <li>
              <div class="slot-head">
                <h3>{c.slot} {c.title}</h3>
                <span class="num">{clock(c.song_s[0])} to {clock(c.song_s[1])}</span>
                <span class="faint">{c.kind === "supplied" ? "Supplied footage" : "To generate"}, {c.cuts ? `${c.cuts} cut` : "one continuous shot"}</span>
              </div>
              {#if editingSlot === c.slot}
                <div class="slot-form">
                  {#each SLOT_FIELDS as [key, label] (key)}
                    <label for="slot-{c.slot}-{key}">{label}</label>
                    <textarea id="slot-{c.slot}-{key}" rows={key === "title" ? 1 : 2} bind:value={slotForm[key]}></textarea>
                  {/each}
                  <div class="clip-actions">
                    <button class="primary" disabled={busy} onclick={() => saveSlot(c)}>Save {c.slot} plan</button>
                    <button class="ghost" onclick={() => (editingSlot = "")}>Cancel</button>
                    <span class="faint">Saving changes the packet; it needs approval again.</span>
                  </div>
                </div>
              {:else}
                <dl>
                  <dt>Starts</dt><dd>{c.entry}</dd>
                  <dt>Ends</dt><dd>{c.exit}</dd>
                  <dt>Camera</dt><dd>{c.camera}</dd>
                  {#if c.action}<dt>Action</dt><dd>{c.action}</dd>{/if}
                  <dt>Cast</dt><dd>{c.characters.map((id) => packet.characters.find((x) => x.id === id)?.name ?? id).join(", ")} at {c.location}</dd>
                </dl>
                <button class="ghost small" onclick={() => startSlotEdit(c)}><Icon name="note" />Edit {c.slot}</button>
              {/if}
              {#if !clips.length}
                <p class="placeholder">Planned placeholder. No footage observed for this slot yet.</p>
              {/if}
              {#each clips as k (k.id)}
                <div class="clip">
                  <div class="clip-head">
                    <strong>{k.label}</strong>
                    <span class="faint">{k.source}, {k.media.width}x{k.media.height}, {k.media.frames} frames, {k.media.duration_s}s</span>
                  </div>
                  <div class="frames" aria-label="Generated-shot ranges on the clip's frames">
                    {#each k.shots as x (x.id)}
                      <span class="range {x.status}" style:left="{(x.in / k.media.frames) * 100}%" style:width="{((x.out - x.in) / k.media.frames) * 100}%"
                        title="{x.status} frames {x.in}-{x.out}{x.note ? `: ${x.note}` : ''}"></span>
                    {/each}
                  </div>
                  <div class="clip-actions">
                    <button class="ghost" disabled={busy} onclick={() => proposeCuts(k)}>Propose cuts</button>
                    <button class="primary" disabled={busy || !k.shots.length || k.shots.every((x) => x.status === "reviewed")} onclick={() => markShots(k, true)}>
                      <Icon name="check" />Mark ranges reviewed
                    </button>
                    <span class="faint">{k.shots.filter((x) => x.status === "reviewed").length}/{k.shots.length} reviewed</span>
                  </div>
                </div>
              {/each}
            </li>
          {/each}
        </ol>
      </section>
      {/if}

      {#if current === "prompts"}
      <section id="prompts">
        <h2>Prompts</h2>
        <div class="tabs" role="tablist" aria-label="Clip slot">
          {#each seq.clips.filter((c) => c.kind === "generate") as c (c.slot)}
            <button role="tab" aria-selected={promptSlot === c.slot} class:on={promptSlot === c.slot} onclick={() => loadDraft(c.slot)}>{c.slot} {c.title}</button>
          {/each}
        </div>
        {#if slot}
          {@const map = inputMap(slot, packet.characters)}
          <p class="faint">
            Resolves against {Object.entries(map.subjects).map(([n, v]) => `<Subject ${n}> ${v}`).join(", ")}, &lt;Picture 1&gt; {slot.location}, &lt;Audio 1&gt; song.
            Requested {slotDuration(slot)}s.
          </p>
          <div class="editor">
            <div class="editor-main">
              <label for="draft">Prompt for {slot.slot}</label>
              <textarea id="draft" rows="14" bind:value={draft} oninput={scheduleLint} spellcheck="false"></textarea>
              <div class="editor-actions">
                <label class="sr-only" for="draft-name">Prompt name</label>
                <input id="draft-name" bind:value={draftName} />
                <button class="primary" disabled={busy || !draft.trim()} onclick={savePrompt}>Save prompt</button>
              </div>
            </div>
            <aside class="lint" aria-live="polite">
              {#if draftLint}
                <p class:ok-text={draftLint.ok} class:err-text={!draftLint.ok}>
                  {draftLint.ok ? "Structure checks pass" : "Fix before rendering"}
                </p>
                <p class="faint">Renders {draftLint.frames} frames, {draftLint.duration_actual_s}s</p>
                <ul>
                  {#each draftLint.findings as f, i (i)}
                    <li class={f.severity}><strong>{f.code}</strong> {f.message}{#if f.where}<em>"{f.where}"</em>{/if}</li>
                  {/each}
                </ul>
                <p class="faint">Lint checks labels, sections, timing and wording. Creative fidelity and physics are judged in Review.</p>
              {:else}
                <p class="faint">Type or paste a prompt to check it against this slot's inputs.</p>
              {/if}
            </aside>
          </div>
          <h3 class="subhead">Independent interpretations</h3>
          <ul class="interps">
            {#each Object.entries(s.prompts).filter(([, p]) => p.slot === slot.slot) as [name, p] (name)}
              <li>
                <button class="link" onclick={() => { draftName = name; draft = p.text; draftLint = p.lint; }}>{name}</button>
                <span class:ok-text={p.lint.ok} class:err-text={!p.lint.ok}>{p.lint.ok ? "lint clean" : `${p.lint.findings.length} findings`}</span>
                <span class="faint">packet r{p.packet_revision}</span>
              </li>
            {:else}
              <li class="faint">No saved interpretations for this slot.</li>
            {/each}
          </ul>
        {/if}
        <p class="faint">Writer teams: {Object.entries(s.teams).map(([t, v]) => `${t} (${v.model}, ${v.host}, ${v.transport})`).join("; ") || "none registered"}</p>
      </section>
      {/if}

      {#if current === "runs"}
      <section id="runs">
        <h2>Renders</h2>
        {#if !s.runs.length}
          <p class="placeholder">No renders collected yet. Runs are started from presets in SwarmUI's Generate tab; receipts appear here as they complete.</p>
        {:else}
          <table>
            <thead><tr><th>Candidate</th><th>Slot</th><th>Preset</th><th>State</th><th>GPU time</th><th>Peak VRAM</th><th>Checks</th></tr></thead>
            <tbody>
              {#each s.runs as r (r.prompt_id)}
                <tr>
                  <td>{r.label}</td>
                  <td>{r.slot}</td>
                  <td class="wrap">{r.preset}</td>
                  <td><span class="chip {r.status}">{r.status}</span></td>
                  <td class="num">{r.seconds ? `${Math.round(r.seconds)}s` : ""}</td>
                  <td class="num">{r.gpu_peak_mib ? `${(r.gpu_peak_mib / 1024).toFixed(1)} GB` : ""}</td>
                  <td>
                    {#if r.checks}
                      {r.checks.decoded ? "decodes" : "decode failed"}, {r.checks.frames} frames{r.checks.audio ? ", audio" : ""}{r.checks.black_spans.length ? `, ${r.checks.black_spans.length} black` : ""}{r.checks.freeze_spans.length ? `, ${r.checks.freeze_spans.length} frozen` : ""}
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
          <p class="faint">Local renders cost no fee but use GPU time, VRAM and storage: {Math.round(s.runs.reduce((a, r) => a + (r.seconds ?? 0), 0) / 60)} of {packet.allowance.gpu_minutes} GPU minutes used.</p>
        {/if}
      </section>
      {/if}

      {#if current === "review"}
      <section id="review">
        <h2>Review</h2>
        {#if !s.findings.length}
          <p class="placeholder">No reviews saved yet. Reviewers see anonymous candidates and save before any attribution is revealed.</p>
        {:else}
          {#each [...new Set(s.findings.map((f) => f.candidate))] as cand (cand)}
            {@const fs = findingsFor(cand)}
            <article class="review" class:blocked={hardBlocked(s.findings, cand)}>
              <h3>{cand} {#if hardBlocked(s.findings, cand)}<span class="chip hard">identity or Look blocked</span>{/if}</h3>
              {#each ["shot", "clip", "sequence"] as scope}
                {@const scoped = fs.filter((f) => f.scope === scope)}
                {#if scoped.length}
                  <h4>{scope === "shot" ? "Generated shots" : scope === "clip" ? "Whole clip" : "In sequence context"}</h4>
                  <ul>
                    {#each scoped as f (f.id)}
                      <li class="finding {f.kind} {f.severity}">
                        <span class="kind">{f.kind === "brief" ? "brief/action" : f.kind}</span>
                        {#if f.range_s}<span class="num">{clock(f.range_s[0])}-{clock(f.range_s[1])}</span>{/if}
                        <span>{f.text}</span>
                        {#if f.gate}<span class="chip {f.gate_status === 'confirmed' ? 'hard' : 'pending'}">{f.gate} {f.gate_status}</span>{/if}
                        <span class="faint">{f.reviewer.id}, {f.reviewer.access}{f.uncertainty ? `; ${f.uncertainty}` : ""}</span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              {/each}
            </article>
          {/each}
        {/if}
        {#if s.repairs?.length}
          <h3 class="subhead">Repairs</h3>
          <p class="faint">Each repair answers one finding. Edits of existing media use no GPU; re-renders draw on the repair allowance ({s.repair_allowance.remaining} of {s.repair_allowance.repair_renders} left). Approving a repair never replaces the active cut.</p>
          <ul class="repairs">
            {#each s.repairs as r (r.id)}
              <li class="repair {r.status}">
                <span class="chip {r.status === 'applied' || r.status === 'approved' ? 'approved' : r.status === 'rejected' ? 'hard' : 'pending'}">{r.status}</span>
                <strong>{r.id} {r.kind}</strong> on {r.candidate}: {r.scope}
                <span class="faint">{r.rationale}{r.gpu_attempts ? ` (uses ${r.gpu_attempts} render)` : " (no GPU)"}{r.result ? `; result ${r.result}` : ""}</span>
                {#if r.status === "proposed"}
                  <span class="clip-actions">
                    <button class="primary" disabled={busy || (r.gpu_attempts > 0 && s.repair_allowance.remaining < r.gpu_attempts)} onclick={() => decideRepair(r, "approved")}><Icon name="check" />Approve repair</button>
                    <button class="ghost" disabled={busy} onclick={() => decideRepair(r, "rejected")}><Icon name="close" />Reject</button>
                  </span>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </section>
      {/if}

      {#if current === "edit"}
      <section id="edit">
        <h2>Edit and Keep</h2>
        {#if !candidates.length}
          <p class="placeholder">No candidate cut yet. Salvaged ranges and repairs become candidates here; the active cut only changes when you Keep one.</p>
        {:else}
          <div class="tabs" role="tablist" aria-label="Candidate cuts">
            {#each candidates as c (c.id)}
              <button role="tab" aria-selected={shownCandidate?.id === c.id} class:on={shownCandidate?.id === c.id} onclick={() => (candidateView = c.id)}>
                {c.label} <span class="chip {c.status}">{c.id === s.edit.active ? "active" : c.status}</span>
              </button>
            {/each}
          </div>
          {#if shownCandidate}
            <div class="cut">
              {#if shownCandidate.url}
                <!-- svelte-ignore a11y_media_has_caption -->
                <video bind:this={player} src={shownCandidate.url} controls preload="metadata"></video>
              {/if}
              <div class="cut-info">
                {#if shownCandidate.repair_of}<p>Repair of {shownCandidate.repair_of}.</p>{/if}
                {#if shownCandidate.note}<p>{shownCandidate.note}</p>{/if}
                <h4>Segments</h4>
                <ul>
                  {#each shownCandidate.segments as g, i (i)}
                    <li><strong>{g.label}</strong> <span class="num">{clock(g.in_s)}-{clock(g.out_s)}</span> at song <span class="num">{clock(g.song_s)}</span> ({slotOf(g.song_s)?.slot ?? "?"})</li>
                  {/each}
                </ul>
                <h4>Joins</h4>
                <ul>
                  {#each shownCandidate.joins as j, i (i)}
                    <li class="join-row {j.verdict}"><span class="chip {j.verdict === 'valid' ? 'approved' : 'hard'}">{j.verdict}</span> song <span class="num">{clock(j.at_s)}</span>: {j.reasons.join("; ")}</li>
                  {/each}
                </ul>
                <div class="clip-actions">
                  <button class="primary" disabled={busy || shownCandidate.id === s.edit.active || shownCandidate.status === "rejected" || hardBlocked(s.findings, shownCandidate.id) || shownCandidate.joins.some((j) => j.verdict === "unsafe")}
                    onclick={() => editAction(shownCandidate!, "keep")}><Icon name="check" />Keep as active cut</button>
                  <button class="ghost" disabled={busy || shownCandidate.status === "rejected" || shownCandidate.id === s.edit.active} onclick={() => editAction(shownCandidate!, "reject")}><Icon name="close" />Reject</button>
                  {#if shownCandidate.id === s.edit.active && shownCandidate.repair_of}
                    <button class="ghost" disabled={busy} onclick={() => editAction(shownCandidate!, "restore")}><Icon name="undo" />Restore previous cut</button>
                  {/if}
                </div>
                {#if shownCandidate.joins.some((j) => j.verdict === "unsafe")}<p class="warn-text">An unsafe join blocks Keep.</p>{/if}
              </div>
            </div>
          {/if}
        {/if}
      </section>
      {/if}

      {#if current === "export"}
      <section id="export">
        <h2>Export</h2>
        {#if activeCandidate?.url}
          <p>The active cut plays from <a href={activeCandidate.url}>{activeCandidate.label}</a>. The evidence package beside it holds the packet, prompts, receipts, reviews and edit decisions.</p>
        {:else}
          <p class="placeholder">Keep a candidate cut to make it exportable.</p>
        {/if}
      </section>
      {/if}
    {/if}
  </main>
</div>

<style>
  .studio {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    min-height: 100vh;
    font-size: 16px;
    line-height: 1.5;
    --rule: #27272a;
    --text: #f4f4f5;
    --faint: #a1a1aa;
    --rose: #e7a6a6;
  }
  .num {
    font-variant-numeric: tabular-nums;
  }
  .repairs {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 10px;
  }
  .repair {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border: 1px solid var(--rule);
    border-radius: 8px;
  }
  /* Inside the studio's Production view: no full-height page, framed like the embedded Take Review. */
  .studio.embedded {
    min-height: 0;
    border: 1px solid #27272a;
    border-radius: 12px;
    overflow: clip;
    background: var(--ink);
  }
  /* The studio already supplies navigation: drop the inner rail and use the step bar. */
  .studio.embedded {
    grid-template-columns: minmax(0, 1fr);
  }
  .embedded .rail {
    display: none;
  }
  .embedded main {
    padding: 0 22px 28px;
  }
  .embedded .spine {
    margin: 0 -22px;
    padding-inline: 22px;
    position: static;
  }
  .stepbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    padding: 12px 0 4px;
    border-bottom: 1px solid #1d1d20;
  }
  .stepbar .step {
    padding: 8px 12px;
  }
  .step.current {
    background: #1f1f23;
    color: var(--text);
  }
  .bar-gate {
    margin-left: auto;
    color: var(--amber);
    font-size: 0.9em;
  }
  .stepbar button.small {
    margin-top: 0;
  }
  .rail {
    position: sticky;
    top: 0;
    align-self: start;
    max-height: 100vh;
    overflow-y: auto;
    background: var(--surface);
    border-right: 1px solid #202023;
    padding: 28px 14px 20px;
  }
  .rail-head {
    padding: 0 8px 20px;
  }
  h1,
  h2,
  h3,
  h4 {
    font-family: "Manrope", "Segoe UI", sans-serif;
    margin: 0;
    color: var(--text);
    text-wrap: balance;
  }
  h1 {
    font-size: 1.43em;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  h2 {
    font-size: 1.21em;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin-bottom: 14px;
  }
  h3 {
    font-size: 1em;
    font-weight: 600;
  }
  h4 {
    font-size: 0.93em;
    font-weight: 600;
    margin: 14px 0 6px;
    color: var(--muted);
  }
  .sub,
  .faint {
    color: var(--faint);
    font-size: 0.93em;
  }
  .muted {
    color: var(--faint);
  }
  .approval {
    display: flex;
    gap: 8px;
    align-items: center;
    margin: 12px 0 0;
    color: var(--amber);
    font-weight: 600;
  }
  .approval.ok,
  .ok-text {
    color: var(--mint);
  }
  .err-text,
  .warn-text {
    color: var(--amber);
  }
  nav {
    display: grid;
    gap: 2px;
  }
  .step {
    display: flex;
    gap: 10px;
    align-items: center;
    text-align: left;
    padding: 10px 8px;
    border-radius: 8px;
    color: var(--muted);
  }
  .step:hover {
    background: #1f1f23;
    color: var(--text);
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    border: 1.5px solid var(--line);
    flex: none;
  }
  .step.done .dot {
    background: var(--mint);
    border-color: var(--mint);
  }
  .step.open .dot {
    border-color: var(--amber);
  }
  .step.blocked .dot {
    background: var(--amber);
    border-color: var(--amber);
  }
  .gate {
    margin: 18px 8px 0;
    padding-top: 14px;
    border-top: 1px solid var(--rule);
    display: grid;
    gap: 8px;
  }
  .gate p {
    margin: 0;
    color: var(--amber);
    font-size: 0.93em;
  }
  .flash,
  .error {
    margin: 14px 8px 0;
    font-size: 0.93em;
  }
  .flash {
    color: var(--mint);
  }
  .error {
    color: var(--rose);
  }
  main {
    min-width: 0;
    padding: 0 32px 80px;
  }
  section {
    padding: 34px 0 12px;
    border-bottom: 1px solid #1d1d20;
    scroll-margin-top: 150px;
  }
  .lede {
    max-width: 75ch;
    color: var(--muted);
    line-height: 1.55;
    margin: 0 0 18px;
  }
  button.primary,
  button.ghost {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    border-radius: 8px;
    font-weight: 600;
    min-height: 44px;
    white-space: nowrap;
  }
  button.primary {
    background: var(--mint);
    color: var(--ink);
  }
  button.primary:hover:not(:disabled) {
    background: #bcdccd;
  }
  /* Disabled reads as unavailable, not as a faded primary: no fill, dim outline. */
  button.primary:disabled,
  button.ghost:disabled {
    opacity: 1;
    background: transparent;
    border: 1px dashed #3f3f46;
    color: #8b8b94;
  }
  button.ghost {
    border: 1px solid #3f3f46;
    color: var(--text);
  }
  button.ghost:hover:not(:disabled) {
    border-color: var(--line);
    background: #1c1c20;
  }
  button.small {
    min-height: 36px;
    padding: 6px 12px;
    margin-top: 10px;
    font-weight: 500;
  }
  .slot-form {
    display: grid;
    grid-template-columns: 90px minmax(0, 1fr);
    gap: 8px 14px;
    margin-top: 12px;
    max-width: 90ch;
  }
  .slot-form label {
    color: var(--faint);
    padding-top: 10px;
  }
  .slot-form .clip-actions {
    grid-column: 1 / -1;
  }
  button.link {
    color: var(--text);
    text-decoration: underline;
    text-underline-offset: 3px;
    padding: 0;
  }
  .chip {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 0.86em;
    font-weight: 600;
    border: 1px solid #3f3f46;
    color: var(--muted);
  }
  .chip.approved,
  .chip.complete,
  .chip.kept {
    color: var(--mint);
    border-color: #4d6b5f;
  }
  .chip.pending,
  .chip.running,
  .chip.queued,
  .chip.candidate {
    color: var(--amber);
    border-color: #6d5f43;
  }
  .chip.rejected,
  .chip.failed,
  .chip.uncertain {
    color: var(--faint);
  }
  .chip.hard {
    color: var(--rose);
    border-color: #6e4646;
  }

  /* The spine: the passage on song time, pinned while working. */
  .spine {
    position: sticky;
    top: 0;
    z-index: 5;
    background: rgb(16 16 18 / 96%);
    border-bottom: 1px solid var(--rule);
    padding: 16px 0 14px;
    margin: 0 -32px;
    padding-inline: 32px;
  }
  .spine-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 22px;
    color: var(--muted);
    font-size: 0.93em;
    margin-bottom: 10px;
  }
  .lane {
    position: relative;
    height: 46px;
    border-radius: 8px;
    background: #141416;
  }
  .song-lane {
    height: 30px;
    margin-bottom: 6px;
    background: transparent;
  }
  .chunk {
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 1px solid #3f3f46;
    overflow: hidden;
  }
  .chunk em {
    position: absolute;
    left: 6px;
    top: 2px;
    font-style: normal;
    font-size: 0.78em;
    color: var(--faint);
    white-space: nowrap;
  }
  .beat {
    position: absolute;
    bottom: 0;
    width: 3px;
    border-radius: 2px 2px 0 0;
    background: #52525b;
  }
  .beat.flash {
    background: var(--amber);
  }
  .beat.hold {
    background: #3f5a50;
  }
  .cut-lane {
    height: 22px;
    margin-top: 6px;
    background: transparent;
  }
  /* Same vocabulary as the studio's song-section timeline: flat tinted blocks, square ends, name over time. */
  .slot {
    position: absolute;
    top: 0;
    bottom: 0;
    display: grid;
    align-content: center;
    gap: 2px;
    padding: 0 10px;
    border-radius: 0;
    text-align: left;
    overflow: hidden;
    border: 0;
    border-right: 3px solid var(--ink);
    background: rgb(147 51 234 / 14%);
  }
  .slot.supplied {
    background: rgb(99 102 241 / 14%);
  }
  .slot:hover,
  .slot.selected {
    filter: brightness(1.35);
  }
  .slot strong {
    font-family: "Manrope", sans-serif;
    font-size: 0.93em;
  }
  .slot span {
    font-size: 0.82em;
    color: #d4d4d8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .plan-lane {
    border-radius: 0;
    background: transparent;
  }
  .seg {
    position: absolute;
    top: 0;
    bottom: 0;
    border-radius: 5px;
    background: #2a3631;
    color: var(--mint);
    font-size: 0.78em;
    padding: 2px 6px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    border-right: 1px solid #101012;
  }
  .join {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 3px;
    margin-left: -1px;
    border-radius: 2px;
    background: var(--mint);
  }
  .join.unsafe {
    background: var(--rose);
  }

  .characters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 18px 32px;
    margin-bottom: 22px;
  }
  .character p {
    margin: 6px 0 0;
  }
  .kv span {
    color: var(--faint);
    display: inline-block;
    min-width: 64px;
  }
  .look {
    color: var(--muted);
    line-height: 1.5;
    max-width: 75ch;
  }
  .refs {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 1px;
    background: var(--rule);
    border-radius: 12px;
    overflow: hidden;
  }
  .ref {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: 18px;
    padding: 16px;
    background: var(--ink);
  }
  .ref img,
  .noimg {
    width: 220px;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    border-radius: 6px;
    background: #18181b;
    display: grid;
    place-items: center;
    color: var(--faint);
  }
  .ref.rejected img {
    opacity: 0.4;
  }
  .ref-top {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 12px;
    align-items: center;
  }
  .role {
    color: var(--faint);
    font-size: 0.93em;
  }
  .ref-body p {
    margin: 6px 0 0;
    max-width: 80ch;
    line-height: 1.45;
    color: var(--muted);
  }
  .ref-body p.faint {
    color: var(--faint);
  }
  details summary {
    cursor: pointer;
    color: var(--faint);
    margin-top: 6px;
    width: fit-content;
  }
  details summary:hover {
    color: var(--text);
  }
  .ref-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    flex-wrap: wrap;
  }
  .ref-actions input {
    flex: 1 1 220px;
    padding: 8px 10px;
  }

  .slots {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 22px;
  }
  .slot-head {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    align-items: baseline;
  }
  dl {
    display: grid;
    grid-template-columns: 80px minmax(0, 1fr);
    gap: 4px 14px;
    margin: 10px 0 0;
    max-width: 90ch;
  }
  dt {
    color: var(--faint);
  }
  dd {
    margin: 0;
    color: var(--muted);
    line-height: 1.45;
  }
  .placeholder {
    margin: 12px 0 0;
    padding: 12px 14px;
    border: 1px dashed #3f3f46;
    border-radius: 8px;
    color: var(--faint);
    max-width: 80ch;
  }
  .clip {
    margin-top: 14px;
    padding: 12px 14px;
    border-radius: 10px;
    background: #141416;
  }
  .clip-head {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    align-items: baseline;
  }
  .frames {
    position: relative;
    height: 18px;
    margin: 10px 0;
    background: #1d1d21;
    border-radius: 4px;
  }
  .range {
    position: absolute;
    top: 2px;
    bottom: 2px;
    border-radius: 3px;
    border: 1px dashed var(--amber);
  }
  .range.reviewed {
    border: 0;
    background: #4d6b5f;
  }
  .clip-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-top: 10px;
  }

  .tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }
  .tabs button {
    padding: 8px 12px;
    border-radius: 8px;
    color: var(--muted);
    border: 1px solid transparent;
    display: inline-flex;
    gap: 8px;
    align-items: center;
  }
  .tabs button.on {
    border-color: #3f3f46;
    color: var(--text);
    background: #18181b;
  }
  .tabs button:hover:not(.on) {
    color: var(--text);
  }
  .editor {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: 20px;
    margin-top: 10px;
  }
  .editor label {
    display: block;
    color: var(--faint);
    margin-bottom: 6px;
  }
  .editor textarea {
    line-height: 1.5;
    min-height: 320px;
  }
  .editor-actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }
  .lint p {
    margin: 0 0 6px;
  }
  .lint ul {
    list-style: none;
    padding: 0;
    margin: 8px 0;
    display: grid;
    gap: 8px;
  }
  .lint li {
    font-size: 0.93em;
    line-height: 1.4;
    color: var(--muted);
  }
  .lint li strong {
    display: block;
    font-weight: 600;
  }
  .lint li.error strong {
    color: var(--rose);
  }
  .lint li.warning strong {
    color: var(--amber);
  }
  .lint li em {
    display: block;
    color: var(--faint);
    font-style: normal;
  }
  .subhead {
    margin-top: 20px;
  }
  .interps {
    list-style: none;
    padding: 0;
    margin: 8px 0 12px;
    display: grid;
    gap: 6px;
  }
  .interps li {
    display: flex;
    gap: 14px;
    align-items: baseline;
    flex-wrap: wrap;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.93em;
  }
  th {
    text-align: left;
    font-weight: 600;
    color: var(--faint);
    padding: 8px 10px;
    border-bottom: 1px solid var(--rule);
  }
  td {
    padding: 9px 10px;
    border-bottom: 1px solid #1d1d20;
    color: var(--muted);
    vertical-align: top;
  }
  td.wrap {
    max-width: 280px;
    overflow-wrap: anywhere;
  }

  .review {
    padding: 14px 0;
    border-bottom: 1px solid #1d1d20;
  }
  .review.blocked h3 {
    color: var(--rose);
  }
  .review ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 8px;
  }
  .finding {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    color: var(--muted);
    line-height: 1.45;
  }
  .finding .kind {
    min-width: 92px;
    color: var(--faint);
  }
  .finding.major .kind,
  .finding.hard .kind {
    color: var(--amber);
  }

  .cut {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, 1fr);
    gap: 22px;
  }
  .cut video {
    width: 100%;
    border-radius: 10px;
    background: #000;
  }
  .cut-info ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 6px;
    color: var(--muted);
  }
  .join-row {
    line-height: 1.45;
  }

  .empty {
    max-width: 60ch;
  }
  .empty code {
    display: block;
    margin-top: 10px;
    padding: 10px 12px;
    background: #141416;
    border-radius: 8px;
    overflow-x: auto;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  ::selection {
    background: #3a4a43;
    color: var(--text);
  }

  @media (max-width: 900px) {
    .studio {
      grid-template-columns: 1fr;
    }
    .rail {
      position: static;
      max-height: none;
      border-right: 0;
      border-bottom: 1px solid #202023;
    }
    nav {
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    }
    main {
      padding: 0 16px 60px;
    }
    .spine {
      margin: 0 -16px;
      padding-inline: 16px;
    }
    .editor,
    .cut {
      grid-template-columns: 1fr;
    }
    .ref {
      grid-template-columns: 1fr;
    }
    .ref img,
    .noimg {
      width: 100%;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    :global(html) {
      scroll-behavior: auto;
    }
  }
</style>
