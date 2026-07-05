import { QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import type { ReactNode } from "react";
import { useState } from "react";

import { createQueryClient } from "./queryClient";
import { antTheme } from "./theme";

type AppProvidersProps = {
  children: ReactNode;
};

export const AppProviders = ({ children }: AppProvidersProps) => {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <ConfigProvider theme={antTheme}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ConfigProvider>
  );
};
