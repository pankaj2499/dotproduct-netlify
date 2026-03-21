from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from dashboard.common import apply_dashboard_chrome
from dashboard.product_data import list_collections, load_objects, vectors_matrix, workload_snapshot


apply_dashboard_chrome("Embedding Clustering")
st.title("Embedding Clustering")
st.caption("Run unsupervised clustering directly from stored vectors and compare against workload history.")

collections = list_collections()
if not collections:
    st.warning("No collections found yet.")
    st.stop()

col_left, col_mid, col_right = st.columns(3)
with col_left:
    selected_collection = st.selectbox("Collection", options=collections)
with col_mid:
    n_clusters = st.slider("Clusters", min_value=2, max_value=12, value=4, step=1)
with col_right:
    max_rows = st.slider("Rows to use", min_value=50, max_value=4000, value=800, step=50)

objects_df = load_objects(selected_collection, limit=max_rows)
if len(objects_df) < n_clusters:
    st.warning("Not enough vectors for the selected cluster count.")
    st.stop()

vectors = vectors_matrix(objects_df)
model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
cluster_labels = model.fit_predict(vectors)

clustered_df = objects_df.copy()
clustered_df["cluster_id"] = cluster_labels

summary = (
    clustered_df.groupby("cluster_id")
    .size()
    .rename("members")
    .reset_index()
    .sort_values("members", ascending=False)
)

left, right = st.columns([0.65, 0.35])
with left:
    st.subheader("Cluster Distribution")
    st.bar_chart(summary.set_index("cluster_id"), height=320)
with right:
    st.subheader("KMeans Stats")
    st.metric("Vectors clustered", f"{len(clustered_df)}")
    st.metric("Inertia", f"{model.inertia_:.2f}")
    st.metric("Vector dimension", f"{vectors.shape[1]}")

projection = PCA(n_components=2, random_state=42).fit_transform(vectors)
plot_df = pd.DataFrame(
    {
        "x": projection[:, 0],
        "y": projection[:, 1],
        "cluster": cluster_labels.astype(str),
    }
)
st.subheader("2D Projection")
st.scatter_chart(plot_df, x="x", y="y", color="cluster", size=4)

st.subheader("Cluster Members")
cluster_to_view = st.selectbox("Inspect cluster", options=sorted(summary["cluster_id"].tolist()))
member_df = clustered_df[clustered_df["cluster_id"] == cluster_to_view].copy()
st.dataframe(
    member_df.loc[:, ["uuid", "title", "preview"]],
    use_container_width=True,
    hide_index=True,
)

workload_df, workload_summary = workload_snapshot(limit=200)
st.subheader("Worker Workload Snapshot")
if workload_df.empty:
    st.info("No worker workloads found yet.")
else:
    total_workloads = int(workload_summary.get("total_workloads") or 0)
    completed_workloads = int(workload_summary.get("completed_workloads") or 0)
    failed_workloads = int(workload_summary.get("failed_workloads") or 0)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total workloads", f"{total_workloads}")
    m2.metric("Completed", f"{completed_workloads}")
    m3.metric("Failed", f"{failed_workloads}")

    recent = workload_df.loc[:, ["workload_id", "collection", "status", "algorithm", "member_count", "created_at"]]
    st.dataframe(recent, use_container_width=True, hide_index=True)
