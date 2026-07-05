import {
  AimOutlined,
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  EnvironmentOutlined,
  FileDoneOutlined,
  InfoCircleOutlined,
  NodeIndexOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Modal, Skeleton } from "antd";
import type { LatLngExpression } from "leaflet";
import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useSearchParams } from "react-router-dom";
import "leaflet/dist/leaflet.css";

import { downloadDailyPlan } from "../../api/routes";
import type { LatestRoutePlan, RouteStop, TechnicianRoute } from "../../api/schemas/routes";
import type { SiteSummary } from "../../api/schemas/sites";
import technicianPlanHero from "../../assets/technician-plan-hero.png";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { useLatestRoutePlan, useRefreshOperations, useSites } from "../../hooks/useOperationsData";
import { formatInteger, formatKm, formatKwh, formatMinutes } from "../../utils/format";

type AssignmentFilter = "all" | "ready" | "electrical" | "cleaning" | "review";
type DownloadState = "idle" | "loading" | "success" | "error";

const routeColors = ["#1688ff", "#9a65f7", "#31d48d", "#f3a62f"];

const formatClock = (value?: string | null) => {
  if (!value) return "Unavailable";
  if (/^\d{2}:\d{2}/.test(value)) {
    const [hour, minute] = value.split(":").map(Number);
    return new Intl.DateTimeFormat("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(2026, 0, 1, hour, minute));
  }
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
};

const initials = (name: string) =>
  name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

const displaySkill = (skills: string[]) =>
  skills.length ? skills.map((skill) => skill.replaceAll("_", " ")).join(" + ") : "Skill unavailable";

const routeEnergy = (route: TechnicianRoute) =>
  route.stops.reduce((sum, stop) => sum + stop.job.recoverable_energy_kwh, 0);

const routeStatus = (plan: LatestRoutePlan, route: TechnicianRoute) => {
  if (plan.failure_reason) return "Blocked";
  if (route.stops.length === 0 || plan.unassigned_jobs_count > 0) return "Review";
  return "Ready";
};

const sitesById = (sites: SiteSummary[]) => new Map(sites.map((site) => [site.site_id, site]));

const stopName = (stop: RouteStop, sites: Map<string, SiteSummary>) =>
  sites.get(stop.job.site_id)?.site_name ?? stop.job.site_id;

const filterAssignments = (
  routes: TechnicianRoute[],
  filter: AssignmentFilter,
  plan: LatestRoutePlan,
) => routes.filter((route) => {
  if (filter === "all") return true;
  const status = routeStatus(plan, route).toLowerCase();
  if (filter === "ready" || filter === "review") return status === filter;
  return route.skills.some((skill) => skill.toLowerCase().includes(filter));
});

const planReady = (plan: LatestRoutePlan) =>
  plan.optimisation_status.toLowerCase().includes("optim") &&
  !plan.failure_reason &&
  plan.unassigned_jobs_count === 0;

const FitRoute = ({ routes }: { routes: TechnicianRoute[] }) => {
  const map = useMap();
  useEffect(() => {
    const points = routes.flatMap((route) =>
      route.stops.map((stop) => [stop.job.latitude, stop.job.longitude] as [number, number]),
    );
    if (points.length === 1) map.setView(points[0], 12);
    else if (points.length > 1) map.fitBounds(points, { padding: [28, 28] });
  }, [map, routes]);
  return null;
};

const PlanOverview = ({ plan }: { plan: LatestRoutePlan }) => {
  const ready = planReady(plan);
  return (
    <aside className="sg-plan-overview">
      <div className="sg-plan-overview-head"><strong>Plan overview</strong><span className={ready ? "ready" : "review"}><i />{ready ? "Ready" : "Review"}</span></div>
      <dl>
        <div><dt><TeamOutlined /> Technicians assigned</dt><dd>{plan.field_plan.length}</dd></div>
        <div><dt><FileDoneOutlined /> Jobs selected</dt><dd>{plan.assigned_jobs}</dd></div>
        <div><dt><CheckCircleOutlined /> Route status</dt><dd>{ready ? "Ready" : "Review"}</dd></div>
        <div><dt><ClockCircleOutlined /> Dispatch start</dt><dd>{formatClock(plan.field_plan[0]?.shift_start)}</dd></div>
      </dl>
    </aside>
  );
};

const PlanKpi = ({
  icon, label, value, tone, onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: string;
  onClick: () => void;
}) => (
  <button type="button" className="sg-plan-kpi" onClick={onClick}>
    <span className={`sg-plan-kpi-icon ${tone}`}>{icon}</span>
    <span><small>{label}</small><strong>{value}</strong></span>
  </button>
);

const StatusBadge = ({ status }: { status: string }) => (
  <span className={`sg-plan-status status-${status.toLowerCase()}`}>
    {status === "Ready" ? <CheckCircleOutlined /> : status === "Blocked" ? <WarningOutlined /> : <InfoCircleOutlined />}
    {status}
  </span>
);

const RouteMap = ({
  routes,
  selectedTechnician,
  selectedStop,
  onSelectTechnician,
  onSelectStop,
  sites,
}: {
  routes: TechnicianRoute[];
  selectedTechnician?: string;
  selectedStop?: string;
  onSelectTechnician: (id: string) => void;
  onSelectStop: (decisionId: string) => void;
  sites: Map<string, SiteSummary>;
}) => {
  const defaultCenter: LatLngExpression = [18.5204, 73.8567];
  return (
    <section className="sg-plan-card sg-route-map-card" aria-labelledby="route-map-heading">
      <h2 id="route-map-heading">ROUTE MAP</h2>
      <div className="sg-route-map">
        <MapContainer center={defaultCenter} zoom={11} scrollWheelZoom={false} attributionControl={false}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <FitRoute routes={routes} />
          {routes.map((route, routeIndex) => {
            const points = route.stops.map((stop) => [stop.job.latitude, stop.job.longitude] as [number, number]);
            const active = route.technician_id === selectedTechnician;
            return (
              <Polyline key={route.technician_id} positions={points} pathOptions={{ color: routeColors[routeIndex % routeColors.length], weight: active ? 5 : 3, opacity: active ? 1 : 0.62 }} eventHandlers={{ click: () => onSelectTechnician(route.technician_id) }} />
            );
          })}
          {routes.flatMap((route, routeIndex) =>
            route.stops.map((stop) => {
              const active = stop.job.decision_id === selectedStop;
              return (
                <CircleMarker
                  key={stop.job.decision_id}
                  center={[stop.job.latitude, stop.job.longitude]}
                  radius={active ? 11 : 9}
                  pathOptions={{ color: "#dcecff", fillColor: routeColors[routeIndex % routeColors.length], fillOpacity: 1, weight: active ? 3 : 2 }}
                  eventHandlers={{ click: () => { onSelectTechnician(route.technician_id); onSelectStop(stop.job.decision_id); } }}
                >
                  <Tooltip permanent direction="center" className="sg-route-marker-label">{stop.sequence}</Tooltip>
                  <Tooltip direction="top">{stopName(stop, sites)} · ETA {formatClock(stop.arrival)}</Tooltip>
                </CircleMarker>
              );
            }),
          )}
        </MapContainer>
      </div>
      <div className="sg-route-summary-bar">
        <span><EnvironmentOutlined /> {routes.reduce((sum, route) => sum + route.stops.length, 0)} jobs</span>
        <span><CarOutlined /> {formatKm(routes.reduce((sum, route) => sum + route.distance_km, 0))}</span>
        <span><ClockCircleOutlined /> {formatMinutes(routes.reduce((sum, route) => sum + route.travel_duration_min + route.job_duration_min, 0))}</span>
      </div>
    </section>
  );
};

const SelectedTechnician = ({
  route,
  plan,
  selectedStop,
  onSelectStop,
  sites,
}: {
  route?: TechnicianRoute;
  plan: LatestRoutePlan;
  selectedStop?: string;
  onSelectStop: (id: string) => void;
  sites: Map<string, SiteSummary>;
}) => (
  <section className="sg-plan-card sg-selected-technician" aria-labelledby="selected-technician-heading">
    <div className="sg-plan-card-head"><h2 id="selected-technician-heading">SELECTED TECHNICIAN</h2>{route ? <StatusBadge status={routeStatus(plan, route)} /> : null}</div>
    {!route ? <EmptyState title="Select a technician" description="Review route and ordered stops." /> : (
      <>
        <div className="sg-tech-identity"><Avatar>{initials(route.technician_name ?? route.technician_id)}</Avatar><strong>{route.technician_name ?? route.technician_id}<small>{displaySkill(route.skills)}</small></strong></div>
        <dl className="sg-tech-metrics">
          <div><dt>Shift start</dt><dd>{formatClock(route.shift_start)}</dd></div>
          <div><dt>Assigned jobs</dt><dd>{route.stops.length}</dd></div>
          <div><dt>Route distance</dt><dd>{formatKm(route.distance_km)}</dd></div>
          <div><dt>Travel time</dt><dd>{formatMinutes(route.travel_duration_min)}</dd></div>
          <div><dt>Service time</dt><dd>{formatMinutes(route.job_duration_min)}</dd></div>
          <div><dt>Recoverable energy</dt><dd>{formatKwh(routeEnergy(route))}</dd></div>
        </dl>
        <div className="sg-stop-list" aria-label={`Ordered stops for ${route.technician_name ?? route.technician_id}`}>
          <div><span>STOP SEQUENCE</span><span>ETA</span></div>
          {route.stops.map((stop) => (
            <button type="button" key={stop.job.decision_id} className={selectedStop === stop.job.decision_id ? "is-active" : ""} onClick={() => onSelectStop(stop.job.decision_id)}>
              <i>{stop.sequence}</i><strong>{stopName(stop, sites)}<small>{formatMinutes(stop.job.duration_min)} service</small></strong><span>{formatClock(stop.arrival)}</span>
            </button>
          ))}
        </div>
      </>
    )}
  </section>
);

const unassignedReason = (item: unknown) => {
  if (!item || typeof item !== "object") return "Backend did not provide a constraint reason.";
  const record = item as Record<string, unknown>;
  const reason = record.reason ?? record.blocking_reason;
  return typeof reason === "string" ? reason : "Constraint reason unavailable";
};

const UnassignedJobs = ({ plan }: { plan: LatestRoutePlan }) => {
  if (plan.unassigned_jobs_count === 0) return null;
  return (
    <section className="sg-plan-card sg-unassigned-jobs" aria-labelledby="unassigned-heading">
      <h2 id="unassigned-heading">UNASSIGNED JOBS · {plan.unassigned_jobs_count}</h2>
      {plan.unassigned_jobs.map((item, index) => <p key={index}><WarningOutlined /> {unassignedReason(item)}</p>)}
    </section>
  );
};

const PlanImpact = ({
  plan,
  onViewRoute,
  onDownload,
  downloadState,
}: {
  plan: LatestRoutePlan;
  onViewRoute: () => void;
  onDownload: () => void;
  downloadState: DownloadState;
}) => (
  <section className="sg-plan-card sg-plan-impact" aria-labelledby="plan-impact-heading">
    <h2 id="plan-impact-heading">PLAN IMPACT</h2>
    <dl>
      <div><dt><CarOutlined /> Naive route</dt><dd>{formatKm(plan.naive_distance_km)}</dd></div>
      <div><dt><CheckCircleOutlined /> Optimised route</dt><dd>{formatKm(plan.optimised_distance_km)}</dd></div>
      <div><dt><NodeIndexOutlined /> Distance avoided</dt><dd>{formatKm(plan.distance_avoided_km)}</dd></div>
      <div><dt><ThunderboltOutlined /> Recoverable energy</dt><dd>{formatKwh(plan.total_recoverable_energy_kwh)}</dd></div>
    </dl>
    <div className="sg-plan-impact-actions">
      <Button icon={<AimOutlined />} onClick={onViewRoute}>View Full Route</Button>
      <Button type="primary" icon={<DownloadOutlined />} loading={downloadState === "loading"} onClick={onDownload}>Download Daily O&amp;M Plan.csv</Button>
    </div>
    <div className="sg-plan-download-status" role="status" aria-live="polite">
      {downloadState === "success" ? "Daily O&M plan downloaded." : downloadState === "error" ? "Daily O&M plan could not be downloaded. Retry the request." : ""}
    </div>
  </section>
);

const FullRouteDialog = ({
  open,
  plan,
  sites,
  onClose,
}: {
  open: boolean;
  plan: LatestRoutePlan;
  sites: Map<string, SiteSummary>;
  onClose: () => void;
}) => (
  <Modal open={open} onCancel={onClose} title="Full technician route" width={780} footer={<Button type="primary" onClick={onClose}>Close route</Button>}>
    <div className="sg-full-route-list">
      {plan.field_plan.map((route) => (
        <section key={route.technician_id}>
          <h3>{route.technician_name ?? route.technician_id}</h3>
          <p>{displaySkill(route.skills)} · {formatKm(route.distance_km)} · {formatMinutes(route.travel_duration_min)} travel · {formatMinutes(route.job_duration_min)} service</p>
          <ol>{route.stops.map((stop) => <li key={stop.job.decision_id}><strong>{stopName(stop, sites)}</strong><span>ETA {formatClock(stop.arrival)} · {formatMinutes(stop.job.duration_min)} · {stop.job.recommended_action}</span></li>)}</ol>
        </section>
      ))}
    </div>
  </Modal>
);

export const TechnicianPlanPage = () => {
  const routeQuery = useLatestRoutePlan();
  const sitesQuery = useSites();
  const refresh = useRefreshOperations();
  const [searchParams, setSearchParams] = useSearchParams();
  const [routeDialogOpen, setRouteDialogOpen] = useState(false);
  const [downloadState, setDownloadState] = useState<DownloadState>("idle");

  const plan = routeQuery.data;
  const siteLookup = useMemo(() => sitesById(sitesQuery.data ?? []), [sitesQuery.data]);
  const filter = (searchParams.get("status") as AssignmentFilter) || "all";
  const filteredRoutes = useMemo(
    () => plan ? filterAssignments(plan.field_plan, filter, plan) : [],
    [filter, plan],
  );
  const selectedTechnicianId = searchParams.get("technician") ?? filteredRoutes[0]?.technician_id;
  const selectedRoute = filteredRoutes.find((route) => route.technician_id === selectedTechnicianId) ?? filteredRoutes[0];
  const selectedStop = searchParams.get("stop") ?? selectedRoute?.stops[0]?.job.decision_id;

  const setParam = (key: string, value?: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all") next.delete(key); else next.set(key, value);
    if (key === "status") { next.delete("technician"); next.delete("stop"); }
    setSearchParams(next);
  };

  const selectTechnician = (id: string) => {
    const route = plan?.field_plan.find((item) => item.technician_id === id);
    const next = new URLSearchParams(searchParams);
    next.set("technician", id);
    if (route?.stops[0]) next.set("stop", route.stops[0].job.decision_id);
    setSearchParams(next);
  };

  const runDownload = async () => {
    if (!plan) return;
    setDownloadState("loading");
    try {
      const result = await downloadDailyPlan(plan.route_plan_id);
      const url = URL.createObjectURL(result.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = result.filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setDownloadState("success");
    } catch {
      setDownloadState("error");
    }
  };

  const loading = routeQuery.isLoading || sitesQuery.isLoading;
  const error = routeQuery.error ?? sitesQuery.error;
  if (error) return <ErrorState title="Unable to load technician plan" error={error} onRetry={refresh} />;

  if (!loading && !plan) {
    return <EmptyState title="No field jobs are ready for technician planning" description="Complete remote checks or review Service Queue decisions before generating a plan." />;
  }

  return (
    <div className="sg-technician-plan-page">
      <section className="sg-technician-hero" style={{ backgroundImage: `url(${technicianPlanHero})` }}>
        <div className="sg-technician-hero-copy"><span>TECHNICIAN PLAN</span><h1>Coordinate field execution<br />with confidence.</h1><p>Turn prioritized service decisions into efficient technician routes and daily O&amp;M plans.</p></div>
        {loading || !plan ? <div className="sg-plan-overview"><Skeleton active /></div> : <PlanOverview plan={plan} />}
      </section>

      <div className="sg-plan-main-grid">
        <div className="sg-plan-left-column">
          <section className="sg-plan-kpis" aria-label="Technician plan metrics">
            {loading || !plan ? Array.from({ length: 5 }, (_, index) => <Skeleton.Button key={index} active block />) : (
              <>
                <PlanKpi icon={<TeamOutlined />} label="Assigned Technicians" value={formatInteger(plan.field_plan.length)} tone="blue" onClick={() => setParam("status", "all")} />
                <PlanKpi icon={<FileDoneOutlined />} label="Field Jobs" value={formatInteger(plan.assigned_jobs)} tone="green" onClick={() => setParam("status", "all")} />
                <PlanKpi icon={<CarOutlined />} label="Total Distance" value={formatKm(plan.optimised_distance_km)} tone="purple" onClick={() => setRouteDialogOpen(true)} />
                <PlanKpi icon={<NodeIndexOutlined />} label="Distance Avoided" value={formatKm(plan.distance_avoided_km)} tone="green" onClick={() => setRouteDialogOpen(true)} />
                <PlanKpi icon={<ThunderboltOutlined />} label="Recoverable Energy" value={formatKwh(plan.total_recoverable_energy_kwh)} tone="amber" onClick={() => setParam("status", "all")} />
              </>
            )}
          </section>

          <section className="sg-plan-card sg-technician-assignments" aria-labelledby="technician-assignments-heading">
            <h2 id="technician-assignments-heading">TECHNICIAN ASSIGNMENTS</h2>
            <div className="sg-plan-filters">
              {(["all", "ready", "electrical", "cleaning", "review"] as AssignmentFilter[]).map((value) => <button type="button" key={value} className={filter === value ? "is-active" : ""} aria-pressed={filter === value} onClick={() => setParam("status", value)}>{value === "all" ? "All" : value[0].toUpperCase() + value.slice(1)}</button>)}
            </div>
            {loading || !plan ? <Skeleton active paragraph={{ rows: 6 }} /> : filteredRoutes.length === 0 ? <EmptyState title="No technician assignments match this filter" description="Select All to review the current plan." /> : (
              <>
                <div className="sg-plan-table-wrap">
                  <table className="sg-plan-table">
                    <thead><tr><th>Technician</th><th>Visit sequence</th><th>Required skill</th><th>Jobs</th><th>Travel / service</th><th>Total distance</th><th>Recoverable energy</th><th>Status</th></tr></thead>
                    <tbody>{filteredRoutes.map((route) => {
                      const status = routeStatus(plan, route);
                      return <tr key={route.technician_id} className={selectedRoute?.technician_id === route.technician_id ? "is-selected" : ""} tabIndex={0} aria-selected={selectedRoute?.technician_id === route.technician_id} onClick={() => selectTechnician(route.technician_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") selectTechnician(route.technician_id); }}>
                        <td><div className="sg-table-tech"><Avatar>{initials(route.technician_name ?? route.technician_id)}</Avatar><strong>{route.technician_name ?? route.technician_id}</strong></div></td>
                        <td>{route.stops.map((stop) => stopName(stop, siteLookup)).join(" → ") || "No assigned stop"}</td>
                        <td>{displaySkill(route.skills)}</td>
                        <td>{route.stops.length}</td>
                        <td>{formatMinutes(route.travel_duration_min)}<small>{formatMinutes(route.job_duration_min)} service</small></td>
                        <td>{formatKm(route.distance_km)}</td>
                        <td>{formatKwh(routeEnergy(route))}</td>
                        <td><StatusBadge status={status} /></td>
                      </tr>;
                    })}</tbody>
                  </table>
                  <div className="sg-plan-mobile-list">{filteredRoutes.map((route) => <button type="button" key={route.technician_id} className={selectedRoute?.technician_id === route.technician_id ? "is-selected" : ""} onClick={() => selectTechnician(route.technician_id)}><span><Avatar>{initials(route.technician_name ?? route.technician_id)}</Avatar><StatusBadge status={routeStatus(plan, route)} /></span><strong>{route.technician_name ?? route.technician_id}<small>{displaySkill(route.skills)}</small></strong><dl><div><dt>Jobs</dt><dd>{route.stops.length}</dd></div><div><dt>Next stop</dt><dd>{route.stops[0] ? stopName(route.stops[0], siteLookup) : "None"}</dd></div><div><dt>Distance</dt><dd>{formatKm(route.distance_km)}</dd></div></dl></button>)}</div>
                </div>
                <div className="sg-plan-pagination">Showing 1 to {filteredRoutes.length} of {filteredRoutes.length} technician plans <span>Page 1</span></div>
              </>
            )}
          </section>
          {plan ? <UnassignedJobs plan={plan} /> : null}
        </div>

        <aside className="sg-plan-rail">
          {loading || !plan ? <Skeleton active /> : <RouteMap routes={filteredRoutes} selectedTechnician={selectedRoute?.technician_id} selectedStop={selectedStop} onSelectTechnician={selectTechnician} onSelectStop={(id) => setParam("stop", id)} sites={siteLookup} />}
          {plan ? <SelectedTechnician route={selectedRoute} plan={plan} selectedStop={selectedStop} onSelectStop={(id) => setParam("stop", id)} sites={siteLookup} /> : null}
          {plan ? <PlanImpact plan={plan} onViewRoute={() => setRouteDialogOpen(true)} onDownload={() => void runDownload()} downloadState={downloadState} /> : null}
        </aside>
      </div>
      {plan ? <FullRouteDialog open={routeDialogOpen} plan={plan} sites={siteLookup} onClose={() => setRouteDialogOpen(false)} /> : null}
    </div>
  );
};
