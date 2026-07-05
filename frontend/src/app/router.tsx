import { Route, Routes } from "react-router-dom";

import { CommandCentrePage } from "../features/command-centre/CommandCentrePage";
import { DiagnosticsPage } from "../features/diagnostics/DiagnosticsPage";
import { FleetSitesPage } from "../features/fleet/FleetSitesPage";
import { IncidentsPage } from "../features/incidents/IncidentsPage";
import { ReportsPage } from "../features/reports/ReportsPage";
import { ServiceQueuePage } from "../features/service-queue/ServiceQueuePage";
import { TechnicianPlanPage } from "../features/technician-plan/TechnicianPlanPage";

export const AppRoutes = () => (
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
);
