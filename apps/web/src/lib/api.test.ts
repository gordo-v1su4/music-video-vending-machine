import { afterEach, describe, expect, mock, test } from "bun:test";
import { ApiError, StudioApi, type Asset, type Project } from "./api";

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("studio API trust boundary", () => {
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
