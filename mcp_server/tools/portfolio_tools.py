import json
import logging
import os
from pathlib import Path

import httpx

from backend.services.kite_service import (
    LIVE_ROOT,
    SANDBOX_API_KEY,
    SANDBOX_ROOT,
    get_access_token_for_user,
)

logger = logging.getLogger("PortfolioTools")


def _sample_portfolio(user_id: str, fallback_to_first: bool = False) -> dict:
    base_dir = Path(__file__).resolve().parent.parent.parent
    file_path = base_dir / "data" / "sample_portfolios.json"
    if not file_path.exists():
        return {"status": "error", "message": f"Portfolio database not found at {file_path}"}

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not data:
        return {"status": "error", "message": "Sample portfolio data is empty or invalid."}
    user_data = data.get(user_id)
    if user_data is None and fallback_to_first:
        user_data = next(iter(data.values()))
    if not user_data:
        return {"status": "error", "message": "User portfolio not found."}

    holdings = user_data.get("holdings", [])
    symbols = [item["symbol"] for item in holdings]
    total_invested = sum(
        item["quantity"] * item["average_buy_price"] for item in holdings
    )
    return {
        "status": "success",
        "portfolio_id": user_data["portfolio_id"],
        "risk_profile": user_data.get("risk_profile", "unknown"),
        "symbols": symbols,
        "total_invested_value": round(total_invested, 2),
        "holdings": holdings,
        "source": "sample",
    }


def _sample_fallback(user_id: str, requested_source: str, reason: str) -> dict:
    sample = _sample_portfolio(user_id, fallback_to_first=True)
    if sample.get("status") != "success":
        return sample
    return {
        **sample,
        "requested_source": requested_source,
        "fallback_reason": reason,
        "connection_status": "reconnect_needed" if reason != "not_connected" else "not_connected",
        "fallback_available": True,
        "relogin_path": (
            "/api/kite/sandbox/login"
            if requested_source == "sandbox"
            else None
        ),
    }


def _normalize_kite_holdings(data: list[dict]) -> list[dict]:
    holdings = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Kite returned a malformed holding.")
        symbol = item.get("tradingsymbol")
        if not symbol:
            continue
        quantity = item.get("quantity", 0)
        average_price = item.get("average_price", item.get("buy_price", 0))
        holdings.append(
            {
                "symbol": str(symbol),
                "sector": item.get("sector", "Unknown"),
                "quantity": float(quantity or 0),
                "average_buy_price": float(average_price or 0),
            }
        )
    return holdings


def _kite_portfolio(user_id: str, source: str) -> dict:
    if source not in {"sandbox", "live"}:
        raise ValueError(f"Unsupported portfolio source '{source}'.")
    access_token, connection_status = get_access_token_for_user(user_id, source)
    if not access_token:
        return _sample_fallback(user_id, source, connection_status)

    if source == "sandbox":
        api_root = SANDBOX_ROOT
        api_key = SANDBOX_API_KEY
    elif source == "live":
        api_root = LIVE_ROOT
        api_key = os.getenv("KITE_API_KEY")
        if not api_key:
            raise RuntimeError("KITE_API_KEY is required to fetch live Kite holdings.")
    else:
        raise ValueError(f"Unsupported portfolio source '{source}'.")

    try:
        response = httpx.get(
            f"{api_root}/portfolio/holdings",
            headers={
                "X-Kite-Version": "3",
                "Authorization": f"token {api_key}:{access_token}",
            },
            timeout=10.0,
        )
        if response.status_code in (401, 403):
            logger.warning("Kite %s session was rejected for user %s.", source, user_id)
            return _sample_fallback(user_id, source, "reconnect_needed")
        response.raise_for_status()
        payload = response.json()
        if (
            not isinstance(payload, dict)
            or payload.get("status") != "success"
            or not isinstance(payload.get("data"), list)
        ):
            logger.warning("Kite %s holdings response was invalid for user %s.", source, user_id)
            return _sample_fallback(user_id, source, "kite_unavailable")
        holdings = _normalize_kite_holdings(payload["data"])
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Kite %s holdings unavailable for user %s: %s", source, user_id, exc)
        return _sample_fallback(user_id, source, "kite_unavailable")

    symbols = [holding["symbol"] for holding in holdings]
    if not holdings:
        return {
            "status": "empty_portfolio",
            "message": "No holdings found in this account.",
            "user_id": user_id,
            "portfolio_id": f"kite:{source}:{user_id}",
            "risk_profile": "moderate",
            "symbols": [],
            "holdings": [],
            "source": source,
            "connection_status": "connected",
            "fallback_available": True,
            "fallback_source": "sample",
            "fallback_action": "Select Sample as the portfolio source to continue with demo holdings.",
        }

    total_invested = sum(
        holding["quantity"] * holding["average_buy_price"] for holding in holdings
    )
    return {
        "status": "success",
        "portfolio_id": f"kite:{source}:{user_id}",
        "risk_profile": "moderate",
        "symbols": symbols,
        "total_invested_value": round(total_invested, 2),
        "holdings": holdings,
        "source": source,
        "connection_status": "connected",
        "fallback_available": True,
        "fallback_source": "sample",
    }


def get_portfolio_snapshot(user_id: str, source: str = "sample") -> dict:
    """
    Retrieves sample or user-scoped Kite holdings. Market prices are fetched separately.
    """
    if source == "sample":
        return _sample_portfolio(user_id)
    return _kite_portfolio(user_id, source)

if __name__ == "__main__":
    # Test the extraction
    result = get_portfolio_snapshot("user_123")
    import json as json_lib
    print(json_lib.dumps(result, indent=2))