import os
import json
import sys
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Explicitly add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# All custom imports MUST go below the sys.path.append
from ai_workflows.context_builder.builder import build_financial_context
from ai_workflows.prompt_templates.insight_prompt import build_insight_prompt

# Load environment variables
load_dotenv()

def generate_financial_insight(context_data: dict, max_retries: int = 3) -> dict:
    """
    Sends the compiled financial context to Gemini using the modern google-genai SDK.
    Includes exponential backoff and a model fallback mechanism for 503 errors.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is missing from the .env file."}
    
    # Load model configuration from .env
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    
    client = genai.Client(api_key=api_key)
    
    schema_path = project_root / "data" / "insight_schema.json"
    with open(schema_path, "r") as f:
        insight_schema = json.load(f)

    prompt = build_insight_prompt(context_data)

    current_model = primary_model

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=insight_schema,
                    temperature=0.1
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"  -> Server busy with {current_model}. Switching to fallback model and retrying in {wait_time} seconds (Attempt {attempt + 2}/{max_retries})...")
                    # Downgrade to the lighter model for subsequent attempts
                    current_model = fallback_model 
                    time.sleep(wait_time)
                    continue
            return {"error": f"LLM Generation failed: {error_msg}"}

if __name__ == "__main__":
    import asyncio

    async def test_llm():
        import warnings
        warnings.filterwarnings('ignore', category=FutureWarning)
        
        print("1. Gathering Live Context from Tools...")
        context = await build_financial_context("user_123")
        
        if "error" in context:
            print(f"Context Error: {context['error']}")
            return

        print("2. Sending Context to Gemini API (with fallback routing)...")
        insight = generate_financial_insight(context)
        
        print("\n--- Final AI Insight Output ---")
        print(json.dumps(insight, indent=2))

    asyncio.run(test_llm())