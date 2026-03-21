from __future__ import annotations

import pandas as pd
import streamlit as st
from weaviate.dotproduct import DotproductStore

from dashboard.common import (
    apply_dashboard_chrome,
    extract_preview,
    extract_title,
    format_bytes,
    format_duration,
    open_overview,
)


def _load_cluster_details(store: DotproductStore, workload_id: str) -> pd.DataFrame:
    cluster_results = pd.DataFrame(store.get_cluster_results(workload_id))
    if cluster_results.empty:
        return cluster_results

    members = pd.DataFrame(store.get_workload_members(workload_id))
    detail_df = cluster_results.merge(
        members.loc[:, ["uuid", "rank_index", "distance", "properties", "metadata"]],
        on="uuid",
        how="left",
    )
    detail_df["title"] = detail_df["properties"].apply(extract_title)
    detail_df["preview"] = detail_df["properties"].apply(extract_preview)
    detail_df["source"] = detail_df["metadata"].apply(
        lambda metadata: metadata.get("source") if isinstance(metadata, dict) else None
    )
    return detail_df.sort_values(["cluster_id", "rank_index", "uuid"], na_position="last")


apply_dashboard_chrome("Job Details")

store = DotproductStore()
workload_id = st.session_state.get("selected_workload_id") or st.query_params.get("workload_id")
if workload_id:
    st.session_state["selected_workload_id"] = workload_id

if not workload_id:
    st.title("Job Details")
    st.warning("No workload was selected.")
    if st.button("Back to jobs"):
        open_overview()
    st.stop()

try:
    workload = store.get_workload(workload_id)
except KeyError:
    st.title("Job Details")
    st.error(f"Unknown workload id: {workload_id}")
    if st.button("Back to jobs"):
        open_overview()
    st.stop()

back_col, title_col = st.columns([0.2, 0.8])
with back_col:
    st.caption(" ")
    if st.button("Back to jobs", use_container_width=True):
        open_overview()

with title_col:
    st.title(f"Job {workload_id[:8]}")
    st.caption(f"{workload['collection']} | {workload['algorithm']} | {workload['status']}")

metric_cols = st.columns(4)
metric_cols[0].metric("Status", workload["status"])
metric_cols[1].metric("Submitted via", workload.get("submission_platform") or "unknown")
metric_cols[2].metric("Runtime", workload.get("runtime_platform") or "unknown")
metric_cols[3].metric(
    "Wall time",
    format_duration(workload["wall_time_ms"]),
)

extra_metric_cols = st.columns(2)
extra_metric_cols[0].metric("CPU time", format_duration(workload["cpu_time_ms"]))
extra_metric_cols[1].metric(
    "Final RSS",
    format_bytes(workload["rss_after_bytes"]),
    delta=format_bytes(
        (
            workload["rss_after_bytes"] - workload["rss_before_bytes"]
            if workload["rss_after_bytes"] is not None and workload["rss_before_bytes"] is not None
            else None
        )
    ),
)

meta_col, result_col = st.columns([1, 1.15])

with meta_col:
    st.subheader("Job Metadata")
    st.json(
        {
            "workload_id": workload["workload_id"],
            "executor_task_id": workload["executor_task_id"],
            "collection": workload["collection"],
            "algorithm": workload["algorithm"],
            "submission_platform": workload.get("submission_platform"),
            "runtime_platform": workload.get("runtime_platform"),
            "created_at": workload["created_at"],
            "started_at": workload["started_at"],
            "completed_at": workload["completed_at"],
            "query": workload["query"],
            "params": workload["params"],
        },
        expanded=False,
    )
    if workload["error_message"]:
        st.error(workload["error_message"])

with result_col:
    st.subheader("Stored Result")
    if workload["result"] is None:
        st.info("No result payload was stored for this workload yet.")
    else:
        st.json(workload["result"], expanded=True)

try:
    artifact = store.get_workload_artifact(workload_id, "cluster_plot")
except KeyError:
    artifact = None

if artifact is not None:
    metadata = artifact["metadata"] or {}
    st.subheader("Cluster Plot")
    st.caption(
        f"{artifact['mime_type']} | "
        f"{metadata.get('plot_kind', 'plot')} | "
        f"{metadata.get('point_count', 'unknown')} points"
    )
    st.image(artifact["artifact_blob"], use_container_width=True)

detail_df = _load_cluster_details(store, workload_id)

if detail_df.empty:
    st.info("No cluster assignments were stored for this workload.")
    st.stop()

st.subheader("Cluster Summary")
cluster_counts = detail_df.groupby("cluster_id").size().rename("member_count").reset_index()
summary_col, chart_col = st.columns([0.8, 1.2])

with summary_col:
    st.dataframe(cluster_counts, use_container_width=True, hide_index=True)

with chart_col:
    st.bar_chart(cluster_counts.set_index("cluster_id"), height=240)

cluster_ids = sorted(detail_df["cluster_id"].dropna().unique().tolist())
tabs = st.tabs([f"Cluster {cluster_id}" for cluster_id in cluster_ids])

for tab, cluster_id in zip(tabs, cluster_ids):
    cluster_rows = detail_df[detail_df["cluster_id"] == cluster_id].copy()
    cluster_rows["distance"] = cluster_rows["distance"].round(4)
    with tab:
        st.metric("Members", len(cluster_rows))
        st.dataframe(
            cluster_rows[
                [
                    "uuid",
                    "rank_index",
                    "distance",
                    "title",
                    "preview",
                    "source",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Raw rows"):
            st.dataframe(
                cluster_rows[
                    [
                        "uuid",
                        "cluster_id",
                        "score",
                        "rank_index",
                        "distance",
                        "properties",
                        "metadata",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
