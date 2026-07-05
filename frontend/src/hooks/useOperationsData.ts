import {
  useIsFetching,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { AxiosError } from "axios";

import { runAnalysis } from "../api/analysis";
import { fetchServiceQueue } from "../api/decisions";
import { fetchFleetSummary, fetchFleetTimeseries } from "../api/fleet";
import { fetchHealthStatus } from "../api/health";
import {
  downloadDailyPlan,
  fetchLatestRoutePlan,
  optimizeRoutes,
  type OptimizeRouteRequest,
} from "../api/routes";
import { fetchSiteDiagnostics, fetchSites } from "../api/sites";

export const operationsQueryKeys = {
  health: ["api-health"] as const,
  fleetSummary: ["fleet-summary"] as const,
  fleetTimeseries: ["fleet-timeseries"] as const,
  serviceQueue: ["service-queue"] as const,
  latestRoutePlan: ["latest-route-plan"] as const,
  sites: ["sites"] as const,
  siteDiagnostics: (siteId?: string) => ["site-diagnostics", siteId ?? ""] as const,
  dailyPlanReport: (routePlanId?: string) => ["daily-plan-report", routePlanId ?? ""] as const,
};

export const useApiHealth = () =>
  useQuery({
    queryKey: operationsQueryKeys.health,
    queryFn: ({ signal }) => fetchHealthStatus(signal),
    staleTime: 30_000,
  });

export const useFleetSummary = () =>
  useQuery({
    queryKey: operationsQueryKeys.fleetSummary,
    queryFn: ({ signal }) => fetchFleetSummary(signal),
  });

export const useFleetTimeseries = () =>
  useQuery({
    queryKey: operationsQueryKeys.fleetTimeseries,
    queryFn: ({ signal }) => fetchFleetTimeseries(signal),
  });

export const useServiceQueue = () =>
  useQuery({
    queryKey: operationsQueryKeys.serviceQueue,
    queryFn: ({ signal }) => fetchServiceQueue(signal),
  });

export const useLatestRoutePlan = () =>
  useQuery({
    queryKey: operationsQueryKeys.latestRoutePlan,
    queryFn: ({ signal }) => fetchLatestRoutePlan(signal),
  });

export const useDailyPlanReport = (routePlanId?: string) =>
  useQuery({
    queryKey: operationsQueryKeys.dailyPlanReport(routePlanId),
    queryFn: ({ signal }) => downloadDailyPlan(routePlanId ?? "", signal),
    enabled: Boolean(routePlanId),
  });

export const useSites = () =>
  useQuery({
    queryKey: operationsQueryKeys.sites,
    queryFn: ({ signal }) => fetchSites(signal),
  });

export const useSiteDiagnostics = (siteId?: string) =>
  useQuery({
    queryKey: operationsQueryKeys.siteDiagnostics(siteId),
    queryFn: ({ signal }) => fetchSiteDiagnostics(siteId ?? "", signal),
    enabled: Boolean(siteId),
  });

export const invalidateOperationsQueries = (queryClient: ReturnType<typeof useQueryClient>) =>
  Promise.all([
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.health }),
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.fleetSummary }),
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.fleetTimeseries }),
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.serviceQueue }),
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.latestRoutePlan }),
    queryClient.invalidateQueries({ queryKey: operationsQueryKeys.sites }),
  ]);

export const useRefreshOperations = () => {
  const queryClient = useQueryClient();
  return () => {
    void invalidateOperationsQueries(queryClient);
  };
};

export const useRunAnalysis = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (analysisDate?: string) => runAnalysis(analysisDate),
    onSuccess: async () => {
      await invalidateOperationsQueries(queryClient);
    },
  });
};

export const useOptimizeRoutes = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: OptimizeRouteRequest) => optimizeRoutes(request),
    onSuccess: async () => {
      await invalidateOperationsQueries(queryClient);
    },
  });
};

type ShellStatusKind =
  | "loading"
  | "live"
  | "analysis-required"
  | "partial"
  | "error";

export type OperationsShellStatus = {
  hasCompletedAnalysis: boolean;
  isRefreshing: boolean;
  kind: ShellStatusKind;
  lastUpdated?: Date;
};

const isNotFoundError = (error?: unknown) =>
  error instanceof AxiosError && error.response?.status === 404;

export const useOperationsShellStatus = (): OperationsShellStatus => {
  const health = useApiHealth();
  const fleetSummary = useFleetSummary();
  const fleetTimeseries = useFleetTimeseries();
  const serviceQueue = useServiceQueue();
  const latestRoutePlan = useLatestRoutePlan();
  const shellQueryKeys = [
    operationsQueryKeys.health[0],
    operationsQueryKeys.fleetSummary[0],
    operationsQueryKeys.fleetTimeseries[0],
    operationsQueryKeys.serviceQueue[0],
    operationsQueryKeys.latestRoutePlan[0],
  ] as const;
  const activeFetches = useIsFetching({
    predicate: (query) => {
      const key = query.queryKey[0];
      return (
        typeof key === "string" &&
        shellQueryKeys.some((queryKey) => queryKey === key)
      );
    },
  });

  const lastUpdatedValues = [
    health.dataUpdatedAt,
    fleetSummary.dataUpdatedAt,
    fleetTimeseries.dataUpdatedAt,
    serviceQueue.dataUpdatedAt,
    latestRoutePlan.dataUpdatedAt,
  ].filter((value) => value > 0);
  const lastUpdated = lastUpdatedValues.length
    ? new Date(Math.max(...lastUpdatedValues))
    : undefined;
  const hasCompletedAnalysis = Boolean(fleetSummary.data?.analysis_run_id);
  const summaryUnavailable = !fleetSummary.data && (fleetSummary.isLoading || health.isLoading);
  const hardError =
    Boolean(health.error) ||
    Boolean(fleetSummary.error) ||
    Boolean(serviceQueue.error) ||
    Boolean(fleetTimeseries.error);
  const healthUnavailable = health.data?.database === "unavailable";
  const partialError =
    Boolean(latestRoutePlan.error) && !isNotFoundError(latestRoutePlan.error);

  if (summaryUnavailable) {
    return {
      kind: "loading",
      hasCompletedAnalysis: false,
      isRefreshing: activeFetches > 0,
    };
  }

  if (hardError && !fleetSummary.data) {
    return {
      kind: "error",
      hasCompletedAnalysis: false,
      isRefreshing: false,
      lastUpdated,
    };
  }

  if (healthUnavailable) {
    return {
      kind: "error",
      hasCompletedAnalysis,
      isRefreshing: activeFetches > 0,
      lastUpdated,
    };
  }

  if (!hasCompletedAnalysis) {
    return {
      kind: "analysis-required",
      hasCompletedAnalysis,
      isRefreshing: activeFetches > 0,
      lastUpdated,
    };
  }

  if (hardError || partialError) {
    return {
      kind: "partial",
      hasCompletedAnalysis,
      isRefreshing: activeFetches > 0,
      lastUpdated,
    };
  }

  return {
    kind: "live",
    hasCompletedAnalysis,
    isRefreshing: activeFetches > 0,
    lastUpdated,
  };
};
