import asyncio

from ai_workflows.context_builder.builder import build_financial_context
from backend.services.mcp_service import execute_mcp_tool


async def refresh_market_data(
    user_id: str,
    source: str = "sample",
    timeframe: str = "3mo",
) -> dict:
    context = await build_financial_context(
        user_id,
        source=source,
        period=timeframe,
    )
    if context.get("status") == "empty_portfolio":
        return {
            **context,
            "user_id": user_id,
            "portfolio_source": context.get("portfolio_source", source),
        }
    if "error" in context:
        raise RuntimeError(context["error"])
    return {
        "user_id": user_id,
        "portfolio_source": context.get("portfolio_profile", {}).get(
            "portfolio_source", source
        ),
        "freshness_timestamp_utc": context.get("freshness_timestamp_utc"),
        "market_snapshot": context.get("market_snapshot", {}),
        "recent_news": context.get("recent_news", {}),
    }


async def run_analytics(
    holdings: list[dict],
    market_data: dict,
    job_id: str | None = None,
) -> dict:
    return await execute_mcp_tool(
        "run_analytics",
        {"holdings": holdings, "market_data": market_data},
        job_id=job_id,
    )
