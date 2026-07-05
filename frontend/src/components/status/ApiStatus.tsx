type ApiStatusKind =
  | "loading"
  | "live"
  | "analysis-required"
  | "partial"
  | "error";

type ApiStatusProps = {
  kind: ApiStatusKind;
};

const labels: Record<ApiStatusKind, string> = {
  loading: "API checking",
  live: "Live",
  "analysis-required": "Analysis required",
  partial: "Partially available",
  error: "Connection error",
};

export const ApiStatus = ({ kind }: ApiStatusProps) => (
  <span className={`sg-api-status is-${kind}`} aria-live="polite">
    <i aria-hidden="true" />
    <span>{labels[kind]}</span>
  </span>
);
