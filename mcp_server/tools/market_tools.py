import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
import asyncio
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Nifty 50 and India VIX for benchmark and volatility comparisons
BENCHMARK_INDICES = ["^NSEI", "^INDIAVIX"]

def to_yahoo_format(symbol: str) -> str:
    """Appends .NS for Indian stocks on the NSE."""
    return symbol if symbol.startswith("^") else f"{symbol}.NS"

async def fetch_dynamic_market_data(portfolio_symbols: list, period: str = "1y") -> dict:
    """
    Fetches market data dynamically based ONLY on the user's current holdings.
    """
    if not portfolio_symbols:
        return {"status": "error", "message": "No portfolio symbols provided."}

    all_symbols = [to_yahoo_format(s) for s in portfolio_symbols] + BENCHMARK_INDICES
    tickers_string = " ".join(all_symbols)
    
    try:
        # BATCH FETCH: yfinance downloads all symbols concurrently in one API call
        raw_data = await asyncio.to_thread(
            yf.download, 
            tickers_string, 
            period=period, 
            group_by='ticker', 
            auto_adjust=False,
            threads=True
        )
        
        if raw_data.empty:
            return {"status": "error", "message": "Failed to retrieve market data."}

        market_context = {}
        anomalies = []
        
        for symbol in all_symbols:
            clean_symbol = symbol.replace(".NS", "")
            
            # Handle pandas multi-index depending on number of tickers fetched
            if len(all_symbols) == 1:
                df = raw_data.copy()
            else:
                if symbol not in raw_data.columns.levels[0]:
                    anomalies.append(f"Missing data for {clean_symbol}")
                    continue
                df = raw_data[symbol].copy()
                
            df = df.dropna(subset=['Close'])
            
            if df.empty:
                anomalies.append(f"Missing data for {clean_symbol}")
                continue
                
            # Grab the latest metrics
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            pct_change = ((float(latest['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100
            
            market_context[clean_symbol] = {
                "latest_close": round(float(latest['Close']), 2),
                "1d_change_pct": round(float(pct_change), 2),
                "volume": int(latest['Volume']),
                "high_volatility_flag": abs(pct_change) > 10.0 
            }
            
        return {
            "status": "success",
            "freshness_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "data": market_context,
            "anomalies": anomalies
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test the async function locally
    async def run_test():
        test_symbols = ["TCS", "RELIANCE"]
        result = await fetch_dynamic_market_data(test_symbols, period="5d")
        print("Market Data Fetch Result:")
        import json
        print(json.dumps(result, indent=2))

    asyncio.run(run_test())