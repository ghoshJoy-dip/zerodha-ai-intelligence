import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Resolve paths to allow root imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.api.routes import app

client = TestClient(app)

def test_get_portfolio_insight():
    """
    End-to-end test verifying the FastAPI route, context builder, 
    LLM generation, and hallucination validator.
    """
    response = client.get("/api/insight/user_123")
    
    # 1. Verify successful HTTP status
    assert response.status_code == 200
    
    # 2. Extract JSON payload
    data = response.json()
    
    # 3. Verify the hallucination detector approved the output
    assert data.get("is_validated") is True
    
    # 4. Verify core schema components exist
    assert "category" in data
    assert "title" in data
    assert "supporting_metrics" in data
    assert len(data["supporting_metrics"]) > 0