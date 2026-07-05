import { ClockCircleOutlined } from "@ant-design/icons";
import { Space, Typography } from "antd";

type DataFreshnessProps = {
  lastUpdated?: Date;
  isRefreshing?: boolean;
  hasCompletedAnalysis?: boolean;
};

const formatFreshness = (lastUpdated?: Date, hasCompletedAnalysis?: boolean) => {
  if (lastUpdated) {
    return `Last refreshed at ${lastUpdated.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kolkata",
    })}`;
  }

  return hasCompletedAnalysis ? "Waiting for latest refresh" : "Analysis required";
};

export const DataFreshness = ({
  lastUpdated,
  isRefreshing = false,
  hasCompletedAnalysis = false,
}: DataFreshnessProps) => (
  <Space size={6} aria-label="Last data refresh time">
    <ClockCircleOutlined />
    <Typography.Text type="secondary">
      {isRefreshing && lastUpdated
        ? "Refreshing data"
        : formatFreshness(lastUpdated, hasCompletedAnalysis)}
    </Typography.Text>
  </Space>
);
