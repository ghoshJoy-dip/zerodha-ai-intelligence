import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.recommendation_engine.engine import generate_actionable_steps

def test_recommendation_engine_risk_alert():
    mock_insight = {
        "is_validated": True,
        "category": "Risk Alert",
        "supporting_metrics": [{"metric_name": "RELIANCE Latest Close", "metric_value": 1292.0}]
    }
    
    steps = generate_actionable_steps(mock_insight)
    
    assert len(steps) == 2
    assert steps[0]["action"] == "REVIEW_HEDGE"
    assert steps[0]["ticker"] == "RELIANCE"
    assert steps[1]["action"] == "REBALANCE"
    assert steps[1]["ticker"] == "PORTFOLIO"