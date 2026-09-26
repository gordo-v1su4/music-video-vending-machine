<script lang="ts">
  import Icon, { type IconName } from "$lib/Icon.svelte";
  import { onMount, onDestroy } from "svelte";
  import {
    StudioApi,
    ApiError,
    type SessionInfo,
    type Project,
    type ProjectAction,
    type Asset,
    type Section,
    type Reference,
    type AudioBreak,
  } from "$lib/api";
  import Transport from "$lib/Transport.svelte";
  import { time, videoPosition } from "$lib/timing";
  import { playbackIdentity } from "$lib/playback-identity";
  import "../app.css";

  type View = "Story" | "References" | "Production" | "Review";
  let view = $state<View>("Story");
  const defaultOrigin =
    import.meta.env.VITE_API_ORIGIN || "http://127.0.0.1:5199";
  let origin = $state(defaultOrigin);
  let token = $state("");
  let api = new StudioApi(defaultOrigin);
  let connected = $state(false);
  let session = $state<SessionInfo | null>(null);
  let sessionCheck = false;
  let expiryTimer: ReturnType<typeof setTimeout> | undefined;
  let connectionEpoch = 0;
  let connecting = $state(false);
  let settingsOpen = $state(false);
  let projects = $state<Project[]>([]);
  let project = $state<Project | null>(null);
  let assets = $state<Asset[]>([]);
  let urls = $state<Record<string, string>>({});
  let name = $state("");
  let busy = $state(false);
  let error = $state("");
  let sessionError = $state("");
  let notice = $state("");
  let treatment = $state("");
  let sections = $state<Section[]>([]);
  let audioBreaks = $state<AudioBreak[]>([]);
  let referenceAsset = $state("");
  let referenceName = $state("");
  let referenceRole = $state<Reference["role"]>("inspiration");
  let referenceDescription = $state("");
  let videoMs = $state(0);
  let conflict = $state(false);
  const position = $derived(videoPosition(videoMs, project?.breaks ?? []));
  const currentSection = $derived(
    project?.sections.find(
      (s) => position.songMs >= s.startMs && position.songMs < s.endMs,
    ),
  );
  const masterAsset = $derived(
    assets.find((a) => a.id === project?.master?.assetId),
  );
  const imageAssets = $derived(
    assets.filter((a) => a.mediaType.startsWith("image/")),
  );
  const songAssets = $derived(
    assets.filter((a) => a.mediaType.startsWith("audio/")),
  );
  const candidateCount = $derived(
    project?.revisions.filter((r) => r.status === "candidate").length ?? 0,
  );
  const dirty = $derived(
    !!project &&
      (treatment !== project.treatment ||
        JSON.stringify(sections) !== JSON.stringify(project.sections) ||
        JSON.stringify(audioBreaks) !== JSON.stringify(project.breaks)),
  );
  const approved = $derived(!!project?.productionApproval);
  const sectionLocked = $derived(
    !!project && (project.shots.length > 0 || project.revisions.length > 0),
  );

  function showLibrary() {
    if (dirty || busy) return;
    project = null;
    assets = [];
    videoMs = 0;
    releaseUrls();
    view = "Story";
  }

  function report(e: unknown) {
    error = e instanceof Error ? e.message : "The request failed.";
    if (e instanceof ApiError && e.status === 409) conflict = true;
    if (e instanceof ApiError && e.status === 401) disconnect();
  }
  async function perform(work: () => Promise<void>) {
    if (busy || connecting) return;
    if (!connected) { error = "Sign in before saving. Your unsaved story stays in this window."; return; }
    busy = true;
    error = "";
    notice = "";
    try {
      await work();
    } catch (e) {
      report(e);
    } finally {
      busy = false;
    }
  }
  function disconnect() {
    clearTimeout(expiryTimer);
    sessionError = "";
    connectionEpoch++;
    api.close();
    session = null;
    connected = false;
    settingsOpen = true;
    releaseUrls();
  }
  async function signOut(all = false) {
    if (busy || connecting) return;
    busy = true;
    error = "";
    try {
      await api.signOut(all);
      disconnect();
      notice = "Signed out. Unsaved work stays in this window until you close it.";
    } catch (e) { report(e); }
    finally { busy = false; }
  }
  async function checkSession() {
    if (!connected || !session) return;
    if (sessionCheck) return;
    const client = api;
    sessionCheck = true;
    try {
      await client.currentSession();
      if (client === api) sessionError = "";
    }
    catch (e) {
      if (client === api && connected) {
        if (e instanceof ApiError && e.status === 401) report(e);
        else sessionError = e instanceof Error ? e.message : "Session check failed. Retrying shortly.";
      }
    }
    finally { sessionCheck = false; }
  }
  async function connect() {
    if (connecting || busy) return;
    const address = origin.replace(/\/+$/, "");
    if (dirty && address !== api.origin) {
      error = "Save or discard your story before changing studio servers.";
      return;
    }
    connecting = true;
    error = "";
    const epoch = ++connectionEpoch;
    const bootstrap = token;
    token = "";
    let next: StudioApi | undefined;
    try {
      next = await StudioApi.connect(address, bootstrap);
      const list = await next.projects();
      if (epoch !== connectionEpoch) { next.close(); return; }
      const sameStudio = address === api.origin;
      api.close();
      releaseUrls();
      if (!sameStudio) { project = null; assets = []; videoMs = 0; }
      api = next;
      session = next.session;
      clearTimeout(expiryTimer);
      if (session) expiryTimer = setTimeout(() => void checkSession(), next.sessionRemainingMs());
      projects = list;
      connected = true;
      sessionError = "";
      settingsOpen = false;
      notice = "Connected to your studio.";
      // Preserve the old revision and local draft; stale saves still conflict.
      if (project) await loadMedia(assets);
    } catch (e) {
      next?.close();
      if (epoch === connectionEpoch) {
        if (!connected || next === api) { disconnect(); report(e); }
        else error = e instanceof Error ? e.message : "Could not connect to the proposed studio. Your existing connection is still available.";
      }
    } finally {
      connecting = false;
    }
  }
  function releaseUrls() {
    Object.values(urls).forEach((url) => URL.revokeObjectURL(url));
    urls = {};
  }
  function replaceProject(saved: Project) {
    if (!project || playbackIdentity(project) !== playbackIdentity(saved))
      videoMs = 0;
    project = saved;
  }
  function adopt(saved: Project) {
    replaceProject(saved);
    treatment = saved.treatment;
    sections = saved.sections.map((s) => ({ ...s }));
    audioBreaks = saved.breaks.map((b) => ({ ...b }));
    projects = [...projects.filter((p) => p.id !== saved.id), saved];
    conflict = false;
  }
  async function loadMedia(list: Asset[]) {
    const client = api;
    const epoch = connectionEpoch;
    const results = await Promise.allSettled(
      list
        .filter(
          (a) =>
            !urls[a.id] &&
            (a.mediaType.startsWith("audio/") ||
              a.mediaType.startsWith("image/")),
        )
        .map(async (a) => ({ id: a.id, url: await client.blob(a) })),
    );
    for (const result of results) {
      if (epoch !== connectionEpoch || !connected) {
        if (result.status === "fulfilled") URL.revokeObjectURL(result.value.url);
        continue;
      }
      if (result.status === "fulfilled")
        urls = { ...urls, [result.value.id]: result.value.url };
      else if (result.reason instanceof ApiError && result.reason.status === 401) report(result.reason);
      else error = "Some imported media could not be previewed. Reload the project to retry.";
    }
  }
  async function openProject(id: string) {
    await perform(async () => {
      const [saved, list] = await Promise.all([
        api.project(id),
        api.assets(id),
      ]);
      if (project?.id !== saved.id) releaseUrls();
      adopt(saved);
      assets = list;
      await loadMedia(list);
    });
  }
  async function createProject() {
    if (!name.trim()) return;
    await perform(async () => {
      const saved = await api.create(name.trim());
      releaseUrls();
      assets = [];
      adopt(saved);
      name = "";
    });
  }
  async function action(
    value: ProjectAction,
    message = "Saved to your project.",
  ) {
    if (!project) return;
    await perform(async () => {
      if (project) adopt(await api.action(project, value));
      notice = message;
    });
  }
  async function saveStory() {
    if (!project) return;
    await perform(async () => {
      if (!project) return;
      // Keep local drafts through sequential revision-aware saves and partial failures.
      let saved = project;
      if (treatment !== saved.treatment) {
        saved = await api.action(saved, {
          type: "setTreatment",
          text: treatment,
        });
        replaceProject(saved);
      }
      if (JSON.stringify(sections) !== JSON.stringify(saved.sections)) {
        saved = await api.action(saved, { type: "setSections", sections });
        replaceProject(saved);
      }
      if (JSON.stringify(audioBreaks) !== JSON.stringify(saved.breaks)) {
        saved = await api.action(saved, {
          type: "setBreaks",
          breaks: audioBreaks,
        });
        replaceProject(saved);
      }
      adopt(saved);
      notice = "Story saved. Production approval reflects the saved inputs.";
    });
  }
  async function importFiles(files: FileList | null) {
    if (!files || !project) return;
    await perform(async () => {
      for (const file of Array.from(files)) {
        const asset = await api.upload(project!.id, file);
        assets = [...assets, asset];
        await loadMedia([asset]);
      }
      notice = "Original files imported and preserved.";
    });
  }
  function addSection() {
    if (!project?.master || sectionLocked) return;
    const startMs = sections.at(-1)?.endMs ?? 0;
    const endMs = project?.master?.durationMs ?? startMs + 30000;
    sections = [
      ...sections,
      {
        id: crypto.randomUUID(),
        name: `Section ${sections.length + 1}`,
        startMs,
        endMs: Math.max(startMs + 1000, endMs),
        intent: "",
      },
    ];
  }
  async function addReference() {
    if (!referenceAsset || !referenceName.trim()) return;
    await action(
      {
        type: "addReference",
        reference: {
          id: crypto.randomUUID(),
          assetId: referenceAsset,
          name: referenceName.trim(),
          role: referenceRole,
          description: referenceDescription,
        },
      },
      "Reference added to the story.",
    );
    if (!error) {
      referenceName = "";
      referenceDescription = "";
      referenceAsset = "";
    }
  }
  function addBreak() {
    audioBreaks = [
      ...audioBreaks,
      {
        id: crypto.randomUUID(),
        kind: "insertion",
        songStartMs: 0,
        durationMs: 3000,
        assetId: null,
      },
    ];
  }
  onMount(() => {
    void connect();
    const timer = setInterval(() => void checkSession(), 15000);
    return () => clearInterval(timer);
  });
  onDestroy(() => { clearTimeout(expiryTimer); connectionEpoch++; api.close(); releaseUrls(); });
</script>

<svelte:head
  ><title>{project ? `${project.name} — ` : ""}Music Vending Machine</title
  ><meta
    name="description"
    content="A private studio for turning a song and a story into a narrative music video."
  /></svelte:head
>

<a class="skip-link" href="#studio-content">Skip to workspace</a>
<div class="studio-shell">
  <aside class="sidebar">
    <button
      onclick={showLibrary}
      disabled={dirty || busy}
      class="brand"
      aria-label="Music Vending Machine project library"
      ><span class="brand-icon" aria-hidden="true">m<span>v</span>m</span><span
        >Music Vending<br />Machine</span
      ></button
    >
    <div class="project-switcher">
      <label for="project-select">Your studio</label>
      <select
        id="project-select"
        value={project?.id ?? ""}
        disabled={!connected || busy || dirty}
        onchange={(e) => {
          if (e.currentTarget.value) void openProject(e.currentTarget.value);
        }}
      >
        <option value="">Choose a project</option>
        {#each projects as item (item.id)}<option value={item.id}
            >{item.name}</option
          >{/each}
      </select>
      {#if dirty}<small>Save story edits before switching.</small>{/if}
      {#if project}<button
          class="quiet full"
          disabled={dirty || busy}
          onclick={showLibrary}>+ New project</button
        >{/if}
    </div>
    <nav aria-label="Studio views">
      {#each ["Story", "References", "Production", "Review"] as item, i (item)}
        <button
          class:active={view === item}
          aria-current={view === item ? "page" : undefined}
          onclick={() => (view = item as View)}
          ><span class="nav-glyph" aria-hidden="true"
            ><Icon
              name={(["story", "image", "production", "review"] as IconName[])[
                i
              ]}
            /></span
          >{item}{#if item === "Review" && candidateCount}<span
              class="nav-count">{candidateCount}</span
            >{/if}</button
        >
      {/each}
    </nav>
    <div class="sidebar-note">
      <span class="little-orbit" aria-hidden="true"></span>
      <p>A song is the beginning.<br />The story is yours.</p>
    </div>
    <button
      class="connection"
      aria-expanded={settingsOpen || !connected}
      aria-controls="connection-settings"
      onclick={() => (settingsOpen = !settingsOpen)}
      ><span class:connected class="dot"></span>{connected
        ? "Studio connected"
        : "Connect your studio"}<span aria-hidden="true"
        ><Icon name="settings" /></span
      ></button
    >
  </aside>

  <main id="studio-content" tabindex="-1">
    <header class="topbar">
      <div>
        <span class="breadcrumb"
          >{project?.name ?? "Your next music video"}</span
        ><span class="crumb-slash">/</span><strong>{view}</strong>
      </div>
      <div class="topbar-actions">
        {#if project}<span class="revision">Revision {project.revision}</span
          ><button
            class="quiet"
            disabled={!connected || connecting || busy || dirty}
            onclick={() => openProject(project!.id)}>Reload saved</button
          >{/if}<span class="private-badge">Private studio</span>
      </div>
    </header>
    {#if error || sessionError}<div class="banner error" role="alert">
        <span>{error || sessionError}</span>{#if conflict && project}<button
            onclick={() => openProject(project!.id)}
            >Discard drafts & reload</button
          >{/if}<button
          class="dismiss"
          aria-label="Dismiss error"
          onclick={() => { error = ""; sessionError = ""; }}><Icon name="close" size={18} /></button
        >
      </div>{/if}
    {#if notice}<div class="banner success" role="status">
        {notice}<button
          class="dismiss"
          aria-label="Dismiss notification"
          onclick={() => (notice = "")}><Icon name="close" size={18} /></button
        >
      </div>{/if}

    {#if settingsOpen || !connected}
      <section class="connection-panel" id="connection-settings">
        <div>
          <h2>Connect to your studio</h2>
          <p>Use the address of your private music-video server.</p>
        </div>
        <form
          onsubmit={(e) => {
            e.preventDefault();
            void connect();
          }}
        >
          <label
            >Server address<input
              type="url"
              bind:value={origin}
              required
            /></label
          ><label
            >Studio access key<input
              type="password"
              bind:value={token}
              autocomplete="off"
              placeholder="Required outside local development"
            /></label
          ><button class="primary" disabled={connecting || busy}
            >{connecting ? "Connecting…" : "Connect studio"}</button
          >
        </form>
        <small>Your access key creates a 12-hour session. Credentials stay in memory and are cleared when you close this window.</small>
        {#if connected}
          <div class="session-controls">
            <p>{session ? `Signed in until ${new Date(session.expiresAt).toLocaleString()}.` : "Connected to local development."}</p>
            <button disabled={busy || connecting} onclick={() => void signOut()}>Sign out</button>
            {#if session}<button disabled={busy || connecting} onclick={() => void signOut(true)}>Sign out all devices</button>{/if}
          </div>
        {/if}
      </section>
    {/if}

    {#if !project}
      <div class="welcome">
        <div class="welcome-copy">
          <h1>Let your song<br />become a story.</h1>
          <p>
            Bring in a track. Find its characters, places, and moments. Shape a
            film around what you hear.
          </p>
          <form
            class="create-form"
            onsubmit={(e) => {
              e.preventDefault();
              void createProject();
            }}
          >
            <label for="project-name">Start a new film</label>
            <div>
              <input
                id="project-name"
                bind:value={name}
                placeholder="Give your project a name"
                required
                maxlength="160"
                disabled={!connected || busy}
              /><button
                class="primary"
                disabled={!connected || busy || !name.trim()}
                >Create project</button
              >
            </div>
          </form>
          {#if !connected}<p class="subtle">
              Connect your studio above to create or open a project.
            </p>{/if}
        </div>
        <div class="welcome-frame" aria-hidden="true">
          <div class="frame-inner">
            <span class="frame-corner tl"></span><span class="frame-corner tr"
            ></span><span class="frame-corner bl"></span><span
              class="frame-corner br"
            ></span>
            <div class="light-beam"></div>
            <span class="frame-poem"
              >Every song<br />has a world<br />inside it.</span
            ><span class="frame-caption"
              >A canvas waiting for your first frame</span
            >
          </div>
          <div class="film-leader">
            <span></span><span></span><span></span><span></span><span
            ></span><span></span><span></span><span></span>
          </div>
        </div>
      </div>
      {#if connected && projects.length}<section class="recent-projects">
          <h2>Continue a film</h2>
          <div>
            {#each projects as item (item.id)}<button
                onclick={() => openProject(item.id)}
                disabled={busy}
                ><span class="project-thumb" aria-hidden="true"
                  ><Icon name="story" /></span
                ><strong>{item.name}</strong><span class="subtle"
                  >Revision {item.revision}</span
                ><span aria-hidden="true"><Icon name="arrow" /></span></button
              >{/each}
          </div>
        </section>{/if}
    {:else}
      <div class="workspace">
        <section class="canvas-column">
          <div class="view-heading">
            <div>
              <h1>
                {view === "Story"
                  ? "The world of your song"
                  : view === "References"
                    ? "Find your visual language"
                    : view === "Production"
                      ? "From intention to footage"
                      : "Make every moment count"}
              </h1>
              <p>
                {view === "Story"
                  ? "A living treatment, one scene at a time."
                  : view === "References"
                    ? "Give the story faces, places, and a point of view."
                    : view === "Production"
                      ? "Approved inputs. Local generation. Visible progress."
                      : "Compare candidates before changing your active cut."}
              </p>
            </div>
            {#if view === "Story"}<div class="button-row">
                {#if dirty}<button
                    class="quiet"
                    disabled={busy}
                    onclick={() => {
                      if (project) adopt(project);
                    }}>Discard drafts</button
                  >{/if}<button
                  class="primary"
                  disabled={!connected || connecting || busy || !dirty || conflict}
                  onclick={saveStory}>{busy ? "Saving…" : "Save story"}</button
                >
              </div>{/if}
          </div>
          {#if view === "Story"}
            <div class="story-canvas">
              <article class="treatment-paper">
                <div class="paper-heading">
                  <span class="paper-icon" aria-hidden="true"
                    ><Icon name="story" /></span
                  >
                  <h2>Treatment</h2>
                  <span class="subtle"
                    >{dirty
                      ? "Unsaved changes"
                      : "Saved with your project"}</span
                  >
                </div>
                <label class="sr-only" for="treatment">Story treatment</label
                ><textarea
                  id="treatment"
                  bind:value={treatment}
                  placeholder="What happens in this film? Start with a character, a place, or a feeling. Describe the journey the song takes us on."
                  rows="7"></textarea>
                <div class="paper-foot">
                  <span>Your direction stays in your hands.</span><span
                    class="subtle"
                    >{treatment.trim().split(/\s+/).filter(Boolean).length} words</span
                  >
                </div>
              </article>
              <div class="section-heading">
                <h2>Story sections</h2>
                <button
                  class="quiet"
                  onclick={addSection}
                  disabled={busy || !project.master || sectionLocked}
                  >+ Add section</button
                >
              </div>
              {#if sectionLocked}<p class="small-note">
                  Section editing is locked once footage or revisions exist in
                  this release.
                </p>{/if}
              <div class="section-grid">
                {#each sections as section, i (section.id)}<article
                    class="section-card"
                  >
                    <div class="section-card-top">
                      <span class="section-number"
                        >{String(i + 1).padStart(2, "0")}</span
                      ><label class="sr-only" for={`section-${section.id}`}
                        >Section name</label
                      ><input
                        id={`section-${section.id}`}
                        bind:value={section.name}
                        disabled={sectionLocked}
                        placeholder="Section name"
                      /><button
                        class="icon-button"
                        aria-label={`Remove ${section.name}`}
                        disabled={sectionLocked}
                        onclick={() =>
                          (sections = sections.filter(
                            (s) => s.id !== section.id,
                          ))}><Icon name="close" size={18} /></button
                      >
                    </div>
                    <div class="section-times">
                      <label
                        >Start (seconds)<input
                          type="number"
                          min="0"
                          step="0.001"
                          value={section.startMs / 1000}
                          disabled={sectionLocked}
                          oninput={(e) =>
                            (section.startMs = Math.round(
                              Number(e.currentTarget.value) * 1000,
                            ))}
                        /></label
                      ><label
                        >End (seconds)<input
                          type="number"
                          min="0"
                          step="0.001"
                          value={section.endMs / 1000}
                          disabled={sectionLocked}
                          oninput={(e) =>
                            (section.endMs = Math.round(
                              Number(e.currentTarget.value) * 1000,
                            ))}
                        /></label
                      >
                    </div>
                    <label class="sr-only" for={`intent-${section.id}`}
                      >Section story intention</label
                    ><textarea
                      id={`intent-${section.id}`}
                      rows="3"
                      bind:value={section.intent}
                      disabled={sectionLocked}
                      placeholder="What changes in this moment?"></textarea>
                    <div class="section-state">
                      <span class="dot amber"></span>Awaiting footage
                    </div>
                  </article>{:else}<div class="empty-inline">
                    <p>
                      Give the song a beginning, a turning point, and somewhere
                      to arrive.
                    </p>
                    {#if !project.master}<p>
                        Import and select a song master before timing your
                        sections.
                      </p>{/if}
                    <button
                      class="quiet"
                      onclick={addSection}
                      disabled={!project.master || sectionLocked}
                      >Add the first section</button
                    >
                  </div>{/each}
              </div>
              <details class="breaks">
                <summary
                  >Dramatic audio breaks <span
                    >{audioBreaks.length
                      ? `${audioBreaks.length} planned`
                      : "Optional"}</span
                  ></summary
                >
                <p>
                  Insert pauses the song and extends the film. Cutout mutes the
                  song while its time continues.
                </p>
                {#each audioBreaks as item (item.id)}<div class="break-row">
                    <label
                      >Behavior<select bind:value={item.kind}
                        ><option value="insertion">Insert pause</option><option
                          value="cutout">Mute interval</option
                        ></select
                      ></label
                    ><label
                      >Song start (s)<input
                        type="number"
                        min="0"
                        value={item.songStartMs / 1000}
                        oninput={(e) =>
                          (item.songStartMs = Math.round(
                            Number(e.currentTarget.value) * 1000,
                          ))}
                      /></label
                    ><label
                      >Duration (s)<input
                        type="number"
                        min="0.001"
                        step="0.001"
                        value={item.durationMs / 1000}
                        oninput={(e) =>
                          (item.durationMs = Math.round(
                            Number(e.currentTarget.value) * 1000,
                          ))}
                      /></label
                    ><label
                      >Dialogue / SFX<select bind:value={item.assetId}
                        ><option value={null}>Silence</option
                        >{#each songAssets as asset (asset.id)}<option
                            value={asset.id}>{asset.name}</option
                          >{/each}</select
                      ></label
                    ><button
                      class="icon-button"
                      aria-label="Remove audio break"
                      onclick={() =>
                        (audioBreaks = audioBreaks.filter(
                          (b) => b.id !== item.id,
                        ))}><Icon name="close" size={18} /></button
                    >
                  </div>{/each}<button class="quiet" onclick={addBreak}
                  >+ Add audio break</button
                >
              </details>
            </div>
          {:else if view === "References"}
            <div class="reference-grid">
              {#each project.references as reference (reference.id)}<article
                  class="reference-card"
                >
                  {#if urls[reference.assetId]}<img
                      loading="lazy"
                      decoding="async"
                      src={urls[reference.assetId]}
                      alt={reference.description || reference.name}
                    />{:else}<div class="reference-placeholder">
                      Reference media unavailable
                    </div>{/if}
                  <div>
                    <span class="tag"
                      >{reference.role === "exact"
                        ? "Exact constraint"
                        : "Inspiration"}</span
                    >
                    <h2>{reference.name}</h2>
                    <p>{reference.description}</p>
                  </div>
                </article>{:else}<div class="empty-inline spacious">
                  <span aria-hidden="true"><Icon name="image" /></span>
                  <h2>Build a shared visual memory.</h2>
                  <p>
                    Import images, then name the characters, locations, and
                    details they should guide.
                  </p>
                </div>{/each}
            </div>
            <form
              class="reference-form panel"
              onsubmit={(e) => {
                e.preventDefault();
                void addReference();
              }}
            >
              <h2>Add a reference</h2>
              <div class="form-pair">
                <label
                  >Imported image<select bind:value={referenceAsset} required
                    ><option value="">Choose an image</option
                    >{#each imageAssets as asset (asset.id)}<option
                        value={asset.id}>{asset.name}</option
                      >{/each}</select
                  ></label
                ><label
                  >Identity or name<input
                    bind:value={referenceName}
                    required
                    placeholder="A character, place, or visual idea"
                  /></label
                >
              </div>
              <label
                >How should it guide the film?<select bind:value={referenceRole}
                  ><option value="inspiration"
                    >Inspiration — a visual direction</option
                  ><option value="exact"
                    >Exact constraint — preserve these details</option
                  ></select
                ></label
              ><label
                >What matters in this reference?<textarea
                  bind:value={referenceDescription}
                  rows="2"
                  placeholder="Describe the details to carry into the story."
                ></textarea></label
              ><button
                class="primary"
                disabled={!connected || connecting || busy ||
                  dirty ||
                  !referenceAsset ||
                  !referenceName.trim()}>Add reference</button
              >{#if dirty}<p class="subtle">
                  Save your story edits before adding a reference.
                </p>{/if}
            </form>
          {:else if view === "Production"}
            <article class="panel approval-panel">
              <div class="section-heading">
                <h2>Production approval</h2>
                <span class:approved class="status-pill"
                  >{approved ? "Approved inputs" : "Approval needed"}</span
                >
              </div>
              <p>
                Approve the exact saved inputs below. Editing them will require
                a fresh approval.
              </p>
              <dl class="approval-details">
                <div>
                  <dt>Song master</dt>
                  <dd>
                    {masterAsset?.name ?? "Choose a master"}{project.master
                      ?.approved
                      ? " · Approved"
                      : ""}
                  </dd>
                </div>
                <div>
                  <dt>Treatment</dt>
                  <dd>
                    {project.treatment.trim()
                      ? `${project.treatment.length} characters saved`
                      : "Write the treatment"}
                  </dd>
                </div>
                <div>
                  <dt>Structure</dt>
                  <dd>
                    {project.sections.length} sections / {project.references
                      .length} references / {project.breaks.length} audio breaks
                  </dd>
                </div>
                <div>
                  <dt>Generation route</dt>
                  <dd>Local only. No paid fallback.</dd>
                </div>
                <div>
                  <dt>Resource allowance</dt>
                  <dd>Up to 3 attempts per shot, including replacements.</dd>
                </div>
              </dl>
              <button
                class="primary"
                disabled={!connected || connecting || busy ||
                  dirty ||
                  approved ||
                  !project.master?.approved ||
                  !project.treatment.trim() ||
                  !project.sections.length}
                onclick={() =>
                  action(
                    { type: "approveProduction", localAttemptsPerShot: 3 },
                    "Production inputs approved. Generation requires a verified local worker.",
                  )}
                >{approved
                  ? "Inputs approved"
                  : "Approve these production inputs"}</button
              >{#if dirty}<p class="subtle">
                  Save story edits before approving production.
                </p>{/if}
            </article>
            <article class="panel capability-panel">
              <span class="capability-symbol" aria-hidden="true"
                ><Icon name="production" /></span
              >
              <div>
                <h2>Generation is not connected yet</h2>
                <p>
                  The local image and video workflows must pass a real
                  generation check before this studio can submit production.
                  Your approvals are saved; no generation has been submitted.
                </p>
                <span class="tag"
                  >Qwen and MiniMax H3 awaiting verification</span
                >
              </div>
            </article>
            {#if project.shots.length}<h2>Shot coverage</h2>
              <div class="shot-list">
                {#each project.shots as shot (shot.id)}<article
                    class="shot-row"
                  >
                    <div>
                      <strong>{shot.intent || "Untitled shot"}</strong><small
                        >{time(shot.startMs)}–{time(shot.endMs)} · {shot.attempts}/3
                        attempts</small
                      >
                    </div>
                    <span class="tag">{shot.status}</span><button
                      class="quiet"
                      disabled={!connected || connecting || busy || dirty}
                      onclick={() =>
                        action({
                          type: "pinShot",
                          shotId: shot.id,
                          pinned: !shot.pinned,
                        })}>{shot.pinned ? "Unpin shot" : "Pin shot"}</button
                    >
                  </article>{/each}
              </div>{/if}
          {:else}
            <article class="panel review-summary">
              <div>
                <h2>
                  {candidateCount
                    ? `${candidateCount} candidate${candidateCount === 1 ? "" : "s"} to consider`
                    : "Room for a better cut"}
                </h2>
                <p>
                  Candidates stay separate until you choose Keep. Your active
                  edit remains safe.
                </p>
              </div>
              <span class="review-ring" aria-hidden="true"
                ><Icon name="review" /></span
              >
            </article>
            {#each project.revisions as revision (revision.id)}<article
                class="panel revision-card"
              >
                <div class="section-heading">
                  <h2>{revision.label}</h2>
                  <span class="tag">{revision.status}</span>
                </div>
                <p>
                  {revision.shots.length} shots · {revision.shots.filter(
                    (s) => s.pinned,
                  ).length} pinned · {revision.shots.filter(
                    (s) => s.status === "gap",
                  ).length} gaps
                </p>
                {#if revision.status === "candidate"}<div class="button-row">
                    <button
                      class="primary"
                      disabled={!connected || connecting || busy || dirty}
                      onclick={() =>
                        action(
                          { type: "keepRevision", revisionId: revision.id },
                          "Candidate kept as the active cut.",
                        )}>Keep candidate</button
                    ><button
                      class="quiet"
                      disabled={!connected || connecting || busy || dirty}
                      onclick={() =>
                        action({
                          type: "rejectRevision",
                          revisionId: revision.id,
                        })}>Reject</button
                    >
                  </div>{:else if revision.status === "archived"}<button
                    class="quiet"
                    disabled={!connected || connecting || busy || dirty}
                    onclick={() =>
                      action(
                        { type: "restoreRevision", revisionId: revision.id },
                        "Restored as a new candidate. Choose Keep to make it active.",
                      )}>Restore as candidate</button
                  >{/if}
              </article>{:else}<div class="empty-inline spacious">
                <span aria-hidden="true"><Icon name="production" /></span>
                <h2>Your first cut will arrive here.</h2>
                <p>
                  Generate and assemble footage before comparing revisions. No
                  review or technical checks have run yet.
                </p>
              </div>{/each}
            <div class="export-note">
              <h2>Finished export</h2>
              <p>
                Export becomes available when the selected range has accepted
                footage and passing technical checks. This project currently
                provides a timed story preview.
              </p>
              <span class="tag">1280 × 720 · 24 fps · H.264 / AAC</span>
            </div>
          {/if}
        </section>

        <aside class="inspector">
          <div class="preview-heading">
            <h2>Preview</h2>
            <span class="tag">Story placeholder</span>
          </div>
          <div class="preview-frame">
            <div class="preview-corners" aria-hidden="true"></div>
            <span class="preview-symbol" aria-hidden="true"
              ><Icon name="production" /></span
            ><strong>{currentSection?.name ?? "Your film starts here"}</strong>
            <p>
              {currentSection?.intent ||
                "Add story sections to preview their intentions alongside the song."}
            </p>
            <small>Unrendered story frame</small>
          </div>
          <section class="master-panel">
            <div class="section-heading">
              <h2>Song master</h2>
              {#if project.master?.approved}<span
                  class="dot connected"
                  title="Approved"
                ></span>{/if}
            </div>
            {#if masterAsset}<strong class="filename">{masterAsset.name}</strong
              >
              <p class="subtle">
                {time(project.master?.durationMs ?? 0)} · {project.master
                  ?.approved
                  ? "Approved master"
                  : "Awaiting your approval"}
              </p>{:else}<p>
                Import your song, then choose the recording this film will
                follow.
              </p>{/if}<label class="sr-only" for="master-select"
              >Choose song master</label
            ><select
              id="master-select"
              value={project.master?.assetId ?? ""}
              disabled={!connected || connecting || busy || dirty || project.revisions.length > 0}
              onchange={(e) => {
                const asset = assets.find(
                  (a) => a.id === e.currentTarget.value,
                );
                if (asset && asset.durationMs)
                  void action({
                    type: "setMaster",
                    assetId: asset.id,
                    durationMs: asset.durationMs,
                  });
              }}
              ><option value="">Select imported audio</option
              >{#each songAssets as asset (asset.id)}<option
                  value={asset.id}
                  disabled={!asset.durationMs}
                  >{asset.name}{!asset.durationMs
                    ? " (duration unavailable)"
                    : ""}</option
                >{/each}</select
            >{#if project.master && !project.master.approved}<button
                class="primary full"
                disabled={!connected || connecting || busy || dirty}
                onclick={() =>
                  action(
                    { type: "approveMaster" },
                    "Song approved as the production master.",
                  )}>Approve this master</button
              >{/if}
            <p class="small-note">
              Beat analysis and automatic section detection are not connected
              yet.
            </p>
          </section>
          <section class="asset-panel">
            <div class="section-heading">
              <h2>Source files</h2>
              <span class="subtle">{assets.length}</span>
            </div>
            <label class="import-zone" class:disabled={!connected || connecting || busy}
              ><input
                type="file"
                accept=".png,.jpg,.jpeg,.webp,.wav,.mp3,.flac,.ogg,.mp4,.webm,.mov"
                multiple
                disabled={!connected || connecting || busy}
                onchange={(e) => {
                  void importFiles(e.currentTarget.files);
                  e.currentTarget.value = "";
                }}
              /><span aria-hidden="true"><Icon name="upload" /></span><strong
                >{busy ? "Working…" : "Import files"}</strong
              ><small>Audio, images, or clips · 128 MiB per file</small></label
            >
            <div class="asset-list">
              {#each assets as asset (asset.id)}<div class="asset">
                  <span class="asset-type"
                    ><Icon
                      name={asset.mediaType.startsWith("audio/")
                        ? "audio"
                        : asset.mediaType.startsWith("image/")
                          ? "image"
                          : "story"}
                    /></span
                  >
                  <div>
                    <strong title={asset.name}>{asset.name}</strong><small
                      >{(asset.sizeBytes / 1024 / 1024).toFixed(1)} MB · Original
                      preserved</small
                    >
                  </div>
                </div>{/each}
            </div>
            <small class="small-note"
              >Audio stems remain source files until alignment is verified. MIDI
              and lyrics intake are not available yet.</small
            >
          </section>
        </aside>
      </div>
      <!-- Only project/audio mapping changes replace playback. Story, reference,
           approval and pin saves keep the active media session and playhead. -->
      {#key playbackIdentity(project)}<Transport
          {project}
          {urls}
          bind:videoMs
        />{/key}
    {/if}
  </main>
</div>
