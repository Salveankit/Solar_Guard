import {
  AlertOutlined,
  BellOutlined,
  BuildOutlined,
  CalendarOutlined,
  DashboardOutlined,
  DownOutlined,
  FileDoneOutlined,
  FileTextOutlined,
  LineChartOutlined,
  SearchOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Avatar, Badge, Button, Input, Layout, Tooltip } from "antd";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import solarGuardLogoIcon from "../../assets/solarguard-logo-icon-hd.png";
import { ApiStatus } from "../status/ApiStatus";
import { DataFreshness } from "../status/DataFreshness";

const { Header, Content } = Layout;

const navItems = [
  {
    key: "/",
    icon: <DashboardOutlined />,
    label: "Command Centre",
  },
  {
    key: "/fleet",
    icon: <TeamOutlined />,
    label: "Fleet Sites",
  },
  {
    key: "/diagnostics",
    icon: <LineChartOutlined />,
    label: "Diagnostics",
  },
  {
    key: "/incidents",
    icon: <AlertOutlined />,
    label: "Incidents",
  },
  {
    key: "/service-queue",
    icon: <FileDoneOutlined />,
    label: "Service Queue",
  },
  {
    key: "/technician-plan",
    icon: <BuildOutlined />,
    label: "Technician Plan",
  },
  {
    key: "/reports",
    icon: <FileTextOutlined />,
    label: "Reports",
  },
];

const routeTitles: Record<string, string> = {
  "/": "Operations Command Centre",
  "/fleet": "Fleet & Sites",
  "/diagnostics": "Site Diagnostics",
  "/incidents": "Incidents",
  "/service-queue": "Service Decision Queue",
  "/technician-plan": "Technician Plan",
  "/reports": "Reports & Daily Plan",
};

type AppShellProps = {
  children: ReactNode;
  apiStatus: "loading" | "live" | "analysis-required" | "partial" | "error";
  isRefreshing: boolean;
  lastUpdated?: Date;
  onRefresh: () => void;
};

const selectedKeyFor = (pathname: string): string => {
  if (pathname.startsWith("/sites/")) {
    return "/diagnostics";
  }
  return routeTitles[pathname] ? pathname : "/";
};

const formatHeaderDate = (value?: Date) => {
  if (!value) {
    return {
      date: "Analysis pending",
      time: "Awaiting backend refresh",
    };
  }

  return {
    date: new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    }).format(value),
    time: new Intl.DateTimeFormat("en-IN", {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    }).format(value),
  };
};

export const AppShell = ({
  children,
  apiStatus,
  isRefreshing,
  lastUpdated,
  onRefresh,
}: AppShellProps) => {
  const [searchValue, setSearchValue] = useState("");
  const location = useLocation();
  const selectedKey = selectedKeyFor(location.pathname);
  const title = useMemo(
    () =>
      location.pathname.startsWith("/sites/")
        ? "Site Diagnostics"
        : routeTitles[selectedKey],
    [location.pathname, selectedKey],
  );
  const headerDate = useMemo(() => formatHeaderDate(lastUpdated), [lastUpdated]);

  return (
    <Layout className="sg-shell" data-page-title={title}>
      <Header className="sg-header">
        <div className="sg-header-left">
          <Link to="/" className="sg-brand" aria-label="SolarGuard home">
            <span className="sg-mark" aria-hidden="true">
              <img src={solarGuardLogoIcon} alt="" />
            </span>
            <span className="sg-brand-title">SOLARGUARD</span>
          </Link>
          <Input
            className="sg-search"
            prefix={<SearchOutlined />}
            suffix={<kbd>⌘ K</kbd>}
            placeholder="Search site, incident, inverter or technician"
            value={searchValue}
            onChange={(event) => setSearchValue(event.target.value)}
            aria-label="Search site, incident, inverter or technician"
          />
        </div>
        <div className="sg-header-actions">
          <Tooltip title="API and analysis availability">
            <span>
              <ApiStatus kind={apiStatus} />
            </span>
          </Tooltip>
          <DataFreshness
            hasCompletedAnalysis={apiStatus !== "analysis-required"}
            isRefreshing={isRefreshing}
            lastUpdated={lastUpdated}
          />
          <Tooltip title="Refresh operational data">
            <Button loading={isRefreshing} onClick={onRefresh} type="text">
              Refresh
            </Button>
          </Tooltip>
          <Badge count={7} size="small">
            <Button
              className="sg-icon-button"
              type="text"
              icon={<BellOutlined />}
              aria-label="Notifications"
            />
          </Badge>
          <div className="sg-date-block" aria-label="Latest data refresh">
            <CalendarOutlined />
            <span>
              <strong>{headerDate.date}</strong>
              <small>{headerDate.time}</small>
            </span>
          </div>
          <div className="sg-user-menu">
            <Avatar size={34}>AC</Avatar>
            <span>
              <strong>Alex Carter</strong>
              <small>Operations Lead</small>
            </span>
            <DownOutlined />
          </div>
        </div>
      </Header>
      <Content>
        <main className="sg-content">{children}</main>
      </Content>
      <nav className="sg-bottom-dock" aria-label="Primary navigation">
        <Link to="/" className="sg-dock-logo" aria-label="SolarGuard home">
          <span className="sg-mark sg-mark-large" aria-hidden="true">
            <img src={solarGuardLogoIcon} alt="" />
          </span>
        </Link>
        {navItems.map((item) => {
          const target = item.key;
          const active =
            selectedKey === item.key ||
            (item.key === "/diagnostics" && location.pathname.startsWith("/sites/"));
          const badge = item.key === "/service-queue";
          return (
            <Tooltip key={item.key} title={item.label}>
              <Link
                to={target}
                className={`sg-dock-item${active ? " is-active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                {item.icon}
                <span>{item.label}</span>
                {badge ? <i aria-label="Service queue has high-priority items" /> : null}
              </Link>
            </Tooltip>
          );
        })}
      </nav>
    </Layout>
  );
};
