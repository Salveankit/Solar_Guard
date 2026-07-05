import { WarningOutlined } from "@ant-design/icons";
import { Alert, Button, Space } from "antd";

import { toApiError } from "../../api/errors";

type ErrorStateProps = {
  error: unknown;
  onRetry?: () => void;
  title?: string;
};

export const ErrorState = ({
  error,
  onRetry,
  title = "This section could not load",
}: ErrorStateProps) => {
  const apiError = toApiError(error);
  return (
    <Alert
      type="error"
      showIcon
      icon={<WarningOutlined />}
      message={title}
      description={
        <Space orientation="vertical" size={10}>
          <span>{apiError.message}</span>
          {onRetry ? (
            <Button size="small" onClick={onRetry}>
              Retry
            </Button>
          ) : null}
        </Space>
      }
    />
  );
};
