import pandas as pd
import numpy as np

def calculate_benchmark_metrics(
    portfolio_daily_returns: pd.Series,
    nifty_daily_returns: pd.Series,
    vix_latest_value: float = None,
    risk_free_rate_annual: float = 0.065 # 6.5% standard Indian RBI repo / 10y G-sec rate
) -> dict:
    """
    Calculates Beta, Alpha, Correlation against Nifty 50 (^NSEI) and compares
    portfolio annualized volatility against India VIX (^INDIAVIX).
    """
    if portfolio_daily_returns.empty or nifty_daily_returns.empty:
        return {"error": "Insufficient return series for benchmark comparison"}

    # Align the series by index to ensure matching dates
    combined = pd.concat([portfolio_daily_returns, nifty_daily_returns], axis=1, join='inner').dropna()
    if len(combined) < 2:
        return {"error": "Not enough overlapping daily data points between portfolio and benchmark"}

    port_ret = combined.iloc[:, 0]
    bench_ret = combined.iloc[:, 1]

    # Covariance and Variance
    cov_matrix = np.cov(port_ret, bench_ret)
    cov = cov_matrix[0, 1]
    bench_var = np.var(bench_ret, ddof=1)

    beta = cov / bench_var if bench_var > 1e-9 else 1.0

    # Correlation
    corr = float(np.corrcoef(port_ret, bench_ret)[0, 1]) if len(port_ret) > 1 else 1.0

    # Annualized Returns (252 trading days)
    port_annual_return = float(port_ret.mean() * 252)
    bench_annual_return = float(bench_ret.mean() * 252)

    # Jensen's Alpha: R_p - (R_f + Beta * (R_m - R_f))
    expected_return = risk_free_rate_annual + beta * (bench_annual_return - risk_free_rate_annual)
    alpha = port_annual_return - expected_return

    # Annualized Volatilities
    port_annual_vol = float(port_ret.std(ddof=1) * np.sqrt(252))
    bench_annual_vol = float(bench_ret.std(ddof=1) * np.sqrt(252))

    vix_comparison = {}
    if vix_latest_value is not None and vix_latest_value > 0:
        vix_comparison = {
            "india_vix_level": round(float(vix_latest_value), 2),
            "portfolio_vol_vs_vix": round((port_annual_vol * 100) - float(vix_latest_value), 2),
            "vix_regime": "High Market Fear (>20)" if vix_latest_value > 20 else (
                "Moderate Volatility (15-20)" if vix_latest_value >= 15 else "Low Volatility Calm (<15)"
            )
        }

    return {
        "beta": round(float(beta), 2),
        "alpha_pct": round(float(alpha * 100), 2),
        "correlation_with_nifty": round(corr, 2),
        "portfolio_annualized_volatility_pct": round(port_annual_vol * 100, 2),
        "nifty_annualized_volatility_pct": round(bench_annual_vol * 100, 2),
        "relative_performance_pct": round((port_annual_return - bench_annual_return) * 100, 2),
        "risk_characterization": "Aggressive / High Beta (>1.2)" if beta > 1.2 else (
            "Defensive / Low Beta (<0.8)" if beta < 0.8 else "Market-Aligned (0.8 - 1.2)"
        ),
        "vix_comparison": vix_comparison
    }

