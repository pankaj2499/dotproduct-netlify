import { useState } from "react";

type ViewId =
  | "overview"
  | "clustering"
  | "classification"
  | "semantic-search"
  | "anomaly-detection"
  | "workers-load"
  | "pricing"
  | "deployment";

const navGroups: Array<{
  title: string;
  items: Array<{ id: ViewId; label: string; badge?: string }>;
}> = [
  {
    title: "Console",
    items: [
      { id: "overview", label: "Project Overview" },
      { id: "workers-load", label: "Workers Load", badge: "Live" },
    ],
  },
  {
    title: "Workflows",
    items: [
      { id: "clustering", label: "Clustering", badge: "Ready" },
      { id: "classification", label: "Classification", badge: "Ready" },
      { id: "semantic-search", label: "Semantic Search", badge: "Production" },
      { id: "anomaly-detection", label: "Anomaly Detection", badge: "Production" },
    ],
  },
  {
    title: "Business",
    items: [
      { id: "pricing", label: "Pricing" },
      { id: "deployment", label: "Deployment" },
    ],
  },
];

const statCards = [
  { label: "Collections", value: "12", detail: "Stored vector groups" },
  { label: "Embedded Docs", value: "18.4K", detail: "Searchable objects" },
  { label: "Cluster Runs", value: "247", detail: "94% completed" },
  { label: "Anomalies", value: "19", detail: "4 require review" },
];

const dashboardCapabilities = [
  "Semantic similarity search over stored embeddings",
  "Classification workflow from labeled embeddings",
  "Clustering workflow with distribution and projection views",
  "Anomaly detection for outlier vectors",
  "Job status, runtime metrics, and detailed workload inspection",
];

const frontendPages = [
  { path: "dashboard/app.py", summary: "product console home and capability map" },
  { path: "dashboard/pages/2_Semantic_Search.py", summary: "cosine-similarity search" },
  { path: "dashboard/pages/3_Classification.py", summary: "logistic-regression classification" },
  { path: "dashboard/pages/4_Clustering.py", summary: "KMeans clustering exploration" },
  { path: "dashboard/pages/5_Anomaly_Detection.py", summary: "Isolation Forest outlier detection" },
  { path: "dashboard/pages/1_Job_Details.py", summary: "detailed workload drill-down" },
];

const workloadRows = [
  {
    id: "wrk-8f39d2",
    collection: "SupportTickets",
    algorithm: "kmeans",
    runtime: "celery-worker+scikit-learn",
    status: "Completed",
    duration: "3.2s",
  },
  {
    id: "wrk-1ca812",
    collection: "ProductCatalog",
    algorithm: "classification",
    runtime: "celery-worker+scikit-learn",
    status: "Running",
    duration: "11.8s",
  },
  {
    id: "wrk-b2aa17",
    collection: "RevenueNotes",
    algorithm: "spark-dot-product",
    runtime: "worker local[*]",
    status: "Queued",
    duration: "-",
  },
];

const clusterBars = [
  { label: "Cluster 2", members: "268 members", width: "88%" },
  { label: "Cluster 0", members: "214 members", width: "72%" },
  { label: "Cluster 1", members: "187 members", width: "61%" },
  { label: "Cluster 3", members: "131 members", width: "43%" },
];

const clusterMembers = [
  {
    uuid: "2b4f8d0a",
    title: "Quarterly refund escalation summary",
    preview: "Customer refund tickets grouped by complaint vectors and policy friction language.",
  },
  {
    uuid: "3ca9701d",
    title: "Billing retention narrative",
    preview: "Retention-related embeddings tied to pricing objections and repeated downgrade intent.",
  },
  {
    uuid: "57df09e2",
    title: "Subscription downgrade intent",
    preview: "Users signaling downgrade likelihood after failed invoice retries or coupon exhaustion.",
  },
];

const classificationScores = [
  { label: "High Intent", probability: "71.0%" },
  { label: "Needs Review", probability: "19.0%" },
  { label: "Low Intent", probability: "10.0%" },
];

const pricingTiers = [
  {
    name: "Starter",
    price: "$29",
    note: "per workspace / month",
    features: ["Semantic Search", "Classification", "Single workspace", "Basic worker metrics"],
  },
  {
    name: "Team",
    price: "$149",
    note: "per workspace / month",
    features: ["Clustering console", "Anomaly reviews", "Shared job history", "Runtime platform visibility"],
  },
  {
    name: "Enterprise",
    price: "Custom",
    note: "annual plan",
    features: ["Dedicated deployment", "Private VM stack", "Advanced workload audit", "Priority support"],
  },
];

function App() {
  const [activeView, setActiveView] = useState<ViewId>("overview");
  const activeLabel =
    navGroups.flatMap((group) => group.items).find((item) => item.id === activeView)?.label ?? "Project Overview";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-mark">EL</span>
          <div>
            <strong>Eigenlake</strong>
            <span>Platform Console</span>
          </div>
        </div>

        {navGroups.map((group) => (
          <section className="nav-group" key={group.title}>
            <p className="nav-group-title">{group.title}</p>
            <div className="nav-list">
              {group.items.map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${activeView === item.id ? "active" : ""}`}
                  onClick={() => setActiveView(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  {item.badge ? <small>{item.badge}</small> : null}
                </button>
              ))}
            </div>
          </section>
        ))}

        <div className="sidebar-footer">
          <p className="nav-group-title">Stack</p>
          <div className="stack-chip-list">
            <span>Streamlit</span>
            <span>Celery</span>
            <span>Redis</span>
            <span>Weaviate</span>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <div className="breadcrumbs">app / Eigenlake / main</div>
            <h1>{activeLabel}</h1>
          </div>
          <div className="topbar-actions">
            <span className="header-pill">Production</span>
            <span className="header-pill muted">Frontend Shell</span>
          </div>
        </header>

        <main className="main-view">
          {activeView === "overview" && <ProjectOverview />}
          {activeView === "clustering" && <ClusteringView />}
          {activeView === "classification" && <ClassificationView />}
          {activeView === "semantic-search" && (
            <ProductionView
              title="Semantic Search"
              summary="The backend page already runs cosine-similarity search over stored vectors. This Netlify tab is reserved for the production API-backed search experience."
            />
          )}
          {activeView === "anomaly-detection" && (
            <ProductionView
              title="Anomaly Detection"
              summary="The backend page already scores outliers with Isolation Forest. This Netlify tab is reserved for the production anomaly review surface."
            />
          )}
          {activeView === "workers-load" && <WorkersLoadView />}
          {activeView === "pricing" && <PricingView />}
          {activeView === "deployment" && <DeploymentView />}
        </main>
      </div>
    </div>
  );
}

function ProjectOverview() {
  return (
    <div className="page-grid">
      <section className="hero-card span-2">
        <div className="section-label">Overview</div>
        <h2>Embedding intelligence for retrieval, classification, clustering, and anomaly review.</h2>
        <p>
          A structured product console with operational visibility, workflow surfaces, pricing, and
          deployment context in one place.
        </p>
      </section>

      <section className="stat-grid span-2">
        {statCards.map((card) => (
          <article className="stat-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">What It Shows</div>
          <h3>Product capabilities</h3>
        </div>
        <ul className="detail-list">
          {dashboardCapabilities.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Worker Behavior</div>
          <h3>Runtime platform types</h3>
        </div>
        <div className="mini-stack">
          <div className="mini-card">
            <span>Cluster workloads</span>
            <strong>scikit-learn worker</strong>
          </div>
          <div className="mini-card">
            <span>PySpark jobs</span>
            <strong>worker local[*] mode</strong>
          </div>
          <div className="mini-card">
            <span>Runtime visibility</span>
            <strong>actual runtime platform shown</strong>
          </div>
        </div>
      </article>

      <article className="panel span-2">
        <div className="panel-head">
          <div className="section-label">Frontend Pages</div>
          <h3>Core product sources mapped into the frontend shell</h3>
        </div>
        <div className="code-table">
          {frontendPages.map((item) => (
            <div className="code-row" key={item.path}>
              <code>{item.path}</code>
              <span>{item.summary}</span>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function ClusteringView() {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="panel-top">
          <div>
            <div className="section-label">Ready Workflow</div>
            <h3>Clustering</h3>
          </div>
          <div className="metric-strip">
            <div>
              <span>Vectors clustered</span>
              <strong>800</strong>
            </div>
            <div>
              <span>Inertia</span>
              <strong>173.42</strong>
            </div>
            <div>
              <span>Vector dim</span>
              <strong>1536</strong>
            </div>
          </div>
        </div>
        <p className="panel-copy">
          Modeled directly on `dashboard/pages/4_Clustering.py` where KMeans, PCA projection, and
          cluster member inspection happen.
        </p>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Distribution</div>
          <h3>KMeans summary</h3>
        </div>
        <div className="bar-list">
          {clusterBars.map((item) => (
            <div className="bar-row" key={item.label}>
              <div className="bar-top">
                <strong>{item.label}</strong>
                <span>{item.members}</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: item.width }} />
              </div>
            </div>
          ))}
        </div>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Projection</div>
          <h3>2D view</h3>
        </div>
        <div className="plot-surface">
          <span className="plot-point cyan" style={{ left: "16%", top: "22%" }} />
          <span className="plot-point cyan" style={{ left: "29%", top: "38%" }} />
          <span className="plot-point blue" style={{ left: "54%", top: "19%" }} />
          <span className="plot-point blue" style={{ left: "63%", top: "43%" }} />
          <span className="plot-point slate" style={{ left: "44%", top: "72%" }} />
          <span className="plot-point violet" style={{ left: "80%", top: "58%" }} />
        </div>
      </article>

      <article className="panel span-2">
        <div className="panel-head">
          <div className="section-label">Cluster Members</div>
          <h3>Inspect cluster 2</h3>
        </div>
        <div className="table-list">
          {clusterMembers.map((member) => (
            <div className="table-row" key={member.uuid}>
              <div className="table-main">
                <strong>{member.uuid}</strong>
                <h4>{member.title}</h4>
                <p>{member.preview}</p>
              </div>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function ClassificationView() {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="panel-top">
          <div>
            <div className="section-label">Ready Workflow</div>
            <h3>Classification</h3>
          </div>
          <div className="metric-strip">
            <div>
              <span>Objects with labels</span>
              <strong>1,126</strong>
            </div>
            <div>
              <span>Validation accuracy</span>
              <strong>89.0%</strong>
            </div>
            <div>
              <span>Classes</span>
              <strong>3</strong>
            </div>
          </div>
        </div>
        <p className="panel-copy">
          Modeled on `dashboard/pages/3_Classification.py` where Logistic Regression is trained and
          class probabilities are returned for new embeddings.
        </p>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Prediction</div>
          <h3>Embedding input</h3>
        </div>
        <div className="vector-box">
          0.18, -0.22, 0.71, 0.09, -0.14, 0.31, 0.52, -0.08, 0.63, 0.11...
        </div>
        <div className="prediction-banner">
          <span>Predicted label</span>
          <strong>High Intent</strong>
          <small>71.0% confidence</small>
        </div>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Probabilities</div>
          <h3>Ranked classes</h3>
        </div>
        <div className="score-list">
          {classificationScores.map((item) => (
            <div className="score-row" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.probability}</strong>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function ProductionView(props: { title: string; summary: string }) {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="section-label">In Production</div>
        <h3>{props.title}</h3>
        <p className="panel-copy">{props.summary}</p>
      </article>
    </div>
  );
}

function WorkersLoadView() {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="panel-top">
          <div>
            <div className="section-label">Workers Load</div>
            <h3>Job status, runtime metrics, and runtime platform</h3>
          </div>
          <div className="metric-strip">
            <div>
              <span>Total workloads</span>
              <strong>247</strong>
            </div>
            <div>
              <span>Completed</span>
              <strong>232</strong>
            </div>
            <div>
              <span>Failed</span>
              <strong>5</strong>
            </div>
          </div>
        </div>
        <p className="panel-copy">
          This tab stands in for the dashboard job details and workload snapshot screens. It is the
          operational view for worker output and runtime platform visibility.
        </p>
      </article>

      <article className="panel span-2">
        <div className="panel-head">
          <div className="section-label">Recent workloads</div>
          <h3>Live queue snapshot</h3>
        </div>
        <div className="workload-table">
          <div className="workload-header">
            <span>Workload</span>
            <span>Collection</span>
            <span>Algorithm</span>
            <span>Runtime</span>
            <span>Status</span>
            <span>Duration</span>
          </div>
          {workloadRows.map((row) => (
            <div className="workload-row" key={row.id}>
              <span>{row.id}</span>
              <span>{row.collection}</span>
              <span>{row.algorithm}</span>
              <span>{row.runtime}</span>
              <span className={`status-pill ${row.status.toLowerCase()}`}>{row.status}</span>
              <span>{row.duration}</span>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function PricingView() {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="section-label">Pricing</div>
        <h3>Commercial packaging for the console</h3>
        <p className="panel-copy">
          Added as a dedicated business tab so the frontend feels like a full platform rather than a
          single demo page.
        </p>
      </article>

      {pricingTiers.map((tier) => (
        <article className="panel span-1" key={tier.name}>
          <div className="panel-head">
            <div className="section-label">{tier.name}</div>
            <h3>{tier.price}</h3>
          </div>
          <p className="tier-note">{tier.note}</p>
          <ul className="detail-list">
            {tier.features.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}

function DeploymentView() {
  return (
    <div className="page-grid">
      <article className="panel span-2">
        <div className="section-label">Production Deployment</div>
        <h3>Single-VM runtime for the full application stack</h3>
        <p className="panel-copy">
          The deployed application depends on long-running services plus a shared SQLite metadata
          file: Streamlit, worker, Redis, Weaviate, and `/workspace/.data/dotproduct.sqlite3`.
          Because the application and worker share the same SQLite state, the correct deployment
          target is a single VM running Docker Compose.
        </p>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">Bundle</div>
          <h3>Prepared files</h3>
        </div>
        <ul className="detail-list">
          <li>`docker-compose.prod.yml`</li>
          <li>`deploy/Caddyfile`</li>
          <li>`scripts/start-dashboard.sh`</li>
          <li>`scripts/start-worker.sh`</li>
        </ul>
      </article>

      <article className="panel span-1">
        <div className="panel-head">
          <div className="section-label">VM Steps</div>
          <h3>Bring up the stack</h3>
        </div>
        <div className="command-block">
          <code>cat &gt; .env.prod &lt;&lt;'EOF'</code>
          <code>DOTPRODUCT_DOMAIN=your-domain.example.com</code>
          <code>OPENAI_API_KEY=</code>
          <code>EOF</code>
          <code>docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build</code>
        </div>
      </article>
    </div>
  );
}

export default App;
