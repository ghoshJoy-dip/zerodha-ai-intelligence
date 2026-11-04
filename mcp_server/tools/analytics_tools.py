import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from analytics.exposure_metrics import calculate_sector_concentration, calculate_holdings_attribution
from analytics.risk_alerts import calculate_drawdown_and_volatility
from analytics.sector_analysis import analyze_sector_drift_and_profile
from analytics.benchmark_comparison import calculate_benchmark_metrics

def compute_portfolio_analytics(holdings: list, market_data: dict) -> dict:
    """
    Wraps all deterministic analytics computations into a single callable MCP tool.
    Computes HHI concentration, attribution, sector drift, drawdown/volatility, and benchmark metrics.
    """
    if not holdings:
        return {"error": "No holdings provided"}

    # 1. Build portfolio DataFrame
    portfolio_rows = []
    for item in holdings:
        sym = item.get("symbol")
        qty = float(item.get("quantity", 0))
        buy_px = float(item.get("average_buy_price", 0))
        sec = item.get("sector", "Other")

        mkt = market_data.get(sym, {})
        curr_px = float(mkt.get("latest_close", buy_px))
        curr_val = qty * curr_px
        invested_val = qty * buy_px

        portfolio_rows.append({
            "symbol": sym,
            "sector": sec,
            "quantity": qty,
            "average_buy_price": buy_px,
            "current_price": curr_px,
            "current_value": curr_val,
            "invested_value": invested_val
        })

    portfolio_df = pd.DataFrame(portfolio_rows)

    # 2. Exposure & Concentration
    concentration = calculate_sector_concentration(portfolio_df)

    # 3. Attribution
    attribution = calculate_holdings_attribution(holdings, market_data)

    # 4. Sector Drift & Macro
    sector_drift = analyze_sector_drift_and_profile(portfolio_df)

    # 5. Drawdown & Historical Volatility
    stock_histories = {}
    min_len = 9999
    for item in holdings:
        sym = item["symbol"]
        closes = market_data.get(sym, {}).get("history_closes", [])
        if closes:
            stock_histories[sym] = (item["quantity"], closes)
            if len(closes) < min_len:
                min_len = len(closes)

    if stock_histories and min_len >= 2:
        portfolio_series_values = []
        for idx in range(-min_len, 0):
            day_val = sum(qty * closes[idx] for qty, closes in stock_histories.values())
            portfolio_series_values.append(day_val)
        portfolio_price_series = pd.Series(portfolio_series_values)
    else:
        portfolio_price_series = pd.Series([
            attribution.get("total_invested_value", 100000),
            attribution.get("total_current_value", 100000)
        ])

    drawdown_vol = calculate_drawdown_and_volatility(portfolio_price_series)

    # 6. Benchmark Metrics
    nifty_data = market_data.get("^NSEI", {})
    vix_data = market_data.get("^INDIAVIX", {})

    nifty_returns_list = nifty_data.get("daily_returns", [])
    port_returns = portfolio_price_series.pct_change().dropna()
    nifty_returns = pd.Series(nifty_returns_list[-len(port_returns):]) if nifty_returns_list else pd.Series()
    vix_val = vix_data.get("latest_close", 14.5)

    benchmark = calculate_benchmark_metrics(
        portfolio_daily_returns=port_returns,
        nifty_daily_returns=nifty_returns,
        vix_latest_value=vix_val
    )

    return {
        "sector_concentration": concentration,
        "holdings_attribution": attribution,
        "sector_drift_and_macro": sector_drift,
        "drawdown_and_volatility": drawdown_vol,
        "benchmark_comparison": benchmark
    }

def score_risk(analytics_metrics: dict, risk_tolerance: str = "moderate") -> dict:
    """
    Evaluates threshold triggers and assigns a composite risk score and alert flags.
    """
    conc = analytics_metrics.get("sector_concentration", {})
    dd_vol = analytics_metrics.get("drawdown_and_volatility", {})
    bench = analytics_metrics.get("benchmark_comparison", {})
    macro = analytics_metrics.get("sector_drift_and_macro", {}).get("macro_breakdown", {})

    alerts = []
    risk_points = 20 # Base baseline score

    # Concentration checks
    hhi = conc.get("hhi_concentration_score", 0.0)
    top_sector_pct = conc.get("top_sector_weight_pct", 0.0)
    if hhi > 0.25:
        alerts.append({
            "type": "CONCENTRATION_ALERT",
            "severity": "HIGH",
            "message": f"Portfolio HHI concentration score is {hhi:.4f} (exceeds threshold 0.2500)."
        })
        risk_points += 25
    elif top_sector_pct > 40.0:
        alerts.append({
            "type": "SECTOR_CONCENTRATION_ALERT",
            "severity": "HIGH",
            "message": f"Single sector {conc.get('top_sector')} exposure is {top_sector_pct:.1f}% (exceeds 40% threshold)."
        })
        risk_points += 20

    # Drawdown check
    max_dd = dd_vol.get("max_drawdown_pct", 0.0)
    if max_dd < -15.0:
        alerts.append({
            "type": "DRAWDOWN_ALERT",
            "severity": "HIGH" if max_dd < -25.0 else "MEDIUM",
            "message": f"Maximum peak-to-trough drawdown reached {max_dd:.2f}% (exceeds -15.0% threshold)."
        })
        risk_points += 20

    # Volatility check
    ann_vol = dd_vol.get("annualized_volatility_pct", 0.0)
    if ann_vol > 25.0:
        alerts.append({
            "type": "VOLATILITY_ALERT",
            "severity": "HIGH" if ann_vol > 35.0 else "MEDIUM",
            "message": f"Annualized portfolio volatility is {ann_vol:.2f}% (exceeds 25.0% threshold)."
        })
        risk_points += 15

    # Beta check relative to risk profile
    beta = bench.get("beta", 1.0)
    if beta > 1.25 and risk_tolerance.lower() in ("conservative", "moderate"):
        alerts.append({
            "type": "BETA_MISALIGNMENT_ALERT",
            "severity": "MEDIUM",
            "message": f"Portfolio Beta of {beta:.2f} is aggressively tilted for a '{risk_tolerance}' profile."
        })
        risk_points += 15

    # Macro cyclicality check
    cyclical_pct = macro.get("cyclical_pct", 0.0)
    if cyclical_pct > 50.0:
        alerts.append({
            "type": "CYCLICAL_EXPOSURE_ALERT",
            "severity": "MEDIUM",
            "message": f"Cyclical sectors account for {cyclical_pct:.1f}% of portfolio."
        })
        risk_points += 10

    # Cap risk score between 1 and 100
    composite_score = min(max(risk_points, 1), 100)
    risk_level = (
        "Severe" if composite_score >= 80 else (
            "High" if composite_score >= 60 else (
                "Elevated" if composite_score >= 40 else "Moderate"
            )
        )
    )

    return {
        "composite_risk_score": composite_score,
        "risk_level": risk_level,
        "risk_tolerance_profile": risk_tolerance,
        "active_alerts_count": len(alerts),
        "alerts": alerts,
        "is_action_required": len(alerts) > 0
    }

