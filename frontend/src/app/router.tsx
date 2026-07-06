import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { LoadingSection } from "../components/feedback/LoadingSection";

const CommandCentrePage = lazy(() =>
  import("../features/command-centre/CommandCentrePage").then((module) => ({
    default: module.CommandCentrePage,
  })),
);
const FleetSitesPage = lazy(() =>
  import("../features/fleet/FleetSitesPage").then((module) => ({
    default: module.FleetSitesPage,
  })),
);
const DiagnosticsPage = lazy(() =>
  import("../features/diagnostics/DiagnosticsPage").then((module) => ({
    default: module.DiagnosticsPage,
  })),
);
const IncidentsPage = lazy(() =>
  import("../features/incidents/IncidentsPage").then((module) => ({
    default: module.IncidentsPage,
  })),
);
const ServiceQueuePage = lazy(() =>
  import("../features/service-queue/ServiceQueuePage").then((module) => ({
    default: module.ServiceQueuePage,
  })),
);
const TechnicianPlanPage = lazy(() =>
  import("../features/technician-plan/TechnicianPlanPage").then((module) => ({
    default: module.TechnicianPlanPage,
  })),
);
const ReportsPage = lazy(() =>
  import("../features/reports/ReportsPage").then((module) => ({
    default: module.ReportsPage,
  })),
);

export const AppRoutes = () => (
  <Suspense fallback={<LoadingSection rows={6} />}>
    <Routes>
      <Route path="/" element={<CommandCentrePage />} />
      <Route path="/fleet" element={<FleetSitesPage />} />
      <Route path="/sites/:siteId" element={<DiagnosticsPage />} />
      <Route path="/diagnostics" element={<DiagnosticsPage />} />
      <Route path="/incidents" element={<IncidentsPage />} />
      <Route path="/service-queue" element={<ServiceQueuePage />} />
      <Route path="/technician-plan" element={<TechnicianPlanPage />} />
      <Route path="/reports" element={<ReportsPage />} />
    </Routes>
  </Suspense>
);
