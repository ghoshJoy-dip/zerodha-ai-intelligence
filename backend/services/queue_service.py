import logging
from datetime import datetime, timezone
import sys
from pathlib import Path

# Ensure paths resolve if this is ever called independently
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.recommendation_engine.engine import generate_actionable_steps
from backend.database.connection import save_recommendation_cards

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackgroundQueue")

def process_insight_async(user_id: str, insight: dict):
    """
    Simulates a background worker task that saves the insight 
    and triggers the Recommendation Engine.
    """
    current_time = datetime.now(timezone.utc).isoformat()
    logger.info(f"[{current_time}] QUEUE JOB STARTED: Processing insight for {user_id}")
    
    if insight.get("is_validated"):
        logger.info(f"Saving validated insight '{insight.get('title')}' to database...")
        
        # Trigger recommendation engine
        recommendations = generate_actionable_steps(insight)
        logger.info(f"Generated {len(recommendations)} actionable recommendations.")
        for rec in recommendations:
            logger.info(f" -> {rec['action']} on {rec.get('ticker', 'UNKNOWN')}: {rec['reason']}")
    else:
        validation_reason = insight.get("validation_reason") or "Validation failed."
        confidence = insight.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            confidence = 0.0
        card = {
            "category": insight.get("category") or "Summary Follow-up",
            "title": str(insight.get("title") or "Insight flagged for review")[:255],
            "rationale": f"Downgraded because validation failed: {validation_reason}",
            "confidence": confidence,
            "freshness_ts": datetime.now(timezone.utc),
            "disclaimer": insight.get("disclaimer") or "This insight failed validation and requires review.",
            "metrics_json": {
                "status": "downgraded",
                "is_validated": False,
                "validation_reason": validation_reason,
                "supporting_metrics": insight.get("supporting_metrics", [])
            }
        }
        saved_cards = save_recommendation_cards(None, [card])
        logger.info(
            "Persisted downgraded recommendation card for %s (card_id=%s)",
            user_id,
            saved_cards[0]["id"]
        )
        
    logger.info(f"QUEUE JOB COMPLETE: {user_id}")