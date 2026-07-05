import { getJson } from "./client";
import {
  serviceQueueSchema,
  type ServiceQueue,
} from "./schemas/decisions";

export const fetchServiceQueue = (signal?: AbortSignal): Promise<ServiceQueue> =>
  getJson("/api/service-queue", serviceQueueSchema, signal);
