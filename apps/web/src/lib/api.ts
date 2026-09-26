import type { components } from "./generated/api";
export type SessionInfo = components["schemas"]["SessionInfo"];
export type Section = components["schemas"]["Section"];
export type Reference = components["schemas"]["Reference"];
export type AudioBreak = components["schemas"]["AudioBreak"];
export type Shot = components["schemas"]["Shot"];
export type EditRevision = components["schemas"]["EditRevision"];
export type Project = components["schemas"]["Project"];
export type Asset = components["schemas"]["Asset"];
export type ProjectAction = components["schemas"]["Action"];
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Credentials live only in this object, never URLs or persistent browser storage. */
export class StudioApi {
  session: SessionInfo | null = null;
  private controller = new AbortController();
  private closed = false;
  close() {
    this.token = "";
    this.session = null;
    this.closed = true;
    this.controller.abort();
  }
  static async connect(origin: string, bootstrap: string): Promise<StudioApi> {
    const client = new StudioApi(origin);
    try {
      const health = await client.request<{ sessionRequired: boolean }>("/health");
      if (health.sessionRequired) {
        // A separate, short-lived client prevents the bootstrap key reaching project routes.
        const login = new StudioApi(origin, bootstrap);
        try {
          const grant = await login.request<components["schemas"]["SessionGrant"]>("/sessions", {
            method: "POST", body: JSON.stringify({ clientLabel: "Music Vending Machine workspace" }),
          });
          client.token = grant.token;
          client.session = grant.session;
        } finally { login.close(); }
      }
      return client;
    } catch (error) { client.close(); throw error; }
  }
  currentSession() { return this.request<SessionInfo | null>("/sessions/current"); }
  async signOut(all = false) {
    if (this.session) await this.request(all ? "/sessions/revoke-all" : "/sessions/current/revoke", { method: "POST" });
    this.close();
  }
  constructor(
    public origin: string,
    private token = "",
  ) {
    this.origin = origin.replace(/\/+$/, "");
  }
  private headers(): Headers {
    return new Headers(
      this.token ? { Authorization: `Bearer ${this.token}` } : {},
    );
  }
  private requireSession() {
    if (this.session && Date.now() >= Date.parse(this.session.expiresAt)) this.close();
    if (this.closed) throw new ApiError(401, "Sign in to continue.");
  }
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    this.requireSession();
    const headers = this.headers();
    if (options.body && !(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    let response: Response;
    try {
      response = await fetch(`${this.origin}/api/v1${path}`, {
        ...options,
        headers,
        redirect: "error",
        cache: "no-store",
        signal: this.controller.signal,
      });
    } catch {
      throw new Error(
        "The studio server could not be reached. Check its address and connection.",
      );
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message =
        typeof body.error === "string"
          ? body.error
          : typeof body.message === "string"
            ? body.message
            : `Request failed (${response.status}).`;
      throw new ApiError(
        response.status,
        response.status === 409
          ? "This project changed in another window. Reload the saved project before applying your edits."
          : message,
      );
    }
    const result: T = await response.json();
    this.requireSession();
    return result;
  }
  projects() {
    return this.request<Project[]>("/projects");
  }
  create(name: string) {
    return this.request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }
  project(id: string) {
    return this.request<Project>(`/projects/${encodeURIComponent(id)}`);
  }
  assets(id: string) {
    return this.request<Asset[]>(`/projects/${encodeURIComponent(id)}/assets`);
  }
  action(project: Project, action: ProjectAction) {
    return this.request<Project>(
      `/projects/${encodeURIComponent(project.id)}/actions`,
      {
        method: "POST",
        body: JSON.stringify({ expectedRevision: project.revision, action }),
      },
    );
  }
  upload(id: string, file: File) {
    const data = new FormData();
    data.set("file", file);
    return this.request<Asset>(`/projects/${encodeURIComponent(id)}/assets`, {
      method: "POST",
      body: data,
    });
  }
  async blob(asset: Asset): Promise<string> {
    const url = new URL(asset.url, this.origin);
    if (url.origin !== new URL(this.origin).origin)
      throw new Error("Media address does not belong to this studio server.");
    this.requireSession();
    const response = await fetch(url, { headers: this.headers(), redirect: "error", cache: "no-store", signal: this.controller.signal });
    if (!response.ok)
      throw new ApiError(response.status, `Could not load ${asset.name}.`);
    const blob = await response.blob();
    this.requireSession();
    return URL.createObjectURL(blob);
  }
}
