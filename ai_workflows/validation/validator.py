from typing import Any

def _extract_all_numbers(obj: Any) -> list[float]:
    """Recursively collects numbers from deterministic analytics only."""
    numbers = []
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers.extend(_extract_all_numbers(v))
    elif isinstance(obj, list):
        for item in obj:
            numbers.extend(_extract_all_numbers(item))
    return numbers

def detect_hallucinations(insight: dict, context_data: dict) -> dict:
    """
    Validates LLM-generated insight against grounded pre-computed metrics:
      1. Numeric tolerance comparison against deterministic analytics (abs(a - b) < 0.05).
      2. Ensures regulatory disclaimer string is present and non-empty.
      3. Ensures confidence score is present and bounded in [0.0, 1.0].
      4. Does NOT drop failed insights: marks is_validated=False with validation_reason
         so recommendation engine can downgrade rather than discard.
    """
    if not isinstance(insight, dict):
        return {
            "is_validated": False,
            "validation_reason": "Payload was not a valid dictionary."
        }

    if "error" in insight:
        insight["is_validated"] = False
        insight["validation_reason"] = f"LLM returned an error: {insight['error']}"
        return insight

    # 1. Verify Disclaimer
    disclaimer = insight.get("disclaimer")
    if not disclaimer or not isinstance(disclaimer, str) or len(disclaimer.strip()) < 10:
        insight["is_validated"] = False
        insight["validation_reason"] = "Missing or insufficient regulatory disclaimer."
        return insight

    # 2. Verify Confidence Score
    confidence = insight.get("confidence")
    if confidence is None or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        insight["is_validated"] = False
        insight["validation_reason"] = f"Invalid confidence score: {confidence}. Must be between 0.0 and 1.0."
        return insight

    # 3. Ground only against computed analytics, not raw portfolio or market values.
    analytics = context_data.get("deterministic_analytics", {})
    context_numbers = _extract_all_numbers(analytics)
    metrics = insight.get("supporting_metrics", [])
    
    if not metrics:
        insight["is_validated"] = False
        insight["validation_reason"] = "No supporting metrics provided by the LLM."
        return insight

    for metric in metrics:
        val = metric.get("metric_value")
        if val is None or not isinstance(val, (int, float)):
            insight["is_validated"] = False
            insight["validation_reason"] = f"Invalid metric value in metric: {metric.get('metric_name')}"
            return insight

        float_val = float(val)

        matched = any(abs(float_val - c_num) < 0.05 for c_num in context_numbers)

        if not matched:
            metric_name = metric.get("metric_name", "Unknown")
            insight["is_validated"] = False
            insight["validation_reason"] = (
                f"Numeric Grounding Failed: Cited metric '{metric_name}' value {float_val} "
                f"does not match deterministic analytics in context (absolute tolerance 0.05)."
            )
            return insight

    # All checks passed
    insight["is_validated"] = True
    insight["validation_reason"] = "Passed all mathematical grounding, disclaimer, and confidence checks."
    return insight
