import pandas as pd

def calculate_drawdown_and_volatility(price_series: pd.Series) -> dict:
    """
    Calculates the maximum drawdown and flags extreme volatility for a given price series.
    price_series expects a pandas Series of daily closing prices.
    """
    if price_series.empty or len(price_series) < 2:
        return {"error": "Insufficient data"}

    # Calculate daily returns
    daily_returns = price_series.pct_change().dropna()
    
    # Calculate Max Drawdown
    rolling_max = price_series.cummax()
    drawdowns = (price_series - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()

    # Calculate Annualized Volatility (assuming 252 trading days)
    volatility = daily_returns.std() * (252 ** 0.5)
    
    # Latest 1-day drop
    latest_drop = daily_returns.iloc[-1]

    return {
        "max_drawdown_pct": round(float(max_drawdown) * 100, 2),
        "annualized_volatility_pct": round(float(volatility) * 100, 2),
        "latest_daily_return_pct": round(float(latest_drop) * 100, 2),
        # Trigger risk flags based on standard thresholds
        "volatility_alert": bool(volatility > 0.30), # >30% is highly volatile
        "drawdown_alert": bool(max_drawdown < -0.20), # >20% drop from peak
        "sharp_drop_alert": bool(latest_drop < -0.05) # >5% drop in a single day
    }

if __name__ == "__main__":
    # Mock a price crash scenario (100 -> 110 -> 80 -> 75)
    mock_prices = pd.Series([100.0, 110.0, 80.0, 75.0])
    print("Risk Output:", calculate_drawdown_and_volatility(mock_prices))