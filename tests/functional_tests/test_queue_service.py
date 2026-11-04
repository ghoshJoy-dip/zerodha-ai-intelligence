from backend.services import queue_service


def test_unvalidated_insight_persists_downgraded_card(monkeypatch):
    saved = {}

    def fake_save_recommendation_cards(job_id, cards):
        saved["job_id"] = job_id
        saved["cards"] = cards
        return [{"id": 42}]

    monkeypatch.setattr(
        queue_service, "save_recommendation_cards", fake_save_recommendation_cards
    )

    queue_service.process_insight_async("user-test", {
        "is_validated": False,
        "category": "Risk Alert",
        "title": "Test insight",
        "confidence": 0.7,
        "validation_reason": "Unmatched metric",
        "supporting_metrics": [{"metric_name": "Test metric", "metric_value": 2.0}]
    })

    assert saved["job_id"] is None
    assert len(saved["cards"]) == 1
    card = saved["cards"][0]
    assert card["metrics_json"]["status"] == "downgraded"
    assert card["metrics_json"]["is_validated"] is False
    assert card["metrics_json"]["validation_reason"] == "Unmatched metric"
    assert "Downgraded" in card["rationale"]
