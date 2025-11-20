"""Simple Ollama client adapter.
Provides `generate(model, prompt, stream=False)` which returns either a string response
or yields text chunks when `stream=True`.

This adapter is defensive: it tries JSON fields `result`, `text`, `response` and
falls back to streaming raw lines if the server provides chunked text.
"""
from typing import Generator, Optional, Union
import requests
import json
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
            # If Ollama returns a JSON error like {"error": "model 'X' not found"} and the requested
            # model is Claude, automatically fallback to Mixtral (Sofía's policy).
            try:
                j = r.json()
            except Exception:
                j = None

            if j and isinstance(j, dict) and "error" in j and "claude" in model:
                logger.warning("claude_fallback_to_mixtral", error=j.get("error"))
                # attempt fallback to mixtral
                fallback_model = "mixtral:8x7b"
                payload["model"] = fallback_model
                rf = requests.post(url, json=payload, timeout=timeout)
                parsed_f = _parse_json_response(rf)
                if parsed_f is not None:
                    return parsed_f
                return rf.text

            # Try parse JSON-friendly responses
            parsed = _parse_json_response(r)
            if parsed is not None:
                # If parsed is itself JSON-like string, coerce to string
                if isinstance(parsed, (dict, list)):
                    # Convert to pretty text
                    return json.dumps(parsed, ensure_ascii=False)
                return str(parsed)

            # If the response text looks like JSON, try to parse and extract
            text = r.text or ""
            try:
                j2 = json.loads(text)
                parsed2 = None
                if isinstance(j2, dict):
                    for k in ("result", "text", "response", "content"):
                        if k in j2:
                            parsed2 = j2[k]
                            break
                if parsed2:
                    return parsed2 if isinstance(parsed2, str) else json.dumps(parsed2, ensure_ascii=False)
            except Exception:
                pass

            # Fallback: return raw text but cleaned (strip surrounding whitespace)
            return text.strip()
        except Exception as e:
            logger.error("ollama_generate_failed", error=str(e))
            raise

    # Streaming mode: return a generator
    def _stream_generator():
        # Collect all chunks and return the assembled clean text at the end.
        parts = []
        try:
            with requests.post(url, json=payload, stream=True, timeout=timeout) as r:
                for chunk in r.iter_lines(decode_unicode=True):
                    if chunk is None:
                        continue
                    line = chunk.strip()
                    if not line:
                        continue
                    parts.append(line)
            # After stream finishes, try to parse/join and return single clean string
            combined = "\n".join(parts).strip()
            # If combined looks like JSON, try to extract useful fields
            try:
                j = json.loads(combined)
                if isinstance(j, dict):
                    for k in ("result", "text", "response", "content"):
                        if k in j:
                            val = j[k]
                            return val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            except Exception:
                pass
            return combined
        except Exception as e:
            logger.warning("ollama_stream_failed", error=str(e))
            raise

    # For stream=True we return the fully assembled string (not a generator)
    return _stream_generator()
