from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "NOVA Core"
    version: str = "1.0.0-sprint1-mvp"
    ollama_health_url: str = "http://localhost:11434/api/tags"
    ollama_generate_url: str = "http://localhost:11434/api/generate"
    models: list[str] = ["dolphin-mistral:7b", "moondream:1.8b"]
    web_port_start: int = 8000
    web_port_end: int = 8010
    logs_path: str = "logs/nova.log"
    db_path: str = "data/nova_memory.db"
    model_profiles_path: str = "config/model_profiles.json"
    pid_path: str = "data/nova_launcher.pid"
    # LLM Brain toggle and router URL for external LLM-based routing (timeout fallback)
    USE_LLM_BRAIN: bool = False
    llm_router_url: str = "http://localhost:11435/api/llm_route"
    # Optional API keys
    claude_api_key: str | None = None


settings = Settings()
