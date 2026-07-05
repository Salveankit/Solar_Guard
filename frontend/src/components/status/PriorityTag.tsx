import { Tag } from "antd";

import { solarGuardTokens } from "../../app/theme";

type PriorityTagProps = {
  label: "Critical" | "High" | "Medium" | "Low";
};

const colors = {
  Critical: solarGuardTokens.priorityCritical,
  High: solarGuardTokens.priorityHigh,
  Medium: solarGuardTokens.priorityMedium,
  Low: solarGuardTokens.priorityLow,
};

export const PriorityTag = ({ label }: PriorityTagProps) => (
  <Tag color={colors[label]} aria-label={`Priority ${label}`}>
    {label}
  </Tag>
);
