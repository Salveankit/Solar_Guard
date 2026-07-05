from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.api_client import SolarGuardApiClient, SolarGuardApiError
from dashboard.data_views import DISCLOSURE_TEXT


def setup_page(title: str) -> SolarGuardApiClient:
    st.set_page_config(page_title=f"SolarGuard | {title}", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            --sg-ink: #17201c;
            --sg-muted: #66736d;
            --sg-line: #dce4df;
            --sg-bg: #f5f8f6;
            --sg-panel: #ffffff;
            --sg-green: #1d7f5c;
            --sg-amber: #b76b00;
            --sg-red: #b83b32;
            --sg-blue: #2364aa;
        }
        .stApp { background: var(--sg-bg); color: var(--sg-ink); }
        h1, h2, h3 { letter-spacing: 0; }
        section[data-testid="stSidebar"] { background: #eef4f0; }
        div[data-testid="stMetric"] {
            background: var(--sg-panel);
            border: 1px solid var(--sg-line);
            border-radius: 8px;
            padding: 14px 16px;
        }
        .sg-disclosure {
            border: 1px solid var(--sg-line);
            border-left: 4px solid var(--sg-blue);
            background: #ffffff;
            border-radius: 6px;
            padding: 10px 12px;
            color: var(--sg-muted);
            font-size: 0.9rem;
        }
        .sg-chip {
            display: inline-block;
            border: 1px solid var(--sg-line);
            border-radius: 999px;
            padding: 2px 9px;
            background: #ffffff;
            margin-right: 6px;
            font-size: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    client = SolarGuardApiClient.from_env()
    st.caption("SolarGuard · POC — Simulated Data")
    st.title(title)
    st.markdown(f"<div class='sg-disclosure'>{DISCLOSURE_TEXT}</div>", unsafe_allow_html=True)
    return client


def api_call(label: str, fetch: Callable[[], Any]) -> Any | None:
    try:
        with st.spinner(label):
            return fetch()
    except SolarGuardApiError as exc:
        st.error(str(exc))
        st.info("Verify FastAPI is running and `SOLARGUARD_API_URL` points to it.")
        return None


def api_call_optional(label: str, fetch: Callable[[], Any]) -> Any | None:
    try:
        with st.spinner(label):
            return fetch()
    except SolarGuardApiError as exc:
        if exc.status_code == 404:
            return None
        st.error(str(exc))
        st.info("Verify FastAPI is running and `SOLARGUARD_API_URL` points to it.")
        return None


def dataframe(rows: list[dict[str, Any]], *, empty_message: str) -> pd.DataFrame:
    if not rows:
        st.info(empty_message)
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    return frame


def metric_row(items: list[tuple[str, Any]]) -> None:
    columns = st.columns(len(items))
    for column, (label, value) in zip(columns, items, strict=True):
        column.metric(label, value)


def status_chip(label: str) -> None:
    st.markdown(f"<span class='sg-chip'>{label}</span>", unsafe_allow_html=True)
