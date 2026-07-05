import { getJson } from "./client";
import {
  siteDiagnosticsSchema,
  siteListSchema,
  type SiteDiagnostics,
  type SiteSummary,
} from "./schemas/sites";

export const fetchSites = (signal?: AbortSignal): Promise<SiteSummary[]> =>
  getJson("/api/sites", siteListSchema, signal);

export const fetchSiteDiagnostics = (
  siteId: string,
  signal?: AbortSignal,
): Promise<SiteDiagnostics> =>
  getJson(`/api/sites/${encodeURIComponent(siteId)}/diagnostics`, siteDiagnosticsSchema, signal);
