import asyncio
from datetime import datetime, timezone
from ddgs import DDGS

async def fetch_news_for_symbols(portfolio_symbols: list, max_articles_per_stock: int = 3) -> dict:
    """
    Fetches the latest news headlines using DuckDuckGo for the specific stocks.
    """
    if not portfolio_symbols:
        return {"status": "error", "message": "No symbols provided for news fetch."}

    news_context = {}
    anomalies = []

    def fetch_single_ticker_news(symbol: str):
        try:
            query = f"{symbol} share price market news India"
            
            ddgs = DDGS()
            search_results = ddgs.news(query, max_results=max_articles_per_stock)
            
            parsed_articles = []
            if search_results:
                for item in search_results:
                    parsed_articles.append({
                        "title": item.get("title", "No Title"),
                        "publisher": item.get("source", "Unknown"),
                        "link": item.get("url", ""),
                        "timestamp": item.get("date", "")
                    })
            return symbol, parsed_articles
        except Exception as e:
            return symbol, f"Error: {str(e)}"

    loop = asyncio.get_running_loop()
    
    # Sequential fetching to prevent 403 Rate Limit blocks
    for symbol in portfolio_symbols:
        result_symbol, data = await loop.run_in_executor(None, fetch_single_ticker_news, symbol)
        
        if isinstance(data, str) and data.startswith("Error"):
            anomalies.append(f"{result_symbol}: {data}")
        else:
            news_context[result_symbol] = data
            
        # Pause for 2 seconds before the next query to avoid IP bans
        await asyncio.sleep(2)

    return {
        "status": "success",
        "freshness_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data": news_context,
        "anomalies": anomalies
    }

if __name__ == "__main__":
    async def run_test():
        test_symbols = ["TCS", "RELIANCE"]
        result = await fetch_news_for_symbols(test_symbols)
        import json
        print(json.dumps(result, indent=2))

    asyncio.run(run_test())