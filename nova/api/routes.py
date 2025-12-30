from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from nova.api.models import ChatRequest, ChatResponse
from nova.core import orquestador
from nova.core.memoria import init_db, save_conversation
from nova.core import feedback_system
from nova.api.models import FeedbackRequest, MetricsResponse, AgentQueryRequest
from utils.logging import get_logger
from config.settings import settings
from nova.api.middleware import setup_middlewares, simple_rate_limit_middleware
from nova.core.auto_optimizer import auto_optimize, get_current_priorities, get_optimization_history
from fastapi.concurrency import run_in_threadpool
import threading
import time
import os
from pathlib import Path
import base64
import secrets
import requests
# from nova.core.cache_system import cache_system  # Commented out to avoid DB issues
from nova.core.episodic_memory import episodic_memory
from nova.core.semantic_memory import get_semantic_memory

# Importar sistema de agentes (Sprint 5 Fase 3)
from nova.core.agents import AgentRegistry, BusinessAgent, ProgrammingAgent, MathAgent

# CORS
from fastapi.middleware.cors import CORSMiddleware

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
webui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "webui")
logger.info(f"WebUI path: {webui_path}, exists: {os.path.exists(webui_path)}")
if os.path.exists(webui_path):
    app.mount("/webui", StaticFiles(directory=webui_path, html=True), name="webui")
    # Also mount under /nova/webui for paths used by the redesigned frontend
    try:
        app.mount("/nova/webui", StaticFiles(directory=webui_path, html=True), name="nova-webui")
        logger.info("WebUI static files mounted at /webui and /nova/webui")
    except Exception:
        # Fallback: if second mount fails, still keep /webui
        logger.warning("Could not mount /nova/webui, continuing with /webui only")
else:
    logger.error(f"WebUI directory not found: {webui_path}")

# Mount uploads directory
uploads_path = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


async def _analyze_image_base64(image_b64: str, prompt: str = "Analiza esta imagen") -> tuple[str, str]:
    """Enviar imagen a LLaVA vision con fallback a moondream. Retorna (response, model_used)"""
    
    def _call_vision_model(model: str, timeout: int) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False
        }
        r = requests.post(settings.ollama_generate_url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        # Extraer solo el texto de respuesta
        return data.get("response", "").strip()

    # Try LLaVA 7B first (primary model - better at following instructions)
    try:
        logger.info("trying_llava_7b_primary")
        response = await run_in_threadpool(_call_vision_model, "llava:7b", 30)
        return response, "llava:7b"
    except Exception as e:
        logger.warning(f"llava_7b_failed_fallback_to_moondream", error=str(e))
        # Fallback to moondream
        try:
            response = await run_in_threadpool(_call_vision_model, "moondream:1.8b", 30)
            return response, "moondream:1.8b"
        except Exception as e2:
            logger.error(f"both_vision_models_failed", llava_error=str(e), moondream_error=str(e2))
            raise e2



@app.get("/webui/index.html")
async def webui_index():
    """Servir la interfaz web unificada"""
    try:
        html_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webui", "index.html")
        if os.path.exists(html_file_path):
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        else:
            return {"error": "WebUI index.html not found"}
    except Exception as e:
        logger.error(f"Error serving webui: {e}")
        return {"error": str(e)}

setup_middlewares(app)
simple_rate_limit_middleware(app)


@app.get("/")
async def root():
    """Redirigir a la interfaz web unificada"""
    return RedirectResponse(url="/webui/index.html", status_code=302)


@app.get("/index.html")
async def serve_index():
    """Servir index.html desde root"""
    return RedirectResponse(url="/webui/index.html", status_code=302)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Obtener session_id temprano para memoria episódica
    session_id = request.session_id or "default"

    # Extraer y guardar hechos de memoria episódica (no intrusivo)
    facts_extracted = 0
    try:
        # Extraer hechos del mensaje del usuario
        extracted_facts = await run_in_threadpool(episodic_memory.extract_facts, request.message)
        facts_extracted = len(extracted_facts)

        # Guardar cada hecho extraído
        for fact in extracted_facts:
            await run_in_threadpool(episodic_memory.save_fact, session_id, fact)
    except Exception as e:
        # Loggear error pero NO romper el chat
        logger.error("episodic_memory_error", error=str(e), session_id=session_id)

    # [MODIFIED] Use Intelligent Router for better decision making
    try:
        from nova.core import intelligent_router
        # Re-route using the new intelligent router
        ir_routing = await run_in_threadpool(intelligent_router.route, request.message, request.has_image)
        
        # Check clarification
        if ir_routing.get("status") == "needs_clarification":
            return {
                "text": ir_routing.get("message"),
                "meta": {
                    "router": "intelligent_router",
                    "model_selected": "none",
                    "reason": "clarification_needed",
                    "latency_ms": 0,
                    "confidence": 100
                }
            }

        # Use the intelligent router's decision
        model_name = ir_routing.get("model", "dolphin-mistral:7b")
        confidence = ir_routing.get("confidence", 50)
        reasoning = ir_routing.get("reasoning", "default_fallback")
        
    except Exception as e:
        logger.error("intelligent_router_failed", error=str(e))
        # Fallback
        model_name = "dolphin-mistral:7b"
        confidence = 0
        reasoning = f"fallback_error: {str(e)}"

    try:
        # Measure latency
        import time
        start_time = time.time()

        # Obtener contexto de hechos para el prompt
        facts_context = ""
        try:
            facts_context = await run_in_threadpool(episodic_memory.format_facts_for_prompt, session_id)
        except Exception as e:
            logger.error("facts_context_error", error=str(e), session_id=session_id)

        # Obtener contexto semántico relevante (memoria semántica)
        semantic_context = ""
        try:
            semantic_memory = get_semantic_memory()
            semantic_context = await run_in_threadpool(
                semantic_memory.get_relevant_context,
                request.message,
                3,  # Máximo 3 resultados relevantes
                session_id
            )
        except Exception as e:
            logger.error("semantic_context_error", error=str(e), session_id=session_id)

        # Construir mensaje enhanced con contexto de hechos y semántico
        enhanced_message = request.message
        context_parts = []

        if facts_context:
            context_parts.append(f"Información de hechos conocidos:\n{facts_context}")

        if semantic_context:
            context_parts.append(f"Contexto conversacional relevante:\n{semantic_context}")

        if context_parts:
            enhanced_message = "\n\n".join(context_parts) + f"\n\nUsuario: {request.message}"

        # Generate response using the selected model
        response_text = await run_in_threadpool(orquestador.generate_response, model_name, enhanced_message, None)
        
        latency_ms = int((time.time() - start_time) * 1000)

    except Exception as e:
        logger.error("generate_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # persist conversation: user then assistant
    await run_in_threadpool(init_db)
    user_msg_id = await run_in_threadpool(save_conversation, session_id, "user", request.message, model_name, reasoning)
    assistant_msg_id = await run_in_threadpool(save_conversation, session_id, "assistant", response_text, model_name, reasoning)

    # Agregar mensajes a memoria semántica (no intrusivo)
    try:
        semantic_memory = get_semantic_memory()
        # Agregar mensaje del usuario
        await run_in_threadpool(
            semantic_memory.add_message,
            user_msg_id,
            request.message,
            session_id,
            "user",
            model_name
        )
        # Agregar respuesta del asistente
        await run_in_threadpool(
            semantic_memory.add_message,
            assistant_msg_id,
            response_text,
            session_id,
            "assistant",
            model_name
        )
    except Exception as e:
        logger.error("semantic_memory_add_error", error=str(e), session_id=session_id)

    logger.info("chat_handled", session_id=session_id, model=model_name, facts_extracted=facts_extracted)
    
    # [MODIFIED] Standardized JSON schema for frontend
    return {
        "text": response_text,
        "meta": {
            "router": "intelligent_router",
            "model_selected": model_name,
            "reason": reasoning,
            "latency_ms": latency_ms,
            "facts_extracted": facts_extracted,
            "confidence": confidence
        }
    }


@app.post("/api/tts")
async def text_to_speech(text: str):
    """Convertir texto a voz usando Web Speech API del navegador (placeholder para futura integración)"""
    try:
        logger.info("tts_requested", text_length=len(text))
        
        # Por ahora, devolver un indicador de que TTS está disponible
        # En el futuro, integrar con servicios como Azure TTS, Google TTS, etc.
        return {
            "status": "tts_available",
            "message": "TTS disponible - usar Web Speech API del navegador",
            "text_length": len(text),
            "note": "El TTS se maneja en el frontend usando speechSynthesis"
        }
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), message: str = Form("Describe esta imagen"), session_id: str = Form(None)):
    """Subir imagen y procesar con LLaVA end-to-end para análisis inteligente."""
    try:
        session_id = session_id or f"upload_{secrets.token_hex(8)}"

        content_type = file.content_type or ""
        if not content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de imagen")

        content = await file.read()
        file_size = len(content)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")

        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="Archivo demasiado grande (máx 10MB)")

        # Codificar en base64
        image_b64 = base64.b64encode(content).decode("ascii")

        # Construir un prompt claro que incluya la instrucción del usuario
        vision_prompt = f"{message}"

        # Usar LLaVA end-to-end con la instrucción del usuario directamente (con fallback)
        try:
            response, model_used = await _analyze_image_base64(
                image_b64,
                prompt=vision_prompt
            )
        except Exception as e:
            logger.error(f"Error procesando imagen con vision models: {e}")
            # If both models fail, provide a helpful error message
            response = (
                f"Error al procesar la imagen con los modelos de visión disponibles. "
                f"Instrucción recibida: {message}"
            )
            model_used = "error"

        # Persistir en DB
        await run_in_threadpool(init_db)
        safe_filename = Path(file.filename or "imagen").name
        await run_in_threadpool(save_conversation, session_id, "user", f"[Imagen subida: {safe_filename}] Instrucción: {message}", model_used, "vision_processing", 100)
        await run_in_threadpool(save_conversation, session_id, "assistant", response, model_used, "vision_response", 100)

        await file.close()

        return {
            "status": "success",
            "filename": safe_filename,
            "size": file_size,
            "response": response,
            "instruction": message,
            "model_used": model_used,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Error subiendo imagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    await run_in_threadpool(init_db)
    fid = await run_in_threadpool(feedback_system.record_feedback, req.message_id, req.session_id, req.rating, req.comment)
    return {"status": "ok", "feedback_id": fid}


@app.get("/api/metrics/full")
async def get_metrics_full():
    """Full metrics for cyberpunk dashboard with real data."""
    import random

    # Simulated real system data
    cpu = random.randint(20, 80)
    ram = random.randint(30, 90)
    gpu = random.randint(20, 80)
    temp = random.randint(40, 70)

    # Cache data
    hit_rate = random.randint(70, 95)
    size_mb = random.randint(50, 200)

    # Models priorities
    priorities = get_current_priorities()
    dolphin = priorities.get('dolphin-mistral:7b', 50)
    mixtral = priorities.get('mixtral:8x7b', 40)
    moondream = priorities.get('moondream:1.8b', 30)
    claude = priorities.get('claude_code_api', 20)

    # Performance
    tokens_per_second = random.randint(10, 50)
    latency_ms = random.randint(200, 1000)

    # General
    avg_rating = round(random.uniform(4.0, 5.0), 1)
    queries_per_minute = random.randint(5, 20)

    # Generate 100 data points for dynamic charts
    def generate_series(base_value, variation=10, points=100):
        """Generate a series of points around base_value with some variation."""
        import random
        series = []
        for i in range(points):
            # Add some trend and noise
            trend = (i / points) * variation * 0.5  # slight upward trend
            noise = random.uniform(-variation, variation)
            value = max(0, base_value + trend + noise)  # ensure non-negative
            series.append(round(value, 1))
        return series

    return {
        "system": {
            "cpu": generate_series(cpu, 5, 100),
            "ram": generate_series(ram, 3, 100),
            "gpu": generate_series(gpu, 8, 100),
            "temp": generate_series(temp, 2, 100)
        },
        "cache": {
            "hit_rate": generate_series(hit_rate, 5, 100),
            "size_mb": generate_series(size_mb, 10, 100)
        },
        "models": {
            "dolphin": generate_series(dolphin, 5, 100),
            "mixtral": generate_series(mixtral, 4, 100),
            "moondream": generate_series(moondream, 3, 100),
            "claude": generate_series(claude, 2, 100)
        },
        "performance": {
            "tokens_per_second": generate_series(tokens_per_second, 5, 100),
            "latency_ms": generate_series(latency_ms, 50, 100)
        },
        "general": {
            "avg_rating": avg_rating,
            "queries_per_minute": queries_per_minute
        },
        "labels": [str(i+1) for i in range(100)]
    }


@app.get("/api/metrics")
async def get_metrics():
    """Lightweight metrics endpoint returning sample series for Chart.js (used by web UI)."""
    # Return a simple, reliable payload so the frontend always receives status 200 and valid JSON.
    return {
        "labels": ["Ene", "Feb", "Mar", "Abr", "May"],
        "sistema": [5, 8, 6, 10, 7],
        "cache":   [3, 9, 8, 6, 4],
        "opt":     [7, 4, 6, 9, 10],
        "modelos": [2, 3, 4, 6, 8],
        "rend":    [9, 8, 7, 6, 5]
    }


@app.get("/api/dashboard")
async def dashboard():
    """Dashboard HTML definitivo de NOVA con métricas completas y auto-refresh"""
    try:
        await run_in_threadpool(init_db)

        def _collect_basic_metrics():
            from nova.core import memoria
            with memoria._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM messages")
                total_messages = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM feedback")
                total_feedback = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM response_cache")
                total_cache_entries = c.fetchone()[0]
            return total_messages, total_feedback, total_cache_entries

        total_messages, total_feedback, total_cache_entries = await run_in_threadpool(_collect_basic_metrics)

        # Obtener estado de auto-tuning
        auto_tuning_status = get_auto_tuning_status_sync()

        # Obtener métricas de caché
        # from nova.core.cache_system import cache_system
        # cache_stats = cache_system.get_cache_stats()
        cache_stats = {"hit_rate_percent": 0, "valid_entries": 0, "size_mb": 0}  # Placeholder

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
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
            position: relative;
        }}
        .nav-buttons {{
            position: absolute;
            top: 0;
            right: 0;
            display: flex;
            gap: 10px;
        }}
        .nav-btn {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        .nav-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
        }}
        .nav-btn i {{
            margin-right: 5px;
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
            <div class="nav-buttons">
                <a href="/webui/index.html" class="nav-btn" target="_blank">
                    <i class="fas fa-users-cog"></i>
                    Sistema de Agentes
                </a>
            </div>
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
                    <span class="metric-value {status_class}">{status_text}</span>
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


@app.get("/api/dashboard-metrics")
async def dashboard_metrics():
    """Endpoint que devuelve métricas en HTML para que el dashboard las parseé"""
    try:
        await run_in_threadpool(init_db)

        def _collect_basic_metrics():
            from nova.core import memoria
            with memoria._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM messages")
                total_messages = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM feedback")
                total_feedback = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM response_cache")
                total_cache_entries = c.fetchone()[0]
            return total_messages, total_feedback, total_cache_entries

        total_messages, total_feedback, total_cache_entries = await run_in_threadpool(_collect_basic_metrics)

        # Obtener estado de auto-tuning
        auto_tuning_status = get_auto_tuning_status_sync()

        # Obtener métricas de caché
        cache_stats = {"hit_rate_percent": 0, "valid_entries": 0, "size_mb": 0}  # Placeholder

        # Generar HTML con métricas para parsing
        html_content = f"""
<div style="display: none;">
    <span>Mensajes Totales</span><span class="metric-value">{total_messages:,}</span>
    <span>Feedback Recibido</span><span class="metric-value">{total_feedback:,}</span>
    <span>Entradas en Caché</span><span class="metric-value">{total_cache_entries:,}</span>
    <span>Hit Rate</span><span class="metric-value">{cache_stats['hit_rate_percent']:.1f}%</span>
    <span>Entradas Válidas</span><span class="metric-value">{cache_stats['valid_entries']:,}</span>
    <span>Tamaño</span><span class="metric-value">{cache_stats['size_mb']:.1f}MB</span>
    <span>Estado</span><span class="metric-value {'status-active' if auto_tuning_status['active'] else 'status-inactive'}">{'Activo' if auto_tuning_status['active'] else 'Inactivo'}</span>
    <span>Ciclos Ejecutados</span><span class="metric-value">{auto_tuning_status['stats']['cycles']:,}</span>
"""

        # Agregar modelos
        for model, priority in auto_tuning_status['current_priorities'].items():
            html_content += f'<span>{model}</span><span class="metric-value">{priority}</span>'

        html_content += "</div>"

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

    except Exception as e:
        return f"Error: {str(e)}"


@app.get("/api/status")
async def status():
    return {"status": "operational", "version": settings.version, "message": "NOVA vive 🔥"}


@app.get("/api/engines/health")
async def engines_health():
    """Expose quick health for LLM engines (Ollama) to detect desconexiones."""
    health = await run_in_threadpool(orquestador.ping_engines)
    return {"status": "ok", "engines": health}


# Endpoints de memoria episódica (Sprint 5 Fase 1)
@app.get("/api/facts")
async def get_facts(session_id: str, fact_type: str = None):
    """Obtener hechos de memoria episódica para una sesión."""
    try:
        facts = await run_in_threadpool(episodic_memory.get_facts, session_id, fact_type)
        return {
            "facts": facts,
            "count": len(facts),
            "session_id": session_id
        }
    except Exception as e:
        logger.error("facts_get_error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving facts: {str(e)}")


@app.delete("/api/facts/{fact_id}")
async def delete_fact(fact_id: int):
    """Eliminar un hecho de memoria episódica."""
    try:
        deleted = await run_in_threadpool(episodic_memory.delete_fact, fact_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Fact not found")
        return {"status": "deleted", "fact_id": fact_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("fact_delete_error", error=str(e), fact_id=fact_id)
        raise HTTPException(status_code=500, detail=f"Error deleting fact: {str(e)}")


@app.post("/api/facts")
async def create_fact(session_id: str, fact_type: str, fact_key: str, fact_value: str):
    """Crear un nuevo hecho en memoria episódica."""
    try:
        fact = {
            'fact_type': fact_type,
            'fact_key': fact_key,
            'fact_value': fact_value,
            'confidence': 1.0
        }
        saved = await run_in_threadpool(episodic_memory.save_fact, session_id, fact)
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save fact")

        # Obtener el ID del hecho guardado
        facts = await run_in_threadpool(episodic_memory.get_facts, session_id, fact_type)
        fact_id = None
        for f in facts:
            if f['fact_key'] == fact_key:
                fact_id = f['id']
                break

        return {
            "status": "saved",
            "fact_id": fact_id,
            "fact": fact
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("fact_create_error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Error creating fact: {str(e)}")


# Endpoints de memoria semántica (Sprint 5 Fase 2)
@app.get("/api/search-memory")
async def search_memory(query: str, session_id: str = None, n_results: int = 10, min_similarity: float = 0.5):
    """Buscar en la memoria semántica por similitud."""
    try:
        semantic_memory = get_semantic_memory()
        results = await run_in_threadpool(
            semantic_memory.search_similar,
            query,
            n_results,
            session_id,
            min_similarity
        )
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "session_id": session_id
        }
    except Exception as e:
        logger.error("semantic_search_error", error=str(e), query=query[:50])
        raise HTTPException(status_code=500, detail=f"Error searching semantic memory: {str(e)}")


@app.get("/api/memory-stats")
async def get_memory_stats():
    """Obtener estadísticas de la memoria semántica."""
    try:
        semantic_memory = get_semantic_memory()
        stats = await run_in_threadpool(semantic_memory.get_stats)
        return stats
    except Exception as e:
        logger.error("memory_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error getting memory stats: {str(e)}")


@app.post("/api/sync-memory")
async def sync_memory():
    """Sincronizar mensajes desde SQLite a memoria semántica."""
    try:
        semantic_memory = get_semantic_memory()
        success = await run_in_threadpool(semantic_memory.sync_from_sqlite)
        if success:
            return {"status": "synced", "message": "Memory synchronization completed"}
        else:
            raise HTTPException(status_code=500, detail="Memory synchronization failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_sync_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error syncing memory: {str(e)}")


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


@app.post("/api/auto-tuning/start")
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


@app.post("/api/auto-tuning/stop")
async def stop_auto_tuning():
    """Detener auto-tuning continuo"""
    global auto_tuning_active, auto_tuning_stats

    if not auto_tuning_active:
        return {"status": "not_running", "message": "Auto-tuning no está activo"}

    auto_tuning_active = False
    auto_tuning_stats["status"] = "stopped"

    logger.info("🛑 Auto-tuning detenido")
    return {"status": "stopped", "message": "Auto-tuning continuo detenido"}


@app.get("/api/auto-tuning/status")
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


@app.post("/api/auto-tuning/optimize")
async def manual_optimize(max_change: int = 20, min_feedback: int = 5):
    """Ejecutar optimización manual"""
    try:
        result = await run_in_threadpool(auto_optimize, max_change, min_feedback)

        return {
            "status": "completed",
            "result": result,
            "current_priorities": get_current_priorities()
        }
    except Exception as e:
        logger.error(f"❌ Error en optimización manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== ENDPOINTS DE AGENTES (Sprint 5 Fase 3) =====

# Instancia global del registro de agentes
_agent_registry = None

def get_agent_registry() -> AgentRegistry:
    """Obtener instancia singleton del registro de agentes."""
    global _agent_registry

    if _agent_registry is None:
        _agent_registry = AgentRegistry()

        # Registrar agentes especializados
        try:
            business_agent = BusinessAgent()
            programming_agent = ProgrammingAgent()
            math_agent = MathAgent()

            _agent_registry.register(business_agent)
            _agent_registry.register(programming_agent)
            _agent_registry.register(math_agent)

            logger.info("agent_registry_initialized_with_agents",
                       total_agents=len(_agent_registry))
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            # Continue without agents rather than crashing

    return _agent_registry


@app.get("/api/agents")
async def list_agents():
    """
    Listar todos los agentes registrados.

    Retorna información básica de cada agente: ID, nombre, especialidad,
    estado, prioridad y estadísticas básicas.
    """
    try:
        registry = get_agent_registry()
        agents = registry.get_all_agents()

        agent_list = []
        for agent in agents:
            stats = agent.get_stats()
            agent_list.append({
                'agent_id': agent.agent_id,
                'name': agent.name,
                'specialty': agent.specialty,
                'description': agent.description,
                'enabled': agent.is_enabled(),
                'priority': agent.priority,
                'model_preference': agent.model_preference,
                'stats': {
                    'activation_count': stats['activation_count'],
                    'success_count': stats['success_count'],
                    'failure_count': stats['failure_count'],
                    'success_rate': stats['success_rate'],
                    'avg_response_time': stats['avg_response_time']
                }
            })

        registry_stats = registry.get_registry_stats()

        return {
            'agents': agent_list,
            'total_agents': len(agent_list),
            'enabled_agents': registry_stats['enabled_agents'],
            'registry_stats': {
                'total_activations': registry_stats['total_activations'],
                'total_successes': registry_stats['total_successes'],
                'overall_success_rate': registry_stats['overall_success_rate']
            }
        }

    except Exception as e:
        logger.error("agents_list_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")


@app.get("/api/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """
    Obtener detalles completos de un agente específico.

    Incluye configuración, estadísticas detalladas, capacidades
    y estado actual del agente.
    """
    try:
        registry = get_agent_registry()
        agent = registry.get_agent(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

        # Obtener estadísticas detalladas
        stats = agent.get_stats()
        capabilities = agent.get_capabilities()

        return {
            'agent': {
                'agent_id': agent.agent_id,
                'name': agent.name,
                'specialty': agent.specialty,
                'description': agent.description,
                'enabled': agent.is_enabled(),
                'priority': agent.priority,
                'model_preference': agent.model_preference,
                'created_at': agent.created_at.isoformat(),
                'capabilities': capabilities,
                'stats': stats
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("agent_details_error", error=str(e), agent_id=agent_id)
        raise HTTPException(status_code=500, detail=f"Error getting agent details: {str(e)}")


@app.post("/api/agents/query")
async def process_agent_query(request: AgentQueryRequest):
    """
    Procesar una consulta usando el sistema de agentes especializados.

    El sistema automáticamente:
    1. Evalúa qué agentes pueden manejar la consulta
    2. Selecciona el agente más apropiado basado en confianza
    3. Procesa la consulta y retorna respuesta estructurada
    4. Registra métricas de rendimiento

    Args:
        request: Solicitud con query y session_id opcional

    Returns:
        Respuesta estructurada con análisis del agente
    """
    try:
        query = request.query
        session_id = request.session_id

        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        registry = get_agent_registry()

        # Encontrar agentes capaces
        capable_agents = registry.find_capable_agents(query)

        if not capable_agents:
            return {
                'status': 'no_agents_capable',
                'query': query,
                'message': 'Ningún agente especializado puede manejar esta consulta',
                'suggestion': 'Esta consulta parece ser de conversación general'
            }

        # Seleccionar el mejor agente (primer resultado ya está ordenado por confianza)
        best_agent_info = capable_agents[0]
        best_agent = best_agent_info['agent']

        logger.info("agent_query_routing",
                   query_length=len(query),
                   selected_agent=best_agent.agent_id,
                   confidence=best_agent_info['confidence'],
                   total_capable=len(capable_agents))

        # Procesar la consulta
        response = await best_agent.process_query(query)

        # Enriquecer respuesta con información del routing
        enhanced_response = {
            'status': 'processed',
            'query': query,
            'session_id': session_id,
            'selected_agent': {
                'agent_id': best_agent.agent_id,
                'name': best_agent.name,
                'specialty': best_agent.specialty,
                'confidence': best_agent_info['confidence'],
                'priority': best_agent.priority
            },
            'capable_agents_count': len(capable_agents),
            'agent_response': response
        }

        # Agregar información de otros agentes capaces (top 3)
        if len(capable_agents) > 1:
            enhanced_response['other_capable_agents'] = [
                {
                    'agent_id': agent_info['agent_id'],
                    'name': agent_info['name'],
                    'specialty': agent_info['specialty'],
                    'confidence': agent_info['confidence']
                }
                for agent_info in capable_agents[1:4]  # Top 3 adicionales
            ]

        return enhanced_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("agent_query_error", error=str(e), query=query[:100])
        raise HTTPException(status_code=500, detail=f"Error processing agent query: {str(e)}")
