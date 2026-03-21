from __future__ import annotations

import numpy as np
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from dashboard.common import apply_dashboard_chrome
from dashboard.product_data import list_collections, load_objects, parse_vector_input, vectors_matrix


apply_dashboard_chrome("Embedding Classification")
st.title("Embedding Classification")
st.caption("Train a lightweight classifier from labeled object fields and predict labels for new embeddings.")

collections = list_collections()
if not collections:
    st.warning("No collections found yet.")
    st.stop()

selected_collection = st.selectbox("Collection", options=collections)
objects_df = load_objects(selected_collection, limit=4000)

if objects_df.empty:
    st.info("No vectors available for this collection.")
    st.stop()

label_field = st.text_input("Label field key", value="label", help="Reads labels from properties[label_field] first, then metadata[label_field].")

labels: list[str | None] = []
for _, row in objects_df.iterrows():
    label = None
    properties = row["properties"] if isinstance(row["properties"], dict) else {}
    metadata = row["metadata"] if isinstance(row["metadata"], dict) else {}
    if isinstance(properties.get(label_field), str):
        label = properties.get(label_field)
    elif isinstance(metadata.get(label_field), str):
        label = metadata.get(label_field)
    labels.append(label)

objects_df = objects_df.copy()
objects_df["label"] = labels
train_df = objects_df.dropna(subset=["label"])

st.metric("Objects with labels", f"{len(train_df)}")
if len(train_df) < 12 or train_df["label"].nunique() < 2:
    st.warning("Need at least 12 labeled rows and 2 classes to train. Add labels in object properties or metadata.")
    st.stop()

X = vectors_matrix(train_df)
y = train_df["label"].astype(str).to_numpy()

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y,
)

model = LogisticRegression(max_iter=1500, multi_class="auto")
model.fit(X_train, y_train)
accuracy = model.score(X_test, y_test)
st.metric("Validation accuracy", f"{accuracy:.2%}")

query_vector_text = st.text_area(
    "Embedding to classify",
    height=110,
    placeholder="0.11, -0.44, 0.73, ...",
)

if st.button("Predict class", type="primary"):
    query_vector: np.ndarray | None = None
    try:
        query_vector = parse_vector_input(query_vector_text)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if query_vector is None:
        st.stop()
    vector_for_prediction = query_vector
    assert vector_for_prediction is not None

    if vector_for_prediction.shape[0] != X.shape[1]:
        st.error(f"Vector dimension mismatch: expected {X.shape[1]} values.")
        st.stop()

    probabilities = model.predict_proba(vector_for_prediction.reshape(1, -1))[0]
    classes = model.classes_
    scored = sorted(zip(classes, probabilities), key=lambda item: item[1], reverse=True)

    st.subheader("Prediction")
    st.success(f"Predicted label: {scored[0][0]} ({scored[0][1]:.2%})")
    st.dataframe(
        {"label": [row[0] for row in scored], "probability": [round(float(row[1]), 4) for row in scored]},
        use_container_width=True,
        hide_index=True,
    )
