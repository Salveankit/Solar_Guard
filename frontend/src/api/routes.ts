import type { AxiosInstance } from "axios";
import { z } from "zod";

import { apiClient, getJson } from "./client";
import {
  latestRoutePlanSchema,
  type LatestRoutePlan,
} from "./schemas/routes";

export const fetchLatestRoutePlan = (
  signal?: AbortSignal,
): Promise<LatestRoutePlan> =>
  getJson("/api/routes/latest", latestRoutePlanSchema, signal);

const optimizeRouteResponseSchema = z.object({
  route_plan_id: z.string(),
  analysis_run_id: z.string(),
  planning_date: z.string(),
  optimisation_status: z.string(),
});

export type OptimizeRouteRequest = {
  planningDate: string;
  analysisRunId?: string;
  replaceExistingPlan?: boolean;
};

export type OptimizeRouteResponse = z.infer<typeof optimizeRouteResponseSchema>;

export const optimizeRoutes = async (
  request: OptimizeRouteRequest,
  signal?: AbortSignal,
  client: AxiosInstance = apiClient,
): Promise<OptimizeRouteResponse> => {
  const response = await client.post(
    "/api/routes/optimize",
    {
      planning_date: request.planningDate,
      analysis_run_id: request.analysisRunId ?? null,
      replace_existing_plan: request.replaceExistingPlan ?? true,
    },
    { signal },
  );
  return optimizeRouteResponseSchema.parse(response.data);
};

export type DailyPlanDownload = {
  blob: Blob;
  filename: string;
};

export const downloadDailyPlan = async (
  routePlanId: string,
  signal?: AbortSignal,
  client: AxiosInstance = apiClient,
): Promise<DailyPlanDownload> => {
  const response = await client.get<Blob>("/api/reports/daily-plan", {
    params: { route_plan_id: routePlanId, format: "csv" },
    responseType: "blob",
    signal,
    headers: { Accept: "text/csv" },
  });
  const disposition = String(response.headers["content-disposition"] ?? "");
  const matchedName = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  return {
    blob: response.data,
    filename: matchedName ?? `Daily_O&M_Plan_${new Date().toISOString().slice(0, 10)}.csv`,
  };
};
