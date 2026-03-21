from __future__ import annotations

import streamlit as st
from weaviate.dotproduct import DotproductStore

from dashboard.common import (
    apply_dashboard_chrome,
    format_bytes,
    format_duration,
    load_workloads,
    metric_value,
    open_workload_details,
    workload_label,
)


apply_dashboard_chrome("Dotproduct Jobs")

store = DotproductStore()
all_workloads = store.list_workloads(limit=500)
all_collections = sorted({row["collection"] for row in all_workloads})
all_statuses = sorted({row["status"] for row in all_workloads})

with st.sidebar:
    st.title("Job Dashboard")
    st.caption("Inspect Weaviate workloads executed by the worker.")
    if st.button("Refresh"):
        st.rerun()

    limit = st.slider("Recent jobs", min_value=20, max_value=500, value=200, step=20)
    selected_statuses = st.multiselect(
        "Statuses",
        options=all_statuses,
        default=all_statuses,
    )
    selected_collections = st.multiselect(
        "Collections",
        options=all_collections,
        default=[],
    )

df = load_workloads(
    store,
    limit=limit,
    statuses=selected_statuses or None,
    collections=selected_collections or None,
)

st.title("Dotproduct Job Dashboard")
st.caption("Overview of submitted workloads. Open a job to inspect its individual clusters and members.")

if df.empty:
    st.info(
        "No workloads have been submitted yet. Run `collection.cluster(...)` from the notebook to populate this dashboard."
    )
    st.stop()

completed_df = df[df["status"] == "completed"]
active_count = int(df["status"].isin(["queued", "running"]).sum())

metric_cols = st.columns(4)
metric_cols[0].metric("Visible jobs", f"{len(df)}")
metric_cols[1].metric("Active jobs", f"{active_count}")
metric_cols[2].metric("Avg wall time", metric_value(completed_df["wall_time_ms"], format_duration))
metric_cols[3].metric("Avg RSS delta", metric_value(completed_df["rss_delta_bytes"], format_bytes))

chart_left, chart_right = st.columns([1.3, 1])

with chart_left:
    st.subheader("Runtime Trend")
    runtime_df = (
        df.sort_values("created_at")
        .dropna(subset=["wall_time_ms"])
        .loc[:, ["created_at", "wall_time_ms", "cpu_time_ms"]]
        .set_index("created_at")
    )
    if runtime_df.empty:
        st.info("No runtime data yet for the selected workloads.")
    else:
        st.line_chart(runtime_df, height=280)

with chart_right:
    st.subheader("Memory Delta")
    memory_df = (
        df.sort_values("created_at", ascending=False)
        .head(20)
        .loc[:, ["short_workload_id", "rss_delta_bytes", "rss_after_bytes"]]
        .set_index("short_workload_id")
    )
    if memory_df.empty:
        st.info("No memory data yet for the selected workloads.")
    else:
        st.bar_chart(memory_df, height=280)

table_df = df.copy()
table_df["submitted_at"] = table_df["submitted_at_local"].dt.strftime("%Y-%m-%d %H:%M:%S")
table_df["wall_time"] = table_df["wall_time_ms"].apply(format_duration)
table_df["cpu_time"] = table_df["cpu_time_ms"].apply(format_duration)
table_df["rss_delta"] = table_df["rss_delta_bytes"].apply(format_bytes)
table_df["rss_after"] = table_df["rss_after_bytes"].apply(format_bytes)
table_df["result_summary"] = table_df["result"].apply(
    lambda result: result.get("cluster_sizes") if isinstance(result, dict) else None
)
table_df["submitted_via"] = table_df["submission_platform"].fillna("unknown")
table_df["runtime"] = table_df["runtime_platform"].fillna("unknown")

st.subheader("Recent Jobs")
st.dataframe(
    table_df[
        [
            "submitted_at",
            "workload_id",
            "status",
            "collection",
            "algorithm",
            "submitted_via",
            "runtime",
            "member_count",
            "result_count",
            "wall_time",
            "cpu_time",
            "rss_delta",
            "rss_after",
            "result_summary",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Open Job Details")
selector_col, action_col = st.columns([0.8, 0.2])
with selector_col:
    selected_workload_id = st.selectbox(
        "Select a workload",
        options=df["workload_id"].tolist(),
        format_func=lambda workload_id: workload_label(df, workload_id),
    )
with action_col:
    st.caption(" ")
    if st.button("Open job", use_container_width=True, key="open-selected-job"):
        open_workload_details(selected_workload_id)

st.caption("Quick open for the most recent jobs")
card_columns = st.columns(3)
for index, row in df.head(9).reset_index(drop=True).iterrows():
    with card_columns[index % 3]:
        with st.container(border=True):
            st.markdown(f"**{row['short_workload_id']}**")
            st.caption(f"{row['collection']} | {row['status']}")
            st.write(f"Submitted via: {row['submission_platform'] or 'unknown'}")
            st.write(f"Runtime: {row['runtime_platform'] or 'unknown'}")
            st.write(f"Wall time: {format_duration(row['wall_time_ms'])}")
            st.write(f"RSS delta: {format_bytes(row['rss_delta_bytes'])}")
            if st.button("View details", key=f"open-{row['workload_id']}", use_container_width=True):
                open_workload_details(row["workload_id"])
