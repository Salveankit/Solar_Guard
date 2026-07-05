from __future__ import annotations

import ast
from pathlib import Path

from dashboard.data_views import (
    DISCLOSURE_TEXT,
    route_stop_site_ids,
    split_service_queue,
    zero_distance_message,
)


def test_queue_segmentation_keeps_field_remote_and_monitoring_separate() -> None:
    rows = [
        {
            "site_id": "MH-107",
            "actionable": True,
            "visit_required": True,
            "remote_action_available": True,
        },
        {
            "site_id": "MH-126",
            "actionable": True,
            "visit_required": False,
            "remote_action_available": True,
        },
        {
            "site_id": "MH-121",
            "actionable": True,
            "visit_required": False,
            "remote_action_available": False,
        },
        {
            "site_id": "MH-115",
            "actionable": False,
            "visit_required": False,
            "remote_action_available": False,
        },
    ]

    split = split_service_queue(rows)

    assert [item["site_id"] for item in split["field"]] == ["MH-107"]
    assert [item["site_id"] for item in split["remote"]] == ["MH-126"]
    assert [item["site_id"] for item in split["monitoring"]] == ["MH-121", "MH-115"]


def test_monitoring_sites_do_not_appear_in_route_stops() -> None:
    route_plan = {
        "field_plan": [
            {"stops": [{"job": {"site_id": "MH-107"}}, {"job": {"site_id": "MH-119"}}]},
            {"stops": [{"job": {"site_id": "MH-105"}}, {"job": {"site_id": "MH-109"}}]},
        ],
        "monitoring_queue": [{"site_id": "MH-121"}, {"site_id": "MH-124"}],
    }

    stops = route_stop_site_ids(route_plan)

    assert "MH-121" not in stops
    assert "MH-124" not in stops
    assert len(stops) == len(set(stops))


def test_zero_distance_avoided_message_is_honest() -> None:
    message = zero_distance_message({"distance_avoided_km": 0})

    assert message is not None
    assert "does not change total Haversine distance" in message


def test_synthetic_data_disclosure_is_present() -> None:
    assert "synthetic but operationally realistic" in DISCLOSURE_TEXT
    assert "not production-validated fault accuracy" in DISCLOSURE_TEXT


def test_dashboard_pages_do_not_import_database_or_repositories() -> None:
    def is_blocked_import(module_name: str) -> bool:
        return any(
            module_name == item or module_name.startswith(f"{item}.")
            for item in blocked
        )

    dashboard_files = [
        Path("dashboard/Home.py"),
        *Path("dashboard/pages").glob("*.py"),
    ]
    blocked = {"app.database", "app.repositories"}
    violations = []
    for path in dashboard_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if is_blocked_import(node.module):
                    violations.append((path, node.module))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if is_blocked_import(alias.name):
                        violations.append((path, alias.name))

    assert violations == []
