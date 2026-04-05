"""
Model registry for AI engine.
Tracks versions and file paths for trained models.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "model_registry.json"
REGISTRY_PATH = Path(
    os.getenv("AI_MODEL_REGISTRY_PATH", str(DEFAULT_REGISTRY_PATH))
)


def _load_registry() -> Dict:
    if not REGISTRY_PATH.exists():
        return {"models": {}}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"models": {}}


def _save_registry(data: Dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def register_model(name: str, file_path: str, metadata: Optional[Dict] = None) -> Dict:
    data = _load_registry()
    models = data.setdefault("models", {})
    entry = {
        "path": file_path,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    models[name] = entry
    _save_registry(data)
    return entry


def get_model(name: str) -> Optional[Dict]:
    data = _load_registry()
    return data.get("models", {}).get(name)
