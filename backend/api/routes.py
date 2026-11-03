from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from ai_workflows.context_builder.builder import build_financial_context
from ai_workflows.llm_analysis.gemini_client import generate_financial_insight
from ai_workflows.validation.validator import detect_hallucinations
from backend.services.queue_service import process_insight_async

app = FastAPI(title="Zerodha AI Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "active", "service": "Zerodha AI Backend"}

@app.get("/api/insight/{user_id}")
async def get_portfolio_insight(user_id: str, background_tasks: BackgroundTasks):
    try:
        # Step 1: Gather live context
        context = await build_financial_context(user_id)
        if "error" in context:
            raise HTTPException(status_code=400, detail=context["error"])
            
        # Step 2: Generate the insight
        insight = generate_financial_insight(context)
        if "error" in insight:
            raise HTTPException(status_code=502, detail=insight["error"])
            
        # Step 3: Validate against hallucinations
        validated_insight = detect_hallucinations(insight, context)
        if "error" in validated_insight:
             raise HTTPException(status_code=422, detail=validated_insight["error"])
             
        # Step 4: Dispatch background jobs (DB logging, recommendation triggers)
        background_tasks.add_task(process_insight_async, user_id, validated_insight)
             
        return validated_insight
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))