from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from nova.api.models import ChatRequest, ChatResponse
from nova.core import orquestador
from nova.core.memoria import init_db, save_conversation
from nova.core import feedback_system
from nova.api.models import FeedbackRequest, MetricsResponse
from utils.logging import get_logger
from config.settings import settings
from nova.api.middleware import setup_middlewares, simple_rate_limit_middleware
from nova.core.auto_optimizer import auto_optimize, get_current_priorities, get_optimization_history
import threading
import time
from nova.core.cache_system import cache_system

logger = get_logger("api.routes")

# Auto-tuning service global
auto_tuning_thread = None
auto_tuning_active = False
auto_tuning_stats = {"cycles": 0, "last_run": None, "status": "stopped"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("app_startup")
    yield
    # Shutdown
    logger.info("app_shutdown")

app = FastAPI(title=settings.app_name, lifespan=lifespan)

setup_middlewares(app)
simple_rate_limit_middleware(app)


@app.post("/chat")
async def chat(request: ChatRequest):
    routing = orquestador.route_query(request.message, request.has_image)
    # If router asks for clarification, return the clarifying shape and DO NOT generate a model response
    if routing.get("status") == "needs_clarification":
        return {"status": "clarify", "message": routing.get("message")}

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


@app.get("/dashboard")
async def dashboard():
    """Dashboard HTML definitivo de NOVA con métricas completas y auto-refresh"""
    try:
        init_db()

        # Obtener métricas básicas
        from nova.core import memoria
        with memoria._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM messages")
            total_messages = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM feedback")
            total_feedback = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM response_cache")
            total_cache_entries = c.fetchone()[0]

        # Obtener estado de auto-tuning
        auto_tuning_status = get_auto_tuning_status_sync()

        # Obtener métricas de caché
        from nova.core.cache_system import cache_system
        cache_stats = cache_system.get_cache_stats()

        # HTML moderno pero más simple
        html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 NOVA Dashboard - Sistema Inteligente</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            color: #333;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .metric-value {{
            font-weight: bold;
            font-size: 1.2em;
        }}
        .status-active {{ color: #48bb78; }}
        .status-inactive {{ color: #a0aec0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 NOVA - Dashboard Inteligente</h1>
            <p>Auto-refresh cada 30s | Última actualización: {current_time}</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>📊 Sistema General</h3>
                <div class="metric">
                    <span>Mensajes Totales</span>
                    <span class="metric-value">{total_messages}</span>
                </div>
                <div class="metric">
                    <span>Feedback Recibido</span>
                    <span class="metric-value">{total_feedback}</span>
                </div>
                <div class="metric">
                    <span>Entradas en Caché</span>
                    <span class="metric-value">{total_cache_entries}</span>
                </div>
            </div>

            <div class="card">
                <h3>⚡ Caché Inteligente</h3>
                <div class="metric">
                    <span>Hit Rate</span>
                    <span class="metric-value">{hit_rate:.1f}%</span>
                </div>
                <div class="metric">
                    <span>Entradas Válidas</span>
                    <span class="metric-value">{valid_entries}</span>
                </div>
                <div class="metric">
                    <span>Tamaño</span>
                    <span class="metric-value">{size_mb:.1f}MB</span>
                </div>
            </div>

            <div class="card">
                <h3>🎯 Auto-Optimización</h3>
                <div class="metric">
                    <span>Estado</span>
                    <span class="metric-value {status_class}">
                        {status_text}
                    </span>
                </div>
                <div class="metric">
                    <span>Ciclos Ejecutados</span>
                    <span class="metric-value">{cycles}</span>
                </div>
            </div>

            <div class="card">
                <h3>🤖 Modelos y Prioridades</h3>
{models_html}
            </div>
        </div>
    </div>
</body>
</html>"""

        # Generar HTML para modelos
        models_html = ""
        for model, priority in auto_tuning_status['current_priorities'].items():
            models_html += f"""
                <div class="metric">
                    <span>{model}</span>
                    <span class="metric-value">{priority}</span>
                </div>"""

        # Formatear el HTML
        html_content = html_template.format(
            current_time=time.strftime('%H:%M:%S'),
            total_messages=f"{total_messages:,}",
            total_feedback=f"{total_feedback:,}",
            total_cache_entries=f"{total_cache_entries:,}",
            hit_rate=cache_stats['hit_rate_percent'],
            valid_entries=f"{cache_stats['valid_entries']:,}",
            size_mb=cache_stats['size_mb'],
            status_class='status-active' if auto_tuning_status['active'] else 'status-inactive',
            status_text='Activo' if auto_tuning_status['active'] else 'Inactivo',
            cycles=f"{auto_tuning_status['stats']['cycles']:,}",
            models_html=models_html
        )

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    except Exception as e:
        return f"Error: {str(e)}"


@app.get("/status")
async def status():
    return {"status": "operational", "version": settings.version, "message": "NOVA vive 🔥"}


# Auto-tuning background function
def auto_tuning_worker(interval_minutes=30):
    """Worker function para auto-tuning continuo"""
    global auto_tuning_active, auto_tuning_stats

    logger.info(f"🔄 Iniciando auto-tuning continuo (cada {interval_minutes} minutos)")

    while auto_tuning_active:
        try:
            # Ejecutar optimización
            result = auto_optimize(max_change=20, min_feedback=5)
            auto_tuning_stats["cycles"] += 1
            auto_tuning_stats["last_run"] = time.time()

            if result["status"] == "optimized":
                logger.info(f"✅ Auto-tuning: {len(result['changes_applied'])} cambios aplicados")
                for change in result["changes_applied"]:
                    logger.info(f"   {change['model']}: {change['old_priority']} → {change['new_priority']}")
            else:
                logger.debug(f"📭 Auto-tuning: {result['status']}")

        except Exception as e:
            logger.error(f"❌ Error en auto-tuning: {e}")

        # Esperar hasta el próximo ciclo
        time.sleep(interval_minutes * 60)

    logger.info("🛑 Auto-tuning detenido")


@app.post("/auto-tuning/start")
async def start_auto_tuning(interval_minutes: int = 30):
    """Iniciar auto-tuning continuo"""
    global auto_tuning_thread, auto_tuning_active, auto_tuning_stats

    if auto_tuning_active:
        return {"status": "already_running", "message": "Auto-tuning ya está activo"}

    auto_tuning_active = True
    auto_tuning_stats = {"cycles": 0, "last_run": None, "status": "running"}

    # Iniciar thread en background
    auto_tuning_thread = threading.Thread(
        target=auto_tuning_worker,
        args=(interval_minutes,),
        daemon=True
    )
    auto_tuning_thread.start()

    logger.info(f"🚀 Auto-tuning iniciado (intervalo: {interval_minutes} minutos)")
    return {
        "status": "started",
        "message": f"Auto-tuning continuo iniciado cada {interval_minutes} minutos",
        "interval_minutes": interval_minutes
    }


@app.post("/auto-tuning/stop")
async def stop_auto_tuning():
    """Detener auto-tuning continuo"""
    global auto_tuning_active, auto_tuning_stats

    if not auto_tuning_active:
        return {"status": "not_running", "message": "Auto-tuning no está activo"}

    auto_tuning_active = False
    auto_tuning_stats["status"] = "stopped"

    logger.info("🛑 Auto-tuning detenido")
    return {"status": "stopped", "message": "Auto-tuning continuo detenido"}


@app.get("/auto-tuning/status")
async def get_auto_tuning_status():
    """Obtener estado del auto-tuning"""
    global auto_tuning_stats

    return {
        "active": auto_tuning_active,
        "stats": auto_tuning_stats,
        "current_priorities": get_current_priorities(),
        "recent_history": get_optimization_history(limit=5)
    }


def get_auto_tuning_status_sync():
    """Función helper síncrona para obtener estado del auto-tuning"""
    global auto_tuning_stats

    return {
        "active": auto_tuning_active,
        "stats": auto_tuning_stats,
        "current_priorities": get_current_priorities(),
        "recent_history": get_optimization_history(limit=5)
    }


@app.post("/auto-tuning/optimize")
async def manual_optimize(max_change: int = 20, min_feedback: int = 5):
    """Ejecutar optimización manual"""
    try:
        result = auto_optimize(max_change=max_change, min_feedback=min_feedback)

        return {
            "status": "completed",
            "result": result,
            "current_priorities": get_current_priorities()
        }
    except Exception as e:
        logger.error(f"❌ Error en optimización manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))
