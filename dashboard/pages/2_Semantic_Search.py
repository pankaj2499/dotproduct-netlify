from __future__ import annotations

import numpy as np
import streamlit as st

from dashboard.common import apply_dashboard_chrome
from dashboard.product_data import (
    cosine_similarity_search,
    list_collections,
    load_objects,
    parse_vector_input,
)


apply_dashboard_chrome("Semantic Search")
st.title("Semantic Similarity Search")
st.caption("Search embedded objects using cosine similarity over stored vectors.")

collections = list_collections()
if not collections:
    st.warning("No collections found yet. Insert embedded objects first, then reload this page.")
    st.stop()

left, right = st.columns([0.5, 0.5])
with left:
    selected_collection = st.selectbox("Collection", options=collections)
with right:
    top_k = st.slider("Top results", min_value=3, max_value=50, value=10, step=1)

objects_df = load_objects(selected_collection, limit=3000)
if objects_df.empty:
    st.info("No vectors available for this collection.")
    st.stop()

st.metric("Embeddings in collection", f"{len(objects_df)}")
st.metric("Vector dimension", f"{int(objects_df['vector_dim'].iloc[0])}")

mode = st.radio(
    "Query mode",
    options=["Paste vector", "Use existing UUID"],
    horizontal=True,
)

query_vector: np.ndarray | None = None

if mode == "Paste vector":
    raw_vector = st.text_area(
        "Query embedding",
        height=110,
        placeholder="0.18, -0.22, 0.71, ...",
    )
    if st.button("Run similarity search", type="primary"):
        try:
            query_vector = parse_vector_input(raw_vector)
        except ValueError as exc:
            st.error(str(exc))
else:
    selected_uuid = st.selectbox("Reference UUID", options=objects_df["uuid"].tolist())
    if st.button("Run similarity search", type="primary"):
        selected_row = objects_df[objects_df["uuid"] == selected_uuid].iloc[0]
        query_vector = np.asarray(selected_row["vector"], dtype=float)

if query_vector is not None:
    result_df = objects_df.head(0).copy()
    try:
        result_df = cosine_similarity_search(query_vector, objects_df, top_k=top_k)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    result_df = result_df.loc[:, ["uuid", "title", "preview", "similarity"]]
    result_df["similarity"] = result_df["similarity"].round(4)

    st.subheader("Most Similar Objects")
    st.dataframe(result_df, use_container_width=True, hide_index=True)
