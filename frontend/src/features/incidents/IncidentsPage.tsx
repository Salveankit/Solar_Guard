import {
  AlertOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  EllipsisOutlined,
  FieldTimeOutlined,
  FileDoneOutlined,
  InfoCircleOutlined,
  LineChartOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Card, Modal, Skeleton, Tooltip } from "antd";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import incidentsHeroImage from "../../assets/incidents-hero.png";
import { solarGuardTokens } from "../../app/theme";
import type { ServiceDecision } from "../../api/schemas/decisions";
import type { SiteSummary } from "../../api/schemas/sites";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import {
  useRefreshOperations,
  useServiceQueue,
  useSites,
} from "../../hooks/useOperationsData";
import {
  formatInr,
  formatInteger,
  formatKwh,
  formatPercent,
} from "../../utils/format";
import { displayIssue } from "../command-centre/data";

type PriorityFilter = "All" | "Critical" | "High" | "Medium" | "Low" | "CriticalHigh";
type ActionFilter = "all" | "remote" | "field";
type IssueFilter = "all" | IssueBucket;
type SortMode = "priority" | "impact";
type IssueBucket =
  | "communication"
  | "outage"
  | "gradual"
  | "time"
  | "unknown";

type IncidentRow = ServiceDecision & {
  site?: SiteSummary;
  issueBucket: IssueBucket;
};

const priorityFilters: PriorityFilter[] = ["All", "Critical", "High", "Medium", "Low"];
const pageSize = 5;

const issueBuckets: Record<IssueBucket, { label: string; color: string }> = {
  communication: {
    label: "Communication / Data Failure",
    color: solarGuardTokens.colorDanger,
  },
  outage: {
    label: "Sudden Production Outage",
    color: solarGuardTokens.colorWarning,
  },
  gradual: {
    label: "Gradual Underperformance",
    color: solarGuardTokens.colorInfo,
  },
  time: {
    label: "Time-Specific Underperformance",
    color: solarGuardTokens.colorSuccess,
  },
  unknown: {
    label: "Unknown / Insufficient Evidence",
    color: solarGuardTokens.colorUnknown,
  },
};

const priorityOrder: Record<string, number> = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
};

const issueBucketFor = (issue: string): IssueBucket => {
  const normalized = issue.toLowerCase();
  if (normalized.includes("communication") || normalized.includes("data")) {
    return "communication";
  }
  if (normalized.includes("sudden") || normalized.includes("outage") || normalized.includes("interruption")) {
    return "outage";
  }
  if (normalized.includes("gradual") || normalized.includes("soiling") || normalized.includes("degradation")) {
    return "gradual";
  }
  if (normalized.includes("time") || normalized.includes("shading") || normalized.includes("obstruction")) {
    return "time";
  }
  return "unknown";
};

const normaliseAction = (value: string): string =>
  value
    .replaceAll("_", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());

const formatShortInr = (value: number): string => {
  if (value >= 100000) {
    return `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value / 100000)}L`;
  }
  return formatInr(value);
};

const formatTime = (value?: string | null): string => {
  if (!value) {
    return "Unavailable";
  }
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
};

const detectedSince = (incident: IncidentRow): string =>
  `Reported ${formatTime(incident.created_at)}`;

const enrichIncidents = (
  items: ServiceDecision[],
  sites: SiteSummary[],
): IncidentRow[] => {
  const sitesById = new Map(sites.map((site) => [site.site_id, site]));
  return items.map((item) => ({
    ...item,
    site: sitesById.get(item.site_id),
    issueBucket: issueBucketFor(item.probable_issue),
  }));
};

const filterRows = (
  rows: IncidentRow[],
  priority: PriorityFilter,
  action: ActionFilter,
  issue: IssueFilter,
): IncidentRow[] =>
  rows.filter((row) => {
    const priorityMatch =
      priority === "All" ||
      (priority === "CriticalHigh" && ["Critical", "High"].includes(row.priority_label)) ||
      row.priority_label === priority;
    const actionMatch =
      action === "all" ||
      (action === "remote" && row.remote_action_available && !row.visit_required) ||
      (action === "field" && row.visit_required);
    const issueMatch = issue === "all" || row.issueBucket === issue;
    return priorityMatch && actionMatch && issueMatch;
  });

const sortRows = (rows: IncidentRow[], sort: SortMode): IncidentRow[] =>
  [...rows].sort((left, right) => {
    if (sort === "impact") {
      return right.estimated_value_at_risk_inr - left.estimated_value_at_risk_inr;
    }
    return (
      (priorityOrder[right.priority_label] ?? 0) - (priorityOrder[left.priority_label] ?? 0) ||
      right.priority_score - left.priority_score
    );
  });

const distributionOption = (rows: IncidentRow[]): EChartsOption => {
  const data = (Object.keys(issueBuckets) as IssueBucket[]).map((bucket) => ({
    name: issueBuckets[bucket].label,
    value: rows.filter((row) => row.issueBucket === bucket).length,
    bucket,
  }));
  const total = data.reduce((sum, item) => sum + item.value, 0);
  return {
    color: data.map((item) => issueBuckets[item.bucket].color),
    tooltip: { trigger: "item" },
    legend: { show: false },
    series: [
      {
        name: "Incident distribution",
        type: "pie",
        radius: ["52%", "74%"],
        center: ["30%", "52%"],
        label: { show: false },
        itemStyle: {
          borderColor: solarGuardTokens.colorSurface,
          borderWidth: 2,
        },
        data,
      },
    ],
    graphic: [
      {
        type: "text",
        left: "26%",
        top: "42%",
        style: {
          text: String(total),
          fill: solarGuardTokens.colorText,
          fontSize: 28,
          fontWeight: 650,
          align: "center",
        },
      },
      {
        type: "text",
        left: "25%",
        top: "57%",
        style: {
          text: "Total",
          fill: solarGuardTokens.colorTextSecondary,
          fontSize: 12,
          align: "center",
        },
      },
    ],
  };
};

const miniEvidenceOption = (incident: IncidentRow): EChartsOption => ({
  color: [solarGuardTokens.chartExpected, solarGuardTokens.chartActual],
  grid: { left: 6, right: 6, top: 8, bottom: 8 },
  xAxis: { show: false, type: "category", data: ["1", "2", "3", "4", "5", "6"] },
  yAxis: { show: false, type: "value" },
  series: [
    {
      name: "Expected",
      type: "line",
      showSymbol: false,
      data: [6, 7, 8, 8, 7, 6],
      lineStyle: { width: 2, type: "dashed" },
    },
    {
      name: "Actual",
      type: "line",
      showSymbol: false,
      data:
        incident.issueBucket === "communication"
          ? [null, null, null, null, null, null]
          : incident.issueBucket === "unknown"
            ? [5, null, 4, 6, null, 5]
            : [6, 6.5, 1, 0.4, 0.2, 0.5],
      lineStyle: { width: 2 },
    },
  ],
});

const PriorityBadge = ({ value }: { value: ServiceDecision["priority_label"] }) => (
  <span className={`sg-incident-priority priority-${value.toLowerCase()}`}>
    <i />
    {value}
  </span>
);

const StatusBadge = ({ incident }: { incident: IncidentRow }) => {
  const label = incident.visit_required
    ? "Review"
    : incident.remote_action_available
      ? "Remote"
      : incident.actionable
        ? "Active"
        : "Monitor";
  return <span className={`sg-incident-status ${label.toLowerCase()}`}>{label}</span>;
};

const KpiItem = ({
  icon,
  label,
  value,
  note,
  tone,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  tone: string;
  onClick: () => void;
}) => (
  <button type="button" className="sg-incident-kpi" onClick={onClick}>
    <span className={`sg-incident-kpi-icon ${tone}`}>{icon}</span>
    <span>
      <small>{label}</small>
      <strong>{value}</strong>
      <em>{note}</em>
    </span>
  </button>
);

const IncidentOverview = ({ rows }: { rows: IncidentRow[] }) => {
  const critical = rows.filter((item) => item.priority_label === "Critical").length;
  const remote = rows.filter((item) => item.remote_action_available && !item.visit_required).length;
  const field = rows.filter((item) => item.visit_required).length;
  return (
    <aside className="sg-incident-overview">
      <div>
        <strong>Incident overview</strong>
        <span><i />Live</span>
      </div>
      <dl>
        <div>
          <dt><AlertOutlined /> Active incidents</dt>
          <dd>{formatInteger(rows.length)}</dd>
        </div>
        <div>
          <dt><WarningOutlined /> Critical</dt>
          <dd>{formatInteger(critical)}</dd>
        </div>
        <div>
          <dt><NodeIndexOutlined /> Remote-check candidates</dt>
          <dd>{formatInteger(remote)}</dd>
        </div>
        <div>
          <dt><FieldTimeOutlined /> Field-review candidates</dt>
          <dd>{formatInteger(field)}</dd>
        </div>
      </dl>
    </aside>
  );
};

const IncidentTable = ({
  rows,
  selectedId,
  onSelect,
}: {
  rows: IncidentRow[];
  selectedId?: string;
  onSelect: (row: IncidentRow) => void;
}) => (
  <div className="sg-incident-table-wrap">
    <table className="sg-incident-table">
      <thead>
        <tr>
          <th>Priority</th>
          <th>Site</th>
          <th>Probable Issue</th>
          <th>Confidence</th>
          <th>Energy Value at Risk</th>
          <th>Recommended Action</th>
          <th>Status</th>
          <th>More</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.decision_id}
            className={row.decision_id === selectedId ? "is-selected" : ""}
            aria-selected={row.decision_id === selectedId}
            tabIndex={0}
            onClick={() => onSelect(row)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(row);
              }
            }}
          >
            <td><PriorityBadge value={row.priority_label} /></td>
            <td>
              <strong>{row.site?.site_name ?? row.site_id}</strong>
              <small>{row.site_id}</small>
            </td>
            <td>{displayIssue(row.probable_issue)}</td>
            <td>
              <strong>{formatPercent(row.confidence_score)}</strong>
              <small>{row.confidence_label}</small>
            </td>
            <td>
              <strong>{formatShortInr(row.estimated_value_at_risk_inr)}</strong>
              <small>{formatKwh(row.estimated_energy_loss_kwh)}</small>
            </td>
            <td>{normaliseAction(row.recommended_action)}</td>
            <td><StatusBadge incident={row} /></td>
            <td>
              <Tooltip title="Select incident">
                <Button
                  className="sg-row-action"
                  aria-label={`Select incident ${row.decision_id}`}
                  icon={<EllipsisOutlined />}
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(row);
                  }}
                />
              </Tooltip>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const EvidencePreview = ({ incident }: { incident: IncidentRow }) => (
  <div className="sg-evidence-previews">
    <Tooltip title="Expected versus actual generation preview">
      <div>
        <EChart
          option={miniEvidenceOption(incident)}
          ariaLabel="Expected versus actual evidence preview"
        />
      </div>
    </Tooltip>
    <Tooltip title="Evidence summary">
      <div className="sg-evidence-text-thumb">
        <InfoCircleOutlined />
        <span>{incident.supporting_evidence[0] ?? "Evidence unavailable"}</span>
      </div>
    </Tooltip>
    <Tooltip title="Decision route preview">
      <div className="sg-evidence-text-thumb">
        <ToolOutlined />
        <span>{normaliseAction(incident.recommended_action)}</span>
      </div>
    </Tooltip>
  </div>
);

const SelectedIncident = ({ incident }: { incident?: IncidentRow }) => (
  <Card
    className="sg-card sg-selected-incident-card"
    title={<span className="sg-card-title">SELECTED INCIDENT</span>}
    extra={incident ? <StatusBadge incident={incident} /> : null}
  >
    {incident ? (
      <>
        <header>
          <div>
            <strong>{incident.site?.site_name ?? incident.site_id}</strong>
            <small>
              {incident.site_id} · {incident.site?.service_region ?? "Region unavailable"}
            </small>
          </div>
        </header>
        <dl className="sg-selected-incident-metrics">
          <div>
            <dt>Probable Issue</dt>
            <dd>{displayIssue(incident.probable_issue)}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>
              {formatPercent(incident.confidence_score)}
              <small>{incident.confidence_label}</small>
            </dd>
          </div>
          <div>
            <dt>Energy Value at Risk</dt>
            <dd>
              {formatShortInr(incident.estimated_value_at_risk_inr)}
              <small>{formatKwh(incident.estimated_energy_loss_kwh)}</small>
            </dd>
          </div>
          <div>
            <dt>Detected Since</dt>
            <dd>{detectedSince(incident)}</dd>
          </div>
        </dl>
        <p className="sg-evidence-summary">
          {incident.issueBucket === "communication"
            ? "Telemetry or heartbeat evidence indicates a data-quality incident. Missing readings are not treated as zero production."
            : incident.issueBucket === "unknown"
              ? "Available telemetry does not support a reliable probable-cause classification. Additional evidence is required."
              : incident.supporting_evidence[0] ?? "Supporting evidence is being prepared for this incident."}
        </p>
        <EvidencePreview incident={incident} />
      </>
    ) : (
      <EmptyState title="Select an incident" description="Choose a queue row to inspect supporting evidence." />
    )}
  </Card>
);

const RecommendedActions = ({
  incident,
  onOpenDiagnostics,
  onQueue,
}: {
  incident?: IncidentRow;
  onOpenDiagnostics: () => void;
  onQueue: () => void;
}) => {
  const steps = !incident
    ? []
    : incident.issueBucket === "communication"
      ? [
          "Run remote connectivity or inverter check",
          "Verify communication heartbeat and data gateway",
          "Escalate to field inspection if communication remains unavailable",
        ]
      : incident.issueBucket === "unknown"
        ? [
            "Collect additional telemetry before classification",
            "Run remote connectivity and data-quality checks",
            "Monitor until evidence supports a service decision",
          ]
        : [
            "Check inverter status remotely",
            "Verify grid-side interruption or site-side condition",
            "Create a field job only if remote checks do not resolve the issue",
          ];

  return (
    <Card
      className="sg-card sg-incident-actions-card"
      title={<span className="sg-card-title">RECOMMENDED NEXT ACTIONS</span>}
    >
      {incident ? (
        <>
          <ol>
            {steps.map((step, index) => (
              <li key={step}>
                <span>{index + 1}</span>
                {step}
              </li>
            ))}
          </ol>
          <div className="sg-incident-action-buttons">
            <Button icon={<LineChartOutlined />} onClick={onOpenDiagnostics}>
              Open Diagnostics
            </Button>
            <Button className="warning" icon={<FileDoneOutlined />} onClick={onQueue}>
              Move to Service Queue
            </Button>
          </div>
        </>
      ) : (
        <EmptyState title="No action selected" />
      )}
    </Card>
  );
};

export const IncidentsPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const refreshOperations = useRefreshOperations();
  const queueQuery = useServiceQueue();
  const sitesQuery = useSites();
  const [modalOpen, setModalOpen] = useState(false);
  const [queuedIds, setQueuedIds] = useState<Set<string>>(new Set());
  const [queueNotice, setQueueNotice] = useState<string | null>(null);

  const priority = (searchParams.get("priority") as PriorityFilter | null) ?? "All";
  const action = (searchParams.get("action") as ActionFilter | null) ?? "all";
  const issue = (searchParams.get("issue") as IssueFilter | null) ?? "all";
  const sort = (searchParams.get("sort") as SortMode | null) ?? "priority";
  const page = Math.max(Number(searchParams.get("page") ?? 1), 1);
  const selectedId = searchParams.get("selected") ?? undefined;

  const allRows = useMemo(
    () => enrichIncidents(queueQuery.data?.items ?? [], sitesQuery.data ?? []),
    [queueQuery.data, sitesQuery.data],
  );
  const filteredRows = useMemo(
    () => sortRows(filterRows(allRows, priority, action, issue), sort),
    [action, allRows, issue, priority, sort],
  );
  const pageCount = Math.max(Math.ceil(filteredRows.length / pageSize), 1);
  const safePage = Math.min(page, pageCount);
  const visibleRows = filteredRows.slice((safePage - 1) * pageSize, safePage * pageSize);
  const selectedIncident =
    filteredRows.find((row) => row.decision_id === selectedId) ??
    visibleRows[0] ??
    filteredRows[0] ??
    allRows[0];

  useEffect(() => {
    if (selectedIncident && selectedIncident.decision_id !== selectedId) {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        next.set("selected", selectedIncident.decision_id);
        return next;
      }, { replace: true });
    }
    if (safePage !== page) {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        next.set("page", String(safePage));
        return next;
      }, { replace: true });
    }
  }, [page, safePage, selectedId, selectedIncident, setSearchParams]);

  const setQueryValue = (key: string, value?: string): void => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (!value || value === "all" || value === "All") {
        next.delete(key);
      } else {
        next.set(key, value);
      }
      if (key !== "selected" && key !== "page") {
        next.set("page", "1");
      }
      return next;
    });
  };

  const clearFilters = (): void => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      ["priority", "action", "issue", "sort", "page"].forEach((key) => next.delete(key));
      return next;
    });
  };

  const selectedSiteId = selectedIncident?.site_id;
  const loading = queueQuery.isLoading || sitesQuery.isLoading;
  const error = queueQuery.error || sitesQuery.error;
  const activeCount = allRows.length;
  const criticalHigh = allRows.filter((row) => ["Critical", "High"].includes(row.priority_label)).length;
  const remoteCount = allRows.filter((row) => row.remote_action_available && !row.visit_required).length;
  const fieldCount = allRows.filter((row) => row.visit_required).length;
  const valueAtRisk = allRows.reduce((sum, row) => sum + row.estimated_value_at_risk_inr, 0);
  const siteCount = new Set(allRows.map((row) => row.site_id)).size;
  const start = filteredRows.length === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end = Math.min(safePage * pageSize, filteredRows.length);

  const openDiagnostics = (): void => {
    if (selectedSiteId) {
      void navigate(`/sites/${selectedSiteId}?incident=${selectedIncident?.decision_id ?? ""}`);
    }
  };

  const confirmQueue = (): void => {
    if (!selectedIncident) return;
    setQueuedIds((current) => new Set(current).add(selectedIncident.decision_id));
    setQueueNotice("Incident routed for service-queue review.");
    setModalOpen(false);
  };

  if (loading && allRows.length === 0) {
    return (
      <div className="sg-incidents-page">
        <section className="sg-incidents-loading">
          <Skeleton active paragraph={{ rows: 3 }} />
          <Skeleton active paragraph={{ rows: 8 }} />
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Unable to load incidents"
        error={error}
        onRetry={refreshOperations}
      />
    );
  }

  return (
    <div className="sg-incidents-page">
      <section
        className="sg-incidents-hero"
        style={{ backgroundImage: `url(${incidentsHeroImage})` }}
        aria-labelledby="incidents-title"
      >
        <div>
          <span className="sg-eyebrow">INCIDENTS</span>
          <h1 id="incidents-title">Triage operational incidents with precision.</h1>
          <p>
            Review, prioritize, and route incidents to the right action with confidence.
          </p>
        </div>
        <IncidentOverview rows={allRows} />
      </section>

      <section className="sg-incident-kpi-strip" aria-label="Incident summary KPIs">
        <KpiItem
          icon={<AlertOutlined />}
          label="Active Incidents"
          value={formatInteger(activeCount)}
          note={`Across ${formatInteger(siteCount)} sites`}
          tone="critical"
          onClick={clearFilters}
        />
        <KpiItem
          icon={<WarningOutlined />}
          label="Critical / High Priority"
          value={formatInteger(criticalHigh)}
          note={`${activeCount ? formatPercent((criticalHigh / activeCount) * 100) : "0%"} of active incidents`}
          tone="warning"
          onClick={() => setQueryValue("priority", "CriticalHigh")}
        />
        <KpiItem
          icon={<NodeIndexOutlined />}
          label="Remote-check Candidates"
          value={formatInteger(remoteCount)}
          note={`${activeCount ? formatPercent((remoteCount / activeCount) * 100) : "0%"} of active incidents`}
          tone="remote"
          onClick={() => setQueryValue("action", "remote")}
        />
        <KpiItem
          icon={<FieldTimeOutlined />}
          label="Field Visit Candidates"
          value={formatInteger(fieldCount)}
          note={`${activeCount ? formatPercent((fieldCount / activeCount) * 100) : "0%"} of active incidents`}
          tone="field"
          onClick={() => setQueryValue("action", "field")}
        />
        <KpiItem
          icon={<ThunderboltOutlined />}
          label="Energy Value at Risk"
          value={formatShortInr(valueAtRisk)}
          note="Across all incidents"
          tone="success"
          onClick={() => setQueryValue("sort", "impact")}
        />
      </section>

      <section className="sg-incidents-workspace">
        <Card
          className="sg-card sg-incident-queue-card"
          title={<span className="sg-card-title">INCIDENT QUEUE</span>}
        >
          <div className="sg-incident-filter-row" role="group" aria-label="Incident priority filters">
            {priorityFilters.map((item) => (
              <Button
                key={item}
                className={priority === item ? "is-active" : ""}
                onClick={() => setQueryValue("priority", item)}
              >
                {item}
              </Button>
            ))}
            <span className="sg-incident-secondary-filters">
              <Button
                className={action === "remote" ? "is-active" : ""}
                onClick={() => setQueryValue("action", action === "remote" ? "all" : "remote")}
              >
                Remote Check
              </Button>
              <Button
                className={action === "field" ? "is-active" : ""}
                onClick={() => setQueryValue("action", action === "field" ? "all" : "field")}
              >
                Field Review
              </Button>
            </span>
          </div>
          {visibleRows.length ? (
            <>
              <IncidentTable
                rows={visibleRows}
                selectedId={selectedIncident?.decision_id}
                onSelect={(row) => setQueryValue("selected", row.decision_id)}
              />
              <div className="sg-incident-pagination">
                <span>
                  Showing {formatInteger(start)} to {formatInteger(end)} of{" "}
                  {formatInteger(filteredRows.length)} incidents
                </span>
                <div>
                  <Button
                    aria-label="Previous incident page"
                    disabled={safePage <= 1}
                    onClick={() => setQueryValue("page", String(safePage - 1))}
                  >
                    Previous
                  </Button>
                  {Array.from({ length: Math.min(pageCount, 3) }, (_, index) => index + 1).map((item) => (
                    <Button
                      key={item}
                      className={item === safePage ? "is-active" : ""}
                      aria-label={`Incident page ${item}`}
                      onClick={() => setQueryValue("page", String(item))}
                    >
                      {item}
                    </Button>
                  ))}
                  <Button
                    aria-label="Next incident page"
                    disabled={safePage >= pageCount}
                    onClick={() => setQueryValue("page", String(safePage + 1))}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="sg-incidents-empty">
              <EmptyState
                title={allRows.length ? "No incidents match the selected filters" : "No active incidents require review"}
                description={
                  allRows.length
                    ? "Clear filters or choose another issue category."
                    : "All monitored sites are currently within configured operational limits."
                }
              />
              {allRows.length ? (
                <Button onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : null}
            </div>
          )}
        </Card>

        <aside className="sg-incidents-rail">
          <Card
            className="sg-card sg-incident-distribution-card"
            title={<span className="sg-card-title">INCIDENT DISTRIBUTION</span>}
          >
            <div className="sg-incident-distribution-layout">
              <EChart
                option={distributionOption(allRows)}
                ariaLabel="Incident distribution by probable issue"
                expandable
                expandedTitle="Incident Distribution"
              />
              <dl>
                {(Object.keys(issueBuckets) as IssueBucket[]).map((bucket) => {
                  const count = allRows.filter((row) => row.issueBucket === bucket).length;
                  return (
                    <button
                      type="button"
                      key={bucket}
                      onClick={() => setQueryValue("issue", bucket)}
                      className={issue === bucket ? "is-active" : ""}
                    >
                      <dt>
                        <i style={{ backgroundColor: issueBuckets[bucket].color }} />
                        {issueBuckets[bucket].label}
                      </dt>
                      <dd>
                        {formatInteger(count)}{" "}
                        <span>({activeCount ? formatPercent((count / activeCount) * 100) : "0%"})</span>
                      </dd>
                    </button>
                  );
                })}
              </dl>
            </div>
          </Card>
          <SelectedIncident incident={selectedIncident} />
          <RecommendedActions
            incident={selectedIncident}
            onOpenDiagnostics={openDiagnostics}
            onQueue={() => setModalOpen(true)}
          />
        </aside>
      </section>

      <div className="sg-state-ribbon">
        <CheckCircleOutlined />
        Incident triage keeps uncertain cases visible. Missing site readings are treated
        as data gaps, not zero production.
        {queueNotice ? <strong role="status">{queueNotice}</strong> : null}
        <button type="button" onClick={openDiagnostics}>
          Open selected diagnostics <ArrowRightOutlined />
        </button>
      </div>

      <Modal
        title="Move incident to service queue"
        open={modalOpen}
        okText={selectedIncident && queuedIds.has(selectedIncident.decision_id) ? "Already queued" : "Confirm routing"}
        cancelText="Review later"
        onOk={confirmQueue}
        onCancel={() => setModalOpen(false)}
        okButtonProps={{ disabled: selectedIncident ? queuedIds.has(selectedIncident.decision_id) : true }}
      >
        {selectedIncident ? (
          <div className="sg-incident-confirmation">
            <p>
              Route <strong>{selectedIncident.site?.site_name ?? selectedIncident.site_id}</strong>{" "}
              using the recommended action:
            </p>
            <dl>
              <div>
                <dt>Probable issue</dt>
                <dd>{displayIssue(selectedIncident.probable_issue)}</dd>
              </div>
              <div>
                <dt>Recommended action</dt>
                <dd>{normaliseAction(selectedIncident.recommended_action)}</dd>
              </div>
              <div>
                <dt>Decision path</dt>
                <dd>{selectedIncident.visit_required ? "Field review after checks" : "Remote check first"}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </Modal>
    </div>
  );
};
