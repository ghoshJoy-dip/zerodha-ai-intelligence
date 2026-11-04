import asyncio
import json
import sys
from pathlib import Path
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)

# Explicitly add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.mcp_service import call_mcp_tool, open_mcp_session


async def _build_financial_context(session, user_id: str, source: str = "sample") -> dict:
    portfolio_data = await call_mcp_tool(
        session,
        "fetch_portfolio",
        {"user_id": user_id, "source": source},
    )
    if portfolio_data.get("status") == "error":
        return {"error": portfolio_data.get("message")}

    holdings = portfolio_data.get("holdings", [])
    symbols = portfolio_data.get("symbols", [])

    if not holdings or not symbols:
        return {
            "status": "empty_portfolio",
            "message": portfolio_data.get(
                "message", "No holdings found in this account."
            ),
            "user_id": user_id,
            "portfolio_source": portfolio_data.get("source", source),
            "connection_status": portfolio_data.get("connection_status"),
            "fallback_available": portfolio_data.get("fallback_available", True),
            "fallback_source": portfolio_data.get("fallback_source", "sample"),
            "fallback_action": portfolio_data.get(
                "fallback_action",
                "Select Sample as the portfolio source to continue with demo holdings.",
            ),
            "relogin_path": portfolio_data.get("relogin_path"),
        }

    market_task = call_mcp_tool(
        session, "fetch_market_data", {"tickers": symbols, "period": "3mo"}
    )
    news_task = call_mcp_tool(
        session, "fetch_news", {"symbols": symbols, "max_articles_per_stock": 2}
    )
    market_res, news_res = await asyncio.gather(market_task, news_task)
    market_data = market_res.get("data", {}) if market_res.get("status") == "success" else {}
    news_data = news_res.get("data", {}) if news_res.get("status") == "success" else {}

    analytics_res = await call_mcp_tool(session, "run_analytics", {
        "holdings": holdings,
        "market_data": market_data
    })
    if "error" in analytics_res:
        return {"error": f"Analytics engine failed via MCP: {analytics_res['error']}"}

    risk_score_res = await call_mcp_tool(session, "score_risk", {
        "analytics_metrics": analytics_res,
        "risk_tolerance": portfolio_data.get("risk_profile", "moderate")
    })

    attribution = analytics_res.get("holdings_attribution", {})
    return {
        "portfolio_profile": {
            "user_id": user_id,
            "portfolio_id": portfolio_data.get("portfolio_id", "default"),
            "portfolio_source": portfolio_data.get("source", source),
            "requested_portfolio_source": portfolio_data.get(
                "requested_source", source
            ),
            "connection_status": portfolio_data.get("connection_status"),
            "fallback_reason": portfolio_data.get("fallback_reason"),
            "relogin_path": portfolio_data.get("relogin_path"),
            "risk_tolerance": portfolio_data.get("risk_profile", "moderate"),
            "total_invested_value": attribution.get("total_invested_value"),
            "total_current_value": attribution.get("total_current_value"),
            "overall_unrealized_pnl": attribution.get("overall_unrealized_pnl"),
            "overall_unrealized_pnl_pct": attribution.get("overall_unrealized_pnl_pct"),
            "holdings": holdings
        },
        "deterministic_analytics": analytics_res,
        "risk_evaluation": risk_score_res,
        "market_snapshot": market_data,
        "recent_news": news_data,
        "freshness_timestamp_utc": market_res.get("freshness_timestamp_utc")
    }

async def build_financial_context(
    user_id: str,
    job_id: str | None = None,
    source: str = "sample",
) -> dict:
    """
    Builds context using MCP tools over a stdio connection to a separate server process.
    """
    async with open_mcp_session(job_id) as session:
        return await _build_financial_context(session, user_id, source)

def format_context_for_prompt(context_dict: dict) -> str:
    """Converts the context dictionary into formatted JSON for LLM prompting."""
    return json.dumps(context_dict, indent=2)

if __name__ == "__main__":
    async def test_mcp_context_builder():
        print("Gathering live context strictly through MCP server...")
        ctx = await build_financial_context("user_123")
        print("MCP Context Keys:", list(ctx.keys()))
        print("Analytics Keys (via MCP):", list(ctx.get("deterministic_analytics", {}).keys()))
        print("Risk Score (via MCP):", ctx.get("risk_evaluation", {}).get("composite_risk_score"))
        
    asyncio.run(test_mcp_context_builder())
