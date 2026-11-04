import asyncio

from ai_workflows.recommendation_engine.engine import generate_recommendations
from backend.database.connection import (
    get_insight_by_job,
    get_recommendation_cards_by_job,
    record_audit_event,
    save_recommendation_cards,
    update_job_status,
)


def _serialize_card(row: dict) -> dict:
    metrics = row.get("metrics_json") or {}
    if isinstance(metrics, list):
        supporting_metrics = metrics
        card_status = "validated"
        is_validated = True
        validation_reason = None
    else:
        supporting_metrics = metrics.get("supporting_metrics", [])
        card_status = metrics.get("status", "validated")
        is_validated = metrics.get("is_validated", True)
        validation_reason = metrics.get("validation_reason")
    return {
        "id": row["id"],
        "job_id": row.get("job_id"),
        "category": row["category"],
        "title": row.get("title") or row["category"],
        "rationale": row["rationale"],
        "supporting_metrics": supporting_metrics,
        "confidence": float(row["confidence"]) if row.get("confidence") is not None else 0.0,
        "freshness_timestamp": row.get("freshness_ts"),
        "disclaimer": row.get("disclaimer") or "",
        "status": card_status,
        "is_validated": is_validated,
        "validation_reason": validation_reason,
    }


async def generate_and_persist_recommendations(job_id: str) -> list[dict]:
    insight_record = await asyncio.to_thread(get_insight_by_job, job_id)
    if not insight_record:
        raise LookupError(f"No persisted insight exists for job '{job_id}'.")

    raw_json = insight_record.get("raw_json") or {}
    context = raw_json.get("context_data")
    if not isinstance(context, dict):
        raise ValueError(f"Persisted insight for job '{job_id}' has no analytics context.")

    cards = generate_recommendations(context)
    if not insight_record.get("is_validated"):
        reason = insight_record.get("validation_reason") or "Validation failed."
        for card in cards:
            card["rationale"] = f"Downgraded because validation failed: {reason} {card['rationale']}"
            card["confidence"] = min(float(card["confidence"]), 0.3)
            card["metrics_json"] = {
                "status": "downgraded",
                "is_validated": False,
                "validation_reason": reason,
                "supporting_metrics": card["supporting_metrics"],
            }
    else:
        for card in cards:
            card["metrics_json"] = {
                "status": "validated",
                "is_validated": True,
                "supporting_metrics": card["supporting_metrics"],
            }

    saved = await asyncio.to_thread(save_recommendation_cards, job_id, cards)
    await asyncio.to_thread(
        record_audit_event,
        "recommendation_generation",
        {"job_id": job_id, "card_ids": [card["id"] for card in saved]},
        "success",
        "Recommendation cards generated and persisted.",
    )
    await asyncio.to_thread(update_job_status, job_id, "completed", True)
    return [_serialize_card(card) for card in saved]


async def get_recommendations(job_id: str) -> list[dict]:
    rows = await asyncio.to_thread(get_recommendation_cards_by_job, job_id)
    return [_serialize_card(card) for card in rows]
