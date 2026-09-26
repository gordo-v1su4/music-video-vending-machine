import type { components } from "./generated/api";
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
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = this.headers();
    if (options.body && !(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    let response: Response;
    try {
      response = await fetch(`${this.origin}/api/v1${path}`, {
        ...options,
        headers,
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
    return response.json();
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
    const response = await fetch(url, { headers: this.headers() });
    if (!response.ok)
      throw new ApiError(response.status, `Could not load ${asset.name}.`);
    return URL.createObjectURL(await response.blob());
  }
}
