from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from typing import Callable

def setup_middlewares(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://127.0.0.1"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def simple_rate_limit_middleware(app):
    # Very basic in-memory rate limit per client IP
    limits = {}

    @app.middleware("http")
    async def _rate_limit(request: Request, call_next: Callable):
        ip = request.client.host if request.client else "unknown"
        ts = time.time()
        window = limits.get(ip, [])
        # keep requests in last 60s
        window = [t for t in window if ts - t < 60]
        if len(window) > 100:  # Increased from 30 to 100 requests per minute
            return Response(status_code=429, content="Too Many Requests")
        window.append(ts)
        limits[ip] = window
        return await call_next(request)
