def detect_hallucinations(insight: dict, context_data: dict) -> dict:
    """
    Cross-references the metrics in the LLM insight against the raw context data.
    Flags or rejects the insight if the AI invented numbers.
    """
    if "error" in insight:
        return insight

    metrics = insight.get("supporting_metrics", [])
    context_str = str(context_data) 
    
    for metric in metrics:
        val = metric.get("metric_value")
        # Flag if the specific number the AI cited isn't in the raw data
        if val is not None and str(val) not in context_str:
             return {
                 "error": f"Hallucination Detected: Metric '{metric.get('metric_name')}' with value {val} not found in source data."
             }
             
    insight["is_validated"] = True
    return insight