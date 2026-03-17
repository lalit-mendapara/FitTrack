import os
import time
import base64
import hashlib
import requests
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from cryptography.fernet import Fernet, InvalidToken
from app.database import get_db
from app.models.admin import Admin
from app.models.system_setting import SystemSetting
from app.utils.admin_auth import get_current_admin

router = APIRouter(prefix="/api/admin/settings", tags=["Admin - Settings"])

# ---------------------------------------------------------------------------
# Fernet symmetric encryption for sensitive values at rest
# Key is derived from SECRET_KEY so no extra secret is needed.
# ---------------------------------------------------------------------------
def _get_fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "changeme-set-a-real-secret-key")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns ciphertext as a UTF-8 string."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def _decrypt(stored: str) -> str:
    """Decrypt a Fernet ciphertext. Falls back to the raw value for backward
    compatibility (e.g. values seeded before encryption was introduced)."""
    if not stored:
        return stored
    try:
        return _get_fernet().decrypt(stored.encode()).decode()
    except (InvalidToken, Exception):
        return stored  # Already plaintext — return as-is


# ---------------------------------------------------------------------------
# Default settings seeded from environment on first load
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = [
    # LLM Configuration
    {
        "key": "llm_provider",
        "value_env": lambda: os.getenv("LLM_PROVIDER", "ollama"),
        "description": "LLM provider to use: ollama, openrouter, or openai",
        "category": "llm",
        "is_sensitive": False,
    },
    {
        "key": "llm_model",
        "value_env": lambda: os.getenv("LLM_MODEL", ""),
        "description": "Model name override (leave blank to use provider default)",
        "category": "llm",
        "is_sensitive": False,
    },
    {
        "key": "ollama_url",
        "value_env": lambda: os.getenv("OLLAMA_URL", "http://host.docker.internal:11434"),
        "description": "Ollama server base URL (used when provider is ollama)",
        "category": "llm",
        "is_sensitive": False,
    },
    {
        "key": "ollama_model",
        "value_env": lambda: os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud"),
        "description": "Default Ollama model name",
        "category": "llm",
        "is_sensitive": False,
    },
    {
        "key": "llm_api_key",
        "value_env": lambda: os.getenv("LLM_API_KEY", ""),
        "description": "API key for paid LLM providers (OpenRouter / OpenAI)",
        "category": "llm",
        "is_sensitive": True,
    },
    {
        "key": "guardrails_enabled",
        "value_env": lambda: os.getenv("GUARDRAILS_ENABLED", "false"),
        "description": "Enable Nemoguardrails safety flows for the AI Coach",
        "category": "llm",
        "is_sensitive": False,
    },
    # Observability
    {
        "key": "langfuse_host",
        "value_env": lambda: os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
        "description": "Langfuse tracing host URL",
        "category": "observability",
        "is_sensitive": False,
    },
    {
        "key": "langfuse_public_key",
        "value_env": lambda: os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        "description": "Langfuse public key (optional — leave blank to disable tracing)",
        "category": "observability",
        "is_sensitive": False,
    },
    {
        "key": "langfuse_secret_key",
        "value_env": lambda: os.getenv("LANGFUSE_SECRET_KEY", ""),
        "description": "Langfuse secret key",
        "category": "observability",
        "is_sensitive": True,
    },
    # General
    {
        "key": "app_timezone",
        "value_env": lambda: os.getenv("TZ", "Asia/Kolkata"),
        "description": "Application timezone (affects Celery scheduler)",
        "category": "general",
        "is_sensitive": False,
    },
    # Scheduler
    {
        "key": "diet_plan_schedule_hour",
        "value_env": lambda: os.getenv("DIET_PLAN_SCHEDULE_HOUR", "5"),
        "description": "Hour of the day (0-23) when automatic diet plans are generated",
        "category": "scheduler",
        "is_sensitive": False,
    },
]


def _looks_encrypted(value: str) -> bool:
    """Fernet ciphertexts are base64url and always start with 'gAAAAA'."""
    return value.startswith("gAAAAA")


def seed_default_settings(db: Session) -> None:
    """Insert default settings from env if they don't already exist in the DB.
    Sensitive values are Fernet-encrypted before storage.
    Any existing plaintext sensitive values are re-encrypted on the fly."""
    for item in DEFAULT_SETTINGS:
        existing = db.query(SystemSetting).filter(SystemSetting.key == item["key"]).first()
        if not existing:
            raw_value = item["value_env"]()
            stored_value = _encrypt(raw_value) if (item["is_sensitive"] and raw_value) else raw_value
            setting = SystemSetting(
                key=item["key"],
                value=stored_value,
                description=item["description"],
                category=item["category"],
                is_sensitive=item["is_sensitive"],
            )
            db.add(setting)
        elif existing.is_sensitive and existing.value and not _looks_encrypted(existing.value):
            existing.value = _encrypt(existing.value)
    db.commit()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class SettingOut(BaseModel):
    key: str
    value: Optional[str]
    description: Optional[str]
    category: str
    is_sensitive: bool

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: Optional[str]


class HealthStatus(BaseModel):
    service: str
    status: str          # "ok" | "error"
    latency_ms: Optional[float]
    detail: Optional[str]


class SystemHealthResponse(BaseModel):
    checks: List[HealthStatus]
    overall: str          # "healthy" | "degraded" | "unhealthy"


class CeleryWorkerInfo(BaseModel):
    worker_name: str
    status: str
    active_tasks: int
    scheduled_tasks: int


class CeleryStatusResponse(BaseModel):
    workers_found: int
    workers: List[CeleryWorkerInfo]
    beat_schedule: Dict[str, Any]
    status: str           # "running" | "no_workers" | "error"


class LLMTestResponse(BaseModel):
    status: str           # "ok" | "error"
    provider: str
    model_or_url: str
    detail: str


# ---------------------------------------------------------------------------
# Helper: always return a fixed placeholder for sensitive values.
# We NEVER expose any characters of sensitive keys through the API.
# ---------------------------------------------------------------------------
SENSITIVE_PLACEHOLDER = "***HIDDEN***"


# ---------------------------------------------------------------------------
# GET /api/admin/settings  — list all settings grouped by category
# ---------------------------------------------------------------------------
@router.get("", response_model=Dict[str, List[SettingOut]])
async def get_all_settings(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    seed_default_settings(db)
    rows = db.query(SystemSetting).order_by(SystemSetting.category, SystemSetting.key).all()

    grouped: Dict[str, List[SettingOut]] = {}
    for row in rows:
        display_value = SENSITIVE_PLACEHOLDER if row.is_sensitive else row.value
        out = SettingOut(
            key=row.key,
            value=display_value,
            description=row.description,
            category=row.category,
            is_sensitive=row.is_sensitive,
        )
        grouped.setdefault(row.category, []).append(out)

    return grouped


# ---------------------------------------------------------------------------
# PUT /api/admin/settings/{key}  — update a single setting
# ---------------------------------------------------------------------------
@router.put("/{key}", response_model=SettingOut)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    seed_default_settings(db)
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    # Encrypt sensitive values before storing; store non-sensitive as plaintext
    setting.value = _encrypt(payload.value) if (setting.is_sensitive and payload.value) else payload.value
    setting.updated_by = current_admin.id
    db.commit()
    db.refresh(setting)

    display_value = SENSITIVE_PLACEHOLDER if setting.is_sensitive else setting.value
    return SettingOut(
        key=setting.key,
        value=display_value,
        description=setting.description,
        category=setting.category,
        is_sensitive=setting.is_sensitive,
    )


# ---------------------------------------------------------------------------
# GET /api/admin/settings/health  — live health checks for all services
# ---------------------------------------------------------------------------
@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    checks: List[HealthStatus] = []

    # 1. PostgreSQL
    try:
        start = time.monotonic()
        db.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000, 2)
        checks.append(HealthStatus(service="PostgreSQL", status="ok", latency_ms=latency, detail="Connection healthy"))
    except Exception as e:
        checks.append(HealthStatus(service="PostgreSQL", status="error", latency_ms=None, detail=str(e)))

    # 2. Redis
    try:
        import redis as redis_lib
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        start = time.monotonic()
        r.ping()
        latency = round((time.monotonic() - start) * 1000, 2)
        checks.append(HealthStatus(service="Redis", status="ok", latency_ms=latency, detail="PONG received"))
    except Exception as e:
        checks.append(HealthStatus(service="Redis", status="error", latency_ms=None, detail=str(e)))

    # 3. Qdrant
    try:
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        start = time.monotonic()
        resp = requests.get(f"{qdrant_url}/healthz", timeout=3)
        latency = round((time.monotonic() - start) * 1000, 2)
        if resp.status_code == 200:
            checks.append(HealthStatus(service="Qdrant", status="ok", latency_ms=latency, detail="Healthy"))
        else:
            checks.append(HealthStatus(service="Qdrant", status="error", latency_ms=latency, detail=f"HTTP {resp.status_code}"))
    except Exception as e:
        checks.append(HealthStatus(service="Qdrant", status="error", latency_ms=None, detail=str(e)))

    # 4. Ollama (only when provider is ollama)
    llm_provider = os.getenv("LLM_PROVIDER", "ollama")
    if llm_provider == "ollama":
        try:
            ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
            start = time.monotonic()
            resp = requests.get(f"{ollama_url}/api/tags", timeout=4)
            latency = round((time.monotonic() - start) * 1000, 2)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                detail = f"{len(models)} model(s) loaded" if models else "Connected (no models loaded)"
                checks.append(HealthStatus(service="Ollama", status="ok", latency_ms=latency, detail=detail))
            else:
                checks.append(HealthStatus(service="Ollama", status="error", latency_ms=latency, detail=f"HTTP {resp.status_code}"))
        except Exception as e:
            checks.append(HealthStatus(service="Ollama", status="error", latency_ms=None, detail=str(e)))

    overall = "healthy"
    if any(c.status == "error" for c in checks):
        critical = [c for c in checks if c.service in ("PostgreSQL", "Redis") and c.status == "error"]
        overall = "unhealthy" if critical else "degraded"

    return SystemHealthResponse(checks=checks, overall=overall)


# ---------------------------------------------------------------------------
# GET /api/admin/settings/celery-status  — Celery worker + beat info
# ---------------------------------------------------------------------------
@router.get("/celery-status", response_model=CeleryStatusResponse)
async def celery_status(
    current_admin: Admin = Depends(get_current_admin),
):
    from app.celery_app import celery_app

    beat_schedule = {}
    try:
        beat_schedule = {
            name: {
                "task": entry.get("task"),
                "schedule": str(entry.get("schedule")),
            }
            for name, entry in (celery_app.conf.beat_schedule or {}).items()
        }
    except Exception:
        pass

    try:
        inspector = celery_app.control.inspect(timeout=3)
        active_map = inspector.active() or {}
        scheduled_map = inspector.scheduled() or {}

        if not active_map:
            return CeleryStatusResponse(
                workers_found=0,
                workers=[],
                beat_schedule=beat_schedule,
                status="no_workers",
            )

        workers = []
        for worker_name in active_map:
            active_tasks = len(active_map.get(worker_name) or [])
            scheduled_tasks = len(scheduled_map.get(worker_name) or [])
            workers.append(
                CeleryWorkerInfo(
                    worker_name=worker_name,
                    status="online",
                    active_tasks=active_tasks,
                    scheduled_tasks=scheduled_tasks,
                )
            )

        return CeleryStatusResponse(
            workers_found=len(workers),
            workers=workers,
            beat_schedule=beat_schedule,
            status="running",
        )
    except Exception as e:
        return CeleryStatusResponse(
            workers_found=0,
            workers=[],
            beat_schedule=beat_schedule,
            status=f"error: {str(e)}",
        )


# ---------------------------------------------------------------------------
# POST /api/admin/settings/test-llm  — test LLM connectivity
# ---------------------------------------------------------------------------
@router.post("/test-llm", response_model=LLMTestResponse)
async def test_llm_connection(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    # Read from DB (decrypt sensitive values for internal use), fall back to env
    def get_setting(key: str, env_fallback: str) -> str:
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row and row.value:
            return _decrypt(row.value) if row.is_sensitive else row.value
        return os.getenv(env_fallback, "")

    provider = get_setting("llm_provider", "LLM_PROVIDER") or "ollama"

    if provider == "ollama":
        ollama_url = get_setting("ollama_url", "OLLAMA_URL") or "http://host.docker.internal:11434"
        try:
            resp = requests.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                detail = f"Connected. Available models: {', '.join(models)}" if models else "Connected but no models loaded"
                return LLMTestResponse(status="ok", provider="ollama", model_or_url=ollama_url, detail=detail)
            else:
                return LLMTestResponse(status="error", provider="ollama", model_or_url=ollama_url, detail=f"HTTP {resp.status_code}")
        except Exception as e:
            return LLMTestResponse(status="error", provider="ollama", model_or_url=ollama_url, detail=str(e))

    elif provider in ("openrouter", "openai"):
        api_key_row = db.query(SystemSetting).filter(SystemSetting.key == "llm_api_key").first()
        raw_key = (api_key_row.value if api_key_row and api_key_row.value else None) or os.getenv("LLM_API_KEY", "")
        api_key = _decrypt(raw_key) if raw_key else ""
        if not api_key:
            return LLMTestResponse(status="error", provider=provider, model_or_url="N/A", detail="LLM API key not configured")
        base_url = "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        try:
            resp = requests.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5,
            )
            if resp.status_code == 200:
                return LLMTestResponse(status="ok", provider=provider, model_or_url=base_url, detail="API key valid — models reachable")
            else:
                return LLMTestResponse(status="error", provider=provider, model_or_url=base_url, detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            return LLMTestResponse(status="error", provider=provider, model_or_url=base_url, detail=str(e))

    return LLMTestResponse(status="error", provider=provider, model_or_url="N/A", detail=f"Unknown provider: {provider}")
