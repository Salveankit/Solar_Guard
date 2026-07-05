import { BrowserRouter } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import {
  useOperationsShellStatus,
  useRefreshOperations,
} from "../hooks/useOperationsData";
import { AppRoutes } from "./router";

export const App = () => {
  const shellStatus = useOperationsShellStatus();
  const refreshOperations = useRefreshOperations();

  return (
    <BrowserRouter>
      <AppShell
        apiStatus={shellStatus.kind}
        isRefreshing={shellStatus.isRefreshing}
        lastUpdated={shellStatus.lastUpdated}
        onRefresh={refreshOperations}
      >
        <AppRoutes />
      </AppShell>
    </BrowserRouter>
  );
};
