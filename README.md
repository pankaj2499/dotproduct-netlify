# Dotproduct

Local job execution stack where Jupyter submits work, a separate worker executes it, and a dashboard shows status, timings, memory, and cluster results.

## Architecture

```text
Jupyter notebook -> Redis queue -> Celery worker
                      |              |
                      |              -> runs Python / PySpark jobs
                      |
                      -> result backend

Notebook / worker -> Weaviate -> vector search candidates
Notebook / worker -> SQLite   -> workload metadata, metrics, artifacts
Dashboard         -> SQLite   -> job list and job details
```

### Services

- `notebook`: JupyterLab for submitting jobs
- `worker`: Celery worker that actually runs jobs
- `redis`: queue + Celery result backend
- `weaviate`: local vector database
- `dashboard`: Streamlit UI for jobs, metrics, and cluster results

## Ports

- JupyterLab: `http://localhost:8888/lab?token=devtoken`
- Weaviate HTTP: `http://localhost:8080`
- Weaviate gRPC: `localhost:50051`
- Redis: `localhost:6379`
- Dashboard: `http://localhost:8502`

If `8502` is not what you want, set `DOTPRODUCT_DASHBOARD_PORT` before starting Compose.

## How It Runs

- The notebook does not execute heavy jobs itself.
- Jobs are submitted from the notebook container.
- The worker container executes them.
- Workload metadata is stored in `/workspace/.data/dotproduct.sqlite3`.
- The dashboard reads the same SQLite database.

## Start

```bash
docker compose up --build
```

Optional, if you want notebooks to call OpenAI for cluster naming:

```bash
export OPENAI_API_KEY=your_key_here
docker compose up --build
```

Start in the background:

```bash
docker compose up -d --build
```

## Check Services

```bash
docker compose ps
```

Tail worker logs:

```bash
docker compose logs -f worker
```

Tail dashboard logs:

```bash
docker compose logs -f dashboard
```

## Submit Jobs

### 1. Simple worker job

In a notebook cell:

```python
from app.tasks import long_running_sum

job = long_running_sum.delay([1, 2, 3, 4], delay_seconds=5)
job.status
job.get(timeout=30)
```

### 2. PySpark job in the worker container

```python
from app.tasks import spark_dot_product

job = spark_dot_product.delay([1, 2, 3], [4, 5, 6])
job.get(timeout=60)
```

### 3. Weaviate cluster workload

This flow is what powers the dashboard and stored workload metrics.

```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_dotproduct_local()

docs = client.collections.use("DemoDocs")
if not docs.exists():
    client.collections.create(
        name="DemoDocs",
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="body", data_type=DataType.TEXT),
        ],
        vector_config=Configure.Vectors.self_provided(),
    )

docs.insert(
    properties={"title": "Alpha", "body": "first cluster"},
    vector=[1.0, 1.0, 0.0],
    metadata={"source": "notebook"},
)

docs.insert(
    properties={"title": "Beta", "body": "first cluster neighbor"},
    vector=[0.9, 1.1, 0.1],
    metadata={"source": "notebook"},
)

docs.insert(
    properties={"title": "Gamma", "body": "second cluster"},
    vector=[8.0, 8.0, 0.0],
    metadata={"source": "notebook"},
)

submission = docs.cluster(
    near_vector=[1.0, 1.0, 0.0],
    limit=3,
    params={
        "k": 2,
        "submission_platform": "jupyter-notebook",
    },
)

submission.workload_id
submission.task_id
```

Fetch the worker result:

```python
from celery.result import AsyncResult
from app.celery_app import celery_app

task = AsyncResult(submission.task_id, app=celery_app)
task.get(timeout=60)
```

## Dashboard

Open:

```text
http://localhost:8502
```

What it shows:

- Job status
- Wall time and CPU time
- RSS memory before and after execution
- Submission platform and runtime platform
- Stored cluster plots
- Job details page with individual cluster members

## Worker Behavior

- Cluster workloads currently run in the worker with `scikit-learn`
- PySpark jobs run in the worker container in `local[*]` mode
- The dashboard will show the actual runtime platform used by the worker

## Stop

```bash
docker compose down
```

## Useful Files

- Tasks: [`app/tasks.py`](/Users/sourabhdattawad/cursor/dotproduct/app/tasks.py)
- Compose: [`docker-compose.yml`](/Users/sourabhdattawad/cursor/dotproduct/docker-compose.yml)
- Dashboard: [`dashboard/app.py`](/Users/sourabhdattawad/cursor/dotproduct/dashboard/app.py)
- Weaviate patch: [`vendor/weaviate-python-client/weaviate/collections/collection/sync.py`](/Users/sourabhdattawad/cursor/dotproduct/vendor/weaviate-python-client/weaviate/collections/collection/sync.py)
