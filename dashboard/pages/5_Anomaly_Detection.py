from __future__ import annotations

import numpy as np
import streamlit as st
from sklearn.ensemble import IsolationForest

from dashboard.common import apply_dashboard_chrome
from dashboard.product_data import list_collections, load_objects, vectors_matrix


apply_dashboard_chrome("Anomaly Detection")
st.title("Embedding Anomaly Detection")
st.caption("Detect outlier vectors in each collection using Isolation Forest.")

collections = list_collections()
if not collections:
    st.warning("No collections found yet.")
    st.stop()

left, middle, right = st.columns(3)
with left:
    selected_collection = st.selectbox("Collection", options=collections)
with middle:
    contamination = st.slider("Anomaly ratio", min_value=0.01, max_value=0.30, value=0.08, step=0.01)
with right:
    max_rows = st.slider("Rows to use", min_value=50, max_value=5000, value=1200, step=50)

objects_df = load_objects(selected_collection, limit=max_rows)
if len(objects_df) < 20:
    st.warning("Need at least 20 vectors for reliable anomaly detection.")
    st.stop()

vectors = vectors_matrix(objects_df)
model = IsolationForest(
    contamination=contamination,
    n_estimators=250,
    random_state=42,
)
labels = model.fit_predict(vectors)
raw_scores = model.decision_function(vectors)
anomaly_scores = (-raw_scores).astype(float)

result_df = objects_df.copy()
result_df["is_anomaly"] = labels == -1
result_df["anomaly_score"] = anomaly_scores

anomaly_df = result_df[result_df["is_anomaly"]].sort_values("anomaly_score", ascending=False)

st.metric("Rows evaluated", f"{len(result_df)}")
st.metric("Anomalies detected", f"{len(anomaly_df)}")

st.subheader("Top Anomalies")
if anomaly_df.empty:
    st.info("No anomalies were flagged for this configuration.")
else:
    display_df = anomaly_df.loc[:, ["uuid", "title", "preview", "anomaly_score"]].copy()
    display_df["anomaly_score"] = display_df["anomaly_score"].round(4)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
