"use client";

import AppNavigation from "../../components/AppNavigation";
import { useActiveJobData } from "../../lib/useActiveJob";

export default function OperationsDashboard() {
  const { jobId, job, audit, error, loading } = useActiveJobData();
  const metrics = audit?.operations;
  return (
    <main className="app-shell">
      <AppNavigation />
      <div className="page-content">
        <div className="page-title">
          <p className="eyebrow">Operational telemetry</p>
          <h1>Job operations</h1>
          <p className="muted">Metrics are scoped to this job and read from jobs, audit_events, and feedback.</p>
        </div>
        {loading && <div className="empty-panel">Loading job telemetry…</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!loading && !error && !jobId && <div className="empty-panel">Run a portfolio analysis to inspect its operational data.</div>}
        {job && audit && (
          <>
            <div className="job-strip">
              <span>Job <code>{job.job_id}</code></span>
              <span>Status: {job.status.replaceAll("_", " ")}</span>
              <span>Created {new Date(job.job.created_at).toLocaleString()}</span>
            </div>
            <div className="summary-grid">
              <Metric label="Audit events" value={String(metrics?.event_count ?? 0)} />
              <Metric label="Recorded failures" value={String(metrics?.failed_event_count ?? 0)} />
              <Metric label="Event failure rate" value={`${metrics?.failure_rate_pct ?? 0}%`} />
              <Metric label="Average MCP/tool latency" value={metrics?.average_latency_ms == null ? "Not recorded" : `${metrics.average_latency_ms} ms`} />
              <Metric label="Feedback rows" value={String(metrics?.feedback.total ?? 0)} />
            </div>
            <section className="panel">
              <div className="section-heading"><div><p className="eyebrow">Feedback table</p><h2>Feedback by action</h2></div></div>
              <div className="feedback-trends">
                {["thumbs_up", "thumbs_down", "accepted", "dismissed"].map((action) => (
                  <Metric key={action} label={action.replaceAll("_", " ")} value={String(metrics?.feedback.by_action[action] ?? 0)} />
                ))}
              </div>
            </section>
            <section className="panel">
              <div className="section-heading"><div><p className="eyebrow">Audit events</p><h2>Pipeline activity</h2></div></div>
              <div className="table-scroll">
                <table className="data-table">
                  <thead><tr><th>Time</th><th>Event / tool</th><th>Status</th><th>Latency</th><th>Description</th></tr></thead>
                  <tbody>
                    {audit.events.map((event) => (
                      <tr key={event.id}>
                        <td>{new Date(event.created_at).toLocaleTimeString()}</td>
                        <td>{event.tool_name ?? event.event_type}</td>
                        <td>{event.status ?? "—"}</td>
                        <td>{event.latency_ms == null ? "—" : `${event.latency_ms} ms`}</td>
                        <td>{event.description ?? event.error_message ?? "—"}</td>
                      </tr>
                    ))}
                    {audit.events.length === 0 && <tr><td colSpan={5}>No audit events recorded for this job.</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric-tile"><span>{label}</span><strong>{value}</strong></div>;
}
