from ai_workflows.recommendation_engine.engine import generate_recommendations


def test_recommendations_emit_all_threshold_categories():
    cards = generate_recommendations({
        "freshness_timestamp_utc": "2026-11-04T00:00:00Z",
        "deterministic_analytics": {
            "sector_concentration": {
                "hhi_concentration_score": 0.3,
                "top_sector": "IT",
                "top_sector_weight_pct": 45.0,
            },
            "drawdown_and_volatility": {"max_drawdown_pct": -16.0},
            "holdings_attribution": {
                "stock_attributions": [
                    {"symbol": "TCS", "1d_change_pct": 6.0},
                ],
            },
        },
    })

    assert [card["category"] for card in cards] == [
        "Diversification Review",
        "Risk Alert",
        "Watchlist Monitoring",
    ]
    for card in cards:
        assert card["rationale"]
        assert card["supporting_metrics"]
        assert card["confidence"] > 0
        assert card["freshness_timestamp"] == "2026-11-04T00:00:00Z"
        assert card["disclaimer"]


def test_recommendations_emit_summary_when_no_threshold_is_tripped():
    cards = generate_recommendations({
        "deterministic_analytics": {
            "sector_concentration": {
                "hhi_concentration_score": 0.2,
                "top_sector_weight_pct": 40.0,
            },
            "drawdown_and_volatility": {"max_drawdown_pct": -15.0},
            "holdings_attribution": {
                "overall_unrealized_pnl_pct": 1.5,
                "stock_attributions": [
                    {"symbol": "TCS", "1d_change_pct": 5.0},
                ],
            },
        },
    })

    assert len(cards) == 1
    assert cards[0]["category"] == "Summary Follow-up"
