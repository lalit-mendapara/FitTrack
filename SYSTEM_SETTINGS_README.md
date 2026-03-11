# System Settings Module — Developer Reference

> **Purpose:** This document is the single source of truth for understanding, maintaining, and extending the Admin Panel's System Settings module. Read this before making any changes.

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [File Map](#2-file-map)
3. [Database Model](#3-database-model)
4. [Backend Architecture](#4-backend-architecture)
   - [Encryption Layer](#41-encryption-layer)
   - [Default Settings Seed](#42-default-settings-seed)
   - [API Endpoints](#43-api-endpoints)
   - [Pydantic Schemas](#44-pydantic-schemas)
5. [Security Design](#5-security-design)
6. [LLM Live Config System](#6-llm-live-config-system)
7. [Frontend Architecture](#7-frontend-architecture)
   - [State Management](#71-state-management)
   - [Tab System](#72-tab-system)
   - [Sensitive Field Behavior](#73-sensitive-field-behavior)
   - [Provider-Conditional Fields](#74-provider-conditional-fields)
8. [Health Check System](#8-health-check-system)
9. [Celery Monitoring](#9-celery-monitoring)
10. [How-To: Common Tasks](#10-how-to-common-tasks)
    - [Add a New Setting Key](#101-add-a-new-setting-key)
    - [Add a New Category / Tab](#102-add-a-new-category--tab)
    - [Add a New Health Check Service](#103-add-a-new-health-check-service)
    - [Change the Encryption Key](#104-change-the-encryption-key)
11. [API Reference](#11-api-reference)
12. [Docker Commands](#12-docker-commands)

---

## 1. Module Overview

The System Settings module lets super-admins configure the running application **without touching environment variables or restarting Docker containers**. Key capabilities:

| Capability | What it does |
|---|---|
| **LLM Configuration** | Switch provider (Ollama / OpenRouter / OpenAI), set model name, API key, Ollama URL — changes apply immediately to all new LLM calls |
| **Observability** | Configure Langfuse tracing credentials (host, public key, secret key) |
| **General** | Application timezone (used by Celery beat scheduler) |
| **System Health** | Live ping of PostgreSQL, Redis, Qdrant, Ollama with latency |
| **Celery Monitoring** | See online workers, active task count, registered beat schedule |
| **Test Connection** | Verify LLM provider connectivity using the currently saved DB values |

---

## 2. File Map

```
backend/
├── app/
│   ├── api/
│   │   └── admin/
│   │       └── settings.py          ← All backend logic (encryption, endpoints, health, Celery)
│   ├── models/
│   │   └── system_setting.py        ← SQLAlchemy model for system_settings table
│   ├── services/
│   │   └── llm_service.py           ← get_llm() reads live config from DB via _get_db_llm_config()
│   └── main.py                      ← Router registered here
├── alembic/
│   └── versions/
│       └── 2026_03_f1e2d3c4b5a6_add_system_settings_table.py  ← DB migration

frontend/
└── src/
    ├── pages/
    │   └── admin/
    │       └── SystemSettings.jsx   ← Full frontend page (3 tabs: LLM, Health, Celery)
    ├── components/
    │   └── admin/
    │       ├── AdminLayout.jsx      ← Sidebar nav includes Settings entry
    │       └── AdminProtectedRoute.jsx  ← Guards /admin/settings route
    └── App.jsx                      ← Route /admin/settings registered here
```

---

## 3. Database Model

**File:** `backend/app/models/system_setting.py`

```python
class SystemSetting(Base):
    __tablename__ = "system_settings"

    id          = Column(Integer, primary_key=True)
    key         = Column(String, unique=True, nullable=False, index=True)
    value       = Column(Text, nullable=True)        # Fernet-encrypted if is_sensitive=True
    description = Column(String, nullable=True)
    category    = Column(String, nullable=False)     # "llm" | "observability" | "general"
    is_sensitive = Column(Boolean, default=False)    # True → encrypt at rest, mask in API
    updated_at  = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by  = Column(Integer, ForeignKey("admins.id"), nullable=True)
```

**Key rules:**
- `key` is the unique identifier (e.g. `"llm_provider"`, `"llm_api_key"`). Never change an existing key string — it is the primary lookup identifier.
- `is_sensitive = True` means: encrypt before storing, return `***HIDDEN***` in all API responses.
- `value` stores either plaintext (non-sensitive) or Fernet ciphertext starting with `gAAAAA` (sensitive).

---

## 4. Backend Architecture

**File:** `backend/app/api/admin/settings.py`

### 4.1 Encryption Layer

```
SECRET_KEY (env var)
       │
       ▼  SHA-256 hash → 32 bytes → base64url encode → 44-char Fernet key
    _get_fernet()
       │
       ├─ _encrypt(plaintext) → Fernet ciphertext string (starts with "gAAAAA")
       └─ _decrypt(ciphertext) → plaintext (falls back to input if not valid ciphertext)
```

**Three helpers:**

```python
def _get_fernet() -> Fernet:
    secret = os.getenv("SECRET_KEY", "changeme-set-a-real-secret-key")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def _encrypt(plaintext: str) -> str: ...   # → "gAAAAABpr9y065..."
def _decrypt(stored: str) -> str: ...      # → plaintext or original if not encrypted
```

**Backward compatibility:** `_decrypt()` catches `InvalidToken` and returns the raw value — this means any old plaintext values stored before encryption was introduced are still readable without a migration.

**Re-encryption on load:** `seed_default_settings()` checks each sensitive row on every `GET /settings` call:
```python
elif existing.is_sensitive and existing.value and not _looks_encrypted(existing.value):
    existing.value = _encrypt(existing.value)  # Auto-upgrade plaintext → encrypted
```

`_looks_encrypted(value)` simply checks `value.startswith("gAAAAA")`.

---

### 4.2 Default Settings Seed

`DEFAULT_SETTINGS` is a list of dicts defined at the top of `settings.py`. Each dict has:

```python
{
    "key":          "llm_provider",
    "value_env":    lambda: os.getenv("LLM_PROVIDER", "ollama"),  # Initial value from env
    "description":  "LLM provider to use: ollama, openrouter, or openai",
    "category":     "llm",
    "is_sensitive": False,
}
```

`seed_default_settings(db)` is called at the top of every `GET /settings` and `PUT /settings/{key}` request. It:
1. Inserts missing rows (first run or new key added to code)
2. Re-encrypts any existing plaintext sensitive values
3. Does nothing for rows that already exist with correct values

**Currently seeded keys:**

| Key | Category | Sensitive | Default |
|---|---|---|---|
| `llm_provider` | llm | No | `ollama` |
| `llm_model` | llm | No | `""` (blank = use provider default) |
| `ollama_url` | llm | No | `http://host.docker.internal:11434` |
| `ollama_model` | llm | No | `gpt-oss:120b-cloud` |
| `llm_api_key` | llm | **Yes** | `""` |
| `langfuse_host` | observability | No | `https://us.cloud.langfuse.com` |
| `langfuse_public_key` | observability | No | `""` |
| `langfuse_secret_key` | observability | **Yes** | `""` |
| `app_timezone` | general | No | `Asia/Kolkata` |

---

### 4.3 API Endpoints

All routes are under prefix `/api/admin/settings`. Every endpoint requires a valid JWT (`get_current_admin` dependency).

#### `GET /api/admin/settings`
Returns all settings grouped by category. Sensitive values are **always** returned as `***HIDDEN***`.

**Response shape:**
```json
{
  "llm": [
    { "key": "llm_provider", "value": "ollama", "description": "...", "category": "llm", "is_sensitive": false },
    { "key": "llm_api_key",  "value": "***HIDDEN***", "description": "...", "category": "llm", "is_sensitive": true }
  ],
  "observability": [ ... ],
  "general": [ ... ]
}
```

#### `PUT /api/admin/settings/{key}`
Updates a single setting by key.

**Request body:** `{ "value": "new-value" }`

**Behavior:**
- If `is_sensitive = True` → Fernet-encrypts the value before writing to DB
- If `is_sensitive = False` → stores plaintext
- Returns the updated row with sensitive value masked as `***HIDDEN***`

#### `GET /api/admin/settings/health`
Performs live connectivity checks. Returns latency in ms.

**Response:**
```json
{
  "checks": [
    { "service": "PostgreSQL", "status": "ok", "latency_ms": 1.2, "detail": "Connection healthy" },
    { "service": "Redis",      "status": "ok", "latency_ms": 0.8, "detail": "PONG received" },
    { "service": "Qdrant",     "status": "ok", "latency_ms": 3.1, "detail": "Healthy" },
    { "service": "Ollama",     "status": "ok", "latency_ms": 12.4, "detail": "3 model(s) loaded" }
  ],
  "overall": "healthy"   // "healthy" | "degraded" | "unhealthy"
}
```

`overall` logic:
- `"unhealthy"` → PostgreSQL or Redis is down (critical services)
- `"degraded"` → Qdrant or Ollama is down (non-critical)
- `"healthy"` → all checks pass

#### `GET /api/admin/settings/celery-status`
Inspects live Celery workers via `celery_app.control.inspect(timeout=3)`.

**Response:**
```json
{
  "workers_found": 1,
  "workers": [
    { "worker_name": "celery@abc123", "status": "online", "active_tasks": 0, "scheduled_tasks": 2 }
  ],
  "beat_schedule": {
    "generate-daily-plans": { "task": "app.tasks.scheduler.generate_daily_plans_scheduler", "schedule": "crontab(...)" }
  },
  "status": "running"   // "running" | "no_workers" | "error: <msg>"
}
```

#### `POST /api/admin/settings/test-llm`
Tests connectivity using the **current saved DB values** (decrypts sensitive keys internally — never exposes them).

- **Ollama:** hits `{ollama_url}/api/tags` and lists available models
- **OpenRouter / OpenAI:** hits `{base_url}/models` with `Authorization: Bearer {api_key}`

**Response:**
```json
{ "status": "ok", "provider": "ollama", "model_or_url": "http://host.docker.internal:11434", "detail": "Connected. Available models: gpt-oss:120b-cloud, llama3.2:latest" }
```

---

### 4.4 Pydantic Schemas

```python
class SettingOut(BaseModel):
    key: str
    value: Optional[str]       # Always "***HIDDEN***" for sensitive fields
    description: Optional[str]
    category: str
    is_sensitive: bool

class SettingUpdate(BaseModel):
    value: Optional[str]

class HealthStatus(BaseModel):
    service: str
    status: str                # "ok" | "error"
    latency_ms: Optional[float]
    detail: Optional[str]

class SystemHealthResponse(BaseModel):
    checks: List[HealthStatus]
    overall: str               # "healthy" | "degraded" | "unhealthy"

class CeleryWorkerInfo(BaseModel):
    worker_name: str
    status: str
    active_tasks: int
    scheduled_tasks: int

class CeleryStatusResponse(BaseModel):
    workers_found: int
    workers: List[CeleryWorkerInfo]
    beat_schedule: Dict[str, Any]
    status: str                # "running" | "no_workers" | "error: <msg>"

class LLMTestResponse(BaseModel):
    status: str                # "ok" | "error"
    provider: str
    model_or_url: str
    detail: str
```

---

## 5. Security Design

### What is protected and how

| Concern | Solution |
|---|---|
| API key exposed in API response | Sensitive fields always return `***HIDDEN***` — zero characters of the real value |
| API key exposed in DB breach | Fernet AES-128-CBC encryption at rest. Ciphertext is unreadable without `SECRET_KEY` |
| Old plaintext values (before encryption) | `_decrypt()` fallback + auto re-encryption in `seed_default_settings()` |
| Admin accesses page after logout | `AdminProtectedRoute` uses `useEffect` + `window.location.replace('/admin/login')` — renders `null` immediately, no content flash |
| Browser back button after logout | `handleLogout` in `AdminLayout.jsx` calls `window.location.replace('/admin/login')` — **replaces** the admin page in browser history, back button skips it entirely |
| Sensitive input pre-filled in browser | Sensitive fields always start **empty** in the UI. The browser never sees the real value |
| Typing `***HIDDEN***` as a new value | Save button is **disabled** when a sensitive input is empty — you must type a real value |

### Encryption key derivation

```
env SECRET_KEY  →  SHA-256 (32 bytes)  →  base64url encode  →  Fernet key
```

No separate encryption key is needed. The same `SECRET_KEY` used for JWT signing is reused. If `SECRET_KEY` changes, all encrypted settings become unreadable — re-save them through the UI after rotation.

### Sensitive placeholder constant

```python
SENSITIVE_PLACEHOLDER = "***HIDDEN***"
```

This is a fixed constant in `settings.py`. It is **never** a stored value — it is only injected at API response time.

---

## 6. LLM Live Config System

**The problem it solves:** `llm_service.py` used to read `LLM_PROVIDER`, `LLM_API_KEY`, etc. from `config.py` at **module import time** (process startup). Any change in DB had no effect until a container restart.

**The fix:** Two helpers added to `llm_service.py`:

```python
def _decrypt_value(stored: str) -> str:
    # Same Fernet logic as settings.py — duplicated to avoid cross-import
    ...

def _get_db_llm_config() -> dict:
    # Opens its own SessionLocal(), reads the 5 LLM keys, decrypts sensitive ones
    # Returns: { "llm_provider": ..., "llm_model": ..., "ollama_url": ...,
    #            "ollama_model": ..., "llm_api_key": <decrypted> }
    # Falls back to empty dict if DB is unreachable
    ...
```

**Every function that creates an LLM instance now calls `_get_db_llm_config()` first:**

```
get_llm()                           ← reads DB every call, uses DB values over env vars
call_llm_json()                     ← calls get_llm() internally
call_llm()                          ← calls get_llm() internally
validate_user_prompt()              ← calls get_llm() internally
generate_chat_title()               ← reads live provider/model to decide path
generate_refined_chat_title()       ← reads live provider/model to decide path
generate_comprehensive_chat_title() ← reads live provider/model to decide path
_generate_title_direct_ollama()             ← reads live ollama_url + model
_generate_refined_title_direct_ollama()     ← reads live ollama_url + model
_generate_comprehensive_title_direct_ollama() ← reads live ollama_url + model
```

**Config priority (highest → lowest):**

```
DB llm_model  >  env LLM_MODEL  >  DB ollama_model  >  DEFAULT_MODELS[provider]
DB llm_provider  >  env LLM_PROVIDER
DB llm_api_key (decrypted)  >  env LLM_API_KEY
DB ollama_url  >  env OLLAMA_URL  >  "http://localhost:11434"
```

**Fallback guarantee:** If the DB is down or the table is missing, `_get_db_llm_config()` returns `{}` and the module-level env var values are used automatically.

---

## 7. Frontend Architecture

**File:** `frontend/src/pages/admin/SystemSettings.jsx`

### 7.1 State Management

All state lives in the top-level `SystemSettings` component:

```javascript
const [activeTab, setActiveTab]     = useState('llm');         // active tab ID
const [settings, setSettings]       = useState({});            // raw API response (grouped by category)
const [editValues, setEditValues]   = useState({});            // { key: currentInputValue }
const [saving, setSaving]           = useState({});            // { key: boolean }
const [saveMsg, setSaveMsg]         = useState({});            // { key: 'saved' | 'error' | null }
const [health, setHealth]           = useState(null);          // health API response
const [healthLoading, setHealthLoading] = useState(false);
const [celery, setCelery]           = useState(null);          // celery-status API response
const [celeryLoading, setCeleryLoading] = useState(false);
const [llmTest, setLlmTest]         = useState(null);          // test-llm API response
const [llmTesting, setLlmTesting]   = useState(false);
const [loadingSettings, setLoadingSettings] = useState(true);
```

### 7.2 Tab System

Three tabs defined as a constant array:

```javascript
const TABS = [
  { id: 'llm',    icon: '🤖', label: 'LLM Configuration' },
  { id: 'health', icon: '💚', label: 'System Health' },
  { id: 'celery', icon: '⚙️', label: 'Celery Tasks' },
];
```

Tab content is rendered conditionally:
```jsx
{activeTab === 'llm'    && <LLMTab />}
{activeTab === 'health' && <HealthTab />}
{activeTab === 'celery' && <CeleryTab />}
```

**Lazy loading:** Health and Celery data are only fetched when their tab is first opened (checked via `!health` / `!celery` guard in `useEffect`). LLM settings are loaded on component mount.

### 7.3 Sensitive Field Behavior

**Key rule:** Sensitive fields never pre-fill with the stored value (because the API only returns `***HIDDEN***`).

**On settings load:**
```javascript
vals[s.key] = s.is_sensitive ? '' : (s.value || '');
// Sensitive → always empty string
// Non-sensitive → actual value from API
```

**Input rendering:**
```jsx
<input
  type={isSensitive ? 'password' : 'text'}  // 'password' hides typed chars
  value={editValues[s.key] || ''}
  placeholder={isSensitive ? 'Type new value to update (current value is hidden)' : ''}
/>
```

**Save button:**
```jsx
disabled={saving[s.key] || (isSensitive && !editValues[s.key])}
// Sensitive + empty input → button disabled (prevents accidentally sending empty string)
```

**After successful save of sensitive field:** input is cleared back to `''` so it never shows stale typed text.

### 7.4 Provider-Conditional Fields

Certain input rows are hidden based on the currently selected provider:

```javascript
const currentProvider = editValues['llm_provider'] || 'ollama';

if (s.key === 'ollama_url'   && currentProvider !== 'ollama') return null;
if (s.key === 'ollama_model' && currentProvider !== 'ollama') return null;
if (s.key === 'llm_api_key'  && currentProvider === 'ollama') return null;
```

| Provider | Visible fields |
|---|---|
| `ollama` | `llm_provider`, `llm_model`, `ollama_url`, `ollama_model` |
| `openrouter` | `llm_provider`, `llm_model`, `llm_api_key` |
| `openai` | `llm_provider`, `llm_model`, `llm_api_key` |

The `llm_provider` field renders as a `<select>` dropdown (special-cased via `isProvider = s.key === 'llm_provider'`). All other fields render as `<input>`.

---

## 8. Health Check System

**Endpoint:** `GET /api/admin/settings/health`

Each service check follows the same pattern:
1. Record `time.monotonic()` before the call
2. Make the connection attempt
3. Calculate latency: `round((time.monotonic() - start) * 1000, 2)` ms
4. Append a `HealthStatus` object with `status="ok"` or `status="error"`

**Services checked:**

| Service | How checked | URL source |
|---|---|---|
| PostgreSQL | `db.execute(text("SELECT 1"))` | Existing SQLAlchemy session |
| Redis | `redis.from_url(...).ping()` | `REDIS_URL` env var |
| Qdrant | `GET {qdrant_url}/healthz` | `QDRANT_URL` env var |
| Ollama | `GET {ollama_url}/api/tags` | `OLLAMA_URL` env var (only when `LLM_PROVIDER=ollama`) |

**Overall status logic:**
```python
overall = "healthy"
if any(c.status == "error" for c in checks):
    critical = [c for c in checks if c.service in ("PostgreSQL", "Redis") and c.status == "error"]
    overall = "unhealthy" if critical else "degraded"
```

---

## 9. Celery Monitoring

**Endpoint:** `GET /api/admin/settings/celery-status`

Uses Celery's built-in `control.inspect()` API with a 3-second timeout:

```python
inspector = celery_app.control.inspect(timeout=3)
active_map    = inspector.active()    # { worker_name: [task, ...] }
scheduled_map = inspector.scheduled() # { worker_name: [task, ...] }
```

Beat schedule is read from `celery_app.conf.beat_schedule` — this is the static config from `celery_app.py`, not live execution data.

**Status values:**
- `"running"` — at least one worker responded
- `"no_workers"` — inspect returned empty dict (workers offline or not started)
- `"error: <msg>"` — exception thrown during inspect

---

## 10. How-To: Common Tasks

### 10.1 Add a New Setting Key

**Step 1 — Add to `DEFAULT_SETTINGS` in `settings.py`:**
```python
{
    "key":          "my_new_setting",
    "value_env":    lambda: os.getenv("MY_NEW_SETTING", "default_value"),
    "description":  "What this setting controls",
    "category":     "general",     # Use existing category or add new one
    "is_sensitive": False,          # Set True if it's an API key / secret
},
```

**Step 2 — The new row is auto-inserted** the next time `GET /api/admin/settings` is called (via `seed_default_settings`). No migration needed for new rows.

**Step 3 — Frontend:** If the new key belongs to an existing category (llm / observability / general), it appears automatically via `renderSettingRow()`. No frontend change needed unless you need special rendering (e.g. a dropdown like `llm_provider`).

**Step 4 — If the setting needs to affect LLM calls:** Add it to the `keys` list in `_get_db_llm_config()` in `llm_service.py` and use it inside `get_llm()`.

---

### 10.2 Add a New Category / Tab

**Step 1 — Use the new category string** in `DEFAULT_SETTINGS` entries:
```python
"category": "notifications",
```

**Step 2 — Add to the TABS constant** in `SystemSettings.jsx`:
```javascript
const TABS = [
  { id: 'llm',           icon: '🤖', label: 'LLM Configuration' },
  { id: 'health',        icon: '💚', label: 'System Health' },
  { id: 'celery',        icon: '⚙️', label: 'Celery Tasks' },
  { id: 'notifications', icon: '🔔', label: 'Notifications' },  // ← new
];
```

**Step 3 — Add a tab content component** and wire it up:
```jsx
const NotificationsTab = () => {
  const notifSettings = settings['notifications'] || [];
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Notifications</h3>
        {loadingSettings ? <p className="text-gray-400 text-sm">Loading…</p> : notifSettings.map(renderSettingRow)}
      </div>
    </div>
  );
};

// In the render section:
{activeTab === 'notifications' && <NotificationsTab />}
```

---

### 10.3 Add a New Health Check Service

In `settings.py`, inside the `system_health()` function, append a new block following the existing pattern:

```python
# My New Service
try:
    my_url = os.getenv("MY_SERVICE_URL", "http://my-service:port")
    start = time.monotonic()
    resp = requests.get(f"{my_url}/health", timeout=3)
    latency = round((time.monotonic() - start) * 1000, 2)
    if resp.status_code == 200:
        checks.append(HealthStatus(service="MyService", status="ok", latency_ms=latency, detail="Healthy"))
    else:
        checks.append(HealthStatus(service="MyService", status="error", latency_ms=latency, detail=f"HTTP {resp.status_code}"))
except Exception as e:
    checks.append(HealthStatus(service="MyService", status="error", latency_ms=None, detail=str(e)))
```

Decide if the service is critical (adds it to the `critical` list for `"unhealthy"` detection):
```python
critical = [c for c in checks if c.service in ("PostgreSQL", "Redis", "MyService") and c.status == "error"]
```

---

### 10.4 Change the Encryption Key

> ⚠️ **Warning:** Changing `SECRET_KEY` invalidates all existing Fernet-encrypted values in the DB. All sensitive settings must be re-entered through the admin UI after rotating the key.

**Steps:**
1. Update `SECRET_KEY` in your `.env` file
2. Restart backend: `docker compose restart backend`
3. Go to Admin → System Settings → LLM Configuration
4. Re-enter all sensitive values (API keys, Langfuse secret key)
5. Click Save for each one

---

## 11. API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/admin/settings` | Admin JWT | List all settings grouped by category |
| `PUT` | `/api/admin/settings/{key}` | Admin JWT | Update a single setting by key |
| `GET` | `/api/admin/settings/health` | Admin JWT | Live health check of all services |
| `GET` | `/api/admin/settings/celery-status` | Admin JWT | Celery worker and beat schedule info |
| `POST` | `/api/admin/settings/test-llm` | Admin JWT | Test LLM connectivity using saved DB values |

**Auth header:** All requests require:
```
Authorization: Bearer <admin_jwt_token>
```

The token is obtained from `POST /api/admin/login` and stored in `localStorage` by `adminAuth.js`.

---

## 12. Docker Commands

```bash
# Restart backend to pick up code changes
docker compose restart backend

# View backend logs (last 50 lines)
docker compose logs --tail=50 backend

# Run Alembic migration (after adding new model or column)
docker compose exec backend alembic upgrade head

# Open a psql shell to inspect the system_settings table directly
docker compose exec postgres psql -U lalit -d fitness_track -c \
  "SELECT key, LEFT(value, 40) AS value_preview, is_sensitive FROM system_settings ORDER BY category, key;"

# Restart Celery worker
docker compose restart celery

# View Celery logs
docker compose logs --tail=50 celery
```

---

*Last updated: March 2026*
