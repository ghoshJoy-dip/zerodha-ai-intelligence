from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ai_workflows.context_builder.builder import build_financial_context
from ai_workflows.llm_analysis.gemini_client import generate_financial_insight

app = FastAPI(title="Zerodha AI Intelligence API")

# Configure CORS so the Next.js frontend can communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Simple endpoint to verify the server is running."""
    return {"status": "active", "service": "Zerodha AI Backend"}

@app.get("/api/insight/{user_id}")
async def get_portfolio_insight(user_id: str):
    """
    1. Fetches portfolio, market, and news data.
    2. Passes it to the Gemini LLM.
    3. Returns the structured JSON insight.
    """
    try:
        # Step 1: Gather the live context
        context = await build_financial_context(user_id)
        if "error" in context:
            raise HTTPException(status_code=400, detail=context["error"])
            
        # Step 2: Generate the insight
        insight = generate_financial_insight(context)
        if "error" in insight:
            raise HTTPException(status_code=502, detail=insight["error"])
            
        return insight
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))