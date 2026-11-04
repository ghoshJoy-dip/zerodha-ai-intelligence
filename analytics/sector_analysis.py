import pandas as pd
import numpy as np

CYCLICAL_SECTORS = {
    "banking", "financial services", "energy", "oil & gas", "metals", "mining",
    "automobile", "auto", "realty", "real estate", "consumer discretionary"
}

DEFENSIVE_SECTORS = {
    "fmcg", "consumer staples", "pharma", "pharmaceuticals", "healthcare",
    "utilities", "power"
}

SENSITIVE_GROWTH_SECTORS = {
    "it", "information technology", "technology", "telecom", "telecommunication",
    "capital goods", "industrials"
}

# Standard balanced benchmark sector weights for Indian markets (approximate Nifty 50 profile)
BENCHMARK_SECTOR_WEIGHTS = {
    "Banking": 30.0,
    "IT": 15.0,
    "Energy": 12.0,
    "FMCG": 9.0,
    "Automobile": 7.0,
    "Pharma": 6.0,
    "Metals": 4.0,
    "Financial Services": 5.0,
    "Utilities": 4.0,
    "Telecommunication": 3.0,
    "Other": 5.0
}

def analyze_sector_drift_and_profile(portfolio_df: pd.DataFrame) -> dict:
    """
    Computes sector drift against standard benchmark allocations and breaks down
    cyclical vs. defensive vs. sensitive/growth exposure.
    Expects DataFrame with columns: ['symbol', 'sector', 'current_value']
    """
    if portfolio_df.empty or 'current_value' not in portfolio_df.columns or 'sector' not in portfolio_df.columns:
        return {"error": "Invalid portfolio data for sector analysis"}

    total_value = portfolio_df['current_value'].sum()
    if total_value <= 0:
        return {"error": "Total portfolio value is zero or negative"}

    # Aggregate by sector
    sector_summary = portfolio_df.groupby('sector')['current_value'].sum().reset_index()
    sector_summary['weight_pct'] = (sector_summary['current_value'] / total_value) * 100.0

    cyclical_weight = 0.0
    defensive_weight = 0.0
    growth_weight = 0.0
    other_weight = 0.0

    sector_drift = {}

    for _, row in sector_summary.iterrows():
        sec = str(row['sector']).strip()
        sec_lower = sec.lower()
        w = float(row['weight_pct'])

        # Categorize macro profile
        if any(c in sec_lower for c in CYCLICAL_SECTORS):
            cyclical_weight += w
        elif any(d in sec_lower for d in DEFENSIVE_SECTORS):
            defensive_weight += w
        elif any(g in sec_lower for g in SENSITIVE_GROWTH_SECTORS):
            growth_weight += w
        else:
            other_weight += w

        # Drift calculation vs benchmark
        benchmark_target = BENCHMARK_SECTOR_WEIGHTS.get(sec, 5.0)
        drift = round(w - benchmark_target, 2)
        sector_drift[sec] = {
            "portfolio_weight_pct": round(w, 2),
            "benchmark_weight_pct": round(benchmark_target, 2),
            "drift_pct": drift,
            "status": "Overweight" if drift > 5.0 else ("Underweight" if drift < -5.0 else "Neutral")
        }

    macro_profile = "Balanced"
    if cyclical_weight > 50.0:
        macro_profile = "Heavy Cyclical Tilt"
    elif defensive_weight > 40.0:
        macro_profile = "Heavy Defensive Tilt"
    elif growth_weight > 45.0:
        macro_profile = "Heavy Tech/Growth Tilt"

    return {
        "macro_breakdown": {
            "cyclical_pct": round(cyclical_weight, 2),
            "defensive_pct": round(defensive_weight, 2),
            "sensitive_growth_pct": round(growth_weight, 2),
            "other_pct": round(other_weight, 2),
            "profile_summary": macro_profile
        },
        "sector_drift": sector_drift,
        "max_drift_sector": max(sector_drift.items(), key=lambda x: abs(x[1]["drift_pct"]))[0] if sector_drift else None
    }

