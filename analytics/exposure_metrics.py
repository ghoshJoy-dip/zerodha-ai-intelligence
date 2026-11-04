import pandas as pd
import numpy as np

def calculate_sector_concentration(portfolio_df: pd.DataFrame) -> dict:
    """
    Calculates portfolio sector exposure and Herfindahl-Hirschman Index (HHI) for concentration risk.
    portfolio_df expects columns: ['symbol', 'sector', 'current_value']
    """
    if portfolio_df.empty or 'current_value' not in portfolio_df.columns:
        return {"error": "Invalid portfolio data"}

    total_value = portfolio_df['current_value'].sum()
    if total_value <= 0:
        return {"error": "Total portfolio value is zero or negative"}
    
    # Calculate weight per sector
    sector_group = portfolio_df.groupby('sector')['current_value'].sum().reset_index()
    sector_group['weight'] = sector_group['current_value'] / total_value
    
    # Herfindahl-Hirschman Index (HHI) - sum of squared weights
    # HHI > 0.25 generally indicates high concentration
    hhi = (sector_group['weight'] ** 2).sum()
    
    # Get top 3 sectors
    top_sectors = sector_group.sort_values(by='weight', ascending=False).head(3)
    top_sectors_dict = {
        row['sector']: round(row['weight'] * 100, 2) 
        for _, row in top_sectors.iterrows()
    }

    # Single sector concentration check (>40% is high risk)
    top_sector_weight = top_sectors.iloc[0]['weight'] if not top_sectors.empty else 0.0

    return {
        "total_portfolio_value": float(total_value),
        "hhi_concentration_score": round(float(hhi), 4),
        "is_highly_concentrated": bool(hhi > 0.25 or top_sector_weight > 0.40),
        "top_sector": top_sectors.iloc[0]['sector'] if not top_sectors.empty else None,
        "top_sector_weight_pct": round(top_sector_weight * 100, 2),
        "top_sectors_exposure_pct": top_sectors_dict
    }

def calculate_holdings_attribution(holdings: list, market_data: dict) -> dict:
    """
    Computes stock-level weight, unrealized P&L, 1-day P&L contribution,
    and identifies the primary drivers of portfolio movement.
    """
    if not holdings:
        return {"error": "No holdings provided for attribution"}

    stock_rows = []
    total_invested = 0.0
    total_current = 0.0

    for item in holdings:
        sym = item.get("symbol")
        qty = float(item.get("quantity", 0))
        buy_px = float(item.get("average_buy_price", 0))
        sec = item.get("sector", "Other")

        # Get latest market close
        sym_data = market_data.get(sym, {})
        latest_px = float(sym_data.get("latest_close", buy_px))
        pct_1d = float(sym_data.get("1d_change_pct", 0.0))

        invested_val = qty * buy_px
        curr_val = qty * latest_px
        unrealized_pnl = curr_val - invested_val
        unrealized_pnl_pct = ((latest_px - buy_px) / buy_px * 100) if buy_px > 0 else 0.0

        total_invested += invested_val
        total_current += curr_val

        stock_rows.append({
            "symbol": sym,
            "sector": sec,
            "quantity": qty,
            "average_buy_price": buy_px,
            "current_price": latest_px,
            "current_value": curr_val,
            "invested_value": invested_val,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "1d_change_pct": round(pct_1d, 2),
            # 1-day cash impact approx: curr_val - (curr_val / (1 + pct_1d/100))
            "1d_pnl_impact": round(curr_val * (pct_1d / 100.0), 2)
        })

    if total_current <= 0:
        return {"error": "Total portfolio current value is zero or negative"}

    # Calculate weight and 1-day weighted contribution
    for r in stock_rows:
        weight = r["current_value"] / total_current
        r["portfolio_weight_pct"] = round(weight * 100, 2)
        r["1d_weighted_contribution_pct"] = round(weight * r["1d_change_pct"], 2)

    # Sort to find top gainers and top laggards
    sorted_by_impact = sorted(stock_rows, key=lambda x: x["1d_weighted_contribution_pct"], reverse=True)
    top_gainer = sorted_by_impact[0] if sorted_by_impact else None
    top_laggard = sorted_by_impact[-1] if sorted_by_impact else None

    overall_unrealized_pnl = total_current - total_invested
    overall_pnl_pct = (overall_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0.0

    return {
        "total_invested_value": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "overall_unrealized_pnl": round(overall_unrealized_pnl, 2),
        "overall_unrealized_pnl_pct": round(overall_pnl_pct, 2),
        "stock_attributions": stock_rows,
        "top_mover_gainer": {
            "symbol": top_gainer["symbol"],
            "1d_change_pct": top_gainer["1d_change_pct"],
            "contribution_pct": top_gainer["1d_weighted_contribution_pct"]
        } if top_gainer else None,
        "top_mover_laggard": {
            "symbol": top_laggard["symbol"],
            "1d_change_pct": top_laggard["1d_change_pct"],
            "contribution_pct": top_laggard["1d_weighted_contribution_pct"]
        } if top_laggard else None
    }
