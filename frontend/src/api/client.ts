import axios, { AxiosError, type AxiosInstance } from "axios";
import type { ZodSchema } from "zod";

import { SolarGuardApiError } from "./errors";

const DEFAULT_API_HOST = "127.0.0.1";
const DEFAULT_API_PORT = "8000";

export const getApiBaseUrl = (): string =>
  typeof import.meta.env.VITE_SOLARGUARD_API_URL === "string" &&
  import.meta.env.VITE_SOLARGUARD_API_URL.trim().length > 0
    ? import.meta.env.VITE_SOLARGUARD_API_URL
    : typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname || DEFAULT_API_HOST}:${DEFAULT_API_PORT}`
      : `http://${DEFAULT_API_HOST}:${DEFAULT_API_PORT}`;

export const createApiClient = (
  baseURL: string = getApiBaseUrl(),
): AxiosInstance =>
  axios.create({
    baseURL,
    timeout: 8000,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
  });

export const apiClient = createApiClient();

const shouldRetry = (error: unknown): boolean => {
  if (!(error instanceof AxiosError)) {
    return false;
  }
  if (error.code === "ERR_CANCELED") {
    return false;
  }
  return !error.response || error.response.status >= 500;
};

export const getJson = async <T>(
  path: string,
  schema: ZodSchema<T>,
  signal?: AbortSignal,
  client: AxiosInstance = apiClient,
): Promise<T> => {
  const maxAttempts = 2;
  let latestError: unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await client.get<unknown>(path, { signal });
      const parsed = schema.safeParse(response.data);
      if (!parsed.success) {
        if (import.meta.env.DEV) {
          console.error("SolarGuard API validation failed", {
            path,
            issues: parsed.error.issues,
          });
        }
        throw new SolarGuardApiError(
          "SolarGuard received malformed API data.",
          "validation",
        );
      }
      return parsed.data;
    } catch (error) {
      latestError = error;
      if (attempt >= maxAttempts || !shouldRetry(error)) {
        break;
      }
    }
  }

  throw latestError;
};
