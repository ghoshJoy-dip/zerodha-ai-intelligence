import json

def build_insight_prompt(context_data: dict) -> str:
    """
    Generates the strict system prompt for the Zerodha Intelligence Platform.
    """
    return f"""
    You are an expert financial AI for the Zerodha Intelligence Platform. 
    Analyze the following portfolio, live market data, and recent news.
    Provide a structured financial insight based strictly on the data provided. Do not hallucinate external numbers.
    Focus on risk, diversification, or recent news impacts.
    
    Data Context:
    {json.dumps(context_data, indent=2)}
    """