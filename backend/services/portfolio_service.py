import asyncio
import logging
import uuid

from ai_workflows.context_builder.builder import build_financial_context
from backend.database.connection import (
    create_job,
    get_insight_by_job,
    get_job,
    record_audit_event,
    update_job_status,
)
from backend.services.compliance_service import generate_validate_and_persist
from backend.services.recommendation_service import (
    generate_and_persist_recommendations,
    get_recommendations,
)

logger = logging.getLogger("PortfolioService")


def _source_from_job_type(job_type: str | None) -> str:
    if job_type and ":" in job_type:
        source = job_type.rsplit(":", 1)[1]
        if source in {"sample", "sandbox", "live"}:
            return source
    return "sample"


async def submit_portfolio_analysis(user_id: str, source: str = "sample") -> dict:
    job_id = str(uuid.uuid4())
    job_type = "portfolio_analysis" if source == "sample" else f"portfolio_analysis:{source}"
    job = await asyncio.to_thread(create_job, job_id, user_id, job_type)
    await asyncio.to_thread(
        record_audit_event,
        "portfolio_analysis",
        {"job_id": job_id, "user_id": user_id},
        "submitted",
        "Portfolio analysis job submitted.",
    )
    return {"job_id": job_id, "status": job["status"]}


async def generate_insight_for_job(job_id: str) -> dict:
    job = await asyncio.to_thread(get_job, job_id)
    if not job:
        raise LookupError(f"Job '{job_id}' was not found.")

    user_id = str(job["portfolio_id"])
    await asyncio.to_thread(update_job_status, job_id, "mcp_tools")
    source = _source_from_job_type(job.get("job_type"))
    context = await build_financial_context(user_id, job_id=job_id, source=source)
    if "error" in context:
        raise RuntimeError(context["error"])
    if context.get("status") == "empty_portfolio":
        return {
            "status": "empty_portfolio",
            "message": context["message"],
            "portfolio_source": context.get("portfolio_source", source),
            "fallback_available": context.get("fallback_available", True),
            "fallback_source": context.get("fallback_source", "sample"),
            "fallback_action": context.get("fallback_action"),
            "relogin_path": context.get("relogin_path"),
        }

    await asyncio.to_thread(update_job_status, job_id, "llm_analysis")
    result = await generate_validate_and_persist(
        job_id=job_id,
        user_id=user_id,
        portfolio_id=str(job["portfolio_id"]),
        context=context,
    )
    await asyncio.to_thread(update_job_status, job_id, "insight_generated")
    await asyncio.to_thread(
        record_audit_event,
        "insight_generation",
        {"job_id": job_id, "user_id": user_id, "insight_id": result["id"]},
        "success",
        "Insight generated, validated, and persisted.",
    )
    return result


async def process_portfolio_analysis(job_id: str, user_id: str) -> None:
    try:
        await asyncio.to_thread(update_job_status, job_id, "fetching_data")
        await asyncio.to_thread(
            record_audit_event,
            "portfolio_analysis",
            {"job_id": job_id, "user_id": user_id},
            "running",
            "Portfolio context gathering started.",
        )
        result = await generate_insight_for_job(job_id)
        if result.get("status") == "empty_portfolio":
            await asyncio.to_thread(
                update_job_status, job_id, "empty_portfolio", True
            )
            await asyncio.to_thread(
                record_audit_event,
                "portfolio_analysis",
                {"job_id": job_id, "user_id": user_id},
                "success",
                "Connected portfolio has no holdings; sample fallback is available.",
            )
            return
        await asyncio.to_thread(update_job_status, job_id, "recommendations")
        cards = await generate_and_persist_recommendations(job_id)
        await asyncio.to_thread(update_job_status, job_id, "completed", True)
        await asyncio.to_thread(
            record_audit_event,
            "portfolio_analysis",
            {"job_id": job_id, "user_id": user_id},
            "success",
            "Portfolio analysis completed and persisted.",
        )
        logger.info(
            "Portfolio job %s completed; insight_id=%s cards=%s embedding_stored=%s",
            job_id,
            result["id"],
            len(cards),
            result["embedding_stored"],
        )
    except Exception as exc:
        logger.exception("Portfolio analysis job %s failed", job_id)
        try:
            await asyncio.to_thread(update_job_status, job_id, "failed", True)
            await asyncio.to_thread(
                record_audit_event,
                "portfolio_analysis",
                {"job_id": job_id, "user_id": user_id},
                "error",
                "Portfolio analysis failed.",
                error_message=str(exc),
            )
        except Exception:
            logger.exception("Failed to persist failure state for job %s", job_id)


async def get_job_result(job_id: str) -> dict | None:
    job = await asyncio.to_thread(get_job, job_id)
    if not job:
        return None
    insight = await asyncio.to_thread(get_insight_by_job, job_id)
    recommendations = await get_recommendations(job_id)
    return {
        "job_id": job_id,
        "status": job["status"],
        "job": job,
        "insight": insight,
        "recommendations": recommendations,
        "empty_state": (
            {
                "message": "No holdings found in this account.",
                "fallback_available": True,
                "fallback_source": "sample",
                "fallback_action": (
                    "Submit a new analysis with source='sample' to use demo holdings."
                ),
            }
            if job["status"] == "empty_portfolio"
            else None
        ),
    }
