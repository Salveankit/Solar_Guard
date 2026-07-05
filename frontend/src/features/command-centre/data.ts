import type { EChartsOption } from "echarts";

import { solarGuardTokens } from "../../app/theme";
import type { ServiceDecision } from "../../api/schemas/decisions";
import type { FleetSummary, FleetTimeseriesItem } from "../../api/schemas/fleet";
import type { LatestRoutePlan } from "../../api/schemas/routes";

export type WorkBreakdown = {
  fieldVisits: number;
  remoteActions: number;
  monitoring: number;
};

export type CategoryCount = {
  name: string;
  value: number;
};

const issuePaletteByLabel: Record<string, string> = {
  "Unknown/Insufficient Evidence": solarGuardTokens.colorUnknown,
  "Communication/Data Failure": solarGuardTokens.priorityCritical,
  "Time-Specific Underperformance": solarGuardTokens.priorityLow,
  "Sudden Production Outage": solarGuardTokens.priorityMedium,
  "Gradual Persistent Underperformance": solarGuardTokens.priorityHigh,
};

const issueLabels: Record<string, string> = {
  "communication or data-logger failure": "Communication/Data Failure",
  "probable inverter or grid-side interruption": "Sudden Production Outage",
  "probable gradual soiling or persistent degradation":
    "Gradual Persistent Underperformance",
  "probable recurring shade or obstruction": "Time-Specific Underperformance",
  "unknown or insufficient evidence": "Unknown/Insufficient Evidence",
};

export const getWorkBreakdown = (
  summary?: FleetSummary,
  route?: LatestRoutePlan,
): WorkBreakdown => ({
  fieldVisits: route?.assigned_jobs ?? summary?.field_visits ?? 0,
  remoteActions: route?.remote_action_queue.length ?? summary?.remote_actions ?? 0,
  monitoring: route?.monitoring_queue.length ?? summary?.insufficient_evidence ?? 0,
});

export const issueDistribution = (
  items: ServiceDecision[],
): CategoryCount[] => {
  const counts = new Map<string, number>();
  for (const item of items) {
    const label = issueLabels[item.probable_issue] ?? displayIssue(item.probable_issue);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((left, right) => right.value - left.value || left.name.localeCompare(right.name));
};

export const priorityDistribution = (
  items: ServiceDecision[],
): CategoryCount[] => {
  const ordered = ["Critical", "High", "Medium", "Low"];
  return ordered.map((name) => ({
    name,
    value: items.filter((item) => item.priority_label === name).length,
  }));
};

export const topPriorityActions = (
  items: ServiceDecision[],
): ServiceDecision[] =>
  items
    .filter((item) => item.queue_rank !== null)
    .sort((left, right) => {
      const leftRank = left.queue_rank ?? Number.MAX_SAFE_INTEGER;
      const rightRank = right.queue_rank ?? Number.MAX_SAFE_INTEGER;
      return leftRank - rightRank;
    })
    .slice(0, 5);

export const topPriorityEvidence = (
  items: ServiceDecision[],
): ServiceDecision | undefined => topPriorityActions(items)[0];

export const displayIssue = (issue: string): string =>
  issue
    .replaceAll("_", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^possible/i, "probable")
    .replace(/\b\w/g, (character) => character.toUpperCase());

export const issueColor = (label: string): string =>
  issuePaletteByLabel[label] ?? solarGuardTokens.colorUnknown;

export const latestGenerationWindow = (rows: FleetTimeseriesItem[]): FleetTimeseriesItem[] =>
  rows.slice(-24);

export const latestIrradianceReading = (rows: FleetTimeseriesItem[]): number | null => {
  const latest = [...rows]
    .reverse()
    .find((row) => typeof row.ghi_wm2 === "number" && row.ghi_wm2 > 0);
  return latest?.ghi_wm2 ?? null;
};

export const planReadinessPercent = (route?: LatestRoutePlan): number => {
  if (!route || route.total_eligible_jobs === 0) {
    return 0;
  }
  return Math.round((route.assigned_jobs / route.total_eligible_jobs) * 100);
};

export const zeroDistanceMessage = (route?: LatestRoutePlan): string => {
  if (!route) {
    return "No technician route plan is available yet.";
  }
  if (route.distance_avoided_km === 0) {
    return "The current route is skill-feasible and shift-compliant. The present two-stop technician routes have equal closed-route distance in either sequence.";
  }
  return "Distance avoided is calculated from the current technician plan.";
};

export const workBreakdownOption = (
  breakdown: WorkBreakdown,
): EChartsOption => ({
  color: [
    solarGuardTokens.colorField,
    solarGuardTokens.colorRemote,
    solarGuardTokens.colorMonitoring,
  ],
  tooltip: { trigger: "axis" },
  grid: { left: 12, right: 18, top: 24, bottom: 22, containLabel: true },
  xAxis: { type: "value", minInterval: 1 },
  yAxis: {
    type: "category",
    data: ["Field visits", "Remote actions", "Monitoring"],
  },
  series: [
    {
      type: "bar",
      data: [
        breakdown.fieldVisits,
        breakdown.remoteActions,
        breakdown.monitoring,
      ],
      barMaxWidth: 28,
    },
  ],
});

export const issueDistributionOption = (
  distribution: CategoryCount[],
): EChartsOption => ({
  color: [
    solarGuardTokens.colorPrimary,
    solarGuardTokens.colorSecondary,
    solarGuardTokens.colorInfo,
    solarGuardTokens.colorWarning,
    solarGuardTokens.colorMonitoring,
  ],
  tooltip: { trigger: "axis" },
  grid: { left: 12, right: 20, top: 24, bottom: 24, containLabel: true },
  xAxis: { type: "value", minInterval: 1 },
  yAxis: {
    type: "category",
    data: distribution.map((item) => item.name),
    axisLabel: {
      width: 210,
      overflow: "truncate",
    },
  },
  series: [
    {
      type: "bar",
      data: distribution.map((item) => item.value),
      barMaxWidth: 24,
    },
  ],
});

export const priorityDistributionOption = (
  distribution: CategoryCount[],
): EChartsOption => ({
  color: [
    solarGuardTokens.priorityCritical,
    solarGuardTokens.priorityHigh,
    solarGuardTokens.priorityMedium,
    solarGuardTokens.priorityLow,
  ],
  tooltip: { trigger: "axis" },
  grid: { left: 12, right: 16, top: 24, bottom: 22, containLabel: true },
  xAxis: {
    type: "category",
    data: distribution.map((item) => item.name),
  },
  yAxis: { type: "value", minInterval: 1 },
  series: [
    {
      type: "bar",
      data: distribution.map((item) => item.value),
      barMaxWidth: 32,
    },
  ],
});

export const fleetTimeseriesOption = (
  rows: FleetTimeseriesItem[],
): EChartsOption => ({
  color: [
    solarGuardTokens.colorPrimary,
    solarGuardTokens.colorSecondary,
    solarGuardTokens.colorDanger,
  ],
  tooltip: { trigger: "axis" },
  legend: { top: 0 },
  grid: { left: 12, right: 20, top: 36, bottom: 22, containLabel: true },
  xAxis: {
    type: "category",
    data: rows.map((row) => row.timestamp),
    axisLabel: { show: false },
  },
  yAxis: { type: "value", name: "kWh" },
  series: [
    {
      name: "Expected",
      type: "line",
      showSymbol: false,
      data: rows.map((row) => row.expected_generation_kwh),
    },
    {
      name: "Actual",
      type: "line",
      showSymbol: false,
      data: rows.map((row) => row.actual_generation_kwh),
    },
    {
      name: "Energy loss",
      type: "bar",
      data: rows.map((row) => row.energy_loss_kwh),
      barMaxWidth: 10,
    },
  ],
});

export const commandGenerationOption = (
  rows: FleetTimeseriesItem[],
): EChartsOption => ({
  color: [
    solarGuardTokens.chartExpected,
    solarGuardTokens.chartActual,
    solarGuardTokens.chartIrradiance,
  ],
  backgroundColor: "transparent",
  tooltip: {
    trigger: "axis",
    valueFormatter: (value) =>
      typeof value === "number" ? value.toLocaleString("en-IN") : String(value ?? ""),
  },
  legend: {
    top: 0,
    right: 12,
    textStyle: { color: solarGuardTokens.colorTextSecondary, fontSize: 11 },
    itemWidth: 18,
    itemHeight: 8,
  },
  grid: { left: 36, right: 42, top: 42, bottom: 26 },
  xAxis: {
    type: "category",
    boundaryGap: false,
    data: rows.map((row) =>
      new Intl.DateTimeFormat("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(new Date(row.timestamp)),
    ),
    axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
    axisLine: { lineStyle: { color: solarGuardTokens.colorBorderSubtle } },
    axisTick: { show: false },
  },
  yAxis: [
    {
      type: "value",
      name: "kWh",
      nameTextStyle: { color: solarGuardTokens.chartActual, fontSize: 11 },
      splitLine: { lineStyle: { color: solarGuardTokens.chartGrid } },
      axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
    },
    {
      type: "value",
      name: "W/m²",
      nameTextStyle: { color: solarGuardTokens.chartActual, fontSize: 11 },
      splitLine: { show: false },
      axisLabel: { color: solarGuardTokens.colorTextMuted, fontSize: 11 },
    },
  ],
  series: [
    {
      name: "Expected",
      type: "line",
      showSymbol: false,
      smooth: false,
      lineStyle: { type: "dashed", width: 2 },
      data: rows.map((row) => row.expected_generation_kwh),
    },
    {
      name: "Actual",
      type: "line",
      showSymbol: false,
      smooth: false,
      lineStyle: { width: 2 },
      data: rows.map((row) => row.actual_generation_kwh),
    },
    {
      name: "Irradiance",
      type: "line",
      yAxisIndex: 1,
      showSymbol: false,
      smooth: false,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.18 },
      data: rows.map((row) => row.ghi_wm2),
    },
  ],
});

export const incidentDonutOption = (
  distribution: CategoryCount[],
  {
    showLegend = false,
  }: {
    showLegend?: boolean;
  } = {},
): EChartsOption => ({
  color: distribution.map((item) => issueColor(item.name)),
  tooltip: { trigger: "item" },
  legend: {
    show: showLegend,
    orient: showLegend ? "vertical" : "horizontal",
    right: showLegend ? 12 : 0,
    left: showLegend ? "60%" : "center",
    top: showLegend ? "middle" : "bottom",
    itemWidth: 9,
    itemHeight: 9,
    textStyle: { color: solarGuardTokens.colorTextSecondary, fontSize: 12 },
  },
  grid: showLegend
    ? { left: 0, right: 0, top: 0, bottom: 0, containLabel: true }
    : undefined,
  series: [
    {
      name: "Incidents",
      type: "pie",
      radius: showLegend ? ["56%", "76%"] : ["58%", "80%"],
      center: showLegend ? ["28%", "52%"] : ["50%", "50%"],
      avoidLabelOverlap: true,
      label: { show: false },
      itemStyle: { borderColor: solarGuardTokens.colorSurface, borderWidth: 2 },
      data: distribution,
    },
  ],
  graphic: [
    {
      type: "text",
      left: showLegend ? "24%" : "44%",
      top: showLegend ? "42%" : "40%",
      style: {
        text: `${distribution.reduce((total, item) => total + item.value, 0)}`,
        fill: solarGuardTokens.colorText,
        fontSize: 28,
        fontWeight: 600,
        align: "center",
      },
    },
    {
      type: "text",
      left: showLegend ? "23%" : "43%",
      top: showLegend ? "56%" : "55%",
      style: {
        text: "Total",
        fill: solarGuardTokens.colorTextSecondary,
        fontSize: 12,
        align: "center",
      },
    },
  ],
});

export const readinessGaugeOption = (readiness: number): EChartsOption => ({
  color: [solarGuardTokens.colorSuccess],
  series: [
    {
      type: "gauge",
      startAngle: 90,
      endAngle: -270,
      radius: "86%",
      pointer: { show: false },
      progress: {
        show: true,
        roundCap: true,
        width: 8,
      },
      axisLine: {
        roundCap: true,
        lineStyle: {
          width: 8,
          color: [[1, "rgba(126, 166, 199, 0.18)"]],
        },
      },
      splitLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      detail: {
        valueAnimation: false,
        formatter: "{value}%",
        color: solarGuardTokens.colorText,
        fontSize: 26,
        fontWeight: 600,
        offsetCenter: [0, "-4%"],
      },
      title: {
        show: true,
        offsetCenter: [0, "22%"],
        color: solarGuardTokens.colorSuccess,
        fontSize: 11,
      },
      data: [{ value: readiness, name: "Plan Readiness" }],
    },
  ],
});
