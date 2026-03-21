#!/usr/bin/env python
# coding: utf-8

# # OpenAI Cookbook Clustering with Downloaded Food Reviews
# 
# This notebook uses the downloaded `fine_food_reviews_with_embeddings_1k.csv` dataset in `/workspace/data`.
# 
# It does four things:
# 
# - loads the local CSV
# - parses the precomputed embeddings already stored in the `embedding` column
# - runs KMeans clustering and t-SNE over the full 1000-review dataset
# - inserts a balanced subset into local Weaviate and runs `collection.cluster()` through the worker container
# 

# In[12]:


import os
from ast import literal_eval
from pathlib import Path
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import weaviate
from IPython.display import Image, display
from celery.result import AsyncResult
from openai import OpenAI
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from weaviate.classes.config import Configure, DataType, Property
from weaviate.dotproduct import DotproductStore

from app.celery_app import celery_app

DATASET_PATH = Path("/workspace/data/fine_food_reviews_with_embeddings_1k.csv")
LABEL_MODEL = os.getenv("OPENAI_CLUSTER_LABEL_MODEL", "gpt-4.1-mini")
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
openai_client = OpenAI() if USE_OPENAI else None

print({
    "dataset_path": str(DATASET_PATH),
    "dataset_exists": DATASET_PATH.exists(),
    "using_openai_for_cluster_naming": USE_OPENAI,
    "label_model": LABEL_MODEL,
})


# In[13]:


df = pd.read_csv(DATASET_PATH)
df = df.rename(columns={"": "row_id", "Unnamed: 0": "row_id"})
df["embedding"] = df["embedding"].apply(literal_eval).apply(np.array)
df["Score"] = df["Score"].astype(int)
df["n_tokens"] = df["n_tokens"].astype(int)

matrix = np.vstack(df["embedding"].values)

display(df[["row_id", "ProductId", "Score", "Summary", "n_tokens"]].head())
matrix.shape


# In[14]:


n_clusters = 4

kmeans = KMeans(
    n_clusters=n_clusters,
    init="k-means++",
    n_init=10,
    random_state=42,
)

df["Cluster"] = kmeans.fit_predict(matrix)

display(df.groupby("Cluster").Score.mean().sort_values().to_frame("mean_score"))
display(df.groupby("Cluster").size().sort_values(ascending=False).to_frame("count"))


# In[15]:


tsne = TSNE(
    n_components=2,
    perplexity=15,
    random_state=42,
    init="random",
    learning_rate=200,
)
vis_dims = tsne.fit_transform(matrix)

x = vis_dims[:, 0]
y = vis_dims[:, 1]
colors = ["#0b7285", "#e8590c", "#2b8a3e", "#c92a2a", "#6741d9", "#495057"]

plt.figure(figsize=(9, 7))
for cluster_id in range(n_clusters):
    xs = x[df.Cluster == cluster_id]
    ys = y[df.Cluster == cluster_id]
    color = colors[cluster_id % len(colors)]
    plt.scatter(xs, ys, color=color, alpha=0.25, label=f"Cluster {cluster_id}")
    plt.scatter(xs.mean(), ys.mean(), marker="x", color=color, s=140)

plt.title("Clusters identified from review embeddings in 2D with t-SNE")
plt.legend()
plt.show()


# In[16]:


def sampled_cluster_reviews(cluster_id: int, sample_size: int = 5) -> pd.Series:
    return (
        df[df.Cluster == cluster_id]
        .combined.str.replace("Title: ", "", regex=False)
        .str.replace("; Content: ", ": ", regex=False)
        .sample(sample_size, random_state=42)
    )


cluster_themes = {}
for cluster_id in range(n_clusters):
    reviews = "\n".join(sampled_cluster_reviews(cluster_id).tolist())
    if USE_OPENAI:
        response = openai_client.responses.create(
            model=LABEL_MODEL,
            input=(
                "What do the following customer reviews have in common? "
                "Return a short theme of at most eight words.\n\n"
                f"Customer reviews:\n{reviews}"
            ),
        )
        theme = response.output_text.strip()
    else:
        theme = f"Cluster {cluster_id}"

    cluster_themes[cluster_id] = theme
    print(f"Cluster {cluster_id} theme: {theme}")
    display(df[df.Cluster == cluster_id][["Score", "Summary"]].sample(5, random_state=42))


# ## Send a balanced subset into local Weaviate
# 
# The local clustering above uses all 1000 embedded reviews.
# 
# For the Weaviate plus worker demonstration, the notebook inserts a balanced subset of 40 reviews from each local cluster. This keeps the notebook responsive while still exercising the patched `collection.insert(...)` and `collection.cluster(...)` flow end to end.
# 

# In[17]:


reviews_per_cluster_for_weaviate = 40
weaviate_df = pd.concat(
    [
        part.sample(min(reviews_per_cluster_for_weaviate, len(part)), random_state=42)
        for _, part in df.groupby("Cluster")
    ],
    ignore_index=True,
)

display(weaviate_df.groupby("Cluster").size().to_frame("rows_for_weaviate"))


# In[18]:


client = weaviate.connect_to_dotproduct_local()
collection_name = "CookbookFoodReviews"
reviews = client.collections.use(collection_name)

if reviews.exists():
    client.collections.delete(collection_name)

client.collections.create(
    name=collection_name,
    properties=[
        Property(name="row_id", data_type=DataType.INT),
        Property(name="product_id", data_type=DataType.TEXT),
        Property(name="user_id", data_type=DataType.TEXT),
        Property(name="score", data_type=DataType.INT),
        Property(name="summary", data_type=DataType.TEXT),
        Property(name="review_text", data_type=DataType.TEXT),
        Property(name="cluster_theme", data_type=DataType.TEXT),
        Property(name="local_cluster", data_type=DataType.INT),
    ],
    vector_config=Configure.Vectors.self_provided(),
)
reviews = client.collections.use(collection_name)

inserted_uuids = []
for row in weaviate_df.itertuples(index=False):
    inserted_uuid = reviews.insert(
        properties={
            "row_id": int(row.row_id),
            "product_id": row.ProductId,
            "user_id": row.UserId,
            "score": int(row.Score),
            "summary": row.Summary,
            "review_text": row.Text,
            "cluster_theme": cluster_themes[int(row.Cluster)],
            "local_cluster": int(row.Cluster),
        },
        vector=row.embedding.tolist(),
        metadata={
            "source_csv": DATASET_PATH.name,
            "n_tokens": int(row.n_tokens),
            "local_cluster": int(row.Cluster),
        },
    )
    inserted_uuids.append(str(inserted_uuid))

insert_summary = {
    "collection": collection_name,
    "inserted_objects": len(inserted_uuids),
}
display(insert_summary)
inserted_uuids[:5]


# In[19]:


submission = reviews.cluster(limit=len(weaviate_df), params={"k": n_clusters, "plot": True})
submission_payload = {
    "workload_id": submission.workload_id,
    "task_id": submission.task_id,
    "collection": submission.collection,
    "status": submission.status,
    "candidate_count": len(submission.uuids),
}
display(submission_payload)
submission_payload


# In[20]:


task = AsyncResult(submission.task_id, app=celery_app)
task_result = task.get(timeout=60)
display(task_result)
pprint(task_result)


# In[21]:


store = DotproductStore()
workload = store.get_workload(submission.workload_id)
cluster_results = pd.DataFrame(store.get_cluster_results(submission.workload_id))
plot_artifact = store.get_workload_artifact(submission.workload_id, "cluster_plot")

result_df = weaviate_df.copy()
result_df["uuid"] = inserted_uuids
result_df = result_df.merge(cluster_results[["uuid", "cluster_id"]], on="uuid", how="left")
result_df = result_df.rename(columns={"Cluster": "local_cluster", "Summary": "summary"})

comparison = pd.crosstab(result_df["local_cluster"], result_df["cluster_id"])

display(workload)
display(plot_artifact["metadata"])
display(Image(data=plot_artifact["artifact_blob"]))
display(cluster_results.head(20))
display(comparison)
display(result_df[["summary", "Score", "local_cluster", "cluster_id"]].sort_values(["cluster_id", "local_cluster", "Score"], ascending=[True, True, False]).head(20))

client.close()


# In[ ]:




