import { ToolOutlined, WifiOutlined, EyeOutlined } from "@ant-design/icons";
import { Tag } from "antd";

import { solarGuardTokens } from "../../app/theme";

type WorkType = "field" | "remote" | "monitoring";

type WorkTypeTagProps = {
  type: WorkType;
};

const config = {
  field: {
    label: "Field visit",
    color: solarGuardTokens.colorField,
    icon: <ToolOutlined />,
  },
  remote: {
    label: "Remote action",
    color: solarGuardTokens.colorRemote,
    icon: <WifiOutlined />,
  },
  monitoring: {
    label: "Monitoring",
    color: solarGuardTokens.colorMonitoring,
    icon: <EyeOutlined />,
  },
};

export const WorkTypeTag = ({ type }: WorkTypeTagProps) => {
  const item = config[type];
  return (
    <Tag color={item.color} icon={item.icon} aria-label={item.label}>
      {item.label}
    </Tag>
  );
};
