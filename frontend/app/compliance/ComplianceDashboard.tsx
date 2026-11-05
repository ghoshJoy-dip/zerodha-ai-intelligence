"use client";

import AppNavigation from "../../components/AppNavigation";
import { useActiveJobData } from "../../lib/useActiveJob";

type ComplianceMetadata = {
  prompt_version?: string;
  model_version?: string;
};

export default function ComplianceDashboard() {
  const { jobId, job, audit, error, loading } = useActiveJobData();
  const raw = job?.insight?.raw_json;
  const insightAudit = audit?.events.find((event) => event.event_type === "insight_generation");
  const parameters = insightAudit?.parameters;
  const metadata = (
    parameters?.compliance_metadata ?? raw?.compliance_metadata
  ) as ComplianceMetadata | undefined;
  const context = parameters?.data_snapshot ?? raw?.context_data;
  const validationResult = parameters?.validation_result;
  const validationReason =
    parameters?.validation_reason ?? job?.insight?.validation_reason;
  return (
    <main className="app-shell">
      <AppNavigation />
      <div className="page-content">
        <div className="page-title">
          <p className="eyebrow">Governance record</p>
          <h1>Compliance</h1>
          <p className="muted">Prompt/model metadata, persisted context snapshot, validation, and job audit.</p>
        </div>
        {loading && <div className="empty-panel">Loading compliance record…</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!loading && !error && !jobId && <div className="empty-panel">Run a portfolio analysis to create a compliance record.</div>}
        {job && (
          <>
            <div className="job-strip"><span>Job <code>{job.job_id}</code></span><span>Status: {job.status.replaceAll("_", " ")}</span></div>
            <div className="summary-grid">
              <Metric label="Prompt version" value={metadata?.prompt_version ?? "Not recorded for this job"} />
              <Metric label="Model version" value={metadata?.model_version ?? "Not recorded for this job"} />
              <Metric label="Insight validation" value={typeof validationResult === "boolean" ? validationResult ? "Passed" : "Flagged" : job.insight?.is_validated ? "Passed" : job.insight ? "Flagged" : "No insight"} />
              <Metric label="Validation reason" value={typeof validationReason === "string" ? validationReason : "—"} />
              <Metric label="Audit events" value={String(audit?.events.length ?? 0)} />
            </div>
            <section className="panel">
              <div className="section-heading"><div><p className="eyebrow">Persisted input</p><h2>Data snapshot for this job</h2></div></div>
              <pre className="json-snapshot">{JSON.stringify(context ?? { message: "No persisted context snapshot for this job." }, null, 2)}</pre>
            </section>
            <section className="panel">
              <div className="section-heading"><div><p className="eyebrow">Audit trail</p><h2>Recorded job events</h2></div></div>
              <ul className="audit-list">
                {audit?.events.map((event) => (
                  <li key={event.id}>
                    <span className="status-pill">{event.status ?? event.event_type}</span>
                    <div><strong>{event.tool_name ?? event.event_type}</strong><p>{event.description ?? event.error_message ?? "—"}</p></div>
                    <time>{new Date(event.created_at).toLocaleString()}</time>
                  </li>
                ))}
              </ul>
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
