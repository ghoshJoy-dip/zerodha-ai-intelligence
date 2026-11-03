def generate_actionable_steps(insight: dict) -> list[dict]:
    """
    Translates a validated financial insight into actionable portfolio recommendations.
    """
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
                    "reason": f"Significant downside pressure identified for {ticker}."
                })
        
        # Add a general portfolio-level recommendation
        recommendations.append({
            "action": "REBALANCE",
            "ticker": "PORTFOLIO",
            "reason": "Consider increasing cash position or hedging broad market exposure due to high VIX and localized drawdowns."
        })

    return recommendations