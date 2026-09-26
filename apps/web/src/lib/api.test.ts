import { afterEach, describe, expect, mock, test } from "bun:test";
import { ApiError, StudioApi, type Asset, type Project } from "./api";

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("studio API trust boundary", () => {
  test("sign-out reaches the coordinator even when local time is beyond server expiry", async () => {
    const fetchSpy = mock(async (_input: string | URL | Request, _options?: RequestInit) => Response.json({ revoked: true }));
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199", "session-only");
    api.session = { id: "expired", clientLabel: "test", createdAt: new Date(0).toISOString(), expiresAt: new Date(1).toISOString() };
    await api.signOut();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("/sessions/current/revoke");
    expect(api.session).toBeNull();
  });
  test("a fetch rejected by session abort explains sign-in instead of network failure", async () => {
    globalThis.fetch = mock((_input: unknown, options?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    })) as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199", "session-only");
    const pending = api.projects();
    api.close();
    await expect(pending).rejects.toThrow("Your session has ended");
  });
  test("exchanges the bootstrap once and uses only the session on project routes", async () => {
    const sent: { path: string; authorization: string | null }[] = [];
    globalThis.fetch = mock(async (input: string | URL | Request, options?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      sent.push({ path, authorization: new Headers(options?.headers).get("authorization") });
      expect(options?.redirect).toBe("error");
      expect(options?.cache).toBe("no-store");
      if (path.endsWith("/health")) return Response.json({ sessionRequired: true });
      if (path.endsWith("/sessions")) return Response.json({ token: "session-only", session: { id: "one", clientLabel: "test", createdAt: "2000-01-01T00:00:00Z", expiresAt: "2000-01-01T12:00:00Z" } });
      return Response.json([]);
    }) as unknown as typeof fetch;
    const api = await StudioApi.connect("http://127.0.0.1:5199", "bootstrap-only");
    expect(api.sessionRemainingMs()).toBeGreaterThan(43_190_000);
    expect(api.sessionRemainingMs()).toBeLessThanOrEqual(43_200_000);
    await api.projects();
    await api.signOut();
    expect(sent).toEqual([
      { path: "/api/v1/health", authorization: null },
      { path: "/api/v1/sessions", authorization: "Bearer bootstrap-only" },
      { path: "/api/v1/projects", authorization: "Bearer session-only" },
      { path: "/api/v1/sessions/current/revoke", authorization: "Bearer session-only" },
    ]);
    expect(api.session).toBeNull();
    await expect(api.projects()).rejects.toThrow("Sign in");
    expect(sent).toHaveLength(4);
  });

  test("closing during a response discards its data and aborts further requests", async () => {
    let deliver!: (response: Response) => void;
    let signal: AbortSignal | null | undefined;
    globalThis.fetch = mock((_input: unknown, options?: RequestInit) => {
      signal = options?.signal;
      return new Promise<Response>((resolve) => { deliver = resolve; });
    }) as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199", "session-only");
    const pending = api.projects();
    api.close();
    expect(signal?.aborted).toBe(true);
    deliver(Response.json([{ id: "stale" }]));
    await expect(pending).rejects.toThrow("Sign in");
  });

  test("failed remote signout keeps the session available for retry", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/health")) return Response.json({ sessionRequired: true });
      if (path.endsWith("/sessions")) return Response.json({ token: "session-only", session: { id: "one" } });
      return Response.json({ error: "Storage unavailable" }, { status: 503 });
    }) as unknown as typeof fetch;
    const api = await StudioApi.connect("http://127.0.0.1:5199", "bootstrap-only");
    await expect(api.signOut(true)).rejects.toThrow("Storage unavailable");
    expect(api.session?.id).toBe("one");
    api.close();
  });

  test("sends credentials only in authorization and carries the expected revision", async () => {
    let sentUrl = "";
    let sentOptions: RequestInit | undefined;
    globalThis.fetch = mock(
      async (input: string | URL | Request, options?: RequestInit) => {
        sentUrl = String(input);
        sentOptions = options;
        return Response.json({ revision: 8 });
      },
    ) as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199/", "test-only-token");
    await api.action({ id: "project-one", revision: 7 } as Project, {
      type: "approveMaster",
    });
    expect(sentUrl).toBe(
      "http://127.0.0.1:5199/api/v1/projects/project-one/actions",
    );
    expect(new Headers(sentOptions?.headers).get("Authorization")).toBe(
      "Bearer test-only-token",
    );
    expect(JSON.parse(String(sentOptions?.body))).toEqual({
      expectedRevision: 7,
      action: { type: "approveMaster" },
    });
  });

  test("rejects cross-origin media before transmitting a credential", async () => {
    const fetchSpy = mock(() => Promise.resolve(Response.json({})));
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199", "test-only-token");
    await expect(
      api.blob({ url: "https://unexpected.example/private" } as Asset),
    ).rejects.toThrow("does not belong");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test("surfaces stale writes as conflicts without retrying them", async () => {
    const fetchSpy = mock(() =>
      Promise.resolve(Response.json({ error: "conflict" }, { status: 409 })),
    );
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    const api = new StudioApi("http://127.0.0.1:5199");
    try {
      await api.request("/projects/one/actions");
      throw new Error("Expected conflict");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(409);
    }
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
