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
    logger.info("ollama_generate_called", model=model, stream=stream)
    url = settings.ollama_generate_url
    
    # Parámetros optimizados para velocidad y calidad
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        # Optimizaciones de velocidad
        "options": {
            "temperature": 0.7,      # Balance entre creatividad y velocidad
            "top_p": 0.9,           # Nucleus sampling para diversidad
            "top_k": 40,            # Limitar vocabulario considerado
            "num_predict": 512,     # Máximo tokens de respuesta (más corto = más rápido)
            "repeat_penalty": 1.1,  # Penalizar repeticiones
            "repeat_last_n": 64,    # Memoria para penalización de repeticiones
            "tfs_z": 1.0,           # Tail free sampling
            "mirostat": 0,          # Desactivar mirostat para velocidad
            "mirostat_tau": 5.0,
            "mirostat_eta": 0.1,
            "num_ctx": 2048,        # Contexto más pequeño para velocidad
            "num_thread": -1,       # Usar todos los cores disponibles
        }
    }

    if not stream:
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            
            # Handle HTTP errors immediately for Claude models
            if r.status_code != 200 and "claude" in model:
                logger.warning("claude_http_error_fallback_to_mixtral", status=r.status_code)
                # attempt fallback to mixtral
                fallback_model = "mixtral:8x7b"
                payload["model"] = fallback_model
                rf = requests.post(url, json=payload, timeout=timeout)
                rf.raise_for_status()
                parsed_f = _parse_json_response(rf)
                if parsed_f is not None:
                    return parsed_f
                return rf.text
            
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
                rf.raise_for_status()
                parsed_f = _parse_json_response(rf)
                if parsed_f is not None:
                    return parsed_f
                return rf.text

            # Check for HTTP errors after processing JSON
            r.raise_for_status()

            # Try parse JSON-friendly responses
            parsed = _parse_json_response(r)
            if parsed is not None:
                # If parsed is itself JSON-like string, coerce to string
                if isinstance(parsed, (dict, list)):
                    # Convert to pretty text
                    return json.dumps(parsed, ensure_ascii=False)
                return str(parsed)

            # If the response text looks like JSON or multiple JSON objects (chunked), try to extract 'response' fields
            text = r.text or ""
            # First try single JSON object
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

            # Try parsing the text as newline-separated JSON objects (common streaming format)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            extracted = []
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    if isinstance(obj, dict) and "response" in obj:
                        extracted.append(obj.get("response") or "")
                        continue
                except Exception:
                    pass
                # fallback: append raw line
                extracted.append(ln)

            if extracted:
                return "".join(extracted).strip()

            # Fallback: return raw text but cleaned (strip surrounding whitespace)
            return text.strip()
            
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (like 404 for missing models)
            if "claude" in model and e.response.status_code == 404:
                logger.warning("claude_http_404_fallback_to_mixtral", status=e.response.status_code)
                # attempt fallback to mixtral
                fallback_model = "mixtral:8x7b"
                payload["model"] = fallback_model
                try:
                    rf = requests.post(url, json=payload, timeout=timeout)
                    rf.raise_for_status()
                    parsed_f = _parse_json_response(rf)
                    if parsed_f is not None:
                        return parsed_f
                    return rf.text
                except Exception as fallback_error:
                    logger.error("mixtral_fallback_failed", error=str(fallback_error))
                    raise fallback_error
            else:
                logger.error("ollama_http_error", status=e.response.status_code, error=str(e))
                raise
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
