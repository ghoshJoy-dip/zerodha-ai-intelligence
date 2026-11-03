import asyncio
import json
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Explicitly add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Import the tools we built
from mcp_server.tools.portfolio_tools import get_portfolio_snapshot
from mcp_server.tools.market_tools import fetch_dynamic_market_data
from mcp_server.tools.news_tools import fetch_news_for_symbols

async def build_financial_context(user_id: str) -> dict:
    """
    Aggregates portfolio holdings, live market data, and recent news into a single context object.
    """
    # 1. Fetch the user's portfolio
    portfolio_data = get_portfolio_snapshot(user_id)
    if portfolio_data.get("status") == "error":
        return {"error": portfolio_data.get("message")}
        
    symbols = portfolio_data.get("symbols", [])
    
    # 2. Fetch market data and news concurrently
    market_task = fetch_dynamic_market_data(symbols, period="5d")
    news_task = fetch_news_for_symbols(symbols, max_articles_per_stock=2)
    
    market_data, news_data = await asyncio.gather(market_task, news_task)
    
    # 3. Assemble the context for the LLM
    llm_context = {
        "portfolio_profile": {
            "risk_tolerance": portfolio_data.get("risk_profile"),
            "total_value": portfolio_data.get("total_invested_value"),
            "holdings": portfolio_data.get("holdings")
        },
        "market_snapshot": market_data.get("data", {}),
        "recent_news": news_data.get("data", {})
    }
    
    return llm_context

def format_context_for_prompt(context_dict: dict) -> str:
    """Converts the dictionary into a clean, indented JSON string for the Gemini prompt."""
    return json.dumps(context_dict, indent=2)

if __name__ == "__main__":
    async def test_builder():
        print("Gathering context... (this takes a few seconds due to rate limits)")
        context = await build_financial_context("user_123")
        print("\n--- Final LLM Context ---")
        print(format_context_for_prompt(context))
        
    asyncio.run(test_builder())