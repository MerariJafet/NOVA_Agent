import json
from typing import Dict, Any

_DATA: Dict[str, Any] = {}


def _load():
    global _DATA
    try:
        with open("config/model_profiles.json", "r", encoding="utf-8") as f:
            _DATA = json.load(f)
    except Exception:
        _DATA = {}


_load()


def model_profiles() -> Dict[str, Any]:
    return _DATA
