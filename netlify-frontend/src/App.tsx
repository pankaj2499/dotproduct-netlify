import { useState } from "react";

type TabId = "clustering" | "classification" | "semantic-search" | "anomaly-detection";

const metrics = [
  { label: "Collections", value: "12", delta: "+3 active" },
  { label: "Embedded Docs", value: "18.4K", delta: "+1.2K this week" },
  { label: "Cluster Runs", value: "247", delta: "94% completed" },
  { label: "Anomalies", value: "19", delta: "4 require review" },
];

const tabs: Array<{ id: TabId; label: string; status: "ready" | "production" }> = [
  { id: "clustering", label: "Clustering", status: "ready" },
  { id: "classification", label: "Classification", status: "ready" },
  { id: "semantic-search", label: "Semantic Search", status: "production" },
  { id: "anomaly-detection", label: "Anomaly Detection", status: "production" },
];

const clusterBars = [
  { cluster: "Cluster 2", members: 268, width: "92%" },
  { cluster: "Cluster 0", members: 214, width: "74%" },
  { cluster: "Cluster 1", members: 187, width: "65%" },
  { cluster: "Cluster 3", members: 131, width: "44%" },
];

const clusterMembers = [
  {
    uuid: "2b4f8d0a",
    title: "Quarterly refund escalation summary",
    preview: "Customer refund tickets with repeated complaint vectors around policy friction.",
  },
  {
    uuid: "3ca9701d",
    title: "Billing retention narrative",
    preview: "Retention-related embeddings grouped with payment dispute language and pricing objections.",
  },
  {
    uuid: "57df09e2",
    title: "Subscription downgrade intent",
    preview: "Users signaling plan downgrade likelihood after failed invoice retries.",
  },
];

const classificationScores = [
  { label: "High Intent", probability: "71.0%" },
  { label: "Needs Review", probability: "19.0%" },
  { label: "Low Intent", probability: "10.0%" },
];

function App() {
  const [activeTab, setActiveTab] = useState<TabId>("clustering");

  return (
    <div className="shell">
      <div className="noise" aria-hidden="true" />
      <header className="hero">
        <nav className="topbar">
          <div className="brand">
            <span className="brand-mark">DP</span>
            <div>
              <p>Dotproduct</p>
              <span>Netlify Frontend</span>
            </div>
          </div>
          <a className="ghost-link" href="#workspace">
            Open Workspace
          </a>
        </nav>

        <div className="hero-grid">
          <section className="hero-copy">
            <p className="kicker">Embedding Intelligence Console</p>
            <h1>Tabbed frontend aligned to the product workflow.</h1>
            <p className="hero-text">
              The Netlify app now mirrors the dashboard structure directly. Clustering and
              Classification show live product-style output panels, while Semantic Search and
              Anomaly Detection are marked as in production.
            </p>
            <div className="hero-actions">
              <a className="primary-link" href="#workspace">
                Review Tabs
              </a>
              <a className="secondary-link" href="#status">
                Module Status
              </a>
            </div>
          </section>

          <section className="hero-panel">
            <div className="panel-header">
              <span className="dot live" />
              <span>Frontend Status</span>
            </div>
            <div className="status-stack" id="status">
              <div className="status-line">
                <span>Clustering</span>
                <strong>Ready</strong>
              </div>
              <div className="status-line">
                <span>Classification</span>
                <strong>Ready</strong>
              </div>
              <div className="status-line muted-line">
                <span>Semantic Search</span>
                <strong>In production</strong>
              </div>
              <div className="status-line muted-line">
                <span>Anomaly Detection</span>
                <strong>In production</strong>
              </div>
            </div>
            <div className="source-note">
              <p className="muted">Source parity</p>
              <strong>KMeans and Logistic Regression views mapped from the existing dashboard code.</strong>
            </div>
          </section>
        </div>
      </header>

      <main className="content">
        <section className="metrics" aria-label="Key metrics">
          {metrics.map((metric) => (
            <article className="metric-card" key={metric.label}>
              <p>{metric.label}</p>
              <strong>{metric.value}</strong>
              <span>{metric.delta}</span>
            </article>
          ))}
        </section>

        <section className="workspace" id="workspace">
          <div className="section-heading">
            <p className="kicker">Module Workspace</p>
            <h2>Tabs ordered for the product flow.</h2>
          </div>

          <div className="tab-row" role="tablist" aria-label="Dotproduct modules">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`tab-pill ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={activeTab === tab.id}
                type="button"
              >
                <span>{tab.label}</span>
                <small>{tab.status === "ready" ? "Ready" : "In production"}</small>
              </button>
            ))}
          </div>

          {activeTab === "clustering" && <ClusteringTab />}
          {activeTab === "classification" && <ClassificationTab />}
          {activeTab === "semantic-search" && (
            <ProductionTab
              title="Semantic Search"
              description="This tab is in production next. The backend page already uses cosine similarity over stored vectors, and this frontend slot is reserved for the API-backed search experience."
            />
          )}
          {activeTab === "anomaly-detection" && (
            <ProductionTab
              title="Anomaly Detection"
              description="This tab is in production next. The backend page already uses Isolation Forest to score outliers, and this frontend slot is reserved for the production anomaly review screen."
            />
          )}
        </section>
      </main>
    </div>
  );
}

function ClusteringTab() {
  return (
    <section className="tab-panel">
      <div className="panel-topline">
        <div>
          <p className="kicker">Ready Module</p>
          <h3>Clustering output</h3>
        </div>
        <div className="compact-stats">
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

      <div className="tab-grid">
        <article className="console-card tall-card">
          <div className="section-heading compact">
            <p className="kicker">Cluster Distribution</p>
            <h2>KMeans summary</h2>
          </div>
          <div className="bar-list">
            {clusterBars.map((bar) => (
              <div className="bar-row" key={bar.cluster}>
                <div className="bar-labels">
                  <strong>{bar.cluster}</strong>
                  <span>{bar.members} members</span>
                </div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: bar.width }} />
                </div>
              </div>
            ))}
          </div>
          <div className="plot-box">
            <div className="plot-header">
              <span>2D Projection</span>
              <small>PCA view</small>
            </div>
            <div className="plot-grid">
              <span className="plot-point cyan" style={{ left: "18%", top: "22%" }} />
              <span className="plot-point cyan" style={{ left: "30%", top: "40%" }} />
              <span className="plot-point orange" style={{ left: "58%", top: "24%" }} />
              <span className="plot-point orange" style={{ left: "68%", top: "42%" }} />
              <span className="plot-point red" style={{ left: "48%", top: "70%" }} />
              <span className="plot-point violet" style={{ left: "82%", top: "64%" }} />
            </div>
          </div>
        </article>

        <article className="console-card tall-card">
          <div className="section-heading compact">
            <p className="kicker">Cluster Members</p>
            <h2>Inspect cluster 2</h2>
          </div>
          <div className="table-list">
            {clusterMembers.map((member) => (
              <div className="table-row" key={member.uuid}>
                <div>
                  <strong>{member.uuid}</strong>
                  <h4>{member.title}</h4>
                  <p>{member.preview}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="code-note">
            <p className="muted">Mapped from existing code</p>
            <strong>`dashboard/pages/4_Clustering.py` uses KMeans, distribution stats, PCA projection, and member inspection.</strong>
          </div>
        </article>
      </div>
    </section>
  );
}

function ClassificationTab() {
  return (
    <section className="tab-panel">
      <div className="panel-topline">
        <div>
          <p className="kicker">Ready Module</p>
          <h3>Classification output</h3>
        </div>
        <div className="compact-stats">
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

      <div className="tab-grid">
        <article className="console-card">
          <div className="section-heading compact">
            <p className="kicker">Prediction</p>
            <h2>Embedding to classify</h2>
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

        <article className="console-card">
          <div className="section-heading compact">
            <p className="kicker">Probability Table</p>
            <h2>Class ranking</h2>
          </div>
          <div className="score-table">
            {classificationScores.map((score) => (
              <div className="score-row-table" key={score.label}>
                <span>{score.label}</span>
                <strong>{score.probability}</strong>
              </div>
            ))}
          </div>
          <div className="code-note">
            <p className="muted">Mapped from existing code</p>
            <strong>`dashboard/pages/3_Classification.py` trains Logistic Regression and returns ranked class probabilities.</strong>
          </div>
        </article>
      </div>
    </section>
  );
}

function ProductionTab(props: { title: string; description: string }) {
  return (
    <section className="tab-panel">
      <article className="production-card">
        <p className="kicker">In Production</p>
        <h3>{props.title}</h3>
        <p>{props.description}</p>
      </article>
    </section>
  );
}

export default App;
