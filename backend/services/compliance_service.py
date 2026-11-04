import asyncio

from ai_workflows.llm_analysis.gemini_client import generate_financial_insight
from ai_workflows.validation.validator import detect_hallucinations
from backend.database.connection import save_insight_log
from backend.services.embedding_service import (
    index_insight,
    search_relevant_past_insights,
)


async def generate_validate_and_persist(
    job_id: str,
    user_id: str,
    portfolio_id: str,
    context: dict,
) -> dict:
    examples = await asyncio.to_thread(
        search_relevant_past_insights,
        str(context),
        portfolio_id,
        3,
    )
    context["similar_past_insights"] = [
        {
            "title": item.get("title"),
            "category": item.get("category"),
            "confidence": float(item["confidence_score"])
                if item.get("confidence_score") is not None else None,
            "similarity": float(item["similarity"])
                if item.get("similarity") is not None else None,
        }
        for item in examples
    ]

    generated = await asyncio.to_thread(generate_financial_insight, context)
    validated = detect_hallucinations(generated, context)
    validated.setdefault("category", "Summary Follow-up")
    validated.setdefault("title", "Portfolio insight")
    validated.setdefault("explanation", "")
    validated.setdefault("rationale", "")
    validated.setdefault("supporting_metrics", [])
    validated.setdefault("disclaimer", "This insight is for informational purposes only.")

    confidence = validated.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        confidence = 0.0
    validated["confidence"] = float(confidence)

    persisted_payload = {**validated, "context_data": context}
    insight_id = await asyncio.to_thread(
        save_insight_log,
        job_id,
        user_id,
        str(validated["category"]),
        str(validated["title"]),
        float(confidence),
        bool(validated.get("is_validated")),
        str(validated.get("validation_reason", "")),
        persisted_payload,
    )

    embedding_stored = False
    if validated.get("is_validated"):
        embedding_stored = await asyncio.to_thread(index_insight, insight_id, validated)

    return {
        "id": insight_id,
        "insight": validated,
        "context": context,
        "embedding_stored": embedding_stored,
    }
