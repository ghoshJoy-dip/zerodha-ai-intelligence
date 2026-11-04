import os
import logging
from typing import Optional
from google import genai
from dotenv import load_dotenv

from backend.database.connection import store_insight_embedding, find_similar_insights

load_dotenv()
logger = logging.getLogger("EmbeddingService")

def get_genai_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def generate_embedding(text: str) -> Optional[list[float]]:
    """Generates a 768-dimensional embedding vector using gemini-embedding-001."""
    client = get_genai_client()
    if not client or not text:
        return None

    try:
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": 768}
        )
        if res.embeddings and len(res.embeddings) > 0:
            return res.embeddings[0].values
        return None
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None

def index_insight(insight_id: int, insight_dict: dict) -> bool:
    """Extracts summary text from an insight and stores its embedding in Supabase."""
    title = insight_dict.get("title", "")
    explanation = insight_dict.get("explanation", "")
    category = insight_dict.get("category", "")
    full_text = f"Category: {category}. Title: {title}. Explanation: {explanation}"

    vector = generate_embedding(full_text)
    if vector:
        store_insight_embedding(insight_id, vector)
        logger.info(f"Stored pgvector embedding for insight {insight_id}")
        return True
    return False

def search_relevant_past_insights(
    context_text: str,
    portfolio_id: str,
    limit: int = 3
) -> list[dict]:
    """Retrieves similar past insights from this portfolio using pgvector."""
    vector = generate_embedding(context_text)
    if not vector:
        return []
    return find_similar_insights(vector, portfolio_id=portfolio_id, limit=limit)
