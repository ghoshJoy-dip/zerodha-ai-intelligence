import json
import os
from pathlib import Path

def get_portfolio_snapshot(user_id: str) -> dict:
    """
    Retrieves the portfolio snapshot for a given user.
    Simulates a database or broker API call (e.g., Kite Connect).
    """
    # Resolve the path to the data folder
    base_dir = Path(__file__).resolve().parent.parent.parent
    file_path = base_dir / "data" / "sample_portfolios.json"
    
    if not file_path.exists():
        return {"status": "error", "message": f"Portfolio database not found at {file_path}"}
        
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            
        user_data = data.get(user_id)
        if not user_data:
            return {"status": "error", "message": "User portfolio not found."}
            
        holdings = user_data.get("holdings", [])
        symbols = [item["symbol"] for item in holdings]
        
        # Calculate base metrics
        total_invested = sum(item["quantity"] * item["average_buy_price"] for item in holdings)
        
        return {
            "status": "success",
            "portfolio_id": user_data["portfolio_id"],
            "risk_profile": user_data.get("risk_profile", "unknown"),
            "symbols": symbols,
            "total_invested_value": round(total_invested, 2),
            "holdings": holdings
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test the extraction
    result = get_portfolio_snapshot("user_123")
    import json as json_lib
    print(json_lib.dumps(result, indent=2))