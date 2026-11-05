"use client";

import AppNavigation from "../../components/AppNavigation";
import PortfolioSummary from "../../components/PortfolioSummary";
import { useActiveJobData } from "../../lib/useActiveJob";

type Holding = {
  symbol: string;
  quantity: number;
  average_buy_price: number;
  current_price?: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
};

export default function PortfolioPage() {
  const { jobId, job, error, loading } = useActiveJobData();
  const context = job?.insight?.raw_json.context_data as
    | {
        portfolio_profile?: { holdings?: Holding[] };
        deterministic_analytics?: {
          holdings_attribution?: { stock_attributions?: Holding[] };
        };
      }
    | undefined;
  const holdings =
    context?.deterministic_analytics?.holdings_attribution?.stock_attributions ??
    context?.portfolio_profile?.holdings ??
    [];

  return (
    <main className="app-shell">
      <AppNavigation />
      <div className="page-content">
        <div className="page-title">
          <p className="eyebrow">Portfolio data snapshot</p>
          <h1>Portfolio details</h1>
          <p className="muted">Holdings and valuation from the active persisted job.</p>
        </div>
        {loading && <div className="empty-panel">Loading active portfolio…</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!loading && !error && !jobId && <div className="empty-panel">Run a portfolio analysis to load holdings.</div>}
        {job && (
          <>
            <div className="job-strip"><span>Job <code>{job.job_id}</code></span><span>Status: {job.status.replaceAll("_", " ")}</span></div>
            {job.insight && <PortfolioSummary job={job} />}
            {holdings.length ? (
              <section className="panel table-scroll">
                <table className="data-table">
                  <thead><tr><th>Symbol</th><th>Quantity</th><th>Average buy</th><th>Current price</th><th>Current value</th><th>Unrealized P&amp;L</th></tr></thead>
                  <tbody>
                    {holdings.map((holding) => (
                      <tr key={holding.symbol}>
                        <td>{holding.symbol}</td>
                        <td>{holding.quantity}</td>
                        <td>{currency(holding.average_buy_price)}</td>
                        <td>{currency(holding.current_price)}</td>
                        <td>{currency(holding.current_value)}</td>
                        <td>{currency(holding.unrealized_pnl)} ({holding.unrealized_pnl_pct?.toFixed(2) ?? "—"}%)</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ) : (
              <div className="empty-panel">{job.empty_state?.message ?? "No holdings were included in this job snapshot."}</div>
            )}
          </>
        )}
      </div>
    </main>
  );
}

function currency(value: number | undefined) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value)
    : "—";
}
