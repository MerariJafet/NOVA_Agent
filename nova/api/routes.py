from fastapi import FastAPI, HTTPException
from nova.api.models import ChatRequest, ChatResponse
from nova.core import orquestador
from nova.core.memoria import init_db, save_conversation
from utils.logging import get_logger
from config.settings import settings
from nova.api.middleware import setup_middlewares, simple_rate_limit_middleware

logger = get_logger("api.routes")

app = FastAPI(title=settings.app_name)

setup_middlewares(app)
simple_rate_limit_middleware(app)


@app.on_event("startup")
def _startup():
    init_db()
    logger.info("app_startup")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    routing = orquestador.route_query(request.message, request.has_image)
    try:
        response = orquestador.generate_response(routing["model"], request.message)
    except Exception as e:
        logger.error("generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # persist conversation: user then assistant
    session_id = request.session_id or "default"
    # ensure DB initialized (safety for test environments)
    init_db()
    save_conversation(session_id, "user", request.message, routing["model"], routing.get("reasoning"))
    save_conversation(session_id, "assistant", response, routing["model"], routing.get("reasoning"))

    logger.info("chat_handled", session_id=session_id, model=routing["model"]) 
    return {"response": response, "model_used": routing["model"], "router_confidence": routing["confidence"]}


@app.get("/status")
async def status():
    return {"status": "operational", "version": settings.version, "message": "NOVA vive 🔥"}
