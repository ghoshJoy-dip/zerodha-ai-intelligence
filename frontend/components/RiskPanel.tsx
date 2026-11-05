import type { JobResult } from "../lib/api";

type Analytics = {
  sector_concentration?: {
    hhi_concentration_score?: number;
    top_sector?: string;
    top_sector_weight_pct?: number;
  };
  drawdown_and_volatility?: {
    max_drawdown_pct?: number;
    annualized_volatility_pct?: number;
  };
  benchmark_comparison?: {
    beta?: number;
    alpha_pct?: number;
    benchmark_name?: string;
    vix_value?: number;
  };
};

export default function RiskPanel({ job }: { job: JobResult }) {
  const context = job.insight?.raw_json.context_data as
    | { deterministic_analytics?: Analytics }
    | undefined;
  const metrics = context?.deterministic_analytics;
  const concentration = metrics?.sector_concentration;
  const risk = metrics?.drawdown_and_volatility;
  const benchmark = metrics?.benchmark_comparison;
  const hhi = concentration?.hhi_concentration_score;

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Deterministic analytics</p>
          <h2>Risk overview</h2>
        </div>
        <span className="status-pill">From this job</span>
      </div>
      <div className="risk-grid">
        <div className="risk-metric">
          <div className="risk-line"><span>HHI concentration</span><strong>{format(hhi, 4)}</strong></div>
          <div className="meter"><span style={{ width: `${Math.min(100, Math.max(0, (hhi ?? 0) * 100))}%` }} /></div>
          <small>{concentration?.top_sector ?? "Top sector unavailable"} · {format(concentration?.top_sector_weight_pct)}% exposure</small>
        </div>
        <RiskMetric label="Maximum drawdown" value={`${format(risk?.max_drawdown_pct)}%`} />
        <RiskMetric label="Annualized volatility" value={`${format(risk?.annualized_volatility_pct)}%`} />
        <RiskMetric label={`Beta${benchmark?.benchmark_name ? ` vs ${benchmark.benchmark_name}` : ""}`} value={format(benchmark?.beta)} />
        <RiskMetric label="Alpha" value={`${format(benchmark?.alpha_pct)}%`} />
      </div>
    </section>
  );
}

function RiskMetric({ label, value }: { label: string; value: string }) {
  return <div className="risk-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function format(value: number | undefined, decimals = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(decimals) : "—";
}
