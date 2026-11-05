"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AppNavigation from "../components/AppNavigation";
import PortfolioSummary from "../components/PortfolioSummary";
import RecommendationFeed from "../components/RecommendationFeed";
import RiskPanel from "../components/RiskPanel";
import WorkflowStatus from "../components/WorkflowStatus";
import { useActiveJobId } from "../lib/useActiveJob";
import {
  getJobResult,
  refreshMarket,
  saveActiveJob,
  startPortfolioAnalysis,
  type JobResult,
} from "../lib/api";

const timeframes = [
  { value: "1mo", label: "1 month" },
  { value: "3mo", label: "3 months" },
  { value: "6mo", label: "6 months" },
  { value: "1y", label: "1 year" },
];

export default function Home() {
  const [userId, setUserId] = useState("");
  const [timeframe, setTimeframe] = useState("3mo");
  const storedJobId = useActiveJobId();
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);
  const jobId = submittedJobId ?? storedJobId;
  const [job, setJob] = useState<JobResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshBusy, setRefreshBusy] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState("");
  const [error, setError] = useState("");

  const loadJob = useCallback(async (id: string) => {
    try {
      const result = await getJobResult(id);
      setJob(result);
      setError("");
      return result;
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Could not load job.");
      return null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      const result = await loadJob(jobId);
      if (!active || !result) return;
      if (!["completed", "failed", "empty_portfolio"].includes(result.status)) {
        timer = setTimeout(poll, 1800);
      }
    };
    void poll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [jobId, loadJob]);

  async function submitAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setJob(null);
    setRefreshMessage("");
    setBusy(true);
    try {
      const submission = await startPortfolioAnalysis(userId.trim(), timeframe);
      saveActiveJob(submission.job_id, userId.trim(), timeframe);
      setSubmittedJobId(submission.job_id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Could not submit analysis.");
    } finally {
      setBusy(false);
    }
  }

  async function triggerManualRefresh() {
    setRefreshBusy(true);
    setRefreshMessage("");
    setError("");
    try {
      const result = await refreshMarket(userId.trim(), timeframe);
      const freshAt = result.freshness_timestamp_utc;
      setRefreshMessage(
        typeof freshAt === "string"
          ? `Market data refreshed at ${new Date(freshAt).toLocaleString()}.`
          : "Market data refresh completed.",
      );
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Market refresh failed.");
    } finally {
      setRefreshBusy(false);
    }
  }

  const insight = job?.insight?.raw_json ?? {};
  const insightText = typeof insight.explanation === "string" ? insight.explanation : "";
  const insightRationale = typeof insight.rationale === "string" ? insight.rationale : "";

  return (
    <main className="app-shell">
      <AppNavigation />
      <div className="page-content">
        <section className="hero-panel">
          <div>
            <p className="eyebrow">Portfolio intelligence</p>
            <h1>Understand your portfolio, one job at a time.</h1>
            <p className="muted">Analysis, risk metrics, and recommendations are linked to the same persisted job.</p>
          </div>
          <form className="analysis-form" onSubmit={submitAnalysis}>
            <label>
              Sample portfolio user ID
              <input
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                placeholder="Enter a sample portfolio user ID"
                required
              />
            </label>
            <div className="control-row">
              <label>
                Portfolio source
                <select value="sample" disabled aria-label="Portfolio source">
                  <option value="sample">Sample data</option>
                  <option disabled>Kite Sandbox — coming soon</option>
                  <option disabled>Kite Live — coming soon</option>
                </select>
              </label>
              <label>
                Timeframe
                <select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}>
                  {timeframes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            </div>
            <div className="button-row">
              <button className="button button-primary" disabled={busy || !userId.trim()}>
                {busy ? "Submitting…" : "Run portfolio analysis"}
              </button>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => void triggerManualRefresh()}
                disabled={refreshBusy || !userId.trim()}
                title="Manual refresh starts a separate MCP session. It does not run on a timer."
              >
                {refreshBusy ? "Refreshing…" : "Refresh market data"}
              </button>
            </div>
            <p className="subtle">Refresh is manual only; no background refresh timer is enabled.</p>
            {refreshMessage && <p className="success-message" role="status">{refreshMessage}</p>}
          </form>
        </section>

        {error && <div className="error-banner" role="alert">{error}</div>}
        {!jobId && !job && (
          <div className="empty-panel">
            Submit an analysis to create a job and load persisted portfolio data.
          </div>
        )}
        {jobId && !job && !error && <div className="empty-panel">Loading job {jobId}…</div>}
        {job && (
          <>
            <section className="job-strip">
              <span>Active job <code>{job.job_id}</code></span>
              <span>Created {new Date(job.job.created_at).toLocaleString()}</span>
              <Link href="/portfolio">Portfolio details</Link>
              <Link href="/insights">All insight cards</Link>
            </section>
            <WorkflowStatus status={job.status} />
            {job.status === "empty_portfolio" || job.empty_state ? (
              <div className="empty-panel">
                <h2>{job.empty_state?.message ?? "No holdings found in this account."}</h2>
                <p>{job.empty_state?.fallback_action ?? "Choose Sample data and submit a new analysis."}</p>
              </div>
            ) : job.insight ? (
              <>
                <PortfolioSummary job={job} />
                <RiskPanel job={job} />
                <section className="panel insight-panel">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">{job.insight.category}</p>
                      <h2>{job.insight.title}</h2>
                    </div>
                    <span className={`validation-chip ${job.insight.is_validated ? "valid" : "flagged"}`}>
                      {job.insight.is_validated ? "Validated" : "Flagged"}
                    </span>
                  </div>
                  <p>{insightText || "No explanation was returned for this insight."}</p>
                  {insightRationale && <p className="muted mt-3">{insightRationale}</p>}
                  {typeof insight.disclaimer === "string" && <p className="disclaimer">{insight.disclaimer}</p>}
                </section>
                <RecommendationFeed cards={job.recommendations} />
              </>
            ) : job.status === "completed" ? (
              <div className="empty-panel">The job completed without a persisted insight record.</div>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
