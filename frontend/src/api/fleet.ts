import {
  fleetSummarySchema,
  fleetTimeseriesSchema,
  type FleetSummary,
  type FleetTimeseries,
} from "./schemas/fleet";
import { getJson } from "./client";

export const fetchFleetSummary = (signal?: AbortSignal): Promise<FleetSummary> =>
  getJson("/api/fleet/summary", fleetSummarySchema, signal);

export const fetchFleetTimeseries = (
  signal?: AbortSignal,
): Promise<FleetTimeseries> =>
  getJson("/api/fleet/timeseries", fleetTimeseriesSchema, signal);
