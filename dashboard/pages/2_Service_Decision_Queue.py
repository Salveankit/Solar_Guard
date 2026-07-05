from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.data_views import format_bool, format_inr, split_service_queue
from dashboard.ui import api_call, dataframe, metric_row, setup_page

client = setup_page("Service Decision Queue")

queue = api_call("Loading service decisions...", lambda: client.get_json("/api/service-queue"))
items = (queue or {}).get("items", [])
if not items:
    st.warning("No service decisions are available through the API.")
    st.stop()

priority_values = [
    "All",
    *sorted({str(item.get("priority_label")) for item in items if item.get("priority_label")}),
]
issue_values = [
    "All",
    *sorted({str(item.get("probable_issue")) for item in items if item.get("probable_issue")}),
]
action_values = [
    "All",
    *sorted(
        {str(item.get("recommended_action")) for item in items if item.get("recommended_action")}
    ),
]

filters = st.columns(4)
priority = filters[0].selectbox("Priority", priority_values)
issue = filters[1].selectbox("Probable issue", issue_values)
action = filters[2].selectbox("Action", action_values)
view = filters[3].selectbox("View", ["All", "Field visit", "Remote action", "Monitor/deferred"])

filtered = items
if priority != "All":
    filtered = [item for item in filtered if item.get("priority_label") == priority]
if issue != "All":
    filtered = [item for item in filtered if item.get("probable_issue") == issue]
if action != "All":
    filtered = [item for item in filtered if item.get("recommended_action") == action]

split = split_service_queue(filtered)
if view == "Field visit":
    filtered = split["field"]
elif view == "Remote action":
    filtered = split["remote"]
elif view == "Monitor/deferred":
    filtered = split["monitoring"]
split = split_service_queue(filtered)

metric_row(
    [
        ("Total decisions", len(filtered)),
        ("Field jobs", len(split["field"])),
        ("Remote actions", len(split["remote"])),
        ("Monitor/deferred", len(split["monitoring"])),
        (
            "High/Critical",
            len([i for i in filtered if i.get("priority_label") in {"High", "Critical"}]),
        ),
    ]
)


def display_rows(rows: list[dict], empty: str) -> pd.DataFrame:
    return dataframe(
        [
            {
                "rank": item.get("queue_rank"),
                "site": item.get("site_id"),
                "probable issue": item.get("probable_issue"),
                "confidence": item.get("confidence_score"),
                "priority": f"{item.get('priority_label')} ({item.get('priority_score')})",
                "historical loss": item.get("estimated_energy_loss_kwh"),
                "recoverable value": format_inr(item.get("estimated_recoverable_value_inr")),
                "recommended action": item.get("recommended_action"),
                "remote action": format_bool(item.get("remote_action_available")),
                "visit required": format_bool(item.get("visit_required")),
                "actionable": format_bool(item.get("actionable")),
            }
            for item in sorted(rows, key=lambda row: row.get("queue_rank") or 999)
        ],
        empty_message=empty,
    )


st.subheader("Actionable Queue")
display_rows(
    [*split["field"], *split["remote"]],
    "No actionable field or remote decisions match the current filters.",
)

st.subheader("Monitoring Queue")
display_rows(
    split["monitoring"],
    "No monitoring, deferred or insufficient-evidence rows match the current filters.",
)
