import os
import sys
import json
import logging
import time
import inspect
from pathlib import Path
from typing import Any, Callable
import psycopg2
from dotenv import load_dotenv

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

load_dotenv()

# Import the official MCP Server SDK
from mcp.server.mcpserver import MCPServer

# Import underlying domain tools
from mcp_server.tools.portfolio_tools import get_portfolio_snapshot
from mcp_server.tools.market_tools import fetch_dynamic_market_data
from mcp_server.tools.news_tools import fetch_news_for_symbols
from mcp_server.tools.analytics_tools import compute_portfolio_analytics, score_risk

logger = logging.getLogger("ZerodhaMCPServer")
logging.basicConfig(level=logging.INFO)

# Load tool registry as schema source of truth
REGISTRY_PATH = Path(__file__).resolve().parent / "tool_registry.json"
TOOL_REGISTRY = {}
if REGISTRY_PATH.exists():
    try:
        with open(REGISTRY_PATH, "r") as f:
            TOOL_REGISTRY = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load tool_registry.json: {e}")

# Initialize official MCP server instance
mcp_server = MCPServer("Zerodha Financial Intelligence MCP Server")

def _log_audit_event(
    tool_name: str,
    parameters: dict,
    latency_ms: float,
    status: str,
    error_message: str = None,
    description: str = None
):
    """
    Persists MCP tool execution telemetry to the Supabase audit_events table.
    Degrades gracefully if database is unreachable.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning(f"DATABASE_URL not set; skipping audit log for tool {tool_name}")
        return

    try:
        audit_parameters = dict(parameters)
        job_id = os.getenv("MCP_JOB_ID")
        if job_id:
            audit_parameters["job_id"] = job_id
        conn = psycopg2.connect(db_url, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_events (
                    event_type, tool_name, parameters, latency_ms, status, error_message, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                "mcp_tool_call",
                tool_name,
                json.dumps(audit_parameters),
                latency_ms,
                status,
                error_message,
                description or f"MCP tool call: {tool_name}"
            ))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to write audit_event to DB (non-fatal): {e}")

# -------------------------------------------------------------
# Official MCP Tool Registrations
# -------------------------------------------------------------

async def _execute_tool(name: str, arguments: dict, handler: Callable[..., Any]) -> Any:
    started_at = time.perf_counter()
    try:
        result = handler(**arguments)
        if inspect.isawaitable(result):
            result = await result
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _log_audit_event(
            name,
            arguments,
            latency_ms,
            "success",
            description=f"Executed MCP tool {name} successfully in {latency_ms}ms"
        )
        return result
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _log_audit_event(
            name,
            arguments,
            latency_ms,
            "error",
            error_message=str(exc),
            description=f"MCP tool {name} failed: {exc}"
        )
        raise

@mcp_server.tool(
    name="fetch_portfolio",
    description="Fetches sample, sandbox, or live portfolio holdings for the authenticated user."
)
async def tool_fetch_portfolio(user_id: str, source: str = "sample") -> dict:
    return await _execute_tool(
        "fetch_portfolio",
        {"user_id": user_id, "source": source},
        get_portfolio_snapshot
    )

@mcp_server.tool(
    name="fetch_market_data",
    description="Fetches real-time quotes, 1d change %, benchmarks (^NSEI, ^INDIAVIX), and historical close series."
)
async def tool_fetch_market_data(tickers: list[str], period: str = "3mo") -> dict:
    return await _execute_tool(
        "fetch_market_data",
        {"tickers": tickers, "period": period},
        lambda tickers, period: fetch_dynamic_market_data(tickers, period=period)
    )

@mcp_server.tool(
    name="fetch_news",
    description="Fetches market news and corporate announcements for portfolio symbols."
)
async def tool_fetch_news(symbols: list[str], max_articles_per_stock: int = 2) -> dict:
    return await _execute_tool(
        "fetch_news",
        {"symbols": symbols, "max_articles_per_stock": max_articles_per_stock},
        lambda symbols, max_articles_per_stock: fetch_news_for_symbols(
            symbols,
            max_articles_per_stock=max_articles_per_stock
        )
    )

@mcp_server.tool(
    name="run_analytics",
    description="Computes deterministic portfolio metrics: HHI concentration, sector drift, drawdown/volatility, benchmark beta/alpha, and attribution."
)
async def tool_run_analytics(holdings: list[dict], market_data: dict) -> dict:
    return await _execute_tool(
        "run_analytics",
        {"holdings": holdings, "market_data": market_data},
        compute_portfolio_analytics
    )

@mcp_server.tool(
    name="score_risk",
    description="Evaluates risk thresholds (HHI, drawdown, volatility, beta) and generates composite risk score and alert triggers."
)
async def tool_score_risk(analytics_metrics: dict, risk_tolerance: str = "moderate") -> dict:
    return await _execute_tool(
        "score_risk",
        {"analytics_metrics": analytics_metrics, "risk_tolerance": risk_tolerance},
        score_risk
    )

def list_registered_tools() -> list[dict]:
    """Returns tool registry schemas."""
    return TOOL_REGISTRY.get("tools", [])

if __name__ == "__main__":
    # Keep stdout reserved for the MCP stdio protocol.
    logger.info("Starting MCP stdio server process pid=%s", os.getpid())
    mcp_server.run()
