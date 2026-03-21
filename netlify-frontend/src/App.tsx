const metrics = [
  { label: "Collections", value: "12", delta: "+3 active" },
  { label: "Embedded Docs", value: "18.4K", delta: "+1.2K this week" },
  { label: "Cluster Runs", value: "247", delta: "94% completed" },
  { label: "Anomalies", value: "19", delta: "4 require review" },
];

const modules = [
  {
    title: "Semantic Search",
    eyebrow: "Retrieval",
    body: "Explore nearest-neighbor results with confidence overlays and document previews built for embeddings-first workflows.",
  },
  {
    title: "Classification",
    eyebrow: "Decisioning",
    body: "Train lightweight labeling flows from vectorized examples and inspect confidence drift before shipping a rule.",
  },
  {
    title: "Clustering",
    eyebrow: "Discovery",
    body: "Surface structural patterns in large vector collections and inspect cluster composition with analyst-friendly summaries.",
  },
  {
    title: "Anomaly Detection",
    eyebrow: "Monitoring",
    body: "Flag outliers, compare suspicious records, and route follow-up investigations from one console.",
  },
];

const jobs = [
  { id: "9fd2a0ce", collection: "SupportTickets", status: "Completed", runtime: "3.2s" },
  { id: "4c18f1b2", collection: "ProductCatalog", status: "Running", runtime: "11.8s" },
  { id: "ad73bb41", collection: "RevenueNotes", status: "Queued", runtime: "-" },
];

function App() {
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
          <a className="ghost-link" href="#modules">
            View Modules
          </a>
        </nav>

        <div className="hero-grid">
          <section className="hero-copy">
            <p className="kicker">Embedding Intelligence Console</p>
            <h1>Separate frontend, ready for Netlify.</h1>
            <p className="hero-text">
              This deployment is a standalone web UI for Dotproduct. It mirrors the product surface
              without depending on Streamlit, Celery, Redis, or Weaviate at build time.
            </p>
            <div className="hero-actions">
              <a className="primary-link" href="#dashboard">
                Open Preview
              </a>
              <a className="secondary-link" href="#deploy">
                Deployment Notes
              </a>
            </div>
          </section>

          <section className="hero-panel" id="dashboard">
            <div className="panel-header">
              <span className="dot live" />
              <span>Console Snapshot</span>
            </div>
            <div className="heatmap">
              <div className="heat heat-a" />
              <div className="heat heat-b" />
              <div className="heat heat-c" />
            </div>
            <div className="score-row">
              <div>
                <p className="muted">Retrieval quality</p>
                <strong>0.92 cosine</strong>
              </div>
              <div>
                <p className="muted">Runtime profile</p>
                <strong>Stable</strong>
              </div>
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

        <section className="modules" id="modules">
          <div className="section-heading">
            <p className="kicker">Capability Map</p>
            <h2>Product modules exposed in the frontend shell.</h2>
          </div>
          <div className="module-grid">
            {modules.map((module) => (
              <article className="module-card" key={module.title}>
                <span>{module.eyebrow}</span>
                <h3>{module.title}</h3>
                <p>{module.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="split-layout">
          <article className="console-card">
            <div className="section-heading compact">
              <p className="kicker">Workload Feed</p>
              <h2>Recent runs</h2>
            </div>
            <div className="job-list">
              {jobs.map((job) => (
                <div className="job-row" key={job.id}>
                  <div>
                    <strong>{job.id}</strong>
                    <p>{job.collection}</p>
                  </div>
                  <div>
                    <span className={`pill ${job.status.toLowerCase()}`}>{job.status}</span>
                    <p>{job.runtime}</p>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="console-card">
            <div className="section-heading compact">
              <p className="kicker">Integration State</p>
              <h2>What this Netlify app is</h2>
            </div>
            <ul className="notes-list">
              <li>Deployable static frontend that Netlify can build from GitHub.</li>
              <li>Good for product demos, landing flow, and future API-driven UI.</li>
              <li>Separate from the Python backend stack already in this repository.</li>
              <li>Ready to connect to real APIs once backend endpoints exist.</li>
            </ul>
          </article>
        </section>

        <section className="deploy-card" id="deploy">
          <div className="section-heading compact">
            <p className="kicker">Deploy</p>
            <h2>Netlify configuration</h2>
          </div>
          <p>
            Netlify should use the repo root, with <code>netlify.toml</code> pointing build base
            to <code>netlify-frontend</code>. No backend services are required for the build.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
