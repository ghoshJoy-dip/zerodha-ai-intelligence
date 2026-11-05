import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, RedirectResponse

from ai_workflows.context_builder.builder import build_financial_context
from ai_workflows.llm_analysis.gemini_client import generate_financial_insight
from ai_workflows.validation.validator import detect_hallucinations
from backend.database.connection import (
    get_audit_trail_for_job,
    get_feedback_summary_by_job,
    get_job,
    get_recommendation_card_job,
    record_feedback,
)
from backend.services.kite_service import (
    KITE_OAUTH_COOKIE,
    KITE_SESSION_COOKIE,
    SANDBOX_API_KEY,
    SANDBOX_API_SECRET,
    SANDBOX_ROOT,
    create_oauth_state,
    create_session_cookie,
    get_session_user_id,
    persist_sandbox_session,
    sandbox_login_url,
    sandbox_redirect_url,
    validate_oauth_state,
)
from backend.services.market_service import refresh_market_data, run_analytics
from backend.services.mcp_service import execute_mcp_tool
from backend.services.portfolio_service import (
    generate_insight_for_job,
    get_job_result,
    process_portfolio_analysis,
    submit_portfolio_analysis,
)
from backend.services.recommendation_service import generate_and_persist_recommendations

app = FastAPI(title="Zerodha AI Intelligence API")
logger = logging.getLogger("KiteRoutes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PortfolioAnalysisRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1)
    source: Literal["sample", "sandbox", "live"] = "sample"
    timeframe: Literal["1mo", "3mo", "6mo", "1y"] = "3mo"


class MarketRefreshRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1)
    source: Literal["sample", "sandbox", "live"] = "sample"
    timeframe: Literal["1mo", "3mo", "6mo", "1y"] = "3mo"


class MCPToolRequest(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    job_id: str | None = None


class AnalyticsRequest(BaseModel):
    holdings: list[dict]
    market_data: dict
    job_id: str | None = None


class JobRequest(BaseModel):
    job_id: str = Field(min_length=1)


class FeedbackRequest(BaseModel):
    card_id: int = Field(gt=0)
    action: Literal["thumbs_up", "thumbs_down", "accepted", "dismissed"]
    note: str | None = None


@app.get("/health")
def health_check():
    return {"status": "active", "service": "Zerodha AI Backend"}


def _resolve_request_user(
    request: Request,
    source: str,
    requested_user_id: str | None,
) -> str:
    if source == "sample":
        if not requested_user_id:
            raise HTTPException(
                status_code=422,
                detail="user_id is required for sample data.",
            )
        return requested_user_id
    if source == "live":
        raise HTTPException(
            status_code=501,
            detail="Live Kite login is unavailable until live app credentials are configured.",
        )
    user_id = get_session_user_id(request.cookies.get(KITE_SESSION_COOKIE))
    if not user_id:
        if source == "sandbox":
            return "sample"
        raise HTTPException(
            status_code=401,
            detail="Kite session is missing or expired. Sign in again to continue.",
        )
    return user_id


def _job_source(job: dict) -> str:
    job_type = job.get("job_type") or ""
    parts = job_type.split(":")
    source = parts[1] if len(parts) > 1 else "sample"
    return source if source in {"sample", "sandbox", "live"} else "sample"


def _ensure_job_access(request: Request, job: dict) -> None:
    source = _job_source(job)
    if source == "sample":
        return
    user_id = _resolve_request_user(request, source, None)
    if user_id != str(job.get("portfolio_id")):
        raise HTTPException(status_code=404, detail="Job not found.")


def _set_kite_cookie(response, name: str, value: str, max_age: int, path: str) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=sandbox_redirect_url().startswith("https://"),
        samesite="lax",
        path=path,
    )


@app.get("/api/kite/sandbox/login")
async def kite_sandbox_login():
    state = create_oauth_state()
    response = RedirectResponse(sandbox_login_url(state), status_code=302)
    _set_kite_cookie(
        response,
        KITE_OAUTH_COOKIE,
        state,
        600,
        "/api/kite/sandbox/callback",
    )
    return response


@app.get("/api/kite/sandbox/callback")
async def kite_sandbox_callback(
    request: Request,
    request_token: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    cookie_state = request.cookies.get(KITE_OAUTH_COOKIE)
    if not validate_oauth_state(state, cookie_state):
        raise HTTPException(status_code=400, detail="Invalid or expired Kite login state.")
    if error:
        raise HTTPException(status_code=400, detail="Kite sandbox login was not completed.")
    if not request_token:
        raise HTTPException(
            status_code=400,
            detail="Kite callback did not include a request token.",
        )

    checksum = hashlib.sha256(
        f"{SANDBOX_API_KEY}{request_token}{SANDBOX_API_SECRET}".encode("utf-8")
    ).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SANDBOX_ROOT}/session/token",
                headers={"X-Kite-Version": "3"},
                data={
                    "api_key": SANDBOX_API_KEY,
                    "request_token": request_token,
                    "checksum": checksum,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Kite sandbox token exchange failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Kite sandbox token exchange failed.",
        ) from exc

    if not isinstance(payload, dict):
        logger.warning("Kite sandbox token exchange returned a non-object response.")
        raise HTTPException(
            status_code=502,
            detail="Kite sandbox did not return a valid session.",
        )
    data = payload.get("data")
    user_id = data.get("user_id") if isinstance(data, dict) else None
    access_token = data.get("access_token") if isinstance(data, dict) else None
    if payload.get("status") != "success" or not user_id or not access_token:
        logger.warning("Kite sandbox token exchange returned an invalid response.")
        raise HTTPException(
            status_code=502,
            detail="Kite sandbox did not return a valid session.",
        )

    expires_at = persist_sandbox_session(str(user_id), str(access_token))
    session_cookie = create_session_cookie(str(user_id), expires_at)
    response = JSONResponse(
        {
            "status": "connected",
            "environment": "sandbox",
            "expires_at": expires_at.isoformat(),
        }
    )
    max_age = max(
        0,
        int((expires_at - datetime.now(timezone.utc)).total_seconds()),
    )
    _set_kite_cookie(
        response,
        KITE_SESSION_COOKIE,
        session_cookie,
        max_age,
        "/",
    )
    response.delete_cookie(
        KITE_OAUTH_COOKIE,
        path="/api/kite/sandbox/callback",
        secure=sandbox_redirect_url().startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/api/insight/{user_id}")
async def get_portfolio_insight(user_id: str, background_tasks: BackgroundTasks):
    try:
        context = await build_financial_context(user_id)
        if "error" in context:
            raise HTTPException(status_code=400, detail=context["error"])

        insight = generate_financial_insight(context)
        if "error" in insight:
            raise HTTPException(status_code=502, detail=insight["error"])

        validated_insight = detect_hallucinations(insight, context)
        if "error" in validated_insight:
            raise HTTPException(status_code=422, detail=validated_insight["error"])

        from backend.services.queue_service import process_insight_async
        background_tasks.add_task(process_insight_async, user_id, validated_insight)
        return validated_insight
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/portfolio-analysis", status_code=status.HTTP_202_ACCEPTED)
async def create_portfolio_analysis(
    request: PortfolioAnalysisRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    user_id = _resolve_request_user(http_request, request.source, request.user_id)
    submission = await submit_portfolio_analysis(
        user_id,
        request.source,
        request.timeframe,
    )
    background_tasks.add_task(
        process_portfolio_analysis,
        submission["job_id"],
        user_id,
    )
    return submission


@app.post("/api/market-refresh")
async def market_refresh(request: MarketRefreshRequest, http_request: Request):
    try:
        user_id = _resolve_request_user(http_request, request.source, request.user_id)
        return await refresh_market_data(
            user_id,
            request.source,
            request.timeframe,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/mcp/tools/execute")
async def execute_mcp_tool_route(request: MCPToolRequest, http_request: Request):
    try:
        arguments = dict(request.arguments)
        if request.name == "fetch_portfolio":
            source = arguments.get("source", "sample")
            arguments["user_id"] = _resolve_request_user(
                http_request,
                source,
                arguments.get("user_id"),
            )
        return await execute_mcp_tool(request.name, arguments, request.job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/analytics/run")
async def run_analytics_route(request: AnalyticsRequest):
    try:
        return await run_analytics(
            request.holdings,
            request.market_data,
            request.job_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/insights/generate")
async def generate_insight_route(request: JobRequest, http_request: Request):
    try:
        job = await asyncio.to_thread(get_job, request.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        _ensure_job_access(http_request, job)
        result = await generate_insight_for_job(request.job_id)
        if result.get("status") == "empty_portfolio":
            return {"job_id": request.job_id, **result}
        return {
            "job_id": request.job_id,
            "insight_id": result["id"],
            "insight": result["insight"],
            "embedding_stored": result["embedding_stored"],
        }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/recommendations/generate")
async def generate_recommendations_route(request: JobRequest, http_request: Request):
    try:
        job = await asyncio.to_thread(get_job, request.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        _ensure_job_access(http_request, job)
        cards = await generate_and_persist_recommendations(request.job_id)
        return {"job_id": request.job_id, "recommendations": cards}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/insights/{job_id}")
async def get_insights_for_job(job_id: str, request: Request):
    job = await asyncio.to_thread(get_job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _ensure_job_access(request, job)
    result = await get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result


@app.post("/api/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(request: FeedbackRequest, http_request: Request):
    try:
        card_job = await asyncio.to_thread(
            get_recommendation_card_job,
            request.card_id,
        )
        if card_job and card_job.get("job_type"):
            _ensure_job_access(http_request, card_job)
        return record_feedback(request.card_id, request.action, request.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/audit/{job_id}")
async def get_job_audit(job_id: str, request: Request):
    job = await asyncio.to_thread(get_job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _ensure_job_access(request, job)
    events = await asyncio.to_thread(get_audit_trail_for_job, job_id)
    feedback = await asyncio.to_thread(get_feedback_summary_by_job, job_id)
    timed_events = [
        float(event["latency_ms"])
        for event in events
        if event.get("latency_ms") is not None
    ]
    failed_events = sum(1 for event in events if event.get("status") == "error")
    return {
        "job_id": job_id,
        "job": job,
        "events": events,
        "operations": {
            "event_count": len(events),
            "failed_event_count": failed_events,
            "failure_rate_pct": (
                round(failed_events / len(events) * 100, 2) if events else 0
            ),
            "average_latency_ms": (
                round(sum(timed_events) / len(timed_events), 2)
                if timed_events
                else None
            ),
            "feedback": feedback,
        },
    }
