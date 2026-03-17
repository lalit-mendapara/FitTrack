"""Centralized helper to load and cache Nemoguardrails configuration."""

from __future__ import annotations

import base64
import hashlib
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

try:
    import nest_asyncio

    nest_asyncio.apply()
except Exception:
    pass

try:
    from nemoguardrails import LLMRails, RailsConfig
    _NEMO_GUARDRAILS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    LLMRails = RailsConfig = None  # type: ignore[assignment]
    _NEMO_GUARDRAILS_AVAILABLE = False

try:
    from langchain_core.language_models import BaseChatModel, BaseLLM
except Exception:  # pragma: no cover - optional import at runtime
    BaseChatModel = BaseLLM = object  # type: ignore

from app.database import SessionLocal
from app.models.system_setting import SystemSetting


GuardrailLLM = Union[BaseChatModel, BaseLLM]  # type: ignore[assignment]

GUARDRAILS_FOLDER = Path(__file__).resolve().parent.parent / "guardrails"

DEFAULT_MODELS = {
    "ollama": "gpt-oss:120b-cloud",
    "openrouter": "google/gemini-2.0-flash-001",
    "openai": "gpt-4o",
}

PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None,
}


_rails_lock = threading.Lock()
_rails_instance: Optional[LLMRails] = None
_rails_signature: Optional[Tuple] = None


def extract_usage_from_metadata(metadata: Optional[dict]) -> Tuple[int, int, int, float, float, float]:
    """Return token counts and timings from guardrail metadata."""
    if not metadata:
        return 0, 0, 0, 0.0, 0.0, 0.0

    input_tokens = metadata.get("prompt_eval_count") or 0
    output_tokens = metadata.get("eval_count") or 0
    usage = metadata.get("usage", {})
    if input_tokens == 0 and output_tokens == 0:
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total_tokens = input_tokens + output_tokens

    prompt_eval_duration_ms = round((metadata.get("prompt_eval_duration") or 0) / 1e6, 2)
    eval_duration_ms = round((metadata.get("eval_duration") or 0) / 1e6, 2)
    total_duration_ms = round((metadata.get("total_duration") or 0) / 1e6, 2)

    return input_tokens, output_tokens, total_tokens, prompt_eval_duration_ms, eval_duration_ms, total_duration_ms


def _decrypt_value(stored: str) -> str:
    if not stored:
        return stored
    try:
        from cryptography.fernet import Fernet

        secret = os.getenv("SECRET_KEY", "changeme-set-a-real-secret-key")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        return Fernet(key).decrypt(stored.encode()).decode()
    except Exception:
        return stored


def _bool_from_str(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_live_settings() -> Dict[str, Optional[str]]:
    keys = [
        "llm_provider",
        "llm_model",
        "ollama_url",
        "ollama_model",
        "llm_api_key",
        "guardrails_enabled",
    ]
    try:
        db = SessionLocal()
        rows = db.query(SystemSetting).filter(SystemSetting.key.in_(keys)).all()
        return {
            row.key: (_decrypt_value(row.value) if row.is_sensitive else (row.value or ""))
            for row in rows
        }
    except Exception as exc:
        print(f"[Guardrails] Failed to read system settings: {exc}")
        return {}
    finally:
        try:
            db.close()
        except Exception:
            pass


def _resolve_live_model(settings: Dict[str, Optional[str]]) -> Tuple[str, str, Optional[str]]:
    provider = (settings.get("llm_provider") or os.getenv("LLM_PROVIDER", "ollama")).lower()
    model = (
        settings.get("llm_model")
        or os.getenv("LLM_MODEL")
        or settings.get("ollama_model")
        or os.getenv("OLLAMA_MODEL")
        or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["ollama"])
    )
    api_key = settings.get("llm_api_key") or os.getenv("LLM_API_KEY")
    return provider, model, api_key


def _apply_model_overrides(config: RailsConfig, settings: Dict[str, Optional[str]]) -> None:
    provider, model_name, api_key = _resolve_live_model(settings)
    ollama_url = settings.get("ollama_url") or os.getenv("OLLAMA_URL", "http://localhost:11434")
    engine = provider if provider in {"openai", "openrouter", "ollama"} else "openai"

    for model in config.models:
        if model.type not in {"main", "guardrail"}:
            continue

        model.engine = engine
        model.model = model_name
        params = model.parameters or {}

        if engine == "ollama":
            params["base_url"] = ollama_url.rstrip("/")
        elif provider == "openrouter":
            params["base_url"] = PROVIDER_URLS["openrouter"]
        else:
            params.pop("base_url", None)

        if api_key:
            params["api_key"] = api_key

        model.parameters = params


def _current_signature(settings: Dict[str, Optional[str]]) -> Tuple:
    provider, model_name, api_key = _resolve_live_model(settings)
    ollama_url = settings.get("ollama_url") or os.getenv("OLLAMA_URL", "http://localhost:11434")
    enabled = guardrails_enabled(settings)
    return (provider, model_name, ollama_url, bool(api_key), enabled)


def guardrails_enabled(settings: Optional[Dict[str, Optional[str]]] = None) -> bool:
    if settings is None:
        settings = _get_live_settings()
    if "guardrails_enabled" in settings:
        return _bool_from_str(settings.get("guardrails_enabled"))
    return _bool_from_str(os.getenv("GUARDRAILS_ENABLED", "false"))


def get_guardrails(llm: Optional[GuardrailLLM] = None) -> Optional[LLMRails]:
    global _rails_instance, _rails_signature

    if not _NEMO_GUARDRAILS_AVAILABLE:
        print("[Guardrails] Nemoguardrails is not installed; skipping guardrails initialization.")
        return None

    settings = _get_live_settings()
    if not guardrails_enabled(settings):
        print("[Guardrails] Disabled via settings; guardrails will not run for this request.")
        return None

    signature = _current_signature(settings)

    with _rails_lock:
        if _rails_instance is None or _rails_signature != signature:
            if not GUARDRAILS_FOLDER.exists():
                print("[Guardrails] Config folder missing; skipping guardrails initialization.")
                return None

            config = RailsConfig.from_path(str(GUARDRAILS_FOLDER))
            _apply_model_overrides(config, settings)
            provider, model_name, _ = _resolve_live_model(settings)
            print(
                "[Guardrails] Initializing Nemoguardrails "
                f"(provider={provider}, model={model_name}, enabled={guardrails_enabled(settings)})"
            )
            _rails_instance = LLMRails(config=config)
            _rails_signature = signature

        if llm is not None and _rails_instance is not None:
            try:
                _rails_instance.update_llm(llm)
            except Exception as exc:
                print(f"[Guardrails] Failed to update LLM: {exc}")

        return _rails_instance
