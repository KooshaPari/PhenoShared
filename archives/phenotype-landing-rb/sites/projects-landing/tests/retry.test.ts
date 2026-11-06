import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchWithRetry } from "../scripts/fetch-repos.mjs";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("fetchWithRetry", () => {
  it("resolves on successful fetch", async () => {
    const mockRes = { ok: true, status: 200 };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(mockRes as Response);

    const res = await fetchWithRetry("https://api.github.com/test", {}, 0);
    expect(res.ok).toBe(true);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("retries on network error then resolves", async () => {
    const mockRes = { ok: true, status: 200 };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("ECONNRESET"))
      .mockResolvedValueOnce(mockRes as Response);

    const res = await fetchWithRetry("https://api.github.com/test", {}, 1);
    expect(res.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("retries on timeout (AbortError) then resolves", async () => {
    const mockRes = { ok: true, status: 200 };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new DOMException("The operation was aborted", "AbortError"))
      .mockResolvedValueOnce(mockRes as Response);

    const res = await fetchWithRetry("https://api.github.com/test", {}, 1);
    expect(res.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("throws after exhausting all retries", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValue(new Error("ECONNREFUSED"));

    await expect(
      fetchWithRetry("https://api.github.com/test", {}, 2),
    ).rejects.toThrow("ECONNREFUSED");
    expect(fetchSpy).toHaveBeenCalledTimes(3); // initial + 2 retries
  }, 15_000);

  it("passes through fetch options correctly", async () => {
    const mockRes = { ok: true, status: 200 };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(mockRes as Response);

    const opts = { headers: { Authorization: "Bearer test" } };
    await fetchWithRetry("https://api.github.com/test", opts, 0);

    const callArgs = fetchSpy.mock.calls[0];
    expect(callArgs[0]).toBe("https://api.github.com/test");
    expect(callArgs[1]!.headers).toEqual({ Authorization: "Bearer test" });
  });
});
