from __future__ import annotations

import streamlit as st

from dashboard.common import (
    apply_dashboard_chrome,
)
from dashboard.product_data import list_collections, load_objects, workload_snapshot


apply_dashboard_chrome("Dotproduct AI Console")

collections = list_collections()
workload_df, workload_summary = workload_snapshot(limit=250)
latest_objects = load_objects(collections[0], limit=1200) if collections else None
vector_dim = int(latest_objects["vector_dim"].iloc[0]) if latest_objects is not None and not latest_objects.empty else 0

with st.sidebar:
    st.title("Dotproduct")
    st.caption("Embedding Intelligence Console")
    st.info(
        "Use the pages in the left navigation:\n\n"
        "- Semantic Search\n"
        "- Classification\n"
        "- Clustering\n"
        "- Anomaly Detection\n"
        "- Job Details"
    )
    if st.button("Refresh Console"):
        st.rerun()

st.title("Dotproduct Frontend")
st.caption(
    "A Streamlit product frontend for embedding-first workflows: semantic similarity search, "
    "classification, clustering, and anomaly detection."
)

metric_cols = st.columns(5)
metric_cols[0].metric("Collections", f"{len(collections)}")
metric_cols[1].metric("Stored embeddings", f"{0 if latest_objects is None else len(latest_objects)}")
metric_cols[2].metric("Vector dimension", f"{vector_dim}")
metric_cols[3].metric("Total workloads", f"{int(workload_summary.get('total_workloads') or 0)}")
metric_cols[4].metric("Completed workloads", f"{int(workload_summary.get('completed_workloads') or 0)}")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Product Capability Map")
    st.markdown(
        """
        1. Semantic Similarity Search: rank nearest records with cosine similarity over embeddings.
        2. Classification: train a lightweight classifier from labeled embeddings.
        3. Clustering: discover groups with KMeans and inspect member-level results.
        4. Anomaly Detection: identify outlier vectors with Isolation Forest.
        """
    )

    if latest_objects is not None and not latest_objects.empty:
        st.subheader("Sample Embedded Objects")
        st.dataframe(
            latest_objects.loc[:, ["uuid", "title", "preview", "collection"]].head(10),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No embedded objects found yet. Add data via notebook ingestion first.")

with right:
    st.subheader("Workload Status")
    if workload_df.empty:
        st.info("No workloads have been submitted yet.")
    else:
        status_counts = workload_df["status"].value_counts().rename_axis("status").to_frame("count")
        st.bar_chart(status_counts)

    st.subheader("Getting Started")
    st.markdown(
        """
        1. Insert vectors into a collection.
        2. Open Semantic Search to test nearest-neighbor retrieval.
        3. Add labels and train the Classification page.
        4. Use Clustering and Anomaly pages to explore structure and outliers.
        """
    )
