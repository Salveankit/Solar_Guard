import {
  CalendarOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileDoneOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  TableOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Button, Modal, Skeleton } from "antd";
import type { EChartsOption } from "echarts";
import Papa from "papaparse";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { LatestRoutePlan } from "../../api/schemas/routes";
import reportsHero from "../../assets/reports-hero.png";
import { solarGuardTokens } from "../../app/theme";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import {
  useDailyPlanReport,
  useLatestRoutePlan,
  useRefreshOperations,
} from "../../hooks/useOperationsData";
import { formatInteger } from "../../utils/format";

type ReportCategory = "all" | "daily-ops";
type ReportStatusFilter = "all" | "ready" | "review";
type DownloadState = "idle" | "success" | "error";
type CsvRow = Record<string, string>;

const reportStatus = (plan: LatestRoutePlan) =>
  plan.failure_reason || plan.unassigned_jobs_count > 0 ? "Review" : "Ready";

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00+05:30`));

const reportDistributionOption = (): EChartsOption => ({
  color: [solarGuardTokens.colorPrimary],
  tooltip: { trigger: "item" },
  series: [
    {
      type: "pie",
      radius: ["54%", "75%"],
      center: ["31%", "50%"],
      label: { show: false },
      itemStyle: { borderColor: solarGuardTokens.colorSurface, borderWidth: 2 },
      data: [{ name: "Daily operations", value: 1 }],
    },
  ],
  graphic: [
    { type: "text", left: "27%", top: "39%", style: { text: "1", fill: solarGuardTokens.colorText, fontSize: 27, fontWeight: 650, align: "center" } },
    { type: "text", left: "25%", top: "57%", style: { text: "Report", fill: solarGuardTokens.colorTextSecondary, fontSize: 10 } },
  ],
});

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

const ReportOverview = ({ plan, rowCount }: { plan: LatestRoutePlan; rowCount: number }) => {
  const status = reportStatus(plan);
  return (
    <aside className="sg-report-overview">
      <div className="sg-report-overview-head"><strong>Report overview</strong><span className={status.toLowerCase()}><i />{status}</span></div>
      <dl>
        <div><dt><FileTextOutlined /> Available reports</dt><dd>1</dd></div>
        <div><dt><CalendarOutlined /> Plan date</dt><dd>{formatDate(plan.planning_date)}</dd></div>
        <div><dt><TableOutlined /> Report rows</dt><dd>{rowCount}</dd></div>
        <div><dt><CheckCircleOutlined /> Export format</dt><dd>CSV</dd></div>
      </dl>
    </aside>
  );
};

const ReportKpi = ({
  icon, label, value, tone, onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: string;
  onClick: () => void;
}) => (
  <button type="button" className="sg-report-kpi" onClick={onClick}>
    <span className={`sg-report-kpi-icon ${tone}`}>{icon}</span>
    <span><small>{label}</small><strong>{value}</strong></span>
  </button>
);

const ReportStatusBadge = ({ value }: { value: string }) => (
  <span className={`sg-report-status status-${value.toLowerCase()}`}>
    {value === "Ready" ? <CheckCircleOutlined /> : <WarningOutlined />}
    {value}
  </span>
);

const CsvPreview = ({ rows, compact = false }: { rows: CsvRow[]; compact?: boolean }) => {
  const columns = rows[0] ? Object.keys(rows[0]).slice(0, compact ? 4 : 8) : [];
  const visibleRows = rows.slice(0, compact ? 3 : 12);
  if (!rows.length) return <EmptyState title="The report contains no rows" description="The backend returned a valid empty plan." />;
  return (
    <div className={`sg-csv-preview${compact ? " compact" : ""}`}>
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr></thead>
        <tbody>{visibleRows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{row[column] || "—"}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
};

const SelectedReport = ({
  plan,
  rows,
  onPreview,
}: {
  plan: LatestRoutePlan;
  rows: CsvRow[];
  onPreview: () => void;
}) => (
  <section className="sg-report-card sg-selected-report" aria-labelledby="selected-report-heading">
    <div className="sg-report-card-head"><h2 id="selected-report-heading">SELECTED REPORT</h2><ReportStatusBadge value={reportStatus(plan)} /></div>
    <div className="sg-selected-report-title"><span><CalendarOutlined /></span><strong>Daily O&amp;M Plan<small>Backend-generated operational plan</small></strong></div>
    <dl className="sg-selected-report-meta">
      <div><dt>Scope</dt><dd>All planned work</dd></div>
      <div><dt>Format</dt><dd>CSV</dd></div>
      <div><dt>Plan date</dt><dd>{formatDate(plan.planning_date)}</dd></div>
      <div><dt>Rows</dt><dd>{rows.length}</dd></div>
      <div><dt>Source run</dt><dd>{plan.analysis_run_id}</dd></div>
      <div><dt>Route plan</dt><dd>{plan.route_plan_id}</dd></div>
    </dl>
    <p className="sg-report-description">Operational plan with field visits, remote actions, monitoring work, probable issues, route sequence, and recoverable-energy estimates.</p>
    <div className="sg-report-preview"><CsvPreview rows={rows} compact /></div>
    <Button icon={<EyeOutlined />} onClick={onPreview}>Preview Full Report</Button>
  </section>
);

const ExportCard = ({
  plan,
  loading,
  downloadState,
  onDownload,
  onRetry,
}: {
  plan: LatestRoutePlan;
  loading: boolean;
  downloadState: DownloadState;
  onDownload: () => void;
  onRetry: () => void;
}) => (
  <section className="sg-report-card sg-report-export" aria-labelledby="report-export-heading">
    <h2 id="report-export-heading">DOWNLOAD &amp; EXPORT</h2>
    <div className="sg-report-export-body">
      <Button type="primary" icon={<DownloadOutlined />} loading={loading} onClick={onDownload}>Download Daily O&amp;M Plan.csv</Button>
      <dl>
        <div><dt>Authoritative source</dt><dd>FastAPI report service</dd></div>
        <div><dt>Plan date</dt><dd>{formatDate(plan.planning_date)}</dd></div>
        <div><dt>Delivery</dt><dd>Manual CSV download</dd></div>
      </dl>
    </div>
    <p className="sg-report-capability-note"><InfoCircleOutlined /> Scheduling, email delivery, PDF, and XLSX are not configured for this POC.</p>
    <div role="status" aria-live="polite" className="sg-report-download-status">
      {downloadState === "success" ? "Daily O&M Plan CSV downloaded." : downloadState === "error" ? <><span>Unable to download Daily O&M Plan.</span><Button size="small" icon={<ReloadOutlined />} onClick={onRetry}>Retry</Button></> : ""}
    </div>
  </section>
);

export const ReportsPage = () => {
  const routeQuery = useLatestRoutePlan();
  const refresh = useRefreshOperations();
  const [searchParams, setSearchParams] = useSearchParams();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [downloadState, setDownloadState] = useState<DownloadState>("idle");
  const plan = routeQuery.data;
  const reportQuery = useDailyPlanReport(plan?.route_plan_id);

  useEffect(() => {
    let active = true;
    if (!reportQuery.data?.blob) {
      return () => { active = false; };
    }
    void reportQuery.data.blob.text().then((text) => { if (active) setCsvText(text); });
    return () => { active = false; };
  }, [reportQuery.data?.blob]);

  const parsed = useMemo(
    () => csvText ? Papa.parse<CsvRow>(csvText, { header: true, skipEmptyLines: true }) : undefined,
    [csvText],
  );
  const rows = parsed?.data ?? [];
  const category = (searchParams.get("category") as ReportCategory) || "all";
  const statusFilter = (searchParams.get("status") as ReportStatusFilter) || "all";
  const selected = searchParams.get("selected") ?? "daily-plan";
  const currentStatus = plan ? reportStatus(plan).toLowerCase() : "review";
  const visible = selected === "daily-plan" && (category === "all" || category === "daily-ops") && (statusFilter === "all" || statusFilter === currentStatus);

  const setParam = (key: string, value?: string) => {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all") next.delete(key); else next.set(key, value);
    next.set("page", "1");
    setSearchParams(next);
  };

  const clearFilters = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("category");
    next.delete("status");
    next.set("page", "1");
    setSearchParams(next);
  };

  const runDownload = () => {
    if (!reportQuery.data) return;
    try {
      downloadBlob(reportQuery.data.blob, reportQuery.data.filename);
      setDownloadState("success");
    } catch {
      setDownloadState("error");
    }
  };

  const loading = routeQuery.isLoading || reportQuery.isLoading;
  const error = routeQuery.error ?? reportQuery.error;
  if (routeQuery.error) return <ErrorState title="Unable to load reports" error={routeQuery.error} onRetry={refresh} />;
  if (!loading && !plan) return <EmptyState title="No reports have been generated yet" description="Generate a Technician Plan before downloading the Daily O&M Plan." />;

  return (
    <div className="sg-reports-page">
      <section className="sg-reports-hero" style={{ backgroundImage: `url(${reportsHero})` }}>
        <div className="sg-reports-hero-copy"><span>REPORTS</span><h1>Operational reports,<br />ready to share.</h1><p>Review and export the backend-generated Daily O&amp;M Plan from one operational workspace.</p></div>
        {loading || !plan ? <div className="sg-report-overview"><Skeleton active /></div> : <ReportOverview plan={plan} rowCount={rows.length} />}
      </section>

      <section className="sg-report-kpis" aria-label="Report metrics">
        {loading || !plan ? Array.from({ length: 5 }, (_, index) => <Skeleton.Button key={index} active block />) : (
          <>
            <ReportKpi icon={<FileTextOutlined />} label="Available Reports" value="1" tone="blue" onClick={() => setParam("category", "all")} />
            <ReportKpi icon={<TableOutlined />} label="Report Rows" value={formatInteger(rows.length)} tone="green" onClick={() => setParam("category", "daily-ops")} />
            <ReportKpi icon={<CheckCircleOutlined />} label="Daily Plan Status" value={reportStatus(plan)} tone="blue" onClick={() => setParam("status", reportStatus(plan).toLowerCase())} />
            <ReportKpi icon={<DownloadOutlined />} label="Export Format" value="CSV" tone="green" onClick={() => setParam("category", "daily-ops")} />
            <ReportKpi icon={<EyeOutlined />} label="Pending Review" value={formatInteger(plan.unassigned_jobs_count)} tone="amber" onClick={() => setParam("status", "review")} />
          </>
        )}
      </section>

      <div className="sg-reports-workspace">
        <section className="sg-report-card sg-report-library" aria-labelledby="report-library-heading">
          <div className="sg-report-library-head"><h2 id="report-library-heading">REPORT LIBRARY</h2><span>1 backend report</span></div>
          <div className="sg-report-filters">
            <button type="button" className={category === "all" ? "is-active" : ""} aria-pressed={category === "all"} onClick={() => setParam("category", "all")}>All</button>
            <button type="button" className={category === "daily-ops" ? "is-active" : ""} aria-pressed={category === "daily-ops"} onClick={() => setParam("category", "daily-ops")}>Daily Ops</button>
            <button type="button" className={statusFilter === "ready" ? "is-active" : ""} aria-pressed={statusFilter === "ready"} onClick={() => setParam("status", "ready")}>Ready</button>
            <button type="button" className={statusFilter === "review" ? "is-active" : ""} aria-pressed={statusFilter === "review"} onClick={() => setParam("status", "review")}>Review</button>
          </div>
          {loading || !plan ? <Skeleton active paragraph={{ rows: 6 }} /> : error ? <ErrorState title="Unable to retrieve Daily O&M Plan" error={error} onRetry={() => void reportQuery.refetch()} /> : !visible ? (
            <div className="sg-report-empty"><EmptyState title="No reports match the selected category or status" description="Clear filters to view the Daily O&M Plan." /><Button onClick={clearFilters}>Clear filters</Button></div>
          ) : (
            <>
              <div className="sg-report-table-wrap">
                <table className="sg-report-table">
                  <thead><tr><th>Report name</th><th>Scope</th><th>Frequency</th><th>Plan date</th><th>Format</th><th>Source</th><th>Status</th><th>Action</th></tr></thead>
                  <tbody><tr className="is-selected" tabIndex={0} aria-selected="true" onClick={() => setParam("selected", "daily-plan")} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setParam("selected", "daily-plan"); }}>
                    <td><strong><FileDoneOutlined /> Daily O&amp;M Plan</strong></td><td>All planned work</td><td>On demand</td><td>{formatDate(plan.planning_date)}</td><td><span className="sg-report-format">CSV</span></td><td>FastAPI</td><td><ReportStatusBadge value={reportStatus(plan)} /></td><td><Button size="small" icon={<EyeOutlined />} onClick={(event) => { event.stopPropagation(); setPreviewOpen(true); }}>Preview</Button></td>
                  </tr></tbody>
                </table>
                <div className="sg-report-mobile-list"><button type="button" className="is-selected" onClick={() => setParam("selected", "daily-plan")}><span><FileDoneOutlined /><ReportStatusBadge value={reportStatus(plan)} /></span><strong>Daily O&amp;M Plan<small>{formatDate(plan.planning_date)} · CSV</small></strong><em>All planned work · {rows.length} rows</em></button></div>
              </div>
              <div className="sg-report-pagination"><span>Showing 1 to 1 of 1 report</span><b>Page 1</b></div>
            </>
          )}
        </section>

        <aside className="sg-report-rail">
          <section className="sg-report-card sg-report-distribution" aria-labelledby="report-distribution-heading"><h2 id="report-distribution-heading">REPORT DISTRIBUTION</h2><div><EChart option={reportDistributionOption()} ariaLabel="One Daily Operations report" expandable expandedTitle="Report Distribution" /><dl><div><dt><i />Daily operations</dt><dd>1 (100%)</dd></div></dl></div></section>
          {plan ? <SelectedReport plan={plan} rows={rows} onPreview={() => setPreviewOpen(true)} /> : null}
          {plan ? <ExportCard plan={plan} loading={reportQuery.isLoading} downloadState={downloadState} onDownload={runDownload} onRetry={() => void reportQuery.refetch().then(() => setDownloadState("idle"))} /> : null}
        </aside>
      </div>

      <Modal open={previewOpen} title="Daily O&M Plan preview" width={1000} onCancel={() => setPreviewOpen(false)} footer={<Button type="primary" onClick={() => setPreviewOpen(false)}>Close preview</Button>}>
        <p className="sg-report-preview-disclosure"><DatabaseOutlined /> Demonstration environment — operationally realistic synthetic data.</p>
        {parsed?.errors.length ? <p className="sg-report-parse-warning"><WarningOutlined /> Some preview rows could not be parsed. The downloaded backend file remains authoritative.</p> : null}
        <CsvPreview rows={rows} />
      </Modal>
    </div>
  );
};
