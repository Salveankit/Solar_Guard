import {
  AlertOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  FieldTimeOutlined,
  FileTextOutlined,
  FireOutlined,
  InfoCircleOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { Button, Card, Skeleton, Space } from "antd";
import type { EChartsOption } from "echarts";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import diagnosticsHero from "../../assets/diagnostics-hero.png";
import { solarGuardTokens } from "../../app/theme";
import type { ServiceDecision } from "../../api/schemas/decisions";
import type { SiteDiagnostics, SitePerformancePoint } from "../../api/schemas/sites";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import {
  useRefreshOperations,
  useServiceQueue,
  useSiteDiagnostics,
  useSites,
} from "../../hooks/useOperationsData";
import {
  formatInr,
  formatInteger,
  formatKwh,
  formatPercent,
} from "../../utils/format";
import { displayIssue, topPriorityEvidence } from "../command-centre/data";

type RangeKey = "1D" | "3D" | "7D" | "30D";

const rangeOptions: RangeKey[] = ["1D", "3D", "7D", "30D"];

const formatAction = (value?: string): string =>
  value
    ? value
        .replaceAll("_", " ")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\b\w/g, (character) => character.toUpperCase())
    : "Monitor site";

const issueTone = (issue?: string): "critical" | "warning" | "unknown" => {
  const normalized = (issue ?? "").toLowerCase();
  if (normalized.includes("outage") || normalized.includes("interruption")) {
    return "critical";
  }
  if (normalized.includes("unknown") || normalized.includes("insufficient")) {
    return "unknown";
  }
  return "warning";
};

const latestPerformance = (rows: SitePerformancePoint[]): SitePerformancePoint | undefined =>
  [...rows].reverse().find((row) => row.actual_generation_kwh !== null) ?? rows.at(-1);

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

const formatDate = (value?: string | null): string => {
  if (!value) {
    return "Unavailable";
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
};

const coverageLabel = (rows: SitePerformancePoint[]): string => {
  const latest = latestPerformance(rows);
  return latest?.data_quality_status
    ? latest.data_quality_status.replaceAll("_", " ")
    : "Not exposed";
};

const filteredPerformance = (
  rows: SitePerformancePoint[],
  range: RangeKey,
): SitePerformancePoint[] => {
  if (range === "30D" || rows.length === 0) {
    return rows;
  }
  const count = range === "1D" ? 96 : range === "3D" ? 288 : 672;
  return rows.slice(Math.max(rows.length - count, 0));
};

const diagnosticChartOption = (rows: SitePerformancePoint[]): EChartsOption => {
  const labels = rows.map((row) =>
    new Intl.DateTimeFormat("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Kolkata",
    }).format(new Date(row.timestamp)),
  );
  const anomalyAreas: Array<[{ xAxis: string }, { xAxis: string }]> = [];
  rows.forEach((row, index) => {
    if (row.anomaly_state && row.anomaly_state !== "normal") {
      anomalyAreas.push([
        { xAxis: labels[index] },
        { xAxis: labels[Math.min(index + 1, labels.length - 1)] },
      ]);
    }
  });

  return {
    color: [
      solarGuardTokens.chartExpected,
      solarGuardTokens.chartActual,
      solarGuardTokens.chartIrradiance,
    ],
    tooltip: { trigger: "axis" },
    legend: {
      top: 0,
      right: 12,
      textStyle: { color: solarGuardTokens.colorTextSecondary, fontSize: 11 },
    },
    grid: { left: 40, right: 46, top: 42, bottom: 28 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: labels,
      axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: solarGuardTokens.colorBorderSubtle } },
    },
    yAxis: [
      {
        type: "value",
        name: "kWh",
        axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
        splitLine: { lineStyle: { color: solarGuardTokens.chartGrid } },
      },
      {
        type: "value",
        name: "W/m²",
        axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Expected Generation",
        type: "line",
        smooth: false,
        showSymbol: false,
        lineStyle: { width: 2, type: "dashed" },
        data: rows.map((row) => row.expected_generation_kwh),
      },
      {
        name: "Actual Generation",
        type: "line",
        smooth: false,
        showSymbol: false,
        lineStyle: { width: 2 },
        data: rows.map((row) => row.actual_generation_kwh),
        markArea: anomalyAreas.length
          ? {
              itemStyle: { color: "rgba(245, 71, 104, 0.18)" },
              data: anomalyAreas,
            }
          : undefined,
      },
      {
        name: "Irradiance",
        type: "line",
        yAxisIndex: 1,
        smooth: false,
        showSymbol: false,
        areaStyle: { opacity: 0.16 },
        data: rows.map((row) => row.ghi_wm2),
      },
    ],
  };
};

const confidenceGaugeOption = (confidence: number): EChartsOption => ({
  color: [solarGuardTokens.colorSuccess],
  series: [
    {
      type: "gauge",
      startAngle: 90,
      endAngle: -270,
      radius: "86%",
      pointer: { show: false },
      progress: { show: true, roundCap: true, width: 9 },
      axisLine: {
        roundCap: true,
        lineStyle: {
          width: 9,
          color: [[1, "rgba(126, 166, 199, 0.18)"]],
        },
      },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      detail: {
        formatter: "{value}%",
        color: solarGuardTokens.colorText,
        fontSize: 24,
        fontWeight: 650,
        offsetCenter: [0, "-5%"],
      },
      title: {
        offsetCenter: [0, "24%"],
        color: solarGuardTokens.colorTextSecondary,
        fontSize: 11,
      },
      data: [{ value: Math.round(confidence), name: "Confidence" }],
    },
  ],
});

type KpiProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  tone: "critical" | "success" | "info" | "money" | "action";
};

const DiagnosticKpi = ({ icon, label, value, note, tone }: KpiProps) => (
  <div className="sg-diagnostic-kpi">
    <span className={`sg-diagnostic-kpi-icon ${tone}`}>{icon}</span>
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  </div>
);

const SiteHeroCard = ({ data, decision }: { data: SiteDiagnostics; decision?: ServiceDecision }) => (
  <aside className="sg-diagnostic-site-card">
    <div>
      <DeploymentUnitOutlined />
      <strong>{data.site.site_name}</strong>
      <span className={decision ? "is-live" : "is-muted"}>{decision ? "Attention" : "Healthy"}</span>
    </div>
    <dl>
      <div>
        <dt>Site ID</dt>
        <dd>{data.site.site_id}</dd>
      </div>
      <div>
        <dt>Region</dt>
        <dd>{data.site.service_region}</dd>
      </div>
      <div>
        <dt>Site Status</dt>
        <dd>{decision ? decision.priority_label : "Healthy"}</dd>
      </div>
      <div>
        <dt>Coverage Status</dt>
        <dd>{coverageLabel(data.performance)}</dd>
      </div>
      <div>
        <dt>Latest Analysis</dt>
        <dd>{formatTime(decision?.created_at)}</dd>
      </div>
    </dl>
  </aside>
);

const EvidenceStrip = ({
  data,
  decision,
}: {
  data: SiteDiagnostics;
  decision?: ServiceDecision;
}) => {
  const latest = latestPerformance(data.performance);
  const candidate = data.diagnostics[0]?.candidate;
  return (
    <section className="sg-evidence-strip" aria-label="Diagnostic evidence">
      <div>
        <ClockCircleOutlined />
        <span>Anomaly Start</span>
        <strong>{formatTime(candidate?.start_timestamp)}</strong>
        <small>{formatDate(candidate?.start_timestamp)}</small>
      </div>
      <div>
        <FieldTimeOutlined />
        <span>Persistence</span>
        <strong>
          {candidate?.duration_intervals ?? candidate?.persistence_intervals ?? "Unavailable"}
          {candidate?.duration_intervals || candidate?.persistence_intervals ? " intervals" : ""}
        </strong>
        <small>Backend incident candidate</small>
      </div>
      <div>
        <CloudOutlined />
        <span>Irradiance</span>
        <strong>{latest?.ghi_wm2 ? `${formatInteger(latest.ghi_wm2)} W/m²` : "Unavailable"}</strong>
        <small>Latest diagnostic point</small>
      </div>
      <div>
        <DatabaseOutlined />
        <span>Data Quality</span>
        <strong>{coverageLabel(data.performance)}</strong>
        <small>From expected-generation rows</small>
      </div>
      <div>
        <BarChartOutlined />
        <span>Actual Energy</span>
        <strong>
          {decision?.actual_energy_kwh === null || !decision
            ? "Unavailable"
            : formatKwh(decision.actual_energy_kwh)}
        </strong>
        <small>Missing remains unavailable</small>
      </div>
      <div>
        <ToolOutlined />
        <span>Recommended Checks</span>
        <strong>{formatAction(decision?.recommended_action)}</strong>
        <small>Backend next action</small>
      </div>
    </section>
  );
};

const DiagnosticSummary = ({ decision }: { decision?: ServiceDecision }) => (
  <Card className="sg-card sg-diagnostic-summary-card" title={<span className="sg-card-title">DIAGNOSTIC SUMMARY</span>}>
    {decision ? (
      <>
        <div className="sg-diagnostic-summary-main">
          <EChart
            option={confidenceGaugeOption(decision.confidence_score)}
            ariaLabel="Diagnostic confidence score"
          />
          <div>
            <span>Probable Issue</span>
            <h3>{displayIssue(decision.probable_issue)}</h3>
            <p>
              Expected energy was {formatKwh(decision.expected_energy_kwh)} while
              actual energy was{" "}
              {decision.actual_energy_kwh === null
                ? "unavailable"
                : formatKwh(decision.actual_energy_kwh)}
              .
            </p>
            <dl>
              <div>
                <dt>Confidence</dt>
                <dd>{decision.confidence_label}</dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd>{decision.priority_label}</dd>
              </div>
              <div>
                <dt>Recommendation</dt>
                <dd>{formatAction(decision.recommended_action)}</dd>
              </div>
            </dl>
          </div>
        </div>
        <div className="sg-summary-reasons">
          <article>
            <InfoCircleOutlined />
            <strong>Why</strong>
            <p>{decision.supporting_evidence[0] ?? "Evidence was recorded by backend diagnostics."}</p>
          </article>
          <article>
            <CheckCircleOutlined />
            <strong>Confidence</strong>
            <p>{decision.confidence_label} confidence score based on available evidence.</p>
          </article>
          <article>
            <ExperimentOutlined />
            <strong>Next action</strong>
            <p>{decision.escalation_condition || formatAction(decision.recommended_action)}</p>
          </article>
        </div>
      </>
    ) : (
      <EmptyState
        title="No probable issue for this site"
        description="Backend diagnostics did not return an active decision for the selected site."
      />
    )}
  </Card>
);

export const DiagnosticsPage = () => {
  const { siteId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const refreshOperations = useRefreshOperations();
  const serviceQueue = useServiceQueue();
  const sites = useSites();
  const [range, setRange] = useState<RangeKey>("1D");
  const [noteCreated, setNoteCreated] = useState(false);

  const selectedSiteId = useMemo(() => {
    if (siteId) return siteId;
    if (params.get("site")) return params.get("site") ?? undefined;
    return topPriorityEvidence(serviceQueue.data?.items ?? [])?.site_id ?? sites.data?.[0]?.site_id;
  }, [params, serviceQueue.data, siteId, sites.data]);

  const diagnostics = useSiteDiagnostics(selectedSiteId);
  const data = diagnostics.data;
  const decision = data?.diagnostics[0]?.decision;
  const chartRows = useMemo(
    () => filteredPerformance(data?.performance ?? [], range),
    [data?.performance, range],
  );
  const latest = latestPerformance(data?.performance ?? []);

  const loading = serviceQueue.isLoading || sites.isLoading || diagnostics.isLoading;
  const error = serviceQueue.error || sites.error || diagnostics.error;

  if (loading && !data) {
    return (
      <div className="sg-diagnostics-page">
        <section className="sg-diagnostics-loading">
          <Skeleton active paragraph={{ rows: 4 }} />
          <Skeleton active paragraph={{ rows: 8 }} />
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Unable to load site diagnostics"
        error={error}
        onRetry={refreshOperations}
      />
    );
  }

  if (!data) {
    return (
      <Card className="sg-card">
        <EmptyState
          title="No diagnostics available"
          description="Run analysis and select a site with diagnostic evidence."
        />
      </Card>
    );
  }

  const tone = issueTone(decision?.probable_issue);

  return (
    <div className="sg-diagnostics-page">
      <section
        className="sg-diagnostics-hero"
        style={{ backgroundImage: `url(${diagnosticsHero})` }}
        aria-labelledby="diagnostics-title"
      >
        <div>
          <span className="sg-eyebrow">DIAGNOSTICS</span>
          <h1 id="diagnostics-title">Understand site issues with confidence.</h1>
          <p>
            Inspect expected vs actual generation, evidence, and next diagnostic actions before dispatch.
          </p>
        </div>
        <SiteHeroCard data={data} decision={decision} />
      </section>

      <section className="sg-diagnostic-kpi-strip" aria-label="Selected site diagnostic KPIs">
        <DiagnosticKpi
          icon={<AlertOutlined />}
          label="Probable Issue"
          value={decision ? displayIssue(decision.probable_issue) : "None detected"}
          note={decision ? "Backend diagnosis" : "No active decision"}
          tone={tone === "critical" ? "critical" : "info"}
        />
        <DiagnosticKpi
          icon={<CheckCircleOutlined />}
          label="Confidence"
          value={decision ? formatPercent(decision.confidence_score) : "N/A"}
          note={decision?.confidence_label ?? "Not applicable"}
          tone="success"
        />
        <DiagnosticKpi
          icon={<ThunderboltOutlined />}
          label="Energy Loss Today"
          value={decision ? formatKwh(decision.estimated_energy_loss_kwh) : formatKwh(0)}
          note="Backend estimated loss"
          tone="info"
        />
        <DiagnosticKpi
          icon={<FireOutlined />}
          label="Est. Energy Value at Risk"
          value={decision ? formatInr(decision.estimated_value_at_risk_inr) : formatInr(0)}
          note="At configured tariffs"
          tone="money"
        />
        <DiagnosticKpi
          icon={<ToolOutlined />}
          label="Recommended Action"
          value={formatAction(decision?.recommended_action)}
          note="First diagnostic step"
          tone="action"
        />
        <DiagnosticKpi
          icon={<DatabaseOutlined />}
          label="Data Coverage"
          value={coverageLabel(data.performance)}
          note="From backend result rows"
          tone="success"
        />
      </section>

      <section className="sg-diagnostics-grid">
        <div className="sg-diagnostics-main">
          <Card
            className="sg-card sg-diagnostic-chart-card"
            title={<span className="sg-card-title">EXPECTED VS ACTUAL GENERATION</span>}
            extra={
              <Space className="sg-range-toggle">
                {rangeOptions.map((item) => (
                  <Button
                    key={item}
                    className={range === item ? "is-active" : ""}
                    onClick={() => setRange(item)}
                  >
                    {item}
                  </Button>
                ))}
              </Space>
            }
          >
            {chartRows.length ? (
              <EChart
                option={diagnosticChartOption(chartRows)}
                ariaLabel="Expected generation, actual generation and irradiance for selected site"
                expandable
                expandedTitle="Site Diagnostic Generation Chart"
              />
            ) : (
              <EmptyState title="No performance series" />
            )}
          </Card>

          <Card
            className="sg-card"
            title={<span className="sg-card-title">DIAGNOSTIC EVIDENCE</span>}
            extra={<span className="sg-diagnostic-meta">Evidence evaluated from backend analysis</span>}
          >
            <EvidenceStrip data={data} decision={decision} />
          </Card>

          <Card
            className="sg-card sg-history-card"
            title={<span className="sg-card-title">EVENT &amp; DIAGNOSTIC HISTORY</span>}
          >
            <div className="sg-history-table" role="table" aria-label="Event and diagnostic history">
              <div role="row">
                <span>Time</span>
                <span>Event</span>
                <span>Source</span>
                <span>Status</span>
                <span>Notes</span>
              </div>
              {[
                ["Probable issue detected", "Analytics Engine", "Active", displayIssue(decision?.probable_issue ?? "No issue")],
                ["Diagnostic evidence recorded", "Diagnostics Engine", "Info", decision?.supporting_evidence[0] ?? "No active evidence"],
                ["Latest performance row evaluated", "Expected Generation", "Info", latest?.data_quality_status ?? "No performance row"],
                ["Diagnostics analysis completed", "Diagnostics Engine", "Active", decision ? `Confidence ${formatPercent(decision.confidence_score)}` : "No decision"],
              ].map(([event, source, status, notes], index) => (
                <button
                  key={`${event}-${index}`}
                  type="button"
                  role="row"
                  onClick={() => {
                    if (index === 0 && decision) {
                      void navigate(`/sites/${decision.site_id}`);
                    }
                  }}
                >
                  <span>{index === 0 ? formatTime(data.diagnostics[0]?.candidate?.start_timestamp) : formatTime(decision?.created_at)}</span>
                  <span>{event}</span>
                  <span>{source}</span>
                  <span className={status === "Active" ? "is-active" : "is-info"}>{status}</span>
                  <span>{notes}</span>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <aside className="sg-diagnostics-rail">
          <DiagnosticSummary decision={decision} />

          <Card className="sg-card" title={<span className="sg-card-title">SITE &amp; ANALYSIS CONTEXT</span>}>
            <div className="sg-context-strip">
              <div><CloudOutlined /><span>Irradiance</span><strong>{latest?.ghi_wm2 ? `${formatInteger(latest.ghi_wm2)} W/m²` : "Unavailable"}</strong></div>
              <div><DeploymentUnitOutlined /><span>Capacity DC</span><strong>{formatInteger(data.site.capacity_kw)} kWp</strong></div>
              <div><ThunderboltOutlined /><span>Actual Energy</span><strong>{latest?.actual_generation_kwh === null || !latest ? "Unavailable" : formatKwh(latest.actual_generation_kwh)}</strong></div>
              <div><DatabaseOutlined /><span>Coverage</span><strong>{coverageLabel(data.performance)}</strong></div>
            </div>
          </Card>

          <Card className="sg-card" title={<span className="sg-card-title">RECOMMENDED NEXT ACTIONS</span>}>
            <ol className="sg-next-actions">
              <li>
                <span>1</span>
                <div>
                  <strong>{formatAction(decision?.recommended_action)}</strong>
                  <small>Start with backend recommended action.</small>
                </div>
                <Button onClick={() => void navigate("/service-queue")}>Review</Button>
              </li>
              <li>
                <span>2</span>
                <div>
                  <strong>Verify grid-side and inverter status</strong>
                  <small>Use remote checks before dispatch.</small>
                </div>
                <Button onClick={() => void navigate("/incidents")}>Open</Button>
              </li>
              <li>
                <span>3</span>
                <div>
                  <strong>{decision?.visit_required ? "Prepare field visit if unresolved" : "Continue remote monitoring"}</strong>
                  <small>{decision?.escalation_condition || "Escalate only if evidence supports dispatch."}</small>
                </div>
                <Button onClick={() => void navigate("/technician-plan")}>Plan</Button>
              </li>
            </ol>
            <div className="sg-action-buttons">
              <Link to="/service-queue">
                <Button className="sg-secondary-button" icon={<NodeIndexOutlined />}>
                  View Service Queue
                </Button>
              </Link>
              <Button
                className="sg-secondary-button warning"
                icon={<FileTextOutlined />}
                onClick={() => setNoteCreated(true)}
              >
                {noteCreated ? "Investigation Note Created" : "Create Investigation Note"}
              </Button>
            </div>
          </Card>
        </aside>
      </section>
    </div>
  );
};
