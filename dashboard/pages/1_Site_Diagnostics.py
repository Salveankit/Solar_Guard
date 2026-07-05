from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.data_views import format_bool, format_inr, format_kwh
from dashboard.ui import api_call, metric_row, setup_page, status_chip

client = setup_page("Site Diagnostics")

sites = api_call("Loading sites...", lambda: client.get_json("/api/sites")) or []
if not sites:
    st.warning("No sites are available. Load demo data and run analysis from the API first.")
    st.stop()

priority_sites = sorted(
    sites,
    key=lambda item: (item.get("priority_score") is None, -(item.get("priority_score") or 0)),
)
default_site = next(
    (item["site_id"] for item in priority_sites if item.get("actionable")),
    sites[0]["site_id"],
)
site_id = st.selectbox(
    "Select site",
    [item["site_id"] for item in sites],
    index=[item["site_id"] for item in sites].index(default_site),
)

site = api_call("Loading site metadata...", lambda: client.get_json(f"/api/sites/{site_id}"))
diagnostics = api_call(
    "Loading diagnostics...",
    lambda: client.get_json(f"/api/sites/{site_id}/diagnostics"),
)
if not site or not diagnostics:
    st.stop()

site_meta = diagnostics.get("site", site)
decisions = diagnostics.get("diagnostics", [])
performance = diagnostics.get("performance", [])
primary = decisions[0]["decision"] if decisions else {}

metric_row(
    [
        ("Capacity", f"{site_meta.get('capacity_kw', 0)} kW"),
        ("Region", site_meta.get("service_region", "Unknown")),
        ("Customer", site_meta.get("customer_type", "Unknown")),
        ("Tariff", format_inr(site_meta.get("tariff_per_kwh"))),
        ("Priority", primary.get("priority_label", "Healthy")),
    ]
)
status_chip(f"Status: {'attention' if decisions else 'healthy'}")
if primary:
    status_chip(f"Actionable: {format_bool(primary.get('actionable'))}")
    status_chip(f"Visit required: {format_bool(primary.get('visit_required'))}")

st.subheader("Performance Evidence")
if performance:
    frame = pd.DataFrame(performance)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["expected_generation_kwh"],
            name="Expected generation (kWh)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["actual_generation_kwh"],
            name="Actual generation (kWh)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["ghi_wm2"],
            name="Irradiance (W/m²)",
            yaxis="y2",
            opacity=0.45,
        )
    )
    anomaly_mask = frame["anomaly_state"].astype(str).str.contains(
        "anomaly|missing",
        case=False,
    )
    anomalies = frame[anomaly_mask]
    if not anomalies.empty:
        fig.add_trace(
            go.Scatter(
                x=anomalies["timestamp"],
                y=anomalies["expected_generation_kwh"],
                mode="markers",
                name="Flagged intervals",
                marker={"size": 6, "color": "#b83b32"},
            )
        )
    fig.update_layout(
        yaxis={"title": "Generation (kWh)"},
        yaxis2={"title": "Irradiance (W/m²)", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No interval performance results are available for this site.")

st.subheader("Decision")
if not decisions:
    st.success("No diagnostic issue is currently persisted for this site.")
else:
    decision = primary
    left, right = st.columns([1, 1])
    with left:
        st.markdown(f"**Probable issue:** {decision.get('probable_issue')}")
        st.markdown(
            f"**Confidence:** {decision.get('confidence_label')} "
            f"({decision.get('confidence_score')})"
        )
        st.markdown(f"**Recommended action:** {decision.get('recommended_action')}")
        st.markdown(f"**Escalation condition:** {decision.get('escalation_condition')}")
        st.markdown("**Supporting evidence**")
        for item in decision.get("supporting_evidence") or []:
            st.write(f"- {item}")
        if decision.get("contradictory_evidence"):
            st.markdown("**Contradictory or missing evidence**")
            for item in decision.get("contradictory_evidence") or []:
                st.write(f"- {item}")
    with right:
        metric_row(
            [
                ("Historical loss", format_kwh(decision.get("estimated_energy_loss_kwh"))),
                ("Value at risk", format_inr(decision.get("estimated_value_at_risk_inr"))),
            ]
        )
        metric_row(
            [
                (
                    "Recoverable energy",
                    format_kwh(decision.get("estimated_recoverable_energy_kwh")),
                ),
                ("Recoverable value", format_inr(decision.get("estimated_recoverable_value_inr"))),
            ]
        )
        components = decision.get("priority_components") or {}
        if components:
            st.markdown("**Priority score components**")
            rows = [
                {
                    "component": key.replace("_", " "),
                    "score": value.get("weighted_score", value.get("normalized"))
                    if isinstance(value, dict)
                    else value,
                }
                for key, value in components.items()
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if decision.get("cleaning_decision") not in {None, "not_applicable"}:
            st.markdown("**Cleaning economics**")
            st.write(decision.get("cleaning_reason"))
