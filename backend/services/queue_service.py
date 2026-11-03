import logging
from datetime import datetime, timezone
import sys
from pathlib import Path

# Ensure paths resolve if this is ever called independently
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from ai_workflows.recommendation_engine.engine import generate_actionable_steps

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
        logger.warning("Insight not validated. Flagging for manual audit.")
        
    logger.info(f"QUEUE JOB COMPLETE: {user_id}")