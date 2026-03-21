from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from weaviate.dotproduct import DotproductStore


APP_STYLE = """
<style>
:root {
    --bg: #07111a;
    --bg-elevated: rgba(12, 23, 36, 0.86);
    --bg-panel: rgba(16, 30, 45, 0.92);
    --border: rgba(129, 164, 191, 0.18);
    --text-main: #ecf3f8;
    --text-muted: #97acbc;
    --accent: #ff8a5b;
    --accent-cool: #57d3ff;
    --shadow: 0 18px 40px rgba(1, 8, 15, 0.45);
}
.stApp {
    background:
        radial-gradient(circle at top left, rgba(87, 211, 255, 0.15), transparent 24%),
        radial-gradient(circle at top right, rgba(255, 138, 91, 0.14), transparent 22%),
        radial-gradient(circle at bottom center, rgba(115, 80, 255, 0.14), transparent 28%),
        linear-gradient(180deg, #08131d 0%, #050b12 100%);
    color: var(--text-main);
    font-family: "Avenir Next", "Segoe UI", sans-serif;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1440px;
}
h1, h2, h3 {
    color: var(--text-main);
    letter-spacing: -0.02em;
}
p, label, .stCaption {
    color: var(--text-muted);
}
section[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(11, 22, 34, 0.96) 0%, rgba(7, 15, 25, 0.98) 100%);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * {
    color: var(--text-main);
}
div[data-testid="stMetric"] {
    background:
        linear-gradient(180deg, rgba(19, 34, 49, 0.95) 0%, rgba(12, 22, 33, 0.9) 100%);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 0.9rem 1rem;
    box-shadow: var(--shadow);
}
div[data-testid="stMetricLabel"] {
    color: var(--text-muted);
}
div[data-testid="stMetricValue"] {
    color: var(--text-main);
}
div[data-testid="stMetricDelta"] {
    color: var(--accent-cool);
}
div[data-testid="stDataFrame"],
div[data-testid="stJson"],
div[data-testid="stImage"],
div[data-testid="stAlert"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--bg-elevated);
    box-shadow: var(--shadow);
}
div[data-testid="stDataFrame"] {
    overflow: hidden;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    background: rgba(10, 20, 31, 0.92);
    border-color: var(--border);
    color: var(--text-main);
}
div[data-baseweb="tag"] {
    background: rgba(87, 211, 255, 0.12);
    border: 1px solid rgba(87, 211, 255, 0.22);
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #ff5d8f);
    border: none;
    color: #091119;
    font-weight: 700;
    border-radius: 999px;
    padding: 0.55rem 1rem;
}
.stButton > button:hover {
    color: #091119;
    filter: brightness(1.04);
}
div[data-testid="stToolbar"] {
    visibility: hidden;
}
</style>
"""


def apply_dashboard_chrome(page_title: str) -> None:
    st.set_page_config(page_title=page_title, layout="wide")
    st.markdown(APP_STYLE, unsafe_allow_html=True)


def format_duration(ms: float | int | None) -> str:
    if ms is None or pd.isna(ms):
        return "n/a"
    total_ms = int(ms)
    if total_ms < 1000:
        return f"{total_ms} ms"
    seconds = total_ms / 1000
    if seconds < 60:
        return f"{seconds:.2f} s"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes}m {remaining:.1f}s"


def format_bytes(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = units[0]
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}"


def load_workloads(
    store: DotproductStore,
    *,
    limit: int,
    statuses: list[str] | None,
    collections: list[str] | None,
) -> pd.DataFrame:
    rows = store.list_workloads(limit=limit, statuses=statuses, collections=collections)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True, errors="coerce")
    df["rss_delta_bytes"] = df["rss_after_bytes"] - df["rss_before_bytes"]
    df["short_workload_id"] = df["workload_id"].str.slice(0, 8)
    df["submitted_at_local"] = df["created_at"].dt.tz_convert("Europe/Berlin")
    return df


def metric_value(series: pd.Series, formatter) -> str:
    if series.empty:
        return "n/a"
    return formatter(series.mean())


def workload_label(df: pd.DataFrame, workload_id: str) -> str:
    row = df.loc[df["workload_id"] == workload_id].iloc[0]
    return f"{workload_id[:8]} | {row['collection']} | {row['status']}"


def open_workload_details(workload_id: str) -> None:
    st.session_state["selected_workload_id"] = workload_id
    st.query_params["workload_id"] = workload_id
    st.switch_page("pages/1_Job_Details.py")


def open_overview() -> None:
    st.session_state.pop("selected_workload_id", None)
    st.query_params.clear()
    st.switch_page("app.py")


def extract_title(properties: Any) -> str:
    if not isinstance(properties, dict):
        return "Untitled"
    for key in ("title", "summary", "Summary", "name"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Untitled"


def extract_preview(properties: Any) -> str:
    if not isinstance(properties, dict):
        return ""
    for key in ("body", "text", "Text", "combined", "description"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            text = " ".join(value.split())
            return text[:180] + ("..." if len(text) > 180 else "")
    return ""
