import { z } from "zod";

export const healthSchema = z.object({
  status: z.string(),
  api_version: z.string(),
  database: z.string(),
  model: z.string(),
  configuration_version: z.string(),
});

export type HealthStatus = z.infer<typeof healthSchema>;
