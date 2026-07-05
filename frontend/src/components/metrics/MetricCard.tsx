import { Card } from "antd";
import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  footnote?: string;
};

export const MetricCard = ({ label, value, footnote }: MetricCardProps) => (
  <Card className="sg-metric-card">
    <div className="sg-metric-label">{label}</div>
    <div className="sg-metric-value">{value}</div>
    {footnote ? <div className="sg-metric-footnote">{footnote}</div> : null}
  </Card>
);
