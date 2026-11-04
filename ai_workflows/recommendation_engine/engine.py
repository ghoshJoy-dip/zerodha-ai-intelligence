from datetime import datetime, timezone


DISCLAIMER = (
    "This portfolio insight is for informational and risk-awareness purposes only "
    "and is not investment advice or an instruction to trade."
)


def _card(category: str, rationale: str, metrics: list[dict], freshness: str) -> dict:
    return {
        "category": category,
        "title": category,
        "rationale": rationale,
        "supporting_metrics": metrics,
        "confidence": 0.9 if metrics else 0.75,
        "freshness_timestamp": freshness,
        "disclaimer": DISCLAIMER,
    }


def generate_recommendations(context: dict) -> list[dict]:
    """Create recommendation cards using only deterministic portfolio metrics."""
    analytics = context.get("deterministic_analytics", {})
    concentration = analytics.get("sector_concentration", {})
    drawdown = analytics.get("drawdown_and_volatility", {})
    attribution = analytics.get("holdings_attribution", {})

    freshness = (
        context.get("freshness_timestamp_utc")
        or datetime.now(timezone.utc).isoformat()
    )
    cards = []

    hhi = concentration.get("hhi_concentration_score")
    top_sector_weight = concentration.get("top_sector_weight_pct")
    concentration_metrics = []
    if isinstance(hhi, (int, float)):
        concentration_metrics.append({
            "metric_name": "HHI Concentration Score",
            "metric_value": float(hhi),
        })
    if isinstance(top_sector_weight, (int, float)):
        concentration_metrics.append({
            "metric_name": f"{concentration.get('top_sector') or 'Top sector'} Exposure %",
            "metric_value": float(top_sector_weight),
        })
    if ((isinstance(hhi, (int, float)) and hhi > 0.25)
            or (isinstance(top_sector_weight, (int, float)) and top_sector_weight > 40.0)):
        cards.append(_card(
            "Diversification Review",
            "Portfolio concentration exceeded the HHI or single-sector threshold; review diversification.",
            concentration_metrics,
            freshness,
        ))

    max_drawdown = drawdown.get("max_drawdown_pct")
    if isinstance(max_drawdown, (int, float)) and max_drawdown < -15.0:
        cards.append(_card(
            "Risk Alert",
            "Portfolio drawdown exceeded 15%; review the portfolio's risk exposure.",
            [{"metric_name": "Maximum Drawdown %", "metric_value": float(max_drawdown)}],
            freshness,
        ))

    daily_moves = []
    for holding in attribution.get("stock_attributions", []):
        symbol = holding.get("symbol", "Unknown")
        move = holding.get("1d_change_pct")
        if isinstance(move, (int, float)) and abs(move) > 5.0:
            daily_moves.append({
                "metric_name": f"{symbol} Daily Move %",
                "metric_value": float(move),
            })
    if daily_moves:
        cards.append(_card(
            "Watchlist Monitoring",
            "One or more holdings moved more than 5% in a day; monitor the listed positions.",
            daily_moves,
            freshness,
        ))

    if not cards:
        metrics = []
        pnl_pct = attribution.get("overall_unrealized_pnl_pct")
        if isinstance(pnl_pct, (int, float)):
            metrics.append({
                "metric_name": "Overall Unrealized P&L %",
                "metric_value": float(pnl_pct),
            })
        cards.append(_card(
            "Summary Follow-up",
            "No concentration, drawdown, or daily-move trigger was exceeded.",
            metrics,
            freshness,
        ))

    return cards


def generate_actionable_steps(insight: dict) -> list[dict]:
    """Compatibility wrapper retained for existing callers."""
    if not insight.get("is_validated"):
        return [{"action": "HOLD", "reason": "Insight pending manual validation."}]
    category = insight.get("category", "")
    metrics = insight.get("supporting_metrics", [])
    recommendations = []
    if category == "Risk Alert":
        for metric in metrics:
            name = metric.get("metric_name", "")
            if "Latest Close" in name:
                ticker = name.split()[0]
                recommendations.append({
                    "action": "REVIEW_HEDGE",
                    "ticker": ticker,
                    "reason": f"Significant downside pressure identified for {ticker}.",
                })
        recommendations.append({
            "action": "REBALANCE",
            "ticker": "PORTFOLIO",
            "reason": "Consider reviewing portfolio exposure due to elevated risk.",
        })
    return recommendations
