from __future__ import annotations

from sqlalchemy.engine import Connection

from app.repositories import ServiceDecisionRepository


class OperationsQueryService:
    def __init__(self, connection: Connection) -> None:
        self.repository = ServiceDecisionRepository(connection)

    def fleet_summary(self) -> dict:
        run_id, decisions = self._latest()
        sites = self.repository.read_sites()
        actionable = [item for item in decisions if item["actionable"]]
        field = [item for item in actionable if item["visit_required"]]
        remote = [
            item
            for item in actionable
            if item["remote_action_available"] and not item["visit_required"]
        ]
        insufficient = [
            item
            for item in decisions
            if item["probable_issue"] == "unknown or insufficient evidence"
        ]
        communication = [
            item
            for item in decisions
            if item["probable_issue"] == "communication or data-logger failure"
        ]
        affected_sites = {item["site_id"] for item in decisions}
        return {
            "analysis_run_id": run_id,
            "monitored_sites": len(sites),
            "healthy_sites": len(sites) - len(affected_sites),
            "attention_sites": len(affected_sites),
            "communication_issues": len(communication),
            "insufficient_evidence": len(insufficient),
            "remote_actions": len(remote),
            "field_visits": len(field),
            "estimated_energy_value_at_risk_inr": round(
                sum(item["estimated_value_at_risk_inr"] for item in decisions), 2
            ),
            "estimated_recoverable_energy_kwh": round(
                sum(item["estimated_recoverable_energy_kwh"] for item in actionable), 3
            ),
            "estimated_recoverable_value_inr": round(
                sum(item["estimated_recoverable_value_inr"] for item in actionable), 2
            ),
            "top_priority_site_id": actionable[0]["site_id"] if actionable else None,
        }

    def fleet_timeseries(self) -> dict:
        run_id, _decisions = self._latest()
        if not run_id:
            return {"analysis_run_id": "", "items": []}
        return {
            "analysis_run_id": run_id,
            "items": self.repository.read_fleet_timeseries(run_id),
        }

    def sites(self) -> list[dict]:
        run_id, decisions = self._latest()
        by_site = {item["site_id"]: item for item in decisions}
        rows = []
        for site in self.repository.read_sites().to_dict(orient="records"):
            decision = by_site.get(site["site_id"])
            rows.append(
                {
                    **site,
                    "analysis_run_id": run_id,
                    "status": "attention" if decision else "healthy",
                    "probable_issue": decision["probable_issue"] if decision else None,
                    "priority_label": decision["priority_label"] if decision else None,
                    "priority_score": decision["priority_score"] if decision else None,
                    "actionable": bool(decision["actionable"]) if decision else False,
                }
            )
        return rows

    def site(self, site_id: str) -> dict | None:
        site = self.repository.read_site(site_id)
        if site is None:
            return None
        _run_id, decisions = self._latest()
        site["decisions"] = [item for item in decisions if item["site_id"] == site_id]
        return site

    def diagnostics(self, site_id: str) -> dict | None:
        site = self.repository.read_site(site_id)
        if site is None:
            return None
        run_id, decisions = self._latest()
        site_decisions = [item for item in decisions if item["site_id"] == site_id]
        diagnostics = []
        for decision in site_decisions:
            candidate = self.repository.read_site_candidate(
                run_id, decision["incident_candidate_id"]
            )
            diagnostics.append({"decision": decision, "candidate": candidate})
        return {
            "analysis_run_id": run_id,
            "site": site,
            "diagnostics": diagnostics,
            "performance": self.repository.read_site_performance(run_id, site_id),
        }

    def service_queue(
        self,
        priority: str | None = None,
        probable_issue: str | None = None,
        remote_action: bool | None = None,
        cleaning_candidate: bool | None = None,
        field_visit: bool | None = None,
        insufficient_evidence: bool | None = None,
        actionable_only: bool = False,
    ) -> dict:
        run_id, decisions = self._latest()
        rows = decisions
        if priority:
            rows = [item for item in rows if item["priority_label"].lower() == priority.lower()]
        if probable_issue:
            rows = [
                item
                for item in rows
                if probable_issue.lower() in item["probable_issue"].lower()
            ]
        if remote_action is not None:
            rows = [item for item in rows if bool(item["remote_action_available"]) == remote_action]
        if cleaning_candidate is not None:
            rows = [
                item
                for item in rows
                if (item["cleaning_decision"] == "schedule") == cleaning_candidate
            ]
        if field_visit is not None:
            rows = [item for item in rows if bool(item["visit_required"]) == field_visit]
        if insufficient_evidence is not None:
            rows = [
                item
                for item in rows
                if (item["probable_issue"] == "unknown or insufficient evidence")
                == insufficient_evidence
            ]
        if actionable_only:
            rows = [item for item in rows if item["actionable"]]
        return {"analysis_run_id": run_id, "count": len(rows), "items": rows}

    def _latest(self) -> tuple[str, list[dict]]:
        run_id = self.repository.latest_decision_run_id()
        if run_id is None:
            return "", []
        return run_id, self.repository.read_decisions(run_id)
