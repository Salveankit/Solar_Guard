from __future__ import annotations

import hashlib

import pandas as pd


class AnomalyDetectionService:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.analysis_config = config.get("analysis", {})

    def classify_intervals(self, frame: pd.DataFrame) -> pd.DataFrame:
        classified = frame.copy()
        under = float(self.analysis_config.get("underperformance_ratio", 0.70))
        severe = float(self.analysis_config.get("severe_underperformance_ratio", 0.35))
        near_zero = float(self.analysis_config.get("near_zero_ratio", 0.05))
        classified.loc[~classified["anomaly_eligible"], "anomaly_state"] = "ineligible"
        classified.loc[classified["anomaly_eligible"], "anomaly_state"] = "normal"
        classified.loc[
            classified["anomaly_eligible"] & (classified["performance_ratio"] < under),
            "anomaly_state",
        ] = "underperformance"
        classified.loc[
            classified["anomaly_eligible"] & (classified["performance_ratio"] < severe),
            "anomaly_state",
        ] = "severe underperformance"
        classified.loc[
            classified["anomaly_eligible"] & (classified["performance_ratio"] <= near_zero),
            "anomaly_state",
        ] = "near-zero output"
        classified.loc[
            classified["data_quality_status"].eq("MISSING"),
            "anomaly_state",
        ] = "communication missing"
        return classified

    def incident_candidates(
        self,
        analysis_run_id: str,
        interval_frame: pd.DataFrame,
        telemetry_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        if "anomaly_state" not in interval_frame.columns and not interval_frame.empty:
            interval_frame = self.classify_intervals(interval_frame)
        insufficient_sites = self._insufficient_evidence_sites(interval_frame, telemetry_frame)
        raw_candidates = [
            *self._performance_candidates(analysis_run_id, interval_frame),
            *self._communication_candidates(analysis_run_id, telemetry_frame),
            *self._time_window_candidates(analysis_run_id, interval_frame),
            *self._insufficient_evidence_candidates(
                analysis_run_id,
                interval_frame,
                telemetry_frame,
            ),
        ]
        if not raw_candidates:
            return self._empty_incidents()
        raw = pd.DataFrame(raw_candidates).drop_duplicates(
            subset=["analysis_run_id", "site_id", "start_timestamp", "provisional_category"]
        )
        if insufficient_sites:
            performance_categories = [
                "persistent underperformance",
                "morning time-window candidate",
                "afternoon time-window candidate",
                "recurring time-specific candidate",
            ]
            suppress = raw["site_id"].isin(insufficient_sites) & raw[
                "provisional_category"
            ].isin(performance_categories)
            raw = raw.loc[~suppress].copy()
        communication_sites = set(
            raw.loc[raw["provisional_category"].eq("communication failure"), "site_id"]
        )
        if communication_sites:
            redundant_insufficient = raw["site_id"].isin(communication_sites) & raw[
                "provisional_category"
            ].eq("insufficient evidence")
            raw = raw.loc[~redundant_insufficient].copy()
        consolidated = self._consolidate_candidates(
            analysis_run_id,
            raw,
            interval_frame,
            telemetry_frame,
        )
        if consolidated.empty:
            return raw.reset_index(drop=True)
        return pd.concat([raw, consolidated], ignore_index=True)

    def _performance_candidates(self, analysis_run_id: str, frame: pd.DataFrame) -> list[dict]:
        abnormal = frame[
            frame["anomaly_state"].isin(
                ["underperformance", "severe underperformance", "near-zero output"]
            )
        ].copy()
        if abnormal.empty:
            return []
        persistence = int(self.analysis_config.get("persistence_intervals", 4))
        max_gap = int(self.analysis_config.get("maximum_grouping_gap_intervals", 1))
        candidates = []
        for site_id, group in abnormal.groupby("site_id", sort=False):
            group = group.sort_values("timestamp")
            current = []
            previous = None
            for row in group.itertuples(index=False):
                if previous is not None:
                    gap = int((row.timestamp - previous).total_seconds() / 900) - 1
                    if gap > max_gap:
                        self._append_group(
                            analysis_run_id,
                            candidates,
                            site_id,
                            current,
                            persistence,
                        )
                        current = []
                current.append(row)
                previous = row.timestamp
            self._append_group(analysis_run_id, candidates, site_id, current, persistence)
        return candidates

    def _append_group(
        self,
        analysis_run_id: str,
        candidates: list[dict],
        site_id: str,
        rows: list,
        persistence: int,
    ) -> None:
        if len(rows) < persistence:
            return
        group = pd.DataFrame([row._asdict() for row in rows])
        state = self._dominant_state(group)
        category = (
            "sudden severe underperformance"
            if state in {"near-zero output", "severe underperformance"}
            else "persistent underperformance"
        )
        candidates.append(
            self._candidate_row(
                analysis_run_id=analysis_run_id,
                site_id=site_id,
                start=group["timestamp"].min(),
                end=group["timestamp"].max(),
                group=group,
                anomaly_state=state,
                provisional_category=category,
                evidence={
                    "state": state,
                    "minimum_performance_ratio": _safe_float(group["performance_ratio"].min()),
                    "interval_count": len(group),
                },
                recommendation=None,
            )
        )

    def _communication_candidates(
        self,
        analysis_run_id: str,
        telemetry: pd.DataFrame,
    ) -> list[dict]:
        if telemetry.empty:
            return []
        missing_required = int(self.analysis_config.get("communication_missing_intervals", 4))
        candidates = []
        telemetry = telemetry.copy()
        telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"], errors="coerce")
        missing = telemetry[
            (~telemetry["data_received"].astype(bool))
            & telemetry["generation_kwh"].isna()
            & telemetry["ac_power_kw"].isna()
        ].sort_values(["site_id", "timestamp"])
        for site_id, group in missing.groupby("site_id", sort=False):
            current = []
            previous = None
            for row in group.itertuples(index=False):
                if previous is not None and (row.timestamp - previous).total_seconds() > 900:
                    self._append_communication_group(
                        analysis_run_id,
                        candidates,
                        site_id,
                        current,
                        missing_required,
                    )
                    current = []
                current.append(row)
                previous = row.timestamp
            self._append_communication_group(
                analysis_run_id,
                candidates,
                site_id,
                current,
                missing_required,
            )
        return candidates

    def _append_communication_group(
        self,
        analysis_run_id: str,
        candidates: list[dict],
        site_id: str,
        rows: list,
        missing_required: int,
    ) -> None:
        if len(rows) < missing_required:
            return
        group = pd.DataFrame([row._asdict() for row in rows])
        candidates.append(
            self._candidate_row(
                analysis_run_id=analysis_run_id,
                site_id=site_id,
                start=group["timestamp"].min(),
                end=group["timestamp"].max(),
                group=pd.DataFrame(
                    {
                        "expected_generation_kwh": [0.0] * len(group),
                        "actual_generation_kwh": [None] * len(group),
                        "energy_loss_kwh": [0.0] * len(group),
                        "performance_ratio": [None] * len(group),
                    }
                ),
                anomaly_state="communication missing",
                provisional_category="communication failure",
                evidence={"missing_interval_count": len(group)},
                recommendation="remote connectivity check",
            )
        )

    def _time_window_candidates(self, analysis_run_id: str, frame: pd.DataFrame) -> list[dict]:
        abnormal = frame[
            frame["anomaly_state"].isin(["underperformance", "severe underperformance"])
        ].copy()
        if abnormal.empty:
            return []
        local_time = pd.to_datetime(abnormal["timestamp"]).dt.tz_convert("Asia/Kolkata")
        abnormal["hour"] = local_time.dt.hour
        abnormal["date"] = local_time.dt.date
        candidates = []
        for site_id, site_group in abnormal.groupby("site_id", sort=False):
            for label, hours in {
                "morning time-window candidate": range(8, 12),
                "afternoon time-window candidate": range(14, 18),
            }.items():
                window = site_group[site_group["hour"].isin(hours)]
                if window["date"].nunique() < 3 or len(window) < int(
                    self.analysis_config.get("persistence_intervals", 4)
                ):
                    continue
                candidates.append(
                    self._candidate_row(
                        analysis_run_id=analysis_run_id,
                        site_id=site_id,
                        start=window["timestamp"].min(),
                        end=window["timestamp"].max(),
                        group=window,
                        anomaly_state="underperformance",
                        provisional_category=label,
                        evidence={
                            "recurring_days": int(window["date"].nunique()),
                            "hours": sorted(int(hour) for hour in window["hour"].unique()),
                        },
                        recommendation=None,
                    )
                )
        return candidates

    def _consolidate_candidates(
        self,
        analysis_run_id: str,
        raw: pd.DataFrame,
        interval_frame: pd.DataFrame,
        telemetry_frame: pd.DataFrame,
    ) -> pd.DataFrame:
        insufficient_sites = self._insufficient_evidence_sites(interval_frame, telemetry_frame)
        consolidated_rows = [
            *self._consolidated_communication(analysis_run_id, raw),
            *self._consolidated_sudden(analysis_run_id, raw),
            *self._consolidated_persistent(analysis_run_id, interval_frame, insufficient_sites),
            *self._consolidated_time_windows(analysis_run_id, interval_frame, insufficient_sites),
            *self._consolidated_insufficient(analysis_run_id, raw, telemetry_frame),
        ]
        if not consolidated_rows:
            return self._empty_incidents()
        consolidated = pd.DataFrame(consolidated_rows).drop_duplicates(
            subset=["analysis_run_id", "candidate_stage", "site_id", "provisional_category"]
        )
        return self._resolve_overlapping_candidates(consolidated)

    def _resolve_overlapping_candidates(self, candidates: pd.DataFrame) -> pd.DataFrame:
        if candidates.empty:
            return candidates
        precedence = list(
            self.analysis_config.get(
                "category_precedence",
                [
                    "communication failure",
                    "sudden severe underperformance",
                    "morning time-window candidate",
                    "afternoon time-window candidate",
                    "recurring time-specific candidate",
                    "persistent underperformance",
                    "insufficient evidence",
                ],
            )
        )
        rank = {category: index for index, category in enumerate(precedence)}
        minimum_overlap = float(
            self.analysis_config.get("candidate_overlap_minimum_ratio", 0.50)
        )
        resolved: list[dict] = []
        for _site_id, site_rows in candidates.groupby("site_id", sort=False):
            pending = [row._asdict() for row in site_rows.itertuples(index=False)]
            while pending:
                seed = pending.pop(0)
                cluster = [seed]
                remaining = []
                for candidate in pending:
                    if self._candidate_overlap_ratio(seed, candidate) >= minimum_overlap:
                        cluster.append(candidate)
                    else:
                        remaining.append(candidate)
                pending = remaining
                primary = min(
                    cluster,
                    key=lambda item: rank.get(item["provisional_category"], len(rank)),
                ).copy()
                secondary = [
                    item["provisional_category"]
                    for item in cluster
                    if item["provisional_category"] != primary["provisional_category"]
                ]
                primary["secondary_evidence"] = sorted(set(secondary))
                primary["source_candidate_count"] = int(
                    sum(int(item.get("source_candidate_count", 1)) for item in cluster)
                )
                evidence = dict(primary.get("dominant_evidence") or {})
                evidence["secondary_categories"] = primary["secondary_evidence"]
                primary["dominant_evidence"] = evidence
                resolved.append(primary)
        return pd.DataFrame(resolved)

    @staticmethod
    def _candidate_overlap_ratio(first: dict, second: dict) -> float:
        first_start = pd.Timestamp(first["start_timestamp"])
        first_end = pd.Timestamp(first["end_timestamp"]) + pd.Timedelta(minutes=15)
        second_start = pd.Timestamp(second["start_timestamp"])
        second_end = pd.Timestamp(second["end_timestamp"]) + pd.Timedelta(minutes=15)
        overlap = max(
            0.0,
            (min(first_end, second_end) - max(first_start, second_start)).total_seconds(),
        )
        shortest = min(
            (first_end - first_start).total_seconds(),
            (second_end - second_start).total_seconds(),
        )
        return overlap / shortest if shortest > 0 else 0.0

    def _consolidated_communication(self, analysis_run_id: str, raw: pd.DataFrame) -> list[dict]:
        communication = raw[raw["provisional_category"].eq("communication failure")].copy()
        if communication.empty:
            return []
        return self._merge_candidate_rows(
            analysis_run_id,
            communication,
            "communication failure",
            int(self.analysis_config.get("communication_merge_window_minutes", 360)),
        )

    def _consolidated_sudden(self, analysis_run_id: str, raw: pd.DataFrame) -> list[dict]:
        sudden = raw[raw["provisional_category"].eq("sudden severe underperformance")].copy()
        if sudden.empty:
            return []
        sudden = self._after_warmup(sudden)
        minimum_loss = float(self.analysis_config.get("sudden_minimum_energy_loss_kwh", 2.0))
        near_zero_ratio = float(self.analysis_config.get("sudden_near_zero_ratio", 0.10))
        sudden = sudden[
            (sudden["total_energy_loss_kwh"] >= minimum_loss)
            & (sudden["minimum_performance_ratio"] <= near_zero_ratio)
        ]
        return self._merge_candidate_rows(
            analysis_run_id,
            sudden,
            "sudden severe underperformance",
            int(self.analysis_config.get("incident_merge_window_minutes", 180)),
        )

    def _consolidated_persistent(
        self,
        analysis_run_id: str,
        frame: pd.DataFrame,
        insufficient_sites: set[str],
    ) -> list[dict]:
        if frame.empty:
            return []
        abnormal = frame[frame["anomaly_state"].eq("underperformance")].copy()
        if abnormal.empty:
            return []
        abnormal["timestamp"] = pd.to_datetime(abnormal["timestamp"], utc=True)
        abnormal = self._after_warmup(abnormal)
        if abnormal.empty:
            return []
        minimum_days = int(self.analysis_config.get("persistent_minimum_days", 3))
        minimum_loss = float(self.analysis_config.get("persistent_minimum_energy_loss_kwh", 5.0))
        maximum_ratio = float(self.analysis_config.get("persistent_maximum_average_ratio", 0.68))
        model_bias_days = int(self.analysis_config.get("model_bias_recurring_days", 10))
        rows = []
        for site_id, group in abnormal.groupby("site_id", sort=False):
            if site_id in insufficient_sites:
                continue
            local_dates = group["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
            if local_dates.nunique() >= model_bias_days:
                continue
            if local_dates.nunique() < minimum_days:
                continue
            if float(group["energy_loss_kwh"].sum()) < minimum_loss:
                continue
            if float(group["performance_ratio"].mean()) > maximum_ratio:
                continue
            rows.append(
                self._candidate_row(
                    analysis_run_id=analysis_run_id,
                    site_id=site_id,
                    start=group["timestamp"].min(),
                    end=group["timestamp"].max(),
                    group=group,
                    anomaly_state="underperformance",
                    provisional_category="persistent underperformance",
                    evidence={
                        "recurring_days": int(local_dates.nunique()),
                        "source": "consolidated persistent underperformance",
                    },
                    recommendation=None,
                    candidate_stage="consolidated",
                    source_candidate_count=int(local_dates.nunique()),
                )
            )
        return rows

    def _consolidated_time_windows(
        self,
        analysis_run_id: str,
        frame: pd.DataFrame,
        insufficient_sites: set[str],
    ) -> list[dict]:
        abnormal = frame[
            frame["anomaly_state"].isin(["underperformance", "severe underperformance"])
        ].copy()
        if abnormal.empty:
            return []
        abnormal["timestamp"] = pd.to_datetime(abnormal["timestamp"], utc=True)
        abnormal = self._after_warmup(abnormal)
        if abnormal.empty:
            return []
        local_time = pd.to_datetime(abnormal["timestamp"], utc=True).dt.tz_convert("Asia/Kolkata")
        abnormal["hour"] = local_time.dt.hour
        abnormal["date"] = local_time.dt.date
        minimum_days = int(self.analysis_config.get("recurring_window_minimum_days", 3))
        minimum_loss = float(
            self.analysis_config.get("recurring_window_minimum_energy_loss_kwh", 5.0)
        )
        dominant_loss = float(
            self.analysis_config.get("recurring_window_dominant_energy_loss_kwh", 20.0)
        )
        max_outside_loss_ratio = float(
            self.analysis_config.get("recurring_window_maximum_outside_loss_ratio", 0.20)
        )
        model_bias_days = int(self.analysis_config.get("model_bias_recurring_days", 10))
        rows = []
        for site_id, site_group in abnormal.groupby("site_id", sort=False):
            if site_id in insufficient_sites:
                continue
            site_all = frame[frame["site_id"].eq(site_id)].copy()
            site_all_time = pd.to_datetime(site_all["timestamp"], utc=True).dt.tz_convert(
                "Asia/Kolkata"
            )
            site_all["hour"] = site_all_time.dt.hour
            for label, hours in {
                "morning time-window candidate": range(8, 12),
                "afternoon time-window candidate": range(14, 18),
            }.items():
                window = site_group[site_group["hour"].isin(hours)]
                if window["date"].nunique() < minimum_days:
                    continue
                if window["date"].nunique() >= model_bias_days:
                    continue
                window_loss = float(window["energy_loss_kwh"].sum())
                if window_loss < minimum_loss:
                    continue
                outside = site_all[
                    (~site_all["hour"].isin(hours)) & site_all["anomaly_eligible"].astype(bool)
                ]
                outside_loss = float(outside["energy_loss_kwh"].sum())
                outside_expected = float(outside["expected_generation_kwh"].sum())
                outside_loss_ratio = outside_loss / outside_expected if outside_expected > 0 else 0
                if outside_loss_ratio > max_outside_loss_ratio and window_loss < dominant_loss:
                    continue
                rows.append(
                    self._candidate_row(
                        analysis_run_id=analysis_run_id,
                        site_id=site_id,
                        start=window["timestamp"].min(),
                        end=window["timestamp"].max(),
                        group=window,
                        anomaly_state="underperformance",
                        provisional_category=label,
                        evidence={
                            "recurring_days": int(window["date"].nunique()),
                            "hours": sorted(int(hour) for hour in window["hour"].unique()),
                            "outside_loss_ratio": outside_loss_ratio,
                        },
                        recommendation=None,
                        candidate_stage="consolidated",
                        source_candidate_count=int(window["date"].nunique()),
                    )
                )
        return rows

    def _after_warmup(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        timestamp_column = "timestamp" if "timestamp" in frame.columns else "end_timestamp"
        timestamps = pd.to_datetime(frame[timestamp_column], utc=True)
        first_timestamp = timestamps.min()
        warmup_days = int(self.analysis_config.get("calibration_warmup_days", 20))
        return frame.loc[timestamps >= first_timestamp + pd.Timedelta(days=warmup_days)].copy()

    def _consolidated_insufficient(
        self,
        analysis_run_id: str,
        raw: pd.DataFrame,
        telemetry_frame: pd.DataFrame,
    ) -> list[dict]:
        insufficient = raw[raw["provisional_category"].eq("insufficient evidence")].copy()
        if insufficient.empty:
            return []
        communication_sites = set(
            raw.loc[raw["provisional_category"].eq("communication failure"), "site_id"]
        )
        rows = []
        communication_required = int(self.analysis_config.get("communication_missing_intervals", 4))
        for site_id, group in insufficient.groupby("site_id", sort=False):
            if site_id in communication_sites:
                continue
            evidence_rows = [item for item in group["dominant_evidence"] if isinstance(item, dict)]
            abnormal_intervals = max(
                [int(item.get("abnormal_intervals", 0)) for item in evidence_rows] or [0]
            )
            missing_intervals = max(
                [int(item.get("missing_intervals", 0)) for item in evidence_rows] or [0]
            )
            meaningful_ambiguity = (
                missing_intervals >= 10
                or (0 < missing_intervals <= communication_required and abnormal_intervals >= 100)
            )
            if not meaningful_ambiguity:
                continue
            candidate = self._candidate_row(
                analysis_run_id=analysis_run_id,
                site_id=site_id,
                start=group["start_timestamp"].min(),
                end=group["end_timestamp"].max(),
                group=pd.DataFrame(
                    {
                        "expected_generation_kwh": [group["expected_energy_kwh"].sum()],
                        "actual_generation_kwh": [group["actual_energy_kwh"].sum()],
                        "energy_loss_kwh": [group["total_energy_loss_kwh"].sum()],
                        "performance_ratio": [group["average_performance_ratio"].mean()],
                    }
                ),
                anomaly_state="insufficient evidence",
                provisional_category="insufficient evidence",
                evidence={
                    "source": "consolidated insufficient evidence",
                    "abnormal_intervals": abnormal_intervals,
                    "missing_intervals": missing_intervals,
                },
                recommendation=None,
                candidate_stage="consolidated",
                source_candidate_count=len(group),
            )
            candidate["interval_count"] = int(group["interval_count"].sum())
            candidate["duration_minutes"] = int(group["duration_minutes"].sum())
            rows.append(candidate)
        return rows

    def _merge_candidate_rows(
        self,
        analysis_run_id: str,
        candidates: pd.DataFrame,
        category: str,
        merge_window_minutes: int,
    ) -> list[dict]:
        if candidates.empty:
            return []
        rows = []
        for site_id, site_group in candidates.groupby("site_id", sort=False):
            current = []
            previous_end = None
            for row in site_group.sort_values("start_timestamp").itertuples(index=False):
                if previous_end is not None:
                    gap = (row.start_timestamp - previous_end).total_seconds() / 60
                    if gap > merge_window_minutes:
                        self._append_merged_candidate(
                            analysis_run_id,
                            rows,
                            site_id,
                            category,
                            current,
                        )
                        current = []
                current.append(row)
                previous_end = row.end_timestamp
            self._append_merged_candidate(analysis_run_id, rows, site_id, category, current)
        return rows

    def _append_merged_candidate(
        self,
        analysis_run_id: str,
        rows: list[dict],
        site_id: str,
        category: str,
        raw_rows: list,
    ) -> None:
        if not raw_rows:
            return
        group = pd.DataFrame([row._asdict() for row in raw_rows])
        candidate = self._candidate_row(
            analysis_run_id=analysis_run_id,
            site_id=site_id,
            start=group["start_timestamp"].min(),
            end=group["end_timestamp"].max(),
            group=pd.DataFrame(
                {
                    "expected_generation_kwh": [group["expected_energy_kwh"].sum()],
                    "actual_generation_kwh": [group["actual_energy_kwh"].sum()],
                    "energy_loss_kwh": [group["total_energy_loss_kwh"].sum()],
                    "performance_ratio": [group["average_performance_ratio"].mean()],
                }
            ),
            anomaly_state=str(group["anomaly_state"].iloc[0]),
            provisional_category=category,
            evidence={"source": "merged raw candidates"},
            recommendation=(
                "remote connectivity check" if category == "communication failure" else None
            ),
            candidate_stage="consolidated",
            source_candidate_count=len(group),
        )
        candidate["interval_count"] = int(group["interval_count"].sum())
        candidate["duration_minutes"] = _duration_minutes(
            candidate["start_timestamp"],
            candidate["end_timestamp"],
        )
        rows.append(candidate)

    def _insufficient_evidence_sites(
        self,
        frame: pd.DataFrame,
        telemetry: pd.DataFrame,
    ) -> set[str]:
        if frame.empty:
            return set()
        abnormal_states = ["underperformance", "severe underperformance", "near-zero output"]
        abnormal = frame[frame["anomaly_state"].isin(abnormal_states)]
        if abnormal.empty:
            return set()
        missing_counts: dict[str, int] = {}
        if not telemetry.empty and "data_received" in telemetry.columns:
            missing = telemetry.loc[~telemetry["data_received"].astype(bool), "site_id"]
            missing_counts = missing.value_counts().to_dict()
        insufficient = set()
        for site_id, group in frame.groupby("site_id", sort=False):
            site_abnormal = group[group["anomaly_state"].isin(abnormal_states)]
            if site_abnormal.empty:
                continue
            has_severe = site_abnormal["anomaly_state"].isin(
                ["severe underperformance", "near-zero output"]
            ).any()
            persistent_missing = missing_counts.get(site_id, 0) >= int(
                self.analysis_config.get("communication_missing_intervals", 4)
            )
            if persistent_missing and not has_severe:
                insufficient.add(site_id)
                continue
            if "ghi_wm2" in site_abnormal.columns:
                average_abnormal_irradiance = float(site_abnormal["ghi_wm2"].mean())
            else:
                average_abnormal_irradiance = 1000.0
            if (
                average_abnormal_irradiance < 260
                and len(site_abnormal) < 200
                and not has_severe
            ):
                insufficient.add(site_id)
                continue
            if len(site_abnormal) < int(self.analysis_config.get("persistence_intervals", 4)) * 3:
                insufficient.add(site_id)
        return insufficient

    def _insufficient_evidence_candidates(
        self,
        analysis_run_id: str,
        frame: pd.DataFrame,
        telemetry: pd.DataFrame,
    ) -> list[dict]:
        if telemetry.empty or "data_received" not in telemetry.columns:
            return []
        candidates = []
        abnormal_sites = set(
            frame.loc[
                frame["anomaly_state"].isin(
                    ["underperformance", "severe underperformance", "near-zero output"]
                ),
                "site_id",
            ]
        )
        insufficient_sites = self._insufficient_evidence_sites(frame, telemetry)
        for site_id in sorted(abnormal_sites.intersection(insufficient_sites)):
            site_frame = frame[frame["site_id"].eq(site_id)]
            abnormal_frame = site_frame[
                site_frame["anomaly_state"].isin(
                    ["underperformance", "severe underperformance", "near-zero output"]
                )
            ].copy()
            if abnormal_frame.empty:
                continue
            site_missing = telemetry[
                telemetry["site_id"].eq(site_id)
                & ~telemetry["data_received"].astype(bool)
            ].copy()
            abnormal_count = int(
                len(abnormal_frame)
            )
            missing_count = int(len(site_missing))
            evidence_timestamps = pd.concat(
                [
                    abnormal_frame["timestamp"],
                    site_missing.get("timestamp", pd.Series(dtype=object)),
                ]
            )
            candidates.append(
                self._candidate_row(
                    analysis_run_id=analysis_run_id,
                    site_id=site_id,
                    start=evidence_timestamps.min(),
                    end=evidence_timestamps.max(),
                    group=abnormal_frame,
                    anomaly_state="insufficient evidence",
                    provisional_category="insufficient evidence",
                    evidence={
                        "abnormal_intervals": abnormal_count,
                        "missing_intervals": missing_count,
                    },
                    recommendation=None,
                )
            )
        return candidates

    def _candidate_row(
        self,
        analysis_run_id: str,
        site_id: str,
        start,
        end,
        group: pd.DataFrame,
        anomaly_state: str,
        provisional_category: str,
        evidence: dict,
        recommendation: str | None,
        candidate_stage: str = "raw_grouped",
        source_candidate_count: int = 1,
    ) -> dict:
        interval_count = int(len(group))
        energy_loss = _safe_float(group["energy_loss_kwh"].sum()) or 0.0
        if candidate_stage == "raw_grouped":
            qualification = "unqualified_raw"
            actionable = False
        elif provisional_category == "insufficient evidence":
            qualification = "diagnostic_only"
            actionable = False
        elif provisional_category == "communication failure":
            qualification = "qualified_remote_check"
            actionable = True
        else:
            minimum_actionable_loss = float(
                self.analysis_config.get("actionable_minimum_energy_loss_kwh", 10.0)
            )
            actionable = energy_loss >= minimum_actionable_loss
            qualification = "qualified" if actionable else "monitor_only"
        return {
            "incident_candidate_id": self._candidate_id(
                analysis_run_id,
                site_id,
                str(start),
                provisional_category,
                candidate_stage,
            ),
            "analysis_run_id": analysis_run_id,
            "site_id": site_id,
            "start_timestamp": start,
            "end_timestamp": end,
            "interval_count": interval_count,
            "duration_minutes": interval_count * 15,
            "expected_energy_kwh": _safe_float(group["expected_generation_kwh"].sum()) or 0.0,
            "actual_energy_kwh": _safe_float(group["actual_generation_kwh"].sum()),
            "total_energy_loss_kwh": energy_loss,
            "average_performance_ratio": _safe_float(group["performance_ratio"].mean()),
            "minimum_performance_ratio": _safe_float(group["performance_ratio"].min()),
            "anomaly_state": anomaly_state,
            "dominant_evidence": evidence,
            "data_completeness": 1.0
            - float(evidence.get("missing_interval_count", 0)) / max(interval_count, 1),
            "provisional_category": provisional_category,
            "preliminary_recommendation": recommendation,
            "candidate_stage": candidate_stage,
            "source_candidate_count": source_candidate_count,
            "secondary_evidence": [],
            "operational_qualification_status": qualification,
            "actionable": actionable,
        }

    def _dominant_state(self, group: pd.DataFrame) -> str:
        counts = group["anomaly_state"].value_counts()
        for state in ["near-zero output", "severe underperformance", "underperformance"]:
            if state in counts:
                return state
        return str(counts.index[0])

    def _candidate_id(
        self,
        analysis_run_id: str,
        site_id: str,
        start: str,
        category: str,
        candidate_stage: str,
    ) -> str:
        key = f"{analysis_run_id}|{site_id}|{start}|{category}|{candidate_stage}"
        digest = hashlib.sha1(key.encode()).hexdigest()
        return f"IC-{digest[:24]}"

    def _empty_incidents(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "incident_candidate_id",
                "analysis_run_id",
                "site_id",
                "start_timestamp",
                "end_timestamp",
                "interval_count",
                "duration_minutes",
                "expected_energy_kwh",
                "actual_energy_kwh",
                "total_energy_loss_kwh",
                "average_performance_ratio",
                "minimum_performance_ratio",
                "anomaly_state",
                "dominant_evidence",
                "data_completeness",
                "provisional_category",
                "preliminary_recommendation",
                "candidate_stage",
                "source_candidate_count",
                "secondary_evidence",
                "operational_qualification_status",
                "actionable",
            ]
        )


def _safe_float(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _duration_minutes(start, end) -> int:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return int((end_ts - start_ts).total_seconds() / 60) + 15
