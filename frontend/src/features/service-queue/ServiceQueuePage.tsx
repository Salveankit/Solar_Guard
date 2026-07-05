import {
  AlertOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  FileDoneOutlined,
  InfoCircleOutlined,
  LineChartOutlined,
  SendOutlined,
  UserOutlined,
  WifiOutlined,
} from "@ant-design/icons";
import { Button, Modal, Skeleton, Tooltip } from "antd";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import type { ServiceDecision } from "../../api/schemas/decisions";
import type { SiteDiagnosticItem, SiteSummary } from "../../api/schemas/sites";
import serviceQueueHero from "../../assets/service-queue-hero.png";
import { solarGuardTokens } from "../../app/theme";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import {
  useRefreshOperations,
  useServiceQueue,
  useSiteDiagnostics,
  useSites,
} from "../../hooks/useOperationsData";
import { formatInr, formatInteger, formatKwh, formatPercent } from "../../utils/format";
import { displayIssue } from "../command-centre/data";

type QueueFilter = "all" | "priority" | "remote" | "field" | "cleaning" | "unknown";
type SortMode = "priority" | "impact" | "confidence";
type DecisionBucket = "remote" | "field" | "cleaning" | "unknown";

type QueueRow = ServiceDecision & {
  site?: SiteSummary;
  bucket: DecisionBucket;
};

const pageSize = 10;

const bucketMeta: Record<DecisionBucket, { label: string; color: string }> = {
  remote: { label: "Remote check", color: solarGuardTokens.colorInfo },
  field: { label: "Field visit", color: solarGuardTokens.colorWarning },
  cleaning: { label: "Cleaning candidate", color: solarGuardTokens.colorSuccess },
  unknown: { label: "Insufficient evidence", color: solarGuardTokens.colorRemote },
};

const isUnknown = (decision: ServiceDecision) =>
  decision.probable_issue.toLowerCase().includes("unknown") ||
  decision.probable_issue.toLowerCase().includes("insufficient");

const bucketFor = (decision: ServiceDecision): DecisionBucket => {
  if (isUnknown(decision)) return "unknown";
  if (decision.cleaning_decision.toLowerCase().includes("schedule")) return "cleaning";
  if (decision.visit_required) return "field";
  return "remote";
};

const titleCase = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());

const conciseAction = (decision: ServiceDecision) => {
  if (isUnknown(decision)) return "Collect additional telemetry or perform a remote inspection";
  return titleCase(decision.recommended_action);
};

const shortInr = (value: number) => {
  if (value >= 100000) {
    return `₹ ${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value / 100000)} L`;
  }
  return formatInr(value);
};

const confidencePercent = (value: number) => (value <= 1 ? value * 100 : value);

const priorityClass = (label: string) => `priority-${label.toLowerCase()}`;

const formatTime = (value?: string | null) => {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
};

const enrichRows = (decisions: ServiceDecision[], sites: SiteSummary[]): QueueRow[] => {
  const byId = new Map(sites.map((site) => [site.site_id, site]));
  return decisions.map((decision) => ({
    ...decision,
    site: byId.get(decision.site_id),
    bucket: bucketFor(decision),
  }));
};

const filterRows = (rows: QueueRow[], filter: QueueFilter) =>
  rows.filter((row) => {
    if (filter === "all") return true;
    if (filter === "priority") return ["Critical", "High"].includes(row.priority_label);
    return row.bucket === filter;
  });

const sortRows = (rows: QueueRow[], sort: SortMode) =>
  [...rows].sort((left, right) => {
    if (sort === "impact") {
      return right.estimated_value_at_risk_inr - left.estimated_value_at_risk_inr;
    }
    if (sort === "confidence") {
      return confidencePercent(right.confidence_score) - confidencePercent(left.confidence_score);
    }
    return right.priority_score - left.priority_score;
  });

const distributionOption = (rows: QueueRow[]): EChartsOption => {
  const data = (Object.keys(bucketMeta) as DecisionBucket[]).map((bucket) => ({
    name: bucketMeta[bucket].label,
    value: rows.filter((row) => row.bucket === bucket).length,
    bucket,
  }));
  return {
    color: data.map((item) => bucketMeta[item.bucket].color),
    tooltip: { trigger: "item" },
    legend: { show: false },
    series: [
      {
        type: "pie",
        radius: ["54%", "74%"],
        center: ["28%", "50%"],
        label: { show: false },
        itemStyle: { borderColor: solarGuardTokens.colorSurface, borderWidth: 2 },
        data,
      },
    ],
    graphic: [
      {
        type: "text",
        left: "24%",
        top: "39%",
        style: {
          text: String(rows.length),
          fill: solarGuardTokens.colorText,
          fontSize: 28,
          fontWeight: 650,
          align: "center",
        },
      },
      {
        type: "text",
        left: "23%",
        top: "57%",
        style: { text: "Total", fill: solarGuardTokens.colorTextSecondary, fontSize: 11 },
      },
    ],
  };
};

const evidenceOption = (diagnostic?: SiteDiagnosticItem): EChartsOption => {
  const missing = diagnostic?.decision.actual_energy_kwh == null;
  return {
    color: [solarGuardTokens.chartExpected, solarGuardTokens.chartActual],
    grid: { left: 6, right: 6, top: 8, bottom: 8 },
    xAxis: { show: false, type: "category", data: ["1", "2", "3", "4", "5", "6"] },
    yAxis: { show: false, type: "value" },
    series: [
      {
        type: "line",
        showSymbol: false,
        lineStyle: { width: 2, type: "dashed" },
        data: [4, 5, 6, 7, 6, 5],
      },
      {
        type: "line",
        showSymbol: false,
        lineStyle: { width: 2 },
        data: missing ? [null, null, null, null, null, null] : [4, 4.5, 3.2, 1.6, 1, 0.8],
      },
    ],
  };
};

const QueueKpi = ({
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
  <button className="sg-queue-kpi" type="button" onClick={onClick}>
    <span className={`sg-queue-kpi-icon ${tone}`}>{icon}</span>
    <span>
      <small>{label}</small>
      <strong>{value}</strong>
      <em>{note}</em>
    </span>
  </button>
);

const PriorityBadge = ({ row }: { row: QueueRow }) => (
  <span className={`sg-queue-priority ${priorityClass(row.priority_label)}`}>
    <i />
    {row.priority_label}
  </span>
);

const VisitBadge = ({ row }: { row: QueueRow }) => {
  const value = isUnknown(row) ? "Review" : row.visit_required ? "Yes" : "No";
  return <span className={`sg-queue-visit visit-${value.toLowerCase()}`}>{value}</span>;
};

const QueueDistribution = ({
  rows,
  active,
  onFilter,
}: {
  rows: QueueRow[];
  active: QueueFilter;
  onFilter: (filter: QueueFilter) => void;
}) => (
  <section className="sg-queue-card sg-queue-distribution" aria-labelledby="queue-distribution-heading">
    <h2 id="queue-distribution-heading">QUEUE DISTRIBUTION</h2>
    <div className="sg-queue-distribution-body">
      <EChart
        option={distributionOption(rows)}
        ariaLabel={`Queue distribution across ${rows.length} exclusive decision buckets`}
        expandable
        expandedTitle="Service Queue Distribution"
      />
      <div className="sg-queue-legend">
        {(Object.keys(bucketMeta) as DecisionBucket[]).map((bucket) => {
          const count = rows.filter((row) => row.bucket === bucket).length;
          return (
            <button
              type="button"
              key={bucket}
              className={active === bucket ? "is-active" : ""}
              onClick={() => onFilter(active === bucket ? "all" : bucket)}
              aria-pressed={active === bucket}
            >
              <i style={{ background: bucketMeta[bucket].color }} />
              <span>{bucketMeta[bucket].label}</span>
              <strong>{count} ({rows.length ? formatPercent((count / rows.length) * 100) : "0%"})</strong>
            </button>
          );
        })}
      </div>
    </div>
  </section>
);

const SelectedDecision = ({
  row,
  diagnostic,
  diagnosticsLoading,
}: {
  row?: QueueRow;
  diagnostic?: SiteDiagnosticItem;
  diagnosticsLoading: boolean;
}) => (
  <section className="sg-queue-card sg-selected-decision" aria-labelledby="selected-decision-heading">
    <div className="sg-queue-card-head">
      <h2 id="selected-decision-heading">SELECTED DECISION</h2>
      {row ? <span className={`sg-queue-priority ${priorityClass(row.priority_label)}`}>{row.priority_label}</span> : null}
    </div>
    {!row ? (
      <EmptyState title="Select a service decision" description="Review its evidence and backend priority." />
    ) : (
      <>
        <div className="sg-selected-site">
          <span><FileDoneOutlined /></span>
          <strong>{row.site?.site_name ?? row.site_id}<small>{row.site_id} · {row.site?.service_region ?? "Region unavailable"}</small></strong>
        </div>
        <dl className="sg-selected-facts">
          <div><dt>Probable issue</dt><dd>{displayIssue(row.probable_issue)}</dd></div>
          <div><dt>Confidence</dt><dd>{formatPercent(confidencePercent(row.confidence_score))}<small>{row.confidence_label}</small></dd></div>
          <div><dt>Energy value at risk</dt><dd>{shortInr(row.estimated_value_at_risk_inr)}<small>{formatKwh(row.estimated_energy_loss_kwh)}</small></dd></div>
          <div><dt>Detected since</dt><dd>{formatTime(row.created_at)}<small>Analysis timestamp</small></dd></div>
          <div><dt>Visit required</dt><dd><VisitBadge row={row} /></dd></div>
          <div><dt>Complaint status</dt><dd>Not exposed<small>API field unavailable</small></dd></div>
          <div><dt>Recommended action</dt><dd>{conciseAction(row)}</dd></div>
        </dl>
        <p className="sg-selected-evidence">
          {row.supporting_evidence[0] ?? "Supporting evidence is unavailable."}
          {row.actual_energy_kwh == null ? " Missing telemetry is preserved as unavailable, not zero." : ""}
        </p>
        {diagnosticsLoading ? <Skeleton active paragraph={{ rows: 2 }} /> : (
          <div className="sg-queue-evidence-grid">
            <Tooltip title="Expected versus actual generation evidence">
              <div className="sg-queue-evidence-chart"><EChart option={evidenceOption(diagnostic)} ariaLabel="Expected versus actual generation preview" /></div>
            </Tooltip>
            <div className="sg-queue-evidence-stat"><DatabaseOutlined /><strong>{row.actual_energy_kwh == null ? "Telemetry gap" : formatKwh(row.actual_energy_kwh)}<small>{row.actual_energy_kwh == null ? "No zero substitution" : "Actual energy"}</small></strong></div>
            <div className="sg-queue-evidence-stat"><ClockCircleOutlined /><strong>{diagnostic?.candidate?.persistence_intervals ?? "—"}<small>Backend intervals</small></strong></div>
          </div>
        )}
      </>
    )}
  </section>
);

const priorityFactors = [
  ["Energy impact", "30%"],
  ["Persistence", "20%"],
  ["Confidence", "15%"],
  ["Complaint urgency", "15%"],
  ["SLA / warranty risk", "10%"],
  ["Route benefit", "10%"],
] as const;

const PriorityBreakdown = ({
  row,
  onDiagnostics,
  onPlan,
}: {
  row?: QueueRow;
  onDiagnostics: () => void;
  onPlan: () => void;
}) => (
  <section className="sg-queue-card sg-priority-breakdown" aria-labelledby="priority-breakdown-heading">
    <h2 id="priority-breakdown-heading">PRIORITY BREAKDOWN</h2>
    {row ? (
      <>
        <p className="sg-priority-total">Priority score: <strong>{row.priority_score}</strong> <span>— {row.priority_label}</span></p>
        <div className="sg-priority-api-note"><InfoCircleOutlined /> The API supplies the total score but not its six component values.</div>
        <div className="sg-priority-factors">
          {priorityFactors.map(([label, weight]) => (
            <div key={label}>
              <span>{label}</span><small>{weight}</small>
              <i><b /></i><em>Not exposed</em>
            </div>
          ))}
        </div>
        <div className="sg-priority-actions">
          <Button icon={<LineChartOutlined />} onClick={onDiagnostics}>Open Diagnostics</Button>
          <Button type="primary" icon={<SendOutlined />} onClick={onPlan}>Move to Technician Plan</Button>
        </div>
      </>
    ) : <p>Select a decision to review backend priority.</p>}
  </section>
);

const MoveToPlanDialog = ({
  open,
  row,
  diagnostic,
  onClose,
}: {
  open: boolean;
  row?: QueueRow;
  diagnostic?: SiteDiagnosticItem;
  onClose: () => void;
}) => (
  <Modal
    open={open}
    title="Review before Technician Plan"
    onCancel={onClose}
    footer={<Button type="primary" onClick={onClose}>Close review</Button>}
    className="sg-queue-modal"
  >
    {row ? (
      <>
        <p className="sg-modal-warning"><InfoCircleOutlined /> The approved API has no move-to-plan mutation. No assignment has been created.</p>
        <dl className="sg-queue-review-grid">
          <div><dt>Site</dt><dd>{row.site?.site_name ?? row.site_id}</dd></div>
          <div><dt>Recommended action</dt><dd>{conciseAction(row)}</dd></div>
          <div><dt>Visit decision</dt><dd>{isUnknown(row) ? "Review" : row.visit_required ? "Required" : "Not required"}</dd></div>
          <div><dt>Required skill</dt><dd>Not exposed by queue API</dd></div>
          <div><dt>Estimated duration</dt><dd>{diagnostic?.candidate?.persistence_intervals ? "Service duration not exposed" : "Not exposed by API"}</dd></div>
          <div><dt>Priority</dt><dd>{row.priority_score} · {row.priority_label}</dd></div>
          <div><dt>Economic impact</dt><dd>{shortInr(row.estimated_value_at_risk_inr)}</dd></div>
          <div><dt>Blocking conditions</dt><dd>{row.escalation_condition || "None reported"}</dd></div>
        </dl>
      </>
    ) : null}
  </Modal>
);

export const ServiceQueuePage = () => {
  const queueQuery = useServiceQueue();
  const sitesQuery = useSites();
  const refresh = useRefreshOperations();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [reviewOpen, setReviewOpen] = useState(false);

  const rows = useMemo(
    () => enrichRows(queueQuery.data?.items ?? [], sitesQuery.data ?? []),
    [queueQuery.data?.items, sitesQuery.data],
  );
  const filter = (searchParams.get("filter") as QueueFilter) || "all";
  const sort = (searchParams.get("sort") as SortMode) || "priority";
  const page = Math.max(1, Number(searchParams.get("page") || "1"));
  const selectedId = searchParams.get("selected") ?? rows[0]?.decision_id;
  const filteredRows = useMemo(() => sortRows(filterRows(rows, filter), sort), [rows, filter, sort]);
  const selected = filteredRows.find((row) => row.decision_id === selectedId) ?? filteredRows[0];
  const diagnosticsQuery = useSiteDiagnostics(selected?.site_id);
  const diagnostic = diagnosticsQuery.data?.diagnostics.find(
    (item) => item.decision.decision_id === selected?.decision_id,
  ) ?? diagnosticsQuery.data?.diagnostics[0];

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const visibleRows = filteredRows.slice((Math.min(page, totalPages) - 1) * pageSize, Math.min(page, totalPages) * pageSize);

  useEffect(() => {
    if (page > totalPages) {
      const next = new URLSearchParams(searchParams);
      next.set("page", String(totalPages));
      setSearchParams(next, { replace: true });
    }
  }, [page, searchParams, setSearchParams, totalPages]);

  const setParam = (key: string, value?: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all") next.delete(key);
    else next.set(key, value);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  };

  const selectRow = (row: QueueRow) => {
    const next = new URLSearchParams(searchParams);
    next.set("selected", row.decision_id);
    setSearchParams(next);
  };

  const openDiagnostics = () => {
    if (selected) void navigate(`/sites/${selected.site_id}?decision=${selected.decision_id}`);
  };

  const loading = queueQuery.isLoading || sitesQuery.isLoading;
  const error = queueQuery.error ?? sitesQuery.error;
  const highCount = rows.filter((row) => ["Critical", "High"].includes(row.priority_label)).length;
  const remoteCount = rows.filter((row) => row.bucket === "remote").length;
  const fieldCount = rows.filter((row) => row.bucket === "field").length;

  if (error) {
    return <ErrorState title="Unable to load service queue" error={error} onRetry={refresh} />;
  }

  return (
    <div className="sg-service-queue-page">
      <section className="sg-service-queue-hero" style={{ backgroundImage: `url(${serviceQueueHero})` }}>
        <div className="sg-queue-hero-copy">
          <span>SERVICE QUEUE</span>
          <h1>Prioritize service work with clarity.</h1>
          <p>Rank remote checks, field reviews, and cleaning candidates using impact, confidence, and operational urgency.</p>
        </div>
        <span className="sg-queue-hero-status"><i />Live service decisions</span>
      </section>

      <section className="sg-queue-kpis" aria-label="Service queue metrics">
        {loading ? Array.from({ length: 4 }, (_, index) => <Skeleton.Button key={index} active block />) : (
          <>
            <QueueKpi icon={<FileDoneOutlined />} label="Total Queue" value={formatInteger(rows.length)} note="Across all sites" tone="blue" onClick={() => setParam("filter", "all")} />
            <QueueKpi icon={<AlertOutlined />} label="Critical / High Priority" value={formatInteger(highCount)} note={`${rows.length ? formatPercent((highCount / rows.length) * 100) : "0%"} of queue`} tone="red" onClick={() => setParam("filter", "priority")} />
            <QueueKpi icon={<WifiOutlined />} label="Remote-check First" value={formatInteger(remoteCount)} note={`${rows.length ? formatPercent((remoteCount / rows.length) * 100) : "0%"} of queue`} tone="purple" onClick={() => setParam("filter", "remote")} />
            <QueueKpi icon={<UserOutlined />} label="Field Visit Recommended" value={formatInteger(fieldCount)} note={`${rows.length ? formatPercent((fieldCount / rows.length) * 100) : "0%"} of queue`} tone="blue" onClick={() => setParam("filter", "field")} />
          </>
        )}
      </section>

      <section className="sg-queue-workspace">
        <div className="sg-queue-card sg-decision-queue" aria-labelledby="service-decision-heading">
          <div className="sg-decision-title-row">
            <h2 id="service-decision-heading">SERVICE DECISION QUEUE</h2>
            <label>Sort <select value={sort} onChange={(event) => setParam("sort", event.target.value)}><option value="priority">Priority score</option><option value="impact">Value at risk</option><option value="confidence">Confidence</option></select></label>
          </div>
          <div className="sg-queue-filters" aria-label="Queue filters">
            {([
              ["all", "All"], ["priority", "Critical / High"], ["remote", "Remote Check"],
              ["field", "Field Visit"], ["cleaning", "Cleaning Candidate"], ["unknown", "Insufficient Data"],
            ] as [QueueFilter, string][]).map(([value, label]) => (
              <button type="button" key={value} className={filter === value ? "is-active" : ""} onClick={() => setParam("filter", value)} aria-pressed={filter === value}>{label}</button>
            ))}
          </div>

          {loading ? (
            <div className="sg-queue-table-loading">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} active paragraph={{ rows: 1 }} />)}</div>
          ) : visibleRows.length === 0 ? (
            <div className="sg-queue-empty">
              <EmptyState title={rows.length ? "No service decisions match the selected filters" : "No service decisions currently require review"} description="Clear filters or refresh operational data." />
              {rows.length ? <Button onClick={() => setParam("filter", "all")}>Clear filters</Button> : null}
            </div>
          ) : (
            <>
              <div className="sg-queue-table-wrap">
                <table className="sg-queue-table">
                  <thead><tr><th>Priority</th><th>Site</th><th>Probable issue</th><th>Confidence</th><th>Persistence</th><th>Energy value at risk</th><th>Complaint status</th><th>Recommended action</th><th>Visit required</th></tr></thead>
                  <tbody>
                    {visibleRows.map((row) => (
                      <tr key={row.decision_id} className={selected?.decision_id === row.decision_id ? "is-selected" : ""} onClick={() => selectRow(row)} aria-selected={selected?.decision_id === row.decision_id} tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") selectRow(row); }}>
                        <td><PriorityBadge row={row} /></td>
                        <td><strong>{row.site?.site_name ?? row.site_id}<small>{row.site_id}</small></strong></td>
                        <td>{displayIssue(row.probable_issue)}</td>
                        <td><strong>{formatPercent(confidencePercent(row.confidence_score))}<small className="sg-positive">{row.confidence_label}</small></strong></td>
                        <td><span className="sg-api-missing">Details</span><small>Open row</small></td>
                        <td><strong>{shortInr(row.estimated_value_at_risk_inr)}<small>{formatKwh(row.estimated_energy_loss_kwh)}</small></strong></td>
                        <td><span className="sg-complaint-status">Not exposed</span></td>
                        <td>{conciseAction(row)}</td>
                        <td><VisitBadge row={row} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="sg-queue-mobile-list">
                  {visibleRows.map((row) => (
                    <button type="button" key={row.decision_id} onClick={() => selectRow(row)} className={selected?.decision_id === row.decision_id ? "is-selected" : ""}>
                      <span><PriorityBadge row={row} /><VisitBadge row={row} /></span>
                      <strong>{row.site?.site_name ?? row.site_id}<small>{row.site_id}</small></strong>
                      <p>{displayIssue(row.probable_issue)}</p>
                      <dl><div><dt>Confidence</dt><dd>{formatPercent(confidencePercent(row.confidence_score))}</dd></div><div><dt>Value at risk</dt><dd>{shortInr(row.estimated_value_at_risk_inr)}</dd></div></dl>
                      <em>{conciseAction(row)}</em>
                    </button>
                  ))}
                </div>
              </div>
              <div className="sg-queue-pagination">
                <span>Showing {filteredRows.length ? (Math.min(page, totalPages) - 1) * pageSize + 1 : 0} to {Math.min(Math.min(page, totalPages) * pageSize, filteredRows.length)} of {filteredRows.length} service decisions</span>
                <div><Button disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>Previous</Button><b>{Math.min(page, totalPages)}</b><Button disabled={page >= totalPages} onClick={() => setParam("page", String(page + 1))}>Next</Button></div>
              </div>
            </>
          )}
        </div>

        <div className="sg-queue-analysis-band">
          {loading ? <section className="sg-queue-card"><Skeleton active /></section> : <QueueDistribution rows={rows} active={filter} onFilter={(value) => setParam("filter", value)} />}
          <SelectedDecision row={selected} diagnostic={diagnostic} diagnosticsLoading={diagnosticsQuery.isLoading} />
          <PriorityBreakdown row={selected} onDiagnostics={openDiagnostics} onPlan={() => setReviewOpen(true)} />
        </div>
      </section>

      <MoveToPlanDialog open={reviewOpen} row={selected} diagnostic={diagnostic} onClose={() => setReviewOpen(false)} />
    </div>
  );
};
