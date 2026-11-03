from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class UserSettings(BaseModel):
    user_id: str
    risk_tolerance: str = "moderate"

class InsightLogEntry(BaseModel):
    user_id: str
    category: str
    title: str
    confidence: float
    is_validated: bool
    raw_data: Any
    timestamp: datetime = datetime.utcnow()