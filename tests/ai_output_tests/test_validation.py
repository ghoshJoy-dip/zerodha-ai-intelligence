import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.validation.validator import detect_hallucinations

def test_hallucination_detector_flags_mismatch():
    mock_context = {
        "deterministic_analytics": {"holdings_attribution": {"current_price": 1292.0}}
    }

    # Simulate an LLM hallucinating a price of 5000
    mock_insight = {
        "disclaimer": "This is a valid regulatory disclaimer for testing purposes.",
        "confidence": 0.85,
        "supporting_metrics": [{"metric_name": "RELIANCE Latest Close", "metric_value": 5000.0}]
    }
    
    validated = detect_hallucinations(mock_insight, mock_context)
    
    # In Phase 1: On failure, mark is_validated: false with a reason — do not discard
    assert validated.get("is_validated") is False
    assert "Numeric Grounding Failed" in validated.get("validation_reason", "")

def test_hallucination_detector_approves_within_tolerance():
    mock_context = {
        "deterministic_analytics": {"holdings_attribution": {"current_price": 1292.02}}
    }

    # Cited 1292.0 which is within 0.05 tolerance
    mock_insight = {
        "disclaimer": "This is a valid regulatory disclaimer for testing purposes.",
        "confidence": 0.95,
        "supporting_metrics": [{"metric_name": "RELIANCE Latest Close", "metric_value": 1292.0}]
    }

    validated = detect_hallucinations(mock_insight, mock_context)
    assert validated.get("is_validated") is True

def test_hallucination_detector_does_not_match_raw_context_values():
    mock_context = {
        "portfolio_profile": {"total_invested_value": 1292.0},
        "market_snapshot": {"RELIANCE": {"latest_close": 1292.0}},
        "deterministic_analytics": {"sector_concentration": {"hhi_concentration_score": 0.3}}
    }
    mock_insight = {
        "disclaimer": "This is a valid regulatory disclaimer for testing purposes.",
        "confidence": 0.85,
        "supporting_metrics": [{"metric_name": "RELIANCE Latest Close", "metric_value": 1292.0}]
    }

    validated = detect_hallucinations(mock_insight, mock_context)

    assert validated.get("is_validated") is False
    assert "Numeric Grounding Failed" in validated.get("validation_reason", "")

def test_hallucination_detector_does_not_apply_relative_tolerance():
    mock_context = {
        "deterministic_analytics": {"sector_concentration": {"hhi_concentration_score": 100.0}}
    }
    mock_insight = {
        "disclaimer": "This is a valid regulatory disclaimer for testing purposes.",
        "confidence": 0.85,
        "supporting_metrics": [{"metric_name": "Computed metric", "metric_value": 100.5}]
    }

    validated = detect_hallucinations(mock_insight, mock_context)

    assert validated.get("is_validated") is False
    assert "Numeric Grounding Failed" in validated.get("validation_reason", "")

def test_hallucination_detector_preserves_invalid_payload_as_validation_failure():
    validated = detect_hallucinations(None, {})

    assert validated.get("is_validated") is False
    assert validated.get("validation_reason") == "Payload was not a valid dictionary."
    assert "error" not in validated
