import { AxiosError, type AxiosInstance } from "axios";
import axios from "axios";
import { z } from "zod";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createApiClient, getApiBaseUrl, getJson } from "../src/api/client";
import { downloadDailyPlan } from "../src/api/routes";

describe("API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("reads the API base URL from environment configuration", () => {
    vi.stubEnv("VITE_SOLARGUARD_API_URL", "http://api.example.test");

    expect(getApiBaseUrl()).toBe("http://api.example.test");
  });

  it("falls back to the current browser hostname on port 8000", () => {
    vi.unstubAllEnvs();

    expect(getApiBaseUrl()).toBe(
      `${window.location.protocol}//${window.location.hostname}:8000`,
    );
  });

  it("creates a JSON client with configured base URL and timeout", () => {
    const client = createApiClient("http://api.example.test");

    expect(client.defaults.baseURL).toBe("http://api.example.test");
    expect(client.defaults.timeout).toBe(8000);
    expect(client.defaults.headers.Accept).toBe("application/json");
  });

  it("retries a transient request once", async () => {
    const client = axios.create();
    const request = vi
      .spyOn(client, "get")
      .mockRejectedValueOnce(new AxiosError("network"))
      .mockResolvedValueOnce({ data: { ok: true } });

    await expect(
      getJson("/health", z.object({ ok: z.boolean() }), undefined, client),
    ).resolves.toEqual({ ok: true });
    expect(request).toHaveBeenCalledTimes(2);
  });

  it("rejects malformed API responses with a typed validation error", async () => {
    const client = {
      get: vi.fn(() => Promise.resolve({ data: { ok: "wrong" } })),
    } as unknown as AxiosInstance;

    await expect(
      getJson("/health", z.object({ ok: z.boolean() }), undefined, client),
    ).rejects.toMatchObject({
      kind: "validation",
    });
  });

  it("requests the authoritative daily plan CSV from FastAPI", async () => {
    const blob = new Blob(["plan_date,site_id"], { type: "text/csv" });
    const get = vi.fn(() => Promise.resolve({
      data: blob,
      headers: { "content-disposition": 'attachment; filename="solarguard_daily_plan_2026-07-05.csv"' },
    }));
    const client = {
      get,
    } as unknown as AxiosInstance;

    await expect(downloadDailyPlan("RP-FRONTEND", undefined, client)).resolves.toEqual({
      blob,
      filename: "solarguard_daily_plan_2026-07-05.csv",
    });
    expect(get).toHaveBeenCalledWith(
      "/api/reports/daily-plan",
      expect.objectContaining({
        params: { route_plan_id: "RP-FRONTEND", format: "csv" },
        responseType: "blob",
      }),
    );
  });
});
