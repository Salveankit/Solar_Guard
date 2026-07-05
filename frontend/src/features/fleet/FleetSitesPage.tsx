import {
  ApartmentOutlined,
  AppstoreOutlined,
  ArrowRightOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  DeploymentUnitOutlined,
  EyeOutlined,
  HeartOutlined,
  HomeOutlined,
  InfoCircleOutlined,
  RadarChartOutlined,
  SearchOutlined,
  SelectOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  TeamOutlined,
  WarningOutlined,
  WifiOutlined,
} from "@ant-design/icons";
import { Button, Card, Input, Select, Skeleton, Space, Tooltip } from "antd";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import fleetHeroImage from "../../assets/fleet-sites-hero.png";
import { solarGuardTokens } from "../../app/theme";
import type { ServiceDecision } from "../../api/schemas/decisions";
import type { FleetSummary } from "../../api/schemas/fleet";
import type { SiteSummary } from "../../api/schemas/sites";
import { EChart } from "../../components/charts/EChart";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import {
  useFleetSummary,
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

type HealthState = "healthy" | "attention" | "communication" | "unknown";
type ReportingState = "live" | "delayed" | "offline";
type SortKey = "site" | "region" | "capacity" | "health" | "issue";
type SortOrder = "asc" | "desc";

type EnrichedSite = SiteSummary & {
  health: HealthState;
  reporting: ReportingState;
  decision?: ServiceDecision;
};

type StatusBreakdown = {
  healthy: number;
  attention: number;
  communication: number;
  unknown: number;
};

const allOption = "all";
const pageSizeOptions = [8, 16, 24];
const sortKeys: SortKey[] = ["site", "region", "capacity", "health", "issue"];
const darkSelectClassNames = {
  popup: { root: "sg-dark-select-dropdown" },
} as const;

const healthLabels: Record<HealthState, string> = {
  healthy: "Healthy",
  attention: "Attention",
  communication: "Communication Loss",
  unknown: "Unknown",
};

const reportingLabels: Record<ReportingState, string> = {
  live: "Live",
  delayed: "Delayed",
  offline: "Offline",
};

const normalise = (value?: string | null): string => (value ?? "").toLowerCase();

const deriveHealth = (site: SiteSummary): HealthState => {
  const issue = normalise(site.probable_issue);
  if (issue.includes("communication")) {
    return "communication";
  }
  if (issue.includes("unknown") || issue.includes("insufficient")) {
    return "unknown";
  }
  if (site.status.toLowerCase() === "healthy") {
    return "healthy";
  }
  return "attention";
};

const deriveReporting = (health: HealthState): ReportingState => {
  if (health === "communication") {
    return "offline";
  }
  if (health === "unknown") {
    return "delayed";
  }
  return "live";
};

const enrichSites = (
  sites: SiteSummary[],
  decisions: ServiceDecision[],
): EnrichedSite[] => {
  const decisionsBySite = new Map(decisions.map((item) => [item.site_id, item]));
  return sites.map((site) => {
    const health = deriveHealth(site);
    return {
      ...site,
      health,
      reporting: deriveReporting(health),
      decision: decisionsBySite.get(site.site_id),
    };
  });
};

const statusBreakdown = (
  summary?: FleetSummary,
  sites?: EnrichedSite[],
): StatusBreakdown => {
  if (summary) {
    const communication = summary.communication_issues;
    const unknown = summary.insufficient_evidence;
    return {
      healthy: summary.healthy_sites,
      communication,
      unknown,
      attention: Math.max(
        summary.monitored_sites - summary.healthy_sites - communication - unknown,
        0,
      ),
    };
  }
  const rows = sites ?? [];
  return {
    healthy: rows.filter((site) => site.health === "healthy").length,
    attention: rows.filter((site) => site.health === "attention").length,
    communication: rows.filter((site) => site.health === "communication").length,
    unknown: rows.filter((site) => site.health === "unknown").length,
  };
};

const fieldVisitValue = (items: ServiceDecision[]): number =>
  items
    .filter((item) => item.visit_required)
    .reduce((total, item) => total + item.estimated_recoverable_value_inr, 0);

const issueLabel = (site: EnrichedSite): string =>
  site.probable_issue ? displayIssue(site.probable_issue) : "None detected";

const issueFilterValue = (site: EnrichedSite): string => {
  const issue = normalise(site.probable_issue);
  if (issue.includes("communication")) return "communication";
  if (issue.includes("sudden") || issue.includes("outage") || issue.includes("interruption")) return "sudden";
  if (issue.includes("gradual") || issue.includes("soiling") || issue.includes("degradation")) return "gradual";
  if (issue.includes("time") || issue.includes("shading") || issue.includes("obstruction")) return "time";
  if (issue.includes("unknown") || issue.includes("insufficient")) return "insufficient";
  return "none";
};

const sortSites = (
  sites: EnrichedSite[],
  sortKey: SortKey,
  sortOrder: SortOrder,
): EnrichedSite[] => {
  const multiplier = sortOrder === "asc" ? 1 : -1;
  return [...sites].sort((left, right) => {
    const compare = (a: string | number, b: string | number) =>
      typeof a === "number" && typeof b === "number"
        ? a - b
        : String(a).localeCompare(String(b));
    const result =
      sortKey === "site"
        ? compare(left.site_name, right.site_name)
        : sortKey === "region"
          ? compare(left.service_region, right.service_region)
          : sortKey === "capacity"
            ? compare(left.capacity_kw, right.capacity_kw)
            : sortKey === "health"
              ? compare(left.health, right.health)
              : compare(issueLabel(left), issueLabel(right));
    return result * multiplier;
  });
};

const breakdownOption = (breakdown: StatusBreakdown): EChartsOption => {
  const total =
    breakdown.healthy +
    breakdown.attention +
    breakdown.communication +
    breakdown.unknown;
  return {
    color: [
      solarGuardTokens.colorSuccess,
      solarGuardTokens.colorWarning,
      solarGuardTokens.colorRemote,
      solarGuardTokens.colorUnknown,
    ],
    tooltip: { trigger: "item" },
    legend: { show: false },
    series: [
      {
        type: "pie",
        radius: ["56%", "76%"],
        center: ["32%", "52%"],
        label: { show: false },
        itemStyle: {
          borderColor: solarGuardTokens.colorSurface,
          borderWidth: 2,
        },
        data: [
          { name: "Healthy", value: breakdown.healthy },
          { name: "Attention", value: breakdown.attention },
          { name: "Communication Loss", value: breakdown.communication },
          { name: "Unknown", value: breakdown.unknown },
        ],
      },
    ],
    graphic: [
      {
        type: "text",
        left: "27%",
        top: "43%",
        style: {
          text: String(total),
          fill: solarGuardTokens.colorText,
          fontSize: 25,
          fontWeight: 650,
          align: "center",
        },
      },
      {
        type: "text",
        left: "24%",
        top: "57%",
        style: {
          text: "Total Sites",
          fill: solarGuardTokens.colorTextSecondary,
          fontSize: 11,
          align: "center",
        },
      },
    ],
  };
};

const updateParam = (
  params: URLSearchParams,
  key: string,
  value?: string | number,
) => {
  const stringValue = String(value ?? "");
  if (!stringValue || stringValue === allOption) {
    params.delete(key);
  } else {
    params.set(key, stringValue);
  }
};

type FleetKPIProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  tone: HealthState | "field" | "data" | "total";
};

const FleetKPIItem = ({ icon, label, value, note, tone }: FleetKPIProps) => (
  <div className="sg-fleet-kpi-item">
    <span className={`sg-fleet-kpi-icon ${tone}`}>{icon}</span>
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  </div>
);

const HealthBadge = ({ health }: { health: HealthState }) => (
  <span className={`sg-health-badge ${health}`}>
    {health === "healthy" ? <HeartOutlined /> : null}
    {health === "attention" ? <WarningOutlined /> : null}
    {health === "communication" ? <WifiOutlined /> : null}
    {health === "unknown" ? <InfoCircleOutlined /> : null}
    {healthLabels[health]}
  </span>
);

const ReportingStatus = ({ status }: { status: ReportingState }) => (
  <span className={`sg-reporting-status ${status}`}>
    <i />
    {reportingLabels[status]}
  </span>
);

const DataCompletenessBar = ({ health }: { health: HealthState }) => (
  <Tooltip title="Interval completeness is not exposed by the current /api/sites response. Missing telemetry is not displayed as zero.">
    <div className="sg-data-completeness">
      <span>Unavailable</span>
      <div>
        <i className={health} />
      </div>
    </div>
  </Tooltip>
);

const SiteIcon = ({ site }: { site: EnrichedSite }) => {
  const type = normalise(site.customer_type);
  const Icon = type.includes("residential")
    ? HomeOutlined
    : type.includes("industrial")
      ? DeploymentUnitOutlined
      : ApartmentOutlined;
  return (
    <span className={`sg-site-type-icon ${site.health}`}>
      <Icon />
    </span>
  );
};

type FilterBarProps = {
  regions: string[];
  search: string;
  region: string;
  health: string;
  issue: string;
  reporting: string;
  viewMode: string;
  setQueryValue: (key: string, value?: string | number) => void;
  clearFilters: () => void;
};

const FleetFilterBar = ({
  regions,
  search,
  region,
  health,
  issue,
  reporting,
  viewMode,
  setQueryValue,
  clearFilters,
}: FilterBarProps) => (
  <section className="sg-fleet-toolbar" aria-label="Fleet site filters">
    <Input
      className="sg-fleet-search"
      prefix={<SearchOutlined />}
      allowClear
      placeholder="Search sites..."
      value={search}
      onChange={(event) => setQueryValue("q", event.target.value)}
      aria-label="Search sites"
    />
    <label>
      <span>Region</span>
      <Select
        value={region}
        aria-label="Filter by region"
        classNames={darkSelectClassNames}
        onChange={(value) => setQueryValue("region", value)}
        options={[
          { value: allOption, label: "All Regions" },
          ...regions.map((item) => ({ value: item, label: item })),
        ]}
      />
    </label>
    <label>
      <span>Status</span>
      <Select
        value={health}
        aria-label="Filter by site health"
        classNames={darkSelectClassNames}
        onChange={(value) => setQueryValue("status", value)}
        options={[
          { value: allOption, label: "All Statuses" },
          { value: "healthy", label: "Healthy" },
          { value: "attention", label: "Attention" },
          { value: "communication", label: "Communication Loss" },
          { value: "unknown", label: "Unknown" },
        ]}
      />
    </label>
    <label>
      <span>Probable Issue</span>
      <Select
        value={issue}
        aria-label="Filter by probable issue"
        classNames={darkSelectClassNames}
        onChange={(value) => setQueryValue("issue", value)}
        options={[
          { value: allOption, label: "All Issues" },
          { value: "communication", label: "Communication/Data Failure" },
          { value: "sudden", label: "Sudden Production Outage" },
          { value: "gradual", label: "Gradual Underperformance" },
          { value: "time", label: "Time-Specific Underperformance" },
          { value: "insufficient", label: "Insufficient Evidence" },
        ]}
      />
    </label>
    <label>
      <span>Reporting Status</span>
      <Select
        value={reporting}
        aria-label="Filter by reporting status"
        classNames={darkSelectClassNames}
        onChange={(value) => setQueryValue("reporting", value)}
        options={[
          { value: allOption, label: "All" },
          { value: "live", label: "Live" },
          { value: "delayed", label: "Delayed" },
          { value: "offline", label: "Offline" },
        ]}
      />
    </label>
    <div className="sg-view-toggle" role="group" aria-label="Fleet view mode">
      <Button
        className={viewMode === "list" ? "is-active" : ""}
        onClick={() => setQueryValue("view", "list")}
        icon={<BarChartOutlined />}
      >
        List View
      </Button>
      <Button
        className={viewMode === "map" ? "is-active" : ""}
        onClick={() => setQueryValue("view", "map")}
        icon={<AppstoreOutlined />}
      >
        Map View
      </Button>
    </div>
    <Button className="sg-clear-filter" onClick={clearFilters}>
      Clear Filters
    </Button>
  </section>
);

type SiteInventoryProps = {
  rows: EnrichedSite[];
  totalRows: number;
  selectedSiteId?: string;
  page: number;
  pageSize: number;
  sortKey: SortKey;
  sortOrder: SortOrder;
  onSort: (key: SortKey) => void;
  onSelect: (site: EnrichedSite) => void;
  onPage: (page: number) => void;
  onPageSize: (size: number) => void;
  onOpen: (siteId: string) => void;
  clearFilters: () => void;
};

const SiteInventoryTable = ({
  rows,
  totalRows,
  selectedSiteId,
  page,
  pageSize,
  sortKey,
  sortOrder,
  onSort,
  onSelect,
  onPage,
  onPageSize,
  onOpen,
  clearFilters,
}: SiteInventoryProps) => {
  const pageCount = Math.max(Math.ceil(totalRows / pageSize), 1);
  const start = totalRows === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalRows);

  return (
    <Card
      className="sg-card sg-site-inventory-card"
      title={
        <Space>
          <span className="sg-card-title">SITE INVENTORY</span>
          <span className="sg-count-pill">{formatInteger(totalRows)} sites</span>
        </Space>
      }
    >
      {rows.length ? (
        <>
          <div className="sg-site-table-wrap">
            <table className="sg-site-table">
              <thead>
                <tr>
                  <th>
                    <SortHeaderButton
                      id="site"
                      label="Site"
                      sortKey={sortKey}
                      sortOrder={sortOrder}
                      onSort={onSort}
                    />
                  </th>
                  <th>
                    <SortHeaderButton
                      id="region"
                      label="Region"
                      sortKey={sortKey}
                      sortOrder={sortOrder}
                      onSort={onSort}
                    />
                  </th>
                  <th>
                    <SortHeaderButton
                      id="capacity"
                      label="Capacity DC"
                      sortKey={sortKey}
                      sortOrder={sortOrder}
                      onSort={onSort}
                    />
                  </th>
                  <th>Current Generation Now</th>
                  <th>
                    <SortHeaderButton
                      id="health"
                      label="Site Health"
                      sortKey={sortKey}
                      sortOrder={sortOrder}
                      onSort={onSort}
                    />
                  </th>
                  <th>Data Completeness</th>
                  <th>
                    <SortHeaderButton
                      id="issue"
                      label="Probable Issue"
                      sortKey={sortKey}
                      sortOrder={sortOrder}
                      onSort={onSort}
                    />
                  </th>
                  <th>Last Update</th>
                  <th>View</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((site) => (
                  <tr
                    key={site.site_id}
                    className={site.site_id === selectedSiteId ? "is-selected" : ""}
                    tabIndex={0}
                    onClick={() => onSelect(site)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSelect(site);
                      }
                    }}
                  >
                    <td>
                      <div className="sg-site-cell">
                        <SiteIcon site={site} />
                        <span>
                          <strong>{site.site_name}</strong>
                          <small>{site.site_id}</small>
                        </span>
                      </div>
                    </td>
                    <td>{site.service_region}</td>
                    <td>{formatInteger(site.capacity_kw)} kWp</td>
                    <td>
                      <span className="sg-unavailable-value">Unavailable</span>
                      <small className="sg-table-note">Not exposed by API</small>
                    </td>
                    <td><HealthBadge health={site.health} /></td>
                    <td><DataCompletenessBar health={site.health} /></td>
                    <td>
                      <span>{issueLabel(site)}</span>
                      {site.decision ? (
                        <small className={`sg-priority-dot priority-${site.decision.priority_label.toLowerCase()}`}>
                          {site.decision.priority_label} priority
                        </small>
                      ) : null}
                    </td>
                    <td>
                      <span className="sg-unavailable-value">Analysis run</span>
                      <ReportingStatus status={site.reporting} />
                    </td>
                    <td>
                      <Button
                        className="sg-row-action"
                        aria-label={`Open diagnostics for ${site.site_name}`}
                        icon={<SelectOutlined />}
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpen(site.site_id);
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sg-pagination-bar">
            <span>
              Showing {formatInteger(start)} to {formatInteger(end)} of{" "}
              {formatInteger(totalRows)} sites
            </span>
            <div>
              <Button
                aria-label="Previous page"
                disabled={page <= 1}
                onClick={() => onPage(page - 1)}
              >
                Previous
              </Button>
              {Array.from({ length: Math.min(pageCount, 4) }, (_, index) => index + 1).map((item) => (
                <Button
                  key={item}
                  className={item === page ? "is-active" : ""}
                  aria-label={`Page ${item}`}
                  onClick={() => onPage(item)}
                >
                  {item}
                </Button>
              ))}
              {pageCount > 4 ? <span className="sg-ellipsis">...</span> : null}
              <Button
                aria-label="Next page"
                disabled={page >= pageCount}
                onClick={() => onPage(page + 1)}
              >
                Next
              </Button>
              <Select
                value={pageSize}
                aria-label="Rows per page"
                classNames={darkSelectClassNames}
                onChange={onPageSize}
                options={pageSizeOptions.map((value) => ({
                  value,
                  label: `${value} / page`,
                }))}
              />
            </div>
          </div>
        </>
      ) : (
        <div className="sg-fleet-empty">
          <EmptyState
            title="No sites match these filters"
            description="Clear filters or search by a different site, region, status, or probable issue."
          />
          <Button onClick={clearFilters}>Clear filters</Button>
        </div>
      )}
    </Card>
  );
};

type MapPanelProps = {
  breakdown: StatusBreakdown;
  sites: EnrichedSite[];
  selectedSite?: EnrichedSite;
  onFilter: (health: HealthState) => void;
  onSelect: (site: EnrichedSite) => void;
};

const FleetMapPanel = ({
  breakdown,
  sites,
  selectedSite,
  onFilter,
  onSelect,
}: MapPanelProps) => {
  const firstByHealth = (health: HealthState) =>
    sites.find((site) => site.health === health) ?? sites[0];
  return (
    <Card
      className="sg-card sg-fleet-map-card"
      title={<span className="sg-card-title">PUNE CLUSTER MAP</span>}
    >
      <div className="sg-fleet-map" aria-label="Pune cluster site status map">
        <span className="sg-map-label">Pune</span>
        {([
          ["healthy", breakdown.healthy, "marker-healthy"],
          ["attention", breakdown.attention, "marker-attention"],
          ["communication", breakdown.communication, "marker-communication"],
          ["unknown", breakdown.unknown, "marker-unknown"],
        ] as const).map(([health, count, className]) => (
          <button
            key={health}
            type="button"
            className={`sg-cluster-marker ${className}${selectedSite?.health === health ? " is-selected" : ""}`}
            onClick={() => {
              const site = firstByHealth(health);
              if (site) onSelect(site);
              onFilter(health);
            }}
            aria-label={`Filter ${healthLabels[health]} sites`}
          >
            {formatInteger(count)}
          </button>
        ))}
      </div>
      <div className="sg-map-legend" aria-label="Map legend">
        <span><i className="healthy" /> Healthy {formatInteger(breakdown.healthy)}</span>
        <span><i className="attention" /> Attention {formatInteger(breakdown.attention)}</span>
        <span><i className="communication" /> Comm. Loss {formatInteger(breakdown.communication)}</span>
        <span><i className="unknown" /> Unknown {formatInteger(breakdown.unknown)}</span>
      </div>
    </Card>
  );
};

const StatusBreakdownCard = ({ breakdown }: { breakdown: StatusBreakdown }) => {
  const total =
    breakdown.healthy +
    breakdown.attention +
    breakdown.communication +
    breakdown.unknown;
  const legend = [
    ["healthy", "Healthy", breakdown.healthy],
    ["attention", "Attention", breakdown.attention],
    ["communication", "Comm. Loss", breakdown.communication],
    ["unknown", "Unknown", breakdown.unknown],
  ] as const;
  return (
    <Card
      className="sg-card sg-status-card"
      title={<span className="sg-card-title">SITE STATUS BREAKDOWN</span>}
    >
      <div className="sg-status-layout">
        <EChart
          option={breakdownOption(breakdown)}
          ariaLabel="Site status breakdown"
          expandable
          expandedTitle="Site Status Breakdown"
        />
        <dl className="sg-status-legend">
          {legend.map(([key, label, value]) => (
            <div key={key}>
              <dt><i className={key} /> {label}</dt>
              <dd>
                {formatInteger(value)}{" "}
                <span>({total ? formatPercent((value / total) * 100) : "0%"})</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </Card>
  );
};

const SelectedSiteSnapshot = ({
  site,
  onOpen,
}: {
  site?: EnrichedSite;
  onOpen: (siteId: string) => void;
}) => (
  <Card
    className="sg-card sg-selected-site-card"
    title={<span className="sg-card-title">SELECTED SITE SNAPSHOT</span>}
    extra={site ? <ReportingStatus status={site.reporting} /> : null}
  >
    {site ? (
      <>
        <div className="sg-selected-site-head">
          <SiteIcon site={site} />
          <span>
            <strong>{site.site_name}</strong>
            <small>{site.site_id} - {site.service_region}</small>
          </span>
        </div>
        <dl className="sg-site-snapshot-grid">
          <div>
            <dt>Capacity DC</dt>
            <dd>{formatInteger(site.capacity_kw)} kWp</dd>
          </div>
          <div>
            <dt>Actual Energy</dt>
            <dd>
              {site.decision?.actual_energy_kwh === null || !site.decision
                ? "Unavailable"
                : formatKwh(site.decision.actual_energy_kwh)}
            </dd>
          </div>
          <div>
            <dt>Probable Issue</dt>
            <dd>{issueLabel(site)}</dd>
          </div>
          <div>
            <dt>Confidence Score</dt>
            <dd>
              {site.decision
                ? `${formatPercent(site.decision.confidence_score)} ${site.decision.confidence_label}`
                : "Not applicable"}
            </dd>
          </div>
          <div>
            <dt>Data Completeness</dt>
            <dd>Unavailable</dd>
          </div>
          <div>
            <dt>Energy Value at Risk</dt>
            <dd>{site.decision ? formatInr(site.decision.estimated_value_at_risk_inr) : formatInr(0)}</dd>
          </div>
        </dl>
        <Button
          type="primary"
          block
          icon={<ArrowRightOutlined />}
          onClick={() => onOpen(site.site_id)}
        >
          View Diagnostics
        </Button>
      </>
    ) : (
      <EmptyState title="Select a site" description="Choose a table row or map marker to preview diagnostics." />
    )}
  </Card>
);

const SortHeaderButton = ({
  id,
  label,
  sortKey,
  sortOrder,
  onSort,
}: {
  id: SortKey;
  label: string;
  sortKey: SortKey;
  sortOrder: SortOrder;
  onSort: (key: SortKey) => void;
}) => (
  <button
    type="button"
    className="sg-sort-header"
    aria-label={`Sort by ${label}`}
    onClick={() => onSort(id)}
  >
    {label}
    {sortKey === id ? (
      sortOrder === "asc" ? <SortAscendingOutlined /> : <SortDescendingOutlined />
    ) : null}
  </button>
);

export const FleetSitesPage = () => {
  const navigate = useNavigate();
  const refreshOperations = useRefreshOperations();
  const sitesQuery = useSites();
  const summaryQuery = useFleetSummary();
  const queueQuery = useServiceQueue();
  const [searchParams, setSearchParams] = useSearchParams();

  const search = searchParams.get("q") ?? "";
  const region = searchParams.get("region") ?? allOption;
  const health = searchParams.get("status") ?? allOption;
  const issue = searchParams.get("issue") ?? allOption;
  const reporting = searchParams.get("reporting") ?? allOption;
  const viewMode = searchParams.get("view") === "map" ? "map" : "list";
  const sortParam = searchParams.get("sort");
  const sortKey = sortKeys.includes(sortParam as SortKey) ? (sortParam as SortKey) : "site";
  const sortOrder = searchParams.get("order") === "desc" ? "desc" : "asc";
  const parsedPage = Number(searchParams.get("page") ?? 1);
  const parsedPageSize = Number(searchParams.get("page_size") ?? 8);
  const page = Number.isFinite(parsedPage) ? parsedPage : 1;
  const pageSize = Number.isFinite(parsedPageSize) ? parsedPageSize : 8;
  const selectedSiteId = searchParams.get("selected") ?? undefined;

  const allSites = useMemo(
    () => enrichSites(sitesQuery.data ?? [], queueQuery.data?.items ?? []),
    [queueQuery.data, sitesQuery.data],
  );
  const regions = useMemo(
    () => [...new Set(allSites.map((site) => site.service_region))].sort(),
    [allSites],
  );
  const breakdown = useMemo(
    () => statusBreakdown(summaryQuery.data, allSites),
    [allSites, summaryQuery.data],
  );

  const filteredSites = useMemo(() => {
    const query = normalise(search);
    return allSites.filter((site) => {
      const matchesSearch =
        !query ||
        normalise(site.site_name).includes(query) ||
        normalise(site.site_id).includes(query) ||
        normalise(site.service_region).includes(query);
      const matchesRegion = region === allOption || site.service_region === region;
      const matchesHealth = health === allOption || site.health === health;
      const matchesIssue = issue === allOption || issueFilterValue(site) === issue;
      const matchesReporting = reporting === allOption || site.reporting === reporting;
      return (
        matchesSearch &&
        matchesRegion &&
        matchesHealth &&
        matchesIssue &&
        matchesReporting
      );
    });
  }, [allSites, health, issue, region, reporting, search]);

  const sortedSites = useMemo(
    () => sortSites(filteredSites, sortKey, sortOrder),
    [filteredSites, sortKey, sortOrder],
  );
  const safePageSize = pageSizeOptions.includes(pageSize) ? pageSize : 8;
  const pageCount = Math.max(Math.ceil(sortedSites.length / safePageSize), 1);
  const safePage = Math.min(Math.max(page, 1), pageCount);
  const visibleSites = sortedSites.slice(
    (safePage - 1) * safePageSize,
    safePage * safePageSize,
  );
  const selectedSite =
    allSites.find((site) => site.site_id === selectedSiteId) ?? visibleSites[0] ?? allSites[0];

  useEffect(() => {
    if (page !== safePage || pageSize !== safePageSize) {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        updateParam(next, "page", safePage);
        updateParam(next, "page_size", safePageSize);
        return next;
      });
    }
  }, [page, pageSize, safePage, safePageSize, setSearchParams]);

  const setQueryValue = (key: string, value?: string | number): void => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      updateParam(next, key, value);
      if (key !== "page" && key !== "selected") {
        next.set("page", "1");
      }
      return next;
    });
  };

  const clearFilters = (): void => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      ["q", "region", "status", "issue", "reporting", "page", "selected"].forEach((key) =>
        next.delete(key),
      );
      next.set("view", viewMode);
      next.set("sort", sortKey);
      next.set("order", sortOrder);
      next.set("page_size", String(safePageSize));
      return next;
    });
  };

  const selectSite = (site: EnrichedSite): void => {
    setQueryValue("selected", site.site_id);
  };

  const sortBy = (key: SortKey): void => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      const nextOrder = sortKey === key && sortOrder === "asc" ? "desc" : "asc";
      next.set("sort", key);
      next.set("order", nextOrder);
      next.set("page", "1");
      return next;
    });
  };

  const openDiagnostics = (siteId: string): void => {
    void navigate(`/sites/${siteId}`);
  };

  const hasError = sitesQuery.error || summaryQuery.error || queueQuery.error;
  const loading = sitesQuery.isLoading || summaryQuery.isLoading || queueQuery.isLoading;
  const summary = summaryQuery.data;
  const queueItems = queueQuery.data?.items ?? [];

  return (
    <div className="sg-fleet-page">
      <section
        className="sg-fleet-hero"
        style={{ backgroundImage: `url(${fleetHeroImage})` }}
        aria-labelledby="fleet-sites-title"
      >
        <span className="sg-eyebrow">FLEET SITES</span>
        <h1 id="fleet-sites-title">Monitor every site with clarity.</h1>
        <p>
          Track site health, data completeness, and operational attention across your fleet.
        </p>
      </section>

      {loading ? (
        <section className="sg-fleet-loading" aria-label="Fleet sites loading">
          <Skeleton active paragraph={{ rows: 2 }} />
          <Skeleton active paragraph={{ rows: 8 }} />
        </section>
      ) : null}

      {hasError ? (
        <ErrorState
          title="Unable to load fleet sites"
          error={hasError}
          onRetry={refreshOperations}
        />
      ) : null}

      {summary ? (
        <section className="sg-fleet-kpi-strip" aria-label="Fleet summary KPIs">
          <FleetKPIItem
            icon={<DeploymentUnitOutlined />}
            label="Total Sites"
            value={formatInteger(summary.monitored_sites)}
            note="Across Pune and surrounding region"
            tone="total"
          />
          <FleetKPIItem
            icon={<HeartOutlined />}
            label="Healthy Sites"
            value={formatInteger(summary.healthy_sites)}
            note={`${formatPercent((summary.healthy_sites / Math.max(summary.monitored_sites, 1)) * 100)} of total sites`}
            tone="healthy"
          />
          <FleetKPIItem
            icon={<WarningOutlined />}
            label="Sites Requiring Attention"
            value={formatInteger(summary.attention_sites)}
            note={`${formatPercent((summary.attention_sites / Math.max(summary.monitored_sites, 1)) * 100)} of total sites`}
            tone="attention"
          />
          <FleetKPIItem
            icon={<RadarChartOutlined />}
            label="Communication Issues"
            value={formatInteger(summary.communication_issues)}
            note="Remote check before dispatch"
            tone="communication"
          />
          <FleetKPIItem
            icon={<TeamOutlined />}
            label="Field Visit Candidates"
            value={formatInteger(summary.field_visits)}
            note={`${formatInr(fieldVisitValue(queueItems))} recoverable value`}
            tone="field"
          />
          <FleetKPIItem
            icon={<CheckCircleOutlined />}
            label="Avg. Data Completeness"
            value="Unavailable"
            note="Not exposed by current API"
            tone="data"
          />
        </section>
      ) : null}

      <FleetFilterBar
        regions={regions}
        search={search}
        region={region}
        health={health}
        issue={issue}
        reporting={reporting}
        viewMode={viewMode}
        setQueryValue={setQueryValue}
        clearFilters={clearFilters}
      />

      <div className={`sg-fleet-layout view-${viewMode}`}>
        <SiteInventoryTable
          rows={visibleSites}
          totalRows={sortedSites.length}
          selectedSiteId={selectedSite?.site_id}
          page={safePage}
          pageSize={safePageSize}
          sortKey={sortKey}
          sortOrder={sortOrder}
          onSort={sortBy}
          onSelect={selectSite}
          onPage={(nextPage) => setQueryValue("page", nextPage)}
          onPageSize={(nextSize) => setQueryValue("page_size", nextSize)}
          onOpen={openDiagnostics}
          clearFilters={clearFilters}
        />
        <aside className="sg-fleet-rail" aria-label="Fleet geographic and selected site context">
          <FleetMapPanel
            breakdown={breakdown}
            sites={allSites}
            selectedSite={selectedSite}
            onFilter={(nextHealth) => setQueryValue("status", nextHealth)}
            onSelect={selectSite}
          />
          <StatusBreakdownCard breakdown={breakdown} />
          <SelectedSiteSnapshot site={selectedSite} onOpen={openDiagnostics} />
        </aside>
      </div>

      <div className="sg-state-ribbon">
        <EyeOutlined />
        Site inventory uses backend site, summary, and service-decision APIs. Current power,
        interval completeness, and heartbeat freshness are shown as unavailable until exposed
        by FastAPI.
        <Link to="/service-queue"> Review service queue <ArrowRightOutlined /></Link>
      </div>
    </div>
  );
};
