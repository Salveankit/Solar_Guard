from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data_views import format_inr, format_kwh, tomorrow_iso
from dashboard.ui import api_call, api_call_optional, dataframe, metric_row, setup_page

client = setup_page("Daily Operations Command Centre")

health = api_call("Checking API health...", lambda: client.get_json("/health"))
summary = api_call("Loading fleet summary...", lambda: client.get_json("/api/fleet/summary"))
queue = api_call("Loading service queue...", lambda: client.get_json("/api/service-queue"))
route_plan = api_call_optional(
    "Checking latest route plan...",
    lambda: client.get_json("/api/routes/latest"),
)

if health:
    st.caption(
        f"API {health.get('api_version')} · database {health.get('database')} · "
        f"configuration {health.get('configuration_version')}"
    )

if not summary:
    st.warning("No completed analysis is available through the API.")
else:
    metric_row(
        [
            ("Monitored sites", summary.get("monitored_sites", 0)),
            ("Healthy", summary.get("healthy_sites", 0)),
            ("Require attention", summary.get("attention_sites", 0)),
            ("Remote actions", summary.get("remote_actions", 0)),
            ("Field visits", summary.get("field_visits", 0)),
            ("Value at risk", format_inr(summary.get("estimated_energy_value_at_risk_inr"))),
        ]
    )
    st.subheader("Fleet Attention")
    left, right = st.columns([1.1, 1])
    attention_rows = [
        {"state": "Healthy", "count": summary.get("healthy_sites", 0)},
        {"state": "Communication", "count": summary.get("communication_issues", 0)},
        {"state": "Underperformance/attention", "count": summary.get("attention_sites", 0)},
        {"state": "Insufficient evidence", "count": summary.get("insufficient_evidence", 0)},
    ]
    with left:
        st.plotly_chart(
            px.bar(
                pd.DataFrame(attention_rows),
                x="state",
                y="count",
                color="state",
                labels={"count": "Sites", "state": "Operational state"},
            ),
            use_container_width=True,
        )
    with right:
        st.write("Operational totals")
        metric_row(
            [
                ("Recoverable energy", format_kwh(summary.get("estimated_recoverable_energy_kwh"))),
                ("Recoverable value", format_inr(summary.get("estimated_recoverable_value_inr"))),
            ]
        )
        top_site = summary.get("top_priority_site_id") or "None"
        st.info(f"Highest-priority site: {top_site}")

    st.subheader("Highest-Priority Decisions")
    items = (queue or {}).get("items", [])
    top_items = sorted(
        [item for item in items if item.get("actionable")],
        key=lambda item: item.get("queue_rank") or 999,
    )[:8]
    dataframe(
        [
            {
                "rank": item.get("queue_rank"),
                "site": item.get("site_id"),
                "probable issue": item.get("probable_issue"),
                "priority": item.get("priority_label"),
                "value at risk": format_inr(item.get("estimated_value_at_risk_inr")),
                "recommended action": item.get("recommended_action"),
            }
            for item in top_items
        ],
        empty_message="No actionable service decisions are currently available.",
    )

    st.subheader("Expected vs Actual Fleet Trend")
    timeseries = api_call(
        "Loading fleet trend...",
        lambda: client.get_json("/api/fleet/timeseries"),
    )
    trend_rows = (timeseries or {}).get("items", [])
    if trend_rows:
        trend = pd.DataFrame(trend_rows)
        st.plotly_chart(
            px.line(
                trend,
                x="timestamp",
                y=["expected_generation_kwh", "actual_generation_kwh"],
                labels={"value": "Generation (kWh)", "timestamp": "Time"},
            ),
            use_container_width=True,
        )
    else:
        st.info("Fleet trend is unavailable until expected-generation results are persisted.")

    st.subheader("Tomorrow's O&M Plan")
    regenerate = st.checkbox("Regenerate existing route plan", value=False)
    if route_plan and not regenerate:
        st.success(
            "A route plan is already available. Open Technician Plan to review it, "
            "or tick regeneration before running this action."
        )
    if st.button("Generate Tomorrow's O&M Plan", type="primary"):
        if route_plan and not regenerate:
            st.info("Using the existing route plan; no route optimisation was rerun.")
        else:
            result = api_call(
                "Generating route plan...",
                lambda: client.post_json(
                    "/api/routes/optimize",
                    {
                        "planning_date": tomorrow_iso(),
                        "analysis_run_id": summary.get("analysis_run_id"),
                        "replace_existing_plan": regenerate,
                    },
                ),
            )
            if result:
                st.success(
                    f"Route plan {result.get('route_plan_id')} is ready with "
                    f"{result.get('optimisation_status')} status."
                )
