import { getJson } from "./client";
import { healthSchema, type HealthStatus } from "./schemas/health";

export const fetchHealthStatus = (signal?: AbortSignal): Promise<HealthStatus> =>
  getJson("/health", healthSchema, signal);
