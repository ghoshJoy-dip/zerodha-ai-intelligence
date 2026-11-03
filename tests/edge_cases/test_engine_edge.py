import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.recommendation_engine.engine import generate_actionable_steps

def test_engine_unvalidated_insight():
    # Simulate an insight that failed the hallucination check
    mock_insight = {
        "is_validated": False,
        "category": "Risk Alert"
    }
    
    steps = generate_actionable_steps(mock_insight)
    
    assert len(steps) == 1
    assert steps[0]["action"] == "HOLD"
    assert "manual validation" in steps[0]["reason"]