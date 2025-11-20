from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from nova.core.orquestador import route_query, generate_response

app = FastAPI(title="NOVA Core API")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    has_image: bool = False


@app.post("/chat")
async def chat(request: ChatRequest):
    routing = route_query(request.message, request.has_image)
    try:
        response = generate_response(routing["model"], request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"response": response, "model_used": routing["model"], "router_confidence": routing["confidence"]}


@app.get("/status")
async def status():
    return {"status": "operational", "version": "1.0.0-sprint1-mvp", "message": "NOVA vive 🔥"}
