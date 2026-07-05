import {
  AlertOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  CloudOutlined,
  EnvironmentOutlined,
  EyeOutlined,
  NodeIndexOutlined,
  RadarChartOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Card, Space } from "antd";
import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AxiosError } from "axios";

import heroImage from "../../assets/solar-hero-sunrise.png";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingSection } from "../../components/feedback/LoadingSection";
import {
  useFleetSummary,
  useFleetTimeseries,
  useLatestRoutePlan,
  useOptimizeRoutes,
  useRefreshOperations,
  useRunAnalysis,
  useServiceQueue,
} from "../../hooks/useOperationsData";
import type { ServiceDecision } from "../../api/schemas/decisions";
import type { LatestRoutePlan } from "../../api/schemas/routes";
import {
  formatInr,
  formatInteger,
  formatKm,
  formatKwh,
  formatMinutes,
  formatPercent,
} from "../../utils/format";
import {
  commandGenerationOption,
  displayIssue,
  incidentDonutOption,
  issueColor,
  issueDistribution,
  latestGenerationWindow,
  latestIrradianceReading,
  planReadinessPercent,
  topPriorityActions,
  topPriorityEvidence,
  zeroDistanceMessage,
} from "./data";

const isNotFoundError = (error?: unknown) =>
  error instanceof AxiosError && error.response?.status === 404;

const formatAnalysisTime = (value?: string) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Asia/Kolkata",
      }).format(new Date(value))
    : "Unavailable";

const tomorrowInKolkata = () =>
  new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  })
    .format(new Date(Date.now() + 24 * 60 * 60 * 1000))
    .split("/")
    .reverse()
    .join("-");

const priorityClass = (priority: string): string =>
  `sg-badge priority-${priority.toLowerCase()}`;

const routePreviewPalette = ["#43A7FF", "#F05A8A", "#2FD7A3", "#9A65F7"];

const totalFieldStops = (route?: LatestRoutePlan): number =>
  route?.field_plan.reduce((total, technician) => total + technician.stops.length, 0) ?? 0;

const actionLabel = (value: string): string =>
  value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

type KPIItemProps = {
  icon: React.ReactNode;
  label: string;
  value?: string;
  unit?: string;
  note: string;
  tone: "critical" | "remote" | "field" | "risk" | "recover";
  loading?: boolean;
};

const KPIItem = ({
  icon,
  label,
  value,
  unit,
  note,
  tone,
  loading = false,
}: KPIItemProps) => (
  <div className="sg-kpi-item">
    <span className={`sg-kpi-icon ${tone}`}>{icon}</span>
    <div>
      <span className="sg-kpi-label">{label}</span>
      {loading ? (
        <div className="sg-kpi-skeleton" aria-hidden="true">
          <i />
          <b />
        </div>
      ) : (
        <strong>
          {value ?? "—"}
          {unit ? <small>{unit}</small> : null}
        </strong>
      )}
      <p>{note}</p>
    </div>
  </div>
);

const WeatherOverviewCard = ({
  hasAnalysis,
  isLoading,
  monitoredSites,
  reportingSites,
  latestIrradiance,
  lastAnalysisTime,
}: {
  hasAnalysis: boolean;
  isLoading: boolean;
  monitoredSites?: number;
  reportingSites?: number;
  latestIrradiance: number | null;
  lastAnalysisTime?: string;
}) => (
  <aside className="sg-weather-card" aria-label="Site and weather overview">
    <span className="sg-card-title">SITE &amp; WEATHER OVERVIEW</span>
    <p>
      <EnvironmentOutlined /> Pune Cluster, Maharashtra
    </p>
    {isLoading ? (
      <LoadingSection compact rows={4} />
    ) : (
      <>
        <div className="sg-weather-main">
          <CloudOutlined className="sg-weather-icon" />
          <strong>
            {hasAnalysis && latestIrradiance !== null
              ? `${Math.round(latestIrradiance)} W/m²`
              : hasAnalysis
                ? "Weather data unavailable"
                : "Analysis required"}
          </strong>
          <span className="sg-weather-note">
            {hasAnalysis && latestIrradiance !== null
              ? "Latest observed irradiance across reporting sites"
              : "Weather context is not available yet."}
          </span>
        </div>
        <dl>
          <div>
            <dt>Sites monitored</dt>
            <dd>{monitoredSites != null ? formatInteger(monitoredSites) : "—"}</dd>
          </div>
          <div>
            <dt>Sites reporting</dt>
            <dd>{reportingSites != null ? formatInteger(reportingSites) : "—"}</dd>
          </div>
          <div>
            <dt>Last analysis</dt>
            <dd>{hasAnalysis ? lastAnalysisTime ?? "Unavailable" : "Analysis required"}</dd>
          </div>
        </dl>
        <small>
          {hasAnalysis
            ? "Weather and site coverage context for today’s fleet view."
            : "Run SolarGuard analysis to populate fleet context."}
        </small>
      </>
    )}
  </aside>
);

const PageLifecycleBanner = ({
  hasAnalysis,
  isLoading,
  isRunning,
  onRunAnalysis,
}: {
  hasAnalysis: boolean;
  isLoading: boolean;
  isRunning: boolean;
  onRunAnalysis: () => void;
}) => {
  if (hasAnalysis || isLoading) {
    return null;
  }

  return (
    <div className="sg-command-banner" role="status">
      <div>
        <strong>No completed fleet analysis is available.</strong>
        <p>
          Run SolarGuard analysis to generate expected generation, incidents,
          service priorities, and technician routes.
        </p>
      </div>
      <Button loading={isRunning} onClick={onRunAnalysis} type="primary">
        Run Analysis
      </Button>
    </div>
  );
};

const QueuePreview = ({
  items,
  openSite,
}: {
  items: ServiceDecision[];
  openSite: (siteId: string) => void;
}) => (
  <Card
    className="sg-card sg-queue-card"
    title={
      <Space>
        <span className="sg-card-title">SERVICE PRIORITY QUEUE</span>
        <span className="sg-count-pill">{items.length} items</span>
      </Space>
    }
    extra={
      <Link to="/service-queue" className="sg-card-action">
        View full queue <ArrowRightOutlined />
      </Link>
    }
  >
    {items.length ? (
      <div className="sg-queue-table" role="table" aria-label="Service priority queue">
        <div className="sg-queue-head" role="row">
          <span>Priority</span>
          <span>Site</span>
          <span>Probable Issue</span>
          <span>Confidence</span>
          <span>Value at Risk</span>
          <span>Recommended Action</span>
        </div>
        {items.slice(0, 5).map((item) => (
          <button
            key={item.decision_id}
            className="sg-queue-row"
            type="button"
            aria-label={`Open ${item.site_id}`}
            onClick={() => openSite(item.site_id)}
          >
            <span className={priorityClass(item.priority_label)}>
              {item.priority_label}
            </span>
            <span>{item.site_id}</span>
            <span>{displayIssue(item.probable_issue)}</span>
            <span>{formatPercent(item.confidence_score)}</span>
            <span>{formatInr(item.estimated_value_at_risk_inr)}</span>
            <span>{actionLabel(item.recommended_action)}</span>
          </button>
        ))}
      </div>
    ) : (
      <EmptyState
        title="No sites currently require field attention."
        description="Open Incidents to review remote-check candidates and monitoring states."
        action={
          <Link to="/incidents">
            <Button>Open Incidents</Button>
          </Link>
        }
      />
    )}
  </Card>
);

const EvidenceCard = ({
  item,
  onRunAnalysis,
  isRunning,
}: {
  item?: ServiceDecision;
  onRunAnalysis: () => void;
  isRunning: boolean;
}) => {
  if (!item) {
    return (
      <Card className="sg-card sg-evidence-card">
        <EmptyState
          title="No priority evidence available."
          description="Run analysis to populate the ranked service queue."
          action={
            <Button loading={isRunning} onClick={onRunAnalysis} type="primary">
              Run Analysis
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <Card
      className="sg-card sg-evidence-card"
      title={
        <Space>
          <span className="sg-card-title danger">TOP PRIORITY EVIDENCE</span>
          <span className={priorityClass(item.priority_label)}>{item.priority_label}</span>
        </Space>
      }
    >
      <h3>{displayIssue(item.probable_issue)}</h3>
      <p className="sg-meta">
        <EnvironmentOutlined /> {item.site_id} <span>•</span> Confidence{" "}
        {formatPercent(item.confidence_score)}
      </p>
      <div className="sg-evidence-metrics">
        <span>
          <small>Why</small>
          {item.supporting_evidence[0] ?? "Evidence not exposed"}
        </span>
        <span>
          <small>Energy Value at Risk</small>
          {formatInr(item.estimated_value_at_risk_inr)}
        </span>
        <span>
          <small>Recommended Action</small>
          {actionLabel(item.recommended_action)}
        </span>
      </div>
      <div className="sg-evidence-list">
        <strong>Supporting evidence</strong>
        {item.supporting_evidence.slice(0, 3).map((evidence) => (
          <p key={evidence}>
            <CheckCircleOutlined /> {evidence}
          </p>
        ))}
        {item.contradictory_evidence.length ? (
          <p>
            <WarningOutlined /> Conflicting evidence exists; review before dispatch.
          </p>
        ) : null}
      </div>
      <Link to={`/sites/${item.site_id}`}>
        <Button className="sg-secondary-button">
          View incident details <ArrowRightOutlined />
        </Button>
      </Link>
    </Card>
  );
};

const RoutePreview = ({ route }: { route?: LatestRoutePlan }) => {
  const technicians = useMemo(() => {
    if (!route) {
      return [];
    }

    return route.field_plan.map((technician, index) => ({
      ...technician,
      color: routePreviewPalette[index % routePreviewPalette.length],
    }));
  }, [route]);

  const routeNodes = useMemo(() => {
    const allStops = technicians.flatMap((technician) =>
      technician.stops.map((stop) => ({
        technicianId: technician.technician_id,
        technicianName: technician.technician_name ?? technician.technician_id,
        sequence: stop.sequence,
        siteId: stop.job.site_id,
        arrival: stop.arrival,
        latitude: stop.job.latitude,
        longitude: stop.job.longitude,
        color: technician.color,
      })),
    );

    if (!allStops.length) {
      return [];
    }

    const longitudes = allStops.map((stop) => stop.longitude);
    const latitudes = allStops.map((stop) => stop.latitude);
    const minLongitude = Math.min(...longitudes);
    const maxLongitude = Math.max(...longitudes);
    const minLatitude = Math.min(...latitudes);
    const maxLatitude = Math.max(...latitudes);
    const longitudeSpan = maxLongitude - minLongitude || 0.08;
    const latitudeSpan = maxLatitude - minLatitude || 0.08;

    return allStops.map((stop) => ({
      ...stop,
      x: 16 + ((stop.longitude - minLongitude) / longitudeSpan) * 68,
      y: 78 - ((stop.latitude - minLatitude) / latitudeSpan) * 56,
    }));
  }, [technicians]);

  return (
    <Card
      className="sg-card sg-route-card"
      title={<span className="sg-card-title">TECHNICIAN ROUTE PREVIEW</span>}
      extra={<span className="sg-select-chip">Pune Cluster</span>}
    >
      {route ? (
        <div className="sg-route-layout">
          <div className="sg-map-preview" aria-label="Pune route preview based on planned route stops">
            <svg
              className="sg-route-map-svg"
              viewBox="0 0 100 100"
              role="img"
              aria-label="Technician route sketch"
            >
              {technicians.map((technician) => {
                const points = routeNodes
                  .filter((node) => node.technicianId === technician.technician_id)
                  .sort((left, right) => left.sequence - right.sequence)
                  .map((node) => `${node.x},${node.y}`)
                  .join(" ");
                return points ? (
                  <polyline
                    key={technician.technician_id}
                    points={points}
                    fill="none"
                    stroke={technician.color}
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                ) : null;
              })}
              {routeNodes.map((node) => (
                <g key={`${node.technicianId}-${node.sequence}`} transform={`translate(${node.x}, ${node.y})`}>
                  <circle r="4.2" fill={node.color} stroke="#dcecff" strokeWidth="1.1" />
                  <text y="1.4" textAnchor="middle" fill="#f2f7fc" fontSize="4.2" fontWeight="700">
                    {node.sequence}
                  </text>
                </g>
              ))}
              <g transform="translate(50, 56)">
                <circle r="4.4" fill="#2FD7A3" stroke="#dcecff" strokeWidth="1.1" />
                <text y="1.4" textAnchor="middle" fill="#f2f7fc" fontSize="4.2" fontWeight="700">
                  H
                </text>
              </g>
            </svg>
            <span className="sg-map-label">Pune</span>
            <div className="sg-route-legend" aria-label="Technician route legend">
              {technicians.map((technician) => (
                <span key={technician.technician_id}>
                  <i style={{ backgroundColor: technician.color }} />
                  {technician.technician_name ?? technician.technician_id}
                </span>
              ))}
            </div>
            <span className="sg-map-hub">
              <NodeIndexOutlined />
              Service hub
            </span>
          </div>
          <div className="sg-route-panel">
            <div className="sg-route-summary">
              <span>{formatInteger(totalFieldStops(route))} jobs</span>
              <span>{formatKm(route.optimised_distance_km)}</span>
              <span>{formatMinutes(route.total_travel_duration_min)}</span>
            </div>
            <div className="sg-route-tech-list" aria-label="Technician route groups">
              {technicians.map((technician) => (
                <section key={technician.technician_id} className="sg-route-tech-group">
                  <header>
                    <span className="sg-route-tech-dot" style={{ backgroundColor: technician.color }} />
                    <strong>{technician.technician_name ?? technician.technician_id}</strong>
                    <small>
                      {technician.stops.length} stops • {formatKm(technician.distance_km)}
                    </small>
                  </header>
                  <ol className="sg-route-list">
                    {technician.stops.map((stop) => (
                      <li key={`${stop.technician_id}-${stop.sequence}`}>
                        <span style={{ backgroundColor: technician.color }}>{stop.sequence}</span>
                        <div className="sg-route-stop-copy">
                          <strong>{stop.job.site_id}</strong>
                          <small>{actionLabel(stop.job.recommended_action)}</small>
                        </div>
                        <small>ETA {formatAnalysisTime(stop.arrival)}</small>
                      </li>
                    ))}
                  </ol>
                </section>
              ))}
            </div>
            <p>{zeroDistanceMessage(route)}</p>
            <Link to="/technician-plan">
              <Button type="primary" block icon={<ThunderboltOutlined />}>
                Open Technician Plan
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No valid route has been generated."
          description="This usually means there are no field-worthy jobs, a technician skill mismatch, or a route constraint to review."
          action={
            <Link to="/technician-plan">
              <Button>Open Technician Plan</Button>
            </Link>
          }
        />
      )}
    </Card>
  );
};

export const CommandCentrePage = () => {
  const navigate = useNavigate();
  const refreshOperations = useRefreshOperations();
  const runAnalysis = useRunAnalysis();
  const optimizeRoutes = useOptimizeRoutes();
  const fleetSummary = useFleetSummary();
  const serviceQueue = useServiceQueue();
  const latestRoute = useLatestRoutePlan();
  const fleetTimeseries = useFleetTimeseries();

  const summary = fleetSummary.data;
  const hasAnalysis = Boolean(summary?.analysis_run_id);
  const queueItems = useMemo(
    () => serviceQueue.data?.items ?? [],
    [serviceQueue.data],
  );
  const topActions = useMemo(() => topPriorityActions(queueItems), [queueItems]);
  const topEvidence = useMemo(() => topPriorityEvidence(queueItems), [queueItems]);
  const incidentCounts = useMemo(() => issueDistribution(queueItems), [queueItems]);
  const incidentTotal = useMemo(
    () => incidentCounts.reduce((total, item) => total + item.value, 0),
    [incidentCounts],
  );
  const route = isNotFoundError(latestRoute.error) ? undefined : latestRoute.data;
  const readiness = planReadinessPercent(route);
  const generationRows = useMemo(
    () => latestGenerationWindow(fleetTimeseries.data?.items ?? []),
    [fleetTimeseries.data?.items],
  );
  const latestIrradiance = useMemo(
    () => latestIrradianceReading(generationRows),
    [generationRows],
  );
  const reportingSites =
    summary != null
      ? Math.max(summary.monitored_sites - summary.communication_issues, 0)
      : undefined;
  const lastAnalysisTime = queueItems[0]?.created_at
    ? formatAnalysisTime(queueItems[0].created_at)
    : undefined;
  const pageError = fleetSummary.error && !summary;
  const initialLoading = fleetSummary.isLoading && !summary;
  const partialWarning =
    (Boolean(serviceQueue.error) ||
      Boolean(fleetTimeseries.error) ||
      (Boolean(latestRoute.error) && !isNotFoundError(latestRoute.error))) &&
    hasAnalysis;

  const openSite = (siteId: string): void => {
    void navigate(`/sites/${siteId}`);
  };

  const handleRunAnalysis = async (): Promise<void> => {
    await runAnalysis.mutateAsync(undefined);
  };

  const handleGeneratePlan = async (): Promise<void> => {
    if (!summary?.analysis_run_id) {
      return;
    }
    await optimizeRoutes.mutateAsync({
      analysisRunId: summary.analysis_run_id,
      planningDate: route?.planning_date ?? tomorrowInKolkata(),
    });
    refreshOperations();
    void navigate("/technician-plan");
  };

  if (pageError) {
    return (
      <ErrorState
        error={pageError}
        title="Unable to load the Command Centre."
        onRetry={refreshOperations}
      />
    );
  }

  return (
    <div className="sg-command-page">
      <section
        className="sg-hero"
        style={{ backgroundImage: `url(${heroImage})` }}
        aria-labelledby="command-centre-title"
      >
        <div className="sg-hero-copy">
          <span className="sg-eyebrow">COMMAND CENTRE</span>
          <h1 id="command-centre-title">Focus on impact today.</h1>
          <p>
            Resolve critical alerts, recover energy, and de-risk tomorrow&apos;s shift.
          </p>
          <Button
            disabled={!hasAnalysis}
            loading={optimizeRoutes.isPending}
            type="primary"
            onClick={() => void handleGeneratePlan()}
          >
            Generate Tomorrow&apos;s O&amp;M Plan <ArrowRightOutlined />
          </Button>
        </div>
        <WeatherOverviewCard
          hasAnalysis={hasAnalysis}
          isLoading={initialLoading}
          monitoredSites={summary?.monitored_sites}
          reportingSites={reportingSites}
          latestIrradiance={latestIrradiance}
          lastAnalysisTime={lastAnalysisTime}
        />
      </section>

      <section className="sg-kpi-strip" aria-label="Fleet operation KPIs">
        <KPIItem
          icon={<AlertOutlined />}
          label="Sites Requiring Attention"
          loading={initialLoading}
          note={
            hasAnalysis
              ? `${formatInteger(summary?.communication_issues ?? 0)} communication cases`
              : "Analysis required"
          }
          tone="critical"
          value={hasAnalysis ? formatInteger(summary?.attention_sites ?? 0) : "—"}
        />
        <KPIItem
          icon={<RadarChartOutlined />}
          label="Remote Resolution Candidates"
          loading={initialLoading}
          note={hasAnalysis ? "Remote checks before dispatch" : "Analysis required"}
          tone="remote"
          value={hasAnalysis ? formatInteger(summary?.remote_actions ?? 0) : "—"}
        />
        <KPIItem
          icon={<ToolOutlined />}
          label="Field Visits Recommended"
          loading={initialLoading}
          note={hasAnalysis ? "Visit-required service decisions" : "Analysis required"}
          tone="field"
          value={hasAnalysis ? formatInteger(summary?.field_visits ?? 0) : "—"}
        />
        <KPIItem
          icon={<ThunderboltOutlined />}
          label="Energy Value at Risk"
          loading={initialLoading}
          note={hasAnalysis ? "Estimated from current service priorities" : "Analysis required"}
          tone="risk"
          value={hasAnalysis ? formatInr(summary?.estimated_energy_value_at_risk_inr ?? 0) : "—"}
        />
        <KPIItem
          icon={<ReloadOutlined />}
          label="Recoverable Energy Estimate"
          loading={initialLoading}
          note={
            hasAnalysis
              ? `${formatInr(summary?.estimated_recoverable_value_inr ?? 0)} recoverable value`
              : "Analysis required"
          }
          tone="recover"
          value={hasAnalysis ? formatKwh(summary?.estimated_recoverable_energy_kwh ?? 0) : "—"}
        />
      </section>

      <PageLifecycleBanner
        hasAnalysis={hasAnalysis}
        isLoading={initialLoading}
        isRunning={runAnalysis.isPending}
        onRunAnalysis={() => void handleRunAnalysis()}
      />

      {partialWarning ? (
        <div className="sg-state-ribbon" role="status">
          <WarningOutlined /> Some Command Centre sections are partially available.
          Review section-level warnings and refresh the operational data.
        </div>
      ) : null}

      {summary?.insufficient_evidence ? (
        <div className="sg-state-ribbon">
          <EyeOutlined /> {formatInteger(summary.insufficient_evidence)} sites have
          unknown or insufficient evidence. Collect additional telemetry before
          dispatch decisions.
        </div>
      ) : null}

      <section className="sg-analytics-grid">
        <Card
          className="sg-card sg-generation-card"
          title={<span className="sg-card-title">EXPECTED VS ACTUAL GENERATION</span>}
          extra={<span className="sg-select-chip">Today</span>}
        >
          {fleetTimeseries.isLoading && !generationRows.length ? (
            <LoadingSection rows={5} />
          ) : fleetTimeseries.error ? (
            <ErrorState
              error={fleetTimeseries.error}
              onRetry={() => void fleetTimeseries.refetch()}
            />
          ) : generationRows.length ? (
            <>
              <EChart
                option={commandGenerationOption(generationRows)}
                ariaLabel="Expected generation, actual generation and irradiance trend"
                expandable
                expandedTitle="Expected vs Actual Generation"
              />
              <Link to="/diagnostics" className="sg-card-button">
                View generation analytics <ArrowRightOutlined />
              </Link>
            </>
          ) : (
            <EmptyState
              title="No fleet time series available."
              description="Run analysis to generate expected-versus-actual performance."
              action={
                <Button
                  loading={runAnalysis.isPending}
                  onClick={() => void handleRunAnalysis()}
                  type="primary"
                >
                  Run Analysis
                </Button>
              }
            />
          )}
        </Card>

        <div className="sg-command-summary-rail">
          <Card
            className="sg-card sg-command-incident-card"
            title={<span className="sg-card-title">INCIDENT DISTRIBUTION</span>}
          >
            {serviceQueue.isLoading && !queueItems.length ? (
              <LoadingSection rows={3} />
            ) : serviceQueue.error ? (
              <ErrorState error={serviceQueue.error} onRetry={() => void serviceQueue.refetch()} />
            ) : incidentCounts.length ? (
              <>
                <div className="sg-command-incident-layout">
                  <EChart
                    option={incidentDonutOption(incidentCounts)}
                    expandedOption={incidentDonutOption(incidentCounts, { showLegend: true })}
                    ariaLabel="Incident distribution by probable issue category"
                    className="sg-command-incident-chart"
                    expandable
                    expandedTitle="Incident Distribution"
                  />
                  <dl className="sg-command-incident-summary">
                    {incidentCounts.map((item) => (
                      <div key={item.name}>
                        <dt>
                          <i style={{ backgroundColor: issueColor(item.name) }} />
                          <span>{item.name}</span>
                        </dt>
                        <dd>
                          {formatInteger(item.value)}{" "}
                          <span>
                            ({incidentTotal ? formatPercent((item.value / incidentTotal) * 100) : "0%"})
                          </span>
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <Link to="/incidents" className="sg-card-button">
                  View all incidents <ArrowRightOutlined />
                </Link>
              </>
            ) : (
              <EmptyState title="No active service incidents." />
            )}
          </Card>

          <Card
            className="sg-card sg-operations-card"
            title={<span className="sg-card-title">TODAY&apos;S OPERATIONS</span>}
          >
            {latestRoute.isLoading && !route ? (
              <LoadingSection rows={3} />
            ) : latestRoute.error && !isNotFoundError(latestRoute.error) ? (
              <ErrorState error={latestRoute.error} onRetry={() => void latestRoute.refetch()} />
            ) : route ? (
              <dl className="sg-ops-kpi-grid">
                <div className="is-readiness">
                  <dt>Plan Readiness</dt>
                  <dd>{formatPercent(readiness)}</dd>
                </div>
                <div>
                  <dt>Field Jobs</dt>
                  <dd>{formatInteger(route.assigned_jobs)}</dd>
                </div>
                <div>
                  <dt>Technicians</dt>
                  <dd>{formatInteger(route.field_plan.length)}</dd>
                </div>
                <div>
                  <dt>Distance</dt>
                  <dd>{formatKm(route.optimised_distance_km)}</dd>
                </div>
                <div>
                  <dt>Distance Avoided</dt>
                  <dd>{formatKm(route.distance_avoided_km)}</dd>
                </div>
                <div>
                  <dt>Unassigned</dt>
                  <dd>{formatInteger(route.unassigned_jobs_count)}</dd>
                </div>
              </dl>
            ) : (
              <EmptyState
                title="No technician plan generated."
                description="Generate or review the service queue before planning."
                action={
                  <Link to="/service-queue">
                    <Button>View Service Queue</Button>
                  </Link>
                }
              />
            )}
            <Link to={route ? "/technician-plan" : "/service-queue"} className="sg-card-button">
              {route ? "View today’s plan" : "View Service Queue"} <ArrowRightOutlined />
            </Link>
          </Card>
        </div>
      </section>
      <section className="sg-ops-grid">
        <div className="sg-ops-left-rail">
          {serviceQueue.isLoading && !queueItems.length ? (
            <Card className="sg-card sg-queue-card">
              <LoadingSection rows={5} />
            </Card>
          ) : serviceQueue.error ? (
            <Card className="sg-card sg-queue-card">
              <ErrorState error={serviceQueue.error} onRetry={() => void serviceQueue.refetch()} />
            </Card>
          ) : (
            <QueuePreview items={topActions} openSite={openSite} />
          )}

          <EvidenceCard
            item={topEvidence}
            onRunAnalysis={() => void handleRunAnalysis()}
            isRunning={runAnalysis.isPending}
          />
        </div>

        {latestRoute.isLoading && !route ? (
          <Card className="sg-card sg-route-card">
            <LoadingSection rows={5} />
          </Card>
        ) : (
          <RoutePreview route={route} />
        )}
      </section>
    </div>
  );
};


