from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

from dashboard.data_views import (
    format_inr,
    format_kwh,
    route_stop_site_ids,
    tomorrow_iso,
    zero_distance_message,
)
from dashboard.ui import api_call, api_call_optional, dataframe, metric_row, setup_page

client = setup_page("Technician Plan")

route_plan = api_call_optional(
    "Loading latest route plan...",
    lambda: client.get_json("/api/routes/latest"),
)
if not route_plan:
    st.info("No route plan is available yet.")
    if st.button("Generate Tomorrow's O&M Plan", type="primary"):
        result = api_call(
            "Generating route plan...",
            lambda: client.post_json(
                "/api/routes/optimize",
                {"planning_date": tomorrow_iso(), "replace_existing_plan": False},
            ),
        )
        if result:
            st.success(f"Route plan {result.get('route_plan_id')} is ready.")
            route_plan = result
    if not route_plan:
        st.stop()

route_stop_count = len(route_stop_site_ids(route_plan))
unassigned_count = len(route_plan.get("unassigned_jobs", []))
metric_row(
    [
        ("Plan date", route_plan.get("planning_date")),
        ("Status", route_plan.get("optimisation_status")),
        ("Eligible jobs", route_plan.get("total_eligible_jobs", route_stop_count)),
        ("Assigned", route_plan.get("assigned_jobs", route_stop_count)),
        ("Unassigned", route_plan.get("unassigned_jobs_count", unassigned_count)),
        ("Distance", f"{route_plan.get('optimised_distance_km', 0)} km"),
    ]
)
metric_row(
    [
        ("Naive distance", f"{route_plan.get('naive_distance_km', 0)} km"),
        ("Distance avoided", f"{route_plan.get('distance_avoided_km', 0)} km"),
        ("Travel duration", f"{route_plan.get('total_travel_duration_min', 0)} min"),
        ("Job duration", f"{route_plan.get('total_job_duration_min', 0)} min"),
        ("Recoverable energy", format_kwh(route_plan.get("total_recoverable_energy_kwh"))),
        ("Recoverable value", format_inr(route_plan.get("total_recoverable_value_inr"))),
    ]
)
if message := zero_distance_message(route_plan):
    st.info(message)

st.subheader("Field Routes")
for route in route_plan.get("field_plan", []):
    name = route.get("technician_name") or route.get("technician_id")
    st.markdown(f"### {name}")
    st.caption(
        f"{route.get('technician_id')} · skills: {', '.join(route.get('skills', []))} · "
        f"shift {route.get('shift_start', '09:00:00')} to {route.get('shift_end', '18:00:00')}"
    )
    metric_row(
        [
            ("Route distance", f"{route.get('distance_km', 0)} km"),
            ("Travel", f"{route.get('travel_duration_min', 0)} min"),
            ("Job time", f"{route.get('job_duration_min', 0)} min"),
        ]
    )
    dataframe(
        [
            {
                "sequence": stop.get("sequence"),
                "site": stop.get("job", {}).get("site_id"),
                "probable issue": stop.get("job", {}).get("probable_issue"),
                "recommended action": stop.get("job", {}).get("recommended_action"),
                "priority": stop.get("job", {}).get("priority_label"),
                "arrival": stop.get("arrival"),
                "departure": stop.get("departure"),
                "travel km": stop.get("travel_distance_km"),
                "travel min": stop.get("travel_duration_min"),
                "job min": stop.get("job", {}).get("duration_min"),
            }
            for stop in route.get("stops", [])
        ],
        empty_message="This technician has no assigned field stops.",
    )

st.subheader("Route Map")
stops = [
    (route, stop, stop.get("job", {}))
    for route in route_plan.get("field_plan", [])
    for stop in route.get("stops", [])
]
if stops:
    first_job = stops[0][2]
    fmap = folium.Map(
        location=[first_job.get("latitude", 18.52), first_job.get("longitude", 73.85)],
        zoom_start=11,
        control_scale=True,
    )
    colors = ["blue", "green", "red", "purple"]
    for route_index, (route, stop, job) in enumerate(stops):
        color = colors[route_index % len(colors)]
        folium.Marker(
            [job.get("latitude"), job.get("longitude")],
            popup=f"{route.get('technician_id')} stop {stop.get('sequence')}: {job.get('site_id')}",
            tooltip=f"{stop.get('sequence')} · {job.get('site_id')}",
            icon=folium.Icon(color=color, icon="wrench", prefix="fa"),
        ).add_to(fmap)
    st_folium(fmap, use_container_width=True, height=420)
else:
    st.info("No field stops are available to map.")

st.subheader("Remote Action Queue")
dataframe(
    route_plan.get("remote_action_queue", []),
    empty_message="No remote action items are present.",
)

st.subheader("Deferred or Monitoring Queue")
dataframe(
    route_plan.get("monitoring_queue", []),
    empty_message="No monitoring or deferred items are present.",
)

if route_plan.get("unassigned_jobs"):
    st.subheader("Unassigned Field Jobs")
    dataframe(route_plan["unassigned_jobs"], empty_message="No unassigned jobs.")

st.subheader("Daily O&M Plan Export")
report = api_call_optional(
    "Preparing report download...",
    lambda: client.get_bytes(
        "/api/reports/daily-plan",
        {"route_plan_id": route_plan.get("route_plan_id"), "format": "csv"},
    ),
)
if report:
    st.download_button(
        "Download Daily O&M Plan",
        data=report,
        file_name=f"solarguard_daily_plan_{route_plan.get('planning_date')}.csv",
        mime="text/csv",
        type="primary",
    )
else:
    st.info("Daily O&M report is unavailable until a route plan exists.")

st.caption("Remote and monitoring queues are not shown as technician map stops.")
