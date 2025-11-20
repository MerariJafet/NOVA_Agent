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
