"use client";

import AppNavigation from "../../components/AppNavigation";
import RecommendationFeed from "../../components/RecommendationFeed";
import { useActiveJobData } from "../../lib/useActiveJob";

export default function InsightsPage() {
  const { jobId, job, error, loading } = useActiveJobData();
  return (
    <main className="app-shell">
      <AppNavigation />
      <div className="page-content">
        <div className="page-title">
          <p className="eyebrow">Saved output</p>
          <h1>Insights</h1>
          <p className="muted">Recommendation cards persisted for the active job.</p>
        </div>
        {loading && <div className="empty-panel">Loading active job…</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!loading && !error && !jobId && (
          <div className="empty-panel">Run a portfolio analysis from the dashboard to populate this feed.</div>
        )}
        {job && (
          <>
            <div className="job-strip"><span>Job <code>{job.job_id}</code></span><span>Status: {job.status.replaceAll("_", " ")}</span></div>
            <RecommendationFeed cards={job.recommendations} />
          </>
        )}
      </div>
    </main>
  );
}
