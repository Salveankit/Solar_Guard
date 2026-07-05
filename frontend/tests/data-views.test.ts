import { describe, expect, it } from "vitest";

import {
  getWorkBreakdown,
  issueDistribution,
  priorityDistribution,
  topPriorityActions,
  zeroDistanceMessage,
} from "../src/features/command-centre/data";
import {
  fleetSummaryFixture,
  latestRouteFixture,
  serviceQueueFixture,
} from "./fixtures";

describe("Command Centre display helpers", () => {
  it("uses route work lists to separate field, remote and monitoring work", () => {
    expect(getWorkBreakdown(fleetSummaryFixture, latestRouteFixture)).toEqual({
      fieldVisits: 4,
      remoteActions: 1,
      monitoring: 1,
    });
  });

  it("preserves backend queue rank ordering", () => {
    expect(topPriorityActions(serviceQueueFixture.items).map((item) => item.site_id)).toEqual([
      "SITE-TOP",
      "SITE-REMOTE",
      "SITE-GRADUAL",
      "SITE-TIME",
    ]);
  });

  it("builds issue and priority display distributions from backend labels", () => {
    expect(issueDistribution(serviceQueueFixture.items)[0]).toEqual({
      name: "Communication/Data Failure",
      value: 1,
    });
    expect(priorityDistribution(serviceQueueFixture.items)).toEqual([
      { name: "Critical", value: 1 },
      { name: "High", value: 0 },
      { name: "Medium", value: 3 },
      { name: "Low", value: 1 },
    ]);
  });

  it("states that positive route savings come from the current technician plan", () => {
    expect(zeroDistanceMessage(latestRouteFixture)).toContain(
      "current technician plan",
    );
  });
});
