from fastapi import FastAPI, HTTPException
from nova.api.models import ChatRequest, ChatResponse
from nova.core import orquestador
from nova.core.memoria import init_db, save_conversation
from nova.core import feedback_system
from nova.api.models import FeedbackRequest, MetricsResponse
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


@app.post("/chat")
async def chat(request: ChatRequest):
    routing = orquestador.route_query(request.message, request.has_image)
    # If router asks for clarification, return that directly
    if routing.get("status") == "needs_clarification":
        return {"status": "needs_clarification", "message": routing.get("message")}

    try:
        response = orquestador.generate_response(routing["model"], request.message)
    except Exception as e:
        logger.error("generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # persist conversation: user then assistant
    session_id = request.session_id or "default"
    # ensure DB initialized (safety for test environments)
    init_db()
    user_msg_id = save_conversation(session_id, "user", request.message, routing["model"], routing.get("reasoning"), routing.get("confidence"))
    assistant_msg_id = save_conversation(session_id, "assistant", response, routing["model"], routing.get("reasoning"), routing.get("confidence"))

    logger.info("chat_handled", session_id=session_id, model=routing["model"]) 
    return {"response": response, "model_used": routing["model"], "router_confidence": routing["confidence"]}



@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    init_db()
    fid = feedback_system.record_feedback(req.message_id, req.session_id, req.rating, req.comment)
    return {"status": "ok", "feedback_id": fid}


@app.get("/metrics/routing")
async def metrics_routing():
    init_db()
    perf = feedback_system.analyze_performance()
    return perf


@app.get("/status")
async def status():
    return {"status": "operational", "version": settings.version, "message": "NOVA vive 🔥"}
