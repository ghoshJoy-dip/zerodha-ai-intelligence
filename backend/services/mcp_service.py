import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from backend.services.cache_service import cache_service

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHEABLE_TOOLS = {"fetch_market_data", "fetch_news"}


@asynccontextmanager
async def open_mcp_session(job_id: str | None = None) -> AsyncIterator[ClientSession]:
    child_env = os.environ.copy()
    if job_id:
        child_env["MCP_JOB_ID"] = job_id
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(PROJECT_ROOT),
        env=child_env,
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def call_mcp_tool(
    session: ClientSession,
    name: str,
    arguments: dict,
) -> dict:
    cache_key = None
    if name in CACHEABLE_TOOLS:
        cache_key = f"mcp:{name}:{json.dumps(arguments, sort_keys=True, separators=(',', ':'))}"
        cached = cache_service.get(cache_key)
        if cached is not None:
            return cached

    result = await session.call_tool(name, arguments)
    if getattr(result, "is_error", getattr(result, "isError", False)):
        raise RuntimeError(f"MCP tool '{name}' failed: {result.content}")

    structured = getattr(
        result, "structured_content", getattr(result, "structuredContent", None)
    )
    if isinstance(structured, dict):
        value = structured
    else:
        value = None
        for content in result.content:
            text = getattr(content, "text", None)
            if text:
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    value = parsed
                    break
        if value is None:
            raise RuntimeError(f"MCP tool '{name}' returned no JSON object.")

    if cache_key and value.get("status") == "success":
        cache_service.set(cache_key, value)
    return value


async def execute_mcp_tool(name: str, arguments: dict, job_id: str | None = None) -> dict:
    async with open_mcp_session(job_id) as session:
        return await call_mcp_tool(session, name, arguments)
