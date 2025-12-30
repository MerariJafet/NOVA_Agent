from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    has_image: bool = False

class ChatResponse(BaseModel):
    response: str
    model_used: str
    router_confidence: int

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: int
    rating: int
    comment: Optional[str] = None

class AgentQueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class MetricsResponse(BaseModel):
    model: str
    avg_rating: Optional[float] = None
    feedback_count: int = 0
