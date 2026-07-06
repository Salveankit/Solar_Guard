import { BrowserRouter } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import {
  useOperationsShellStatus,
  useRefreshOperations,
} from "../hooks/useOperationsData";
import { AppRoutes } from "./router";

const AppContent = () => {
  const shellStatus = useOperationsShellStatus();
  const refreshOperations = useRefreshOperations();

  return (
    <AppShell
      apiStatus={shellStatus.kind}
      isRefreshing={shellStatus.isRefreshing}
      lastUpdated={shellStatus.lastUpdated}
      onRefresh={refreshOperations}
    >
      <AppRoutes />
    </AppShell>
  );
};

export const App = () => (
  <BrowserRouter>
    <AppContent />
  </BrowserRouter>
);
