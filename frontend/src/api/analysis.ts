import { z } from "zod";

import { apiClient } from "./client";

const runAnalysisResponseSchema = z.object({
  analysis_run_id: z.string(),
  status: z.string(),
});

export type RunAnalysisResponse = z.infer<typeof runAnalysisResponseSchema>;

export const runAnalysis = async (
  analysisDate?: string,
  signal?: AbortSignal,
): Promise<RunAnalysisResponse> => {
  const response = await apiClient.post(
    "/api/analysis/run",
    analysisDate ? { analysis_date: analysisDate } : {},
    { signal },
  );
  return runAnalysisResponseSchema.parse(response.data);
};
