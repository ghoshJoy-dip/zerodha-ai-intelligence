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

    return {
        "total_portfolio_value": float(total_value),
        "hhi_concentration_score": float(hhi),
        "is_highly_concentrated": bool(hhi > 0.25),
        "top_sectors_exposure_pct": top_sectors_dict
    }

if __name__ == "__main__":
    # Quick local test
    mock_data = pd.DataFrame({
        "symbol": ["TCS", "INFY", "RELIANCE", "HDFCBANK"],
        "sector": ["IT", "IT", "Energy", "Banking"],
        "current_value": [40000, 35000, 15000, 10000]
    })
    
    print("Test Output:", calculate_sector_concentration(mock_data))