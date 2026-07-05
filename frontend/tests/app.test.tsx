import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/app/App";
import { AppProviders } from "../src/app/providers";
import {
  fleetSummaryFixture,
  fleetTimeseriesFixture,
  latestRouteFixture,
  serviceQueueFixture,
  siteDiagnosticsFixture,
  sitesFixture,
} from "./fixtures";

vi.mock("../src/api/fleet", () => ({
  fetchFleetSummary: vi.fn(() => Promise.resolve(fleetSummaryFixture)),
  fetchFleetTimeseries: vi.fn(() => Promise.resolve(fleetTimeseriesFixture)),
}));

vi.mock("../src/api/health", () => ({
  fetchHealthStatus: vi.fn(() =>
    Promise.resolve({
      status: "ok",
      api_version: "1.0.0",
      database: "ready",
      model: "not_loaded",
      configuration_version: "poc-v1",
    })),
}));

vi.mock("../src/api/decisions", () => ({
  fetchServiceQueue: vi.fn(() => Promise.resolve(serviceQueueFixture)),
}));

vi.mock("../src/api/routes", () => ({
  fetchLatestRoutePlan: vi.fn(() => Promise.resolve(latestRouteFixture)),
  downloadDailyPlan: vi.fn(() => {
    const csv =
      "work_category,technician,site_id,probable_issue,priority,recommended_action\r\n" +
      'field_visit,Rohit S.,SITE-TOP,"probable inverter, grid-side interruption",High,urgent field visit\r\n' +
      "remote_action,,SITE-REMOTE,communication failure,Medium,remote connectivity check\r\n";
    return Promise.resolve({
      blob: { text: () => Promise.resolve(csv) } as Blob,
      filename: "Daily_O&M_Plan_2026-07-05.csv",
    });
  }),
}));

vi.mock("../src/api/sites", () => ({
  fetchSites: vi.fn(() => Promise.resolve(sitesFixture)),
  fetchSiteDiagnostics: vi.fn(() => Promise.resolve(siteDiagnosticsFixture)),
}));

const renderApp = () =>
  render(
    <AppProviders>
      <App />
    </AppProviders>,
  );

const integrationTimeoutMs = 30000;

describe("SolarGuard React application", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:solarguard-plan"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(HTMLAnchorElement.prototype, "click", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders the enterprise shell and highlights the active command route", async () => {
    renderApp();

    expect(await screen.findByText("SOLARGUARD")).toBeInTheDocument();
    expect(screen.queryByText(/Demonstration environment/i)).not.toBeInTheDocument();
    expect(screen.getByText("Alex Carter")).toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    const commandCentre = within(dock).getByRole("link", {
      name: /command centre/i,
    });
    expect(commandCentre).toHaveClass("is-active");
  });

  it("renders the Fleet Sites page from backend site data", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /fleet sites/i }));

    expect(
      await screen.findByRole("heading", { name: /monitor every site with clarity/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("SITE INVENTORY")).toBeInTheDocument();
    expect(screen.getAllByText("Greenfield Farm").length).toBeGreaterThan(0);
    expect(screen.getByText("Avg. Data Completeness")).toBeInTheDocument();
    expect(screen.queryByText(/999 kWh/i)).not.toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /fleet sites/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("filters Fleet Sites through the map cluster and keeps missing telemetry explicit", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /fleet sites/i }));
    fireEvent.click(
      await screen.findByRole("button", {
        name: /filter communication loss sites/i,
      }),
    );

    await waitFor(() => {
      expect(screen.getAllByText("Mountain Retreat").length).toBeGreaterThan(0);
    });
    expect(screen.queryByText("Greenfield Farm")).not.toBeInTheDocument();
    expect(screen.getAllByText(/not exposed by api/i).length).toBeGreaterThan(0);
    expect(window.location.search).toContain("status=communication");
  }, integrationTimeoutMs);

  it("opens diagnostics from the selected Fleet Sites snapshot", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /fleet sites/i }));
    await screen.findAllByText("Greenfield Farm");
    await user.click(screen.getByRole("button", { name: /view diagnostics/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/sites/SITE-TOP");
    });
  }, integrationTimeoutMs);

  it("renders Diagnostics with backend evidence and active dock state", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /diagnostics/i }));

    expect(
      await screen.findByRole("heading", {
        name: /understand site issues with confidence/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("EXPECTED VS ACTUAL GENERATION")).toBeInTheDocument();
    expect(screen.getAllByText(/Probable Inverter Or Grid-Side Interruption/i).length).toBeGreaterThan(0);
    expect(screen.getByText("DIAGNOSTIC SUMMARY")).toBeInTheDocument();
    expect(screen.getByText("RECOMMENDED NEXT ACTIONS")).toBeInTheDocument();
    expect(screen.queryByText("SERVICE DECISION SNAPSHOT")).not.toBeInTheDocument();
    expect(screen.queryByText(/Diagnostics display backend evidence/i)).not.toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /diagnostics/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("keeps site diagnostic URLs under the Diagnostics dock item", async () => {
    window.history.pushState({}, "", "/sites/SITE-TOP");
    renderApp();

    expect(await screen.findByText("Greenfield Farm")).toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /diagnostics/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("renders Incidents as an operational triage workspace", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /incidents/i }));

    expect(
      await screen.findByRole("heading", {
        name: /triage operational incidents with precision/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("INCIDENT QUEUE")).toBeInTheDocument();
    expect(screen.getByText("INCIDENT DISTRIBUTION")).toBeInTheDocument();
    expect(screen.getByText("SELECTED INCIDENT")).toBeInTheDocument();
    expect(screen.getByText("RECOMMENDED NEXT ACTIONS")).toBeInTheDocument();
    expect(screen.getAllByText("Greenfield Farm").length).toBeGreaterThan(0);
    expect(screen.getByText(/Unknown \/ Insufficient Evidence/i)).toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /incidents/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("filters Incidents by remote candidates and opens selected diagnostics", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /incidents/i }));
    const remoteControls = await screen.findAllByRole("button", { name: /remote check/i });
    await user.click(remoteControls[0]);

    await waitFor(() => {
      expect(window.location.search).toContain("action=remote");
    });
    expect(screen.getAllByText("Mountain Retreat").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /open diagnostics/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/sites/SITE-GRADUAL");
    });
  }, integrationTimeoutMs);

  it("confirms Incidents service-queue routing without a dead action", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /incidents/i }));
    await screen.findByText("INCIDENT QUEUE");
    await user.click(screen.getByRole("button", { name: /move to service queue/i }));

    expect(await screen.findByText("Move incident to service queue")).toBeInTheDocument();
    expect(screen.getByText(/backend recommendation/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /confirm routing/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Incident routed for service-queue review.",
    );
  }, integrationTimeoutMs);

  it("renders Service Queue as a ranked operational workspace", async () => {
    const user = userEvent.setup();
    renderApp();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    await user.click(within(dock).getByRole("link", { name: /service queue/i }));

    expect(
      await screen.findByRole("heading", {
        name: /prioritize service work with clarity/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("SERVICE DECISION QUEUE")).toBeInTheDocument();
    expect(screen.getByText("QUEUE DISTRIBUTION")).toBeInTheDocument();
    expect(screen.getByText("SELECTED DECISION")).toBeInTheDocument();
    expect(screen.getByText("PRIORITY BREAKDOWN")).toBeInTheDocument();
    expect(screen.getAllByText("Greenfield Farm").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Not exposed/i).length).toBeGreaterThan(0);

    expect(within(dock).getByRole("link", { name: /service queue/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("filters Service Queue and opens selected diagnostics", async () => {
    const user = userEvent.setup();
    renderApp();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    await user.click(within(dock).getByRole("link", { name: /service queue/i }));
    const serviceQueueRemoteControls = await screen.findAllByRole("button", {
      name: /remote check/i,
    });
    await user.click(serviceQueueRemoteControls[0]);

    await waitFor(() => {
      expect(window.location.search).toContain("filter=remote");
    });
    expect(screen.getAllByText("Mountain Retreat").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /open diagnostics/i }));
    await waitFor(() => {
      expect(window.location.pathname).toBe("/sites/SITE-REMOTE");
    });
  }, integrationTimeoutMs);

  it("reviews a Service Queue plan move without claiming persistence", async () => {
    const user = userEvent.setup();
    renderApp();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    await user.click(within(dock).getByRole("link", { name: /service queue/i }));
    await screen.findByText("SERVICE DECISION QUEUE");
    await user.click(screen.getByRole("button", { name: /move to technician plan/i }));

    expect(await screen.findByText("Review before Technician Plan")).toBeInTheDocument();
    expect(screen.getByText(/no move-to-plan mutation/i)).toBeInTheDocument();
    expect(screen.getByText(/No assignment has been created/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /close review/i }));
    expect(screen.queryByRole("dialog", { name: /review before technician plan/i })).not.toBeInTheDocument();
  }, integrationTimeoutMs);

  it("renders the Technician Plan from backend route assignments", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /technician plan/i }));

    expect(
      await screen.findByRole("heading", {
        name: /coordinate field execution/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("TECHNICIAN ASSIGNMENTS")).toBeInTheDocument();
    expect(screen.getByText("ROUTE MAP")).toBeInTheDocument();
    expect(screen.getByText("SELECTED TECHNICIAN")).toBeInTheDocument();
    expect(screen.getByText("PLAN IMPACT")).toBeInTheDocument();
    expect(screen.getAllByText("Rohit S.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Neha P.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("312 kWh").length).toBeGreaterThan(0);

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /technician plan/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("synchronizes technician selection and downloads the backend plan", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /technician plan/i }));
    await screen.findByText("TECHNICIAN ASSIGNMENTS");
    const nehaCells = screen.getAllByText("Neha P.");
    await user.click(nehaCells[0]);

    await waitFor(() => {
      expect(window.location.search).toContain("technician=TECH-02");
    });
    expect(screen.getAllByText("Lakeside Office").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: /download daily o&m plan.csv/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Daily O&M plan downloaded.",
    );
  }, integrationTimeoutMs);

  it("renders the honest Reports workspace from the backend CSV", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /reports/i }));

    expect(
      await screen.findByRole("heading", { name: /operational reports/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("REPORT LIBRARY")).toBeInTheDocument();
    expect(screen.getByText("REPORT DISTRIBUTION")).toBeInTheDocument();
    expect(screen.getByText("SELECTED REPORT")).toBeInTheDocument();
    expect(screen.getByText("DOWNLOAD & EXPORT")).toBeInTheDocument();
    expect(screen.getAllByText("Daily O&M Plan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("CSV").length).toBeGreaterThan(0);
    expect(screen.queryByText("PDF")).not.toBeInTheDocument();
    expect(screen.queryByText(/scheduled reports/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/share via email/i)).not.toBeInTheDocument();

    const dock = screen.getByRole("navigation", { name: /primary navigation/i });
    expect(within(dock).getByRole("link", { name: /reports/i })).toHaveClass(
      "is-active",
    );
  }, integrationTimeoutMs);

  it("previews and downloads the cached Daily O&M Plan CSV", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /reports/i }));
    await screen.findByText("REPORT LIBRARY");
    await user.click(screen.getByRole("button", { name: /preview full report/i }));

    expect(await screen.findByText("Daily O&M Plan preview")).toBeInTheDocument();
    expect(screen.getAllByText(/operationally realistic synthetic data/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/work category/i).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /close preview/i }));

    await user.click(screen.getByRole("button", { name: /download daily o&m plan.csv/i }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Daily O&M Plan CSV downloaded.",
    );
  }, integrationTimeoutMs);

  it("persists Reports category filters in the URL", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /reports/i }));
    await user.click(await screen.findByRole("button", { name: /daily ops/i }));

    await waitFor(() => {
      expect(window.location.search).toContain("category=daily-ops");
    });
    expect(screen.getAllByText("Daily O&M Plan").length).toBeGreaterThan(0);
  }, integrationTimeoutMs);

  it("shows Command Centre KPIs with units and preserves backend queue rank", async () => {
    renderApp();

    expect(await screen.findByText("Sites Requiring Attention")).toBeInTheDocument();
    expect(screen.getAllByText("Energy Value at Risk").length).toBeGreaterThan(0);
    expect(screen.getByText("₹1,930")).toBeInTheDocument();
    expect(screen.getByText("70.2 kWh")).toBeInTheDocument();
    expect(screen.getByText(/₹562 recoverable value/i)).toBeInTheDocument();
    expect(screen.getAllByText("SITE-TOP").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Urgent Field Visit").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /open SITE-TOP/i })).toBeInTheDocument();
  });

  it("opens an enlarged chart view for command-centre presentation", async () => {
    const user = userEvent.setup();
    renderApp();

    await screen.findByText("EXPECTED VS ACTUAL GENERATION");
    await user.click(
      screen.getByRole("button", { name: /expand expected vs actual generation/i }),
    );

    expect(
      await screen.findByText("Expected vs Actual Generation"),
    ).toBeInTheDocument();
  });

  it("keeps remote actions and monitoring states separate", async () => {
    renderApp();

    expect(await screen.findByText("Remote Resolution Candidates")).toBeInTheDocument();
    expect(screen.getByText(/unknown or insufficient evidence/i)).toBeInTheDocument();
    expect(screen.getAllByText(/urgent field visit/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/remote connectivity check/i)).toBeInTheDocument();
    expect(screen.getByText(/unknown or insufficient evidence/i)).toBeInTheDocument();
  });

  it("uses contextual site navigation for the priority table", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByRole("button", { name: /open SITE-TOP/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/sites/SITE-TOP");
    });
  });

  it("displays route distance avoided in operator-facing language", async () => {
    renderApp();

    expect(
      await screen.findByText(/calculated from the current technician plan/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("21 km").length).toBeGreaterThan(0);
  });
});
