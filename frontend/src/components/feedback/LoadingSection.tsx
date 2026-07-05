import { Skeleton } from "antd";

type LoadingSectionProps = {
  rows?: number;
  compact?: boolean;
};

export const LoadingSection = ({ rows = 4, compact = false }: LoadingSectionProps) => (
  <div className={`sg-loading-section${compact ? " is-compact" : ""}`} aria-hidden="true">
    <Skeleton active paragraph={{ rows }} title={compact ? false : undefined} />
  </div>
);
