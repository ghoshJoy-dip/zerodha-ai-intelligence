import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.validation.validator import detect_hallucinations

def test_hallucination_detector_flags_mismatch():
    mock_context = {"RELIANCE": {"currentPrice": 1292.0}}
    
    # Simulate an LLM hallucinating a price of 5000
    mock_insight = {
        "supporting_metrics": [{"metric_name": "RELIANCE Latest Close", "metric_value": 5000.0}]
    }
    
    validated = detect_hallucinations(mock_insight, mock_context)
    
    # The detector should return an error key when it catches a hallucination
    assert "error" in validated
    assert "Hallucination Detected" in validated["error"]