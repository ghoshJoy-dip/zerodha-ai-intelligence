import type { JobResult } from "../lib/api";

type Context = {
  portfolio_profile?: {
    portfolio_source?: string;
    timeframe?: string;
    total_invested_value?: number;
    total_current_value?: number;
    overall_unrealized_pnl?: number;
    overall_unrealized_pnl_pct?: number;
    holdings?: { symbol: string; quantity: number; average_buy_price: number }[];
  };
  deterministic_analytics?: {
    holdings_attribution?: {
      total_invested_value?: number;
      total_current_value?: number;
      overall_unrealized_pnl?: number;
      overall_unrealized_pnl_pct?: number;
      top_mover_gainer?: { symbol: string; "1d_change_pct": number } | null;
      top_mover_laggard?: { symbol: string; "1d_change_pct": number } | null;
    };
  };
};

function money(value: number | undefined) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(value)
    : "—";
}

export default function PortfolioSummary({ job }: { job: JobResult }) {
  const context = (job.insight?.raw_json.context_data ?? {}) as Context;
  const profile = context.portfolio_profile;
  const attribution = context.deterministic_analytics?.holdings_attribution;
  const pnl = attribution?.overall_unrealized_pnl_pct ?? profile?.overall_unrealized_pnl_pct;
  const holdings = profile?.holdings ?? [];

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Portfolio summary</p>
          <h2>Sample portfolio</h2>
        </div>
        <span className="status-pill">Sample · {profile?.timeframe ?? "—"}</span>
      </div>
      <div className="summary-grid">
        <Metric label="Current value" value={money(attribution?.total_current_value ?? profile?.total_current_value)} />
        <Metric label="Invested" value={money(attribution?.total_invested_value ?? profile?.total_invested_value)} />
        <Metric
          label="Unrealized P&L"
          value={pnl === undefined ? "—" : `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}%`}
          positive={pnl === undefined ? undefined : pnl >= 0}
        />
        <Metric label="Holdings" value={String(holdings.length)} />
      </div>
      <div className="movers-grid">
        <p>
          Top daily contributor <strong>{attribution?.top_mover_gainer?.symbol ?? "—"}</strong>
          {attribution?.top_mover_gainer && ` (${attribution.top_mover_gainer["1d_change_pct"]}%)`}
        </p>
        <p>
          Lowest daily contributor <strong>{attribution?.top_mover_laggard?.symbol ?? "—"}</strong>
          {attribution?.top_mover_laggard && ` (${attribution.top_mover_laggard["1d_change_pct"]}%)`}
        </p>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong className={positive === undefined ? "" : positive ? "positive" : "negative"}>
        {value}
      </strong>
    </div>
  );
}
