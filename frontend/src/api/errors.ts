import { AxiosError } from "axios";
import { ZodError } from "zod";

export type ApiErrorKind =
  | "network"
  | "timeout"
  | "http"
  | "validation"
  | "unknown";

export class SolarGuardApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;

  constructor(message: string, kind: ApiErrorKind, status?: number) {
    super(message);
    this.name = "SolarGuardApiError";
    this.kind = kind;
    this.status = status;
  }
}

export const toApiError = (error: unknown): SolarGuardApiError => {
  if (error instanceof SolarGuardApiError) {
    return error;
  }

  if (error instanceof ZodError) {
    return new SolarGuardApiError(
      "The API returned data that SolarGuard cannot safely display.",
      "validation",
    );
  }

  if (error instanceof AxiosError) {
    if (error.code === "ECONNABORTED") {
      return new SolarGuardApiError(
        "SolarGuard API did not respond before the request timed out.",
        "timeout",
      );
    }

    if (error.response) {
      return new SolarGuardApiError(
        "SolarGuard API returned an error for this request.",
        "http",
        error.response.status,
      );
    }

    return new SolarGuardApiError(
      "SolarGuard API is unavailable. Check that FastAPI is running.",
      "network",
    );
  }

  return new SolarGuardApiError(
    "SolarGuard could not complete the request.",
    "unknown",
  );
};
