"""Simple Ollama client adapter.
Provides `generate(model, prompt, stream=False)` which returns either a string response
or yields text chunks when `stream=True`.

This adapter is defensive: it tries JSON fields `result`, `text`, `response` and
falls back to streaming raw lines if the server provides chunked text.
"""
from typing import Generator, Optional, Union
import requests
from config.settings import settings
from utils.logging import get_logger

logger = get_logger("models.ollama_model")


def _parse_json_response(r: requests.Response) -> Optional[str]:
    try:
        data = r.json()
    except Exception:
        return None
    if isinstance(data, dict):
        for k in ("result", "text", "response", "content"):
            if k in data:
                return data[k]
    return None


def generate(model: str, prompt: str, stream: bool = False, timeout: int = 10) -> Union[str, Generator[str, None, None]]:
    url = settings.ollama_generate_url
    payload = {"model": model, "prompt": prompt}

    if not stream:
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            # Try parse JSON-friendly responses
            parsed = _parse_json_response(r)
            if parsed is not None:
                return parsed
            # Fallback: return raw text
            return r.text
        except Exception as e:
            logger.error("ollama_generate_failed", error=str(e))
            raise

    # Streaming mode: return a generator
    def _stream_generator():
        try:
            with requests.post(url, json=payload, stream=True, timeout=timeout) as r:
                # If chunked JSON lines
                for chunk in r.iter_lines(decode_unicode=True):
                    if chunk is None:
                        continue
                    line = chunk.strip()
                    if not line:
                        continue
                    # try to parse JSON chunk
                    try:
                        j = None
                        try:
                            j = r.json() if False else None
                        except Exception:
                            j = None
                        # if it's a plain line, yield it
                        yield line
                    except Exception:
                        # best-effort: yield raw line
                        yield line
        except Exception as e:
            logger.warning("ollama_stream_failed", error=str(e))
            # on stream failure, stop generator
            return

    return _stream_generator()
