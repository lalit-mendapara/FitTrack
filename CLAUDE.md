# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Diet Planner & Fitness Tracker - An AI-powered web application that generates personalized meal plans and workout routines based on user profiles, dietary preferences, and fitness goals. Uses LLMs (via Ollama/OpenRouter/OpenAI) for meal generation and Qdrant vector database for semantic food search.

**Tech Stack:**
- Backend: FastAPI (Python 3.10+), SQLAlchemy ORM, PostgreSQL
- Frontend: React (Vite), Tailwind CSS v4
- Background Tasks: Celery with Redis broker
- AI/ML: LangChain, Qdrant (vector DB), sentence-transformers
- Authentication: JWT tokens with httpOnly cookies

## Common Commands

### Backend Development

```bash
# Setup (from backend/ directory)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run development server with hot-reload
cd backend
uvicorn app.main:app --reload --port 8000

# Run Celery worker with beat scheduler (separate terminal)
cd backend
celery -A app.celery_app worker --beat --loglevel=info

# Run tests
cd backend
pytest                                    # All tests
pytest tests/integration/                 # Integration tests only
pytest tests/test_user_profile_macros.py  # Single test file
pytest -v -s                              # Verbose with output
```

### Frontend Development

```bash
# Setup (from frontend/ directory)
npm install

# Run Vite dev server (port 5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

### Docker Development

```bash
# Start all services (from project root)
docker-compose --env-file .env.docker up -d

# View logs
docker-compose logs -f backend   # Backend only
docker-compose logs -f           # All services

# Rebuild after code changes
docker-compose build --no-cache && docker-compose --env-file .env.docker up -d

# Stop and remove all containers + volumes (fresh start)
docker-compose down -v

# Access backend container shell
docker exec -it diet_planner_backend bash

# Database backup
docker exec -t diet_planner_db pg_dump -U lalit -d fitness_track --clean --if-exists > backup.sql

# Database restore
docker cp backup.sql diet_planner_db:/backup.sql
docker exec -it diet_planner_db psql -U lalit -d fitness_track -f /backup.sql
```

### Database Operations

```bash
# Database tables are auto-created on startup via SQLAlchemy
# See backend/app/main.py: Base.metadata.create_all(bind=engine)
# No manual migrations needed - schema is defined in models

# Access PostgreSQL (Docker)
docker exec -it diet_planner_db psql -U lalit -d fitness_track

# Access PostgreSQL (local)
psql -U your_username -d fitness_track

# Seed database with food items
cd backend
python scripts/db_tools/seed_db.py

# Check database contents
python scripts/db_tools/check_users.py
python scripts/db_tools/inspect_db.py
```

## Architecture

### Backend Structure

```
backend/app/
├── api/              # FastAPI route handlers (endpoints)
│   ├── login.py      # Authentication endpoints
│   ├── users.py      # User CRUD operations
│   ├── user_profile.py
│   ├── meal_plan.py  # Meal plan generation and retrieval
│   ├── workout_plan.py
│   ├── chat.py       # AI Coach chat interface
│   ├── tracking.py   # Meal/workout tracking (modified recently)
│   ├── notifications.py
│   └── social_events.py
├── models/           # SQLAlchemy database models
├── schemas/          # Pydantic validation schemas (request/response)
├── crud/             # Database operations (Create, Read, Update, Delete)
├── services/         # Business logic layer
│   ├── llm_service.py       # LLM provider abstraction (Ollama/OpenRouter/OpenAI)
│   ├── meal_service.py      # Meal plan generation logic
│   ├── workout_service.py
│   ├── vector_service.py    # Qdrant semantic search
│   ├── ai_coach.py          # Conversational AI coach
│   └── nutrition_service.py
├── tasks/            # Celery background tasks
│   └── scheduler.py  # Daily meal plan generation scheduler (runs every minute to check for 5am users)
├── utils/            # Utility functions (auth, calculations)
├── database.py       # SQLAlchemy setup and session management
├── celery_app.py     # Celery configuration
└── main.py           # FastAPI app initialization and CORS setup
```

### Frontend Structure

```
frontend/src/
├── api/              # Axios API client setup
├── components/       # Reusable UI components
├── context/          # React Context providers
│   └── AuthContext.jsx  # Global auth state management
├── pages/            # Main route components
│   ├── Login.jsx, Signup.jsx
│   ├── DietPlan.jsx     # Meal plan display and regeneration
│   ├── WorkoutPlan.jsx
│   ├── Dashboard.jsx    # Nutrition tracking dashboard
│   └── AICoach.jsx      # Chat interface
└── index.css         # Global styles + Tailwind directives
```

## Key Architectural Patterns

### Authentication Flow

1. User logs in via [/login/json](backend/app/api/login.py:49) (JSON body) or [/login](backend/app/api/login.py:14) (OAuth2 form)
2. Backend validates credentials using `verify_password` from [backend/app/utils/utils.py](backend/app/utils/utils.py)
3. JWT token is generated via `create_access_token` and returned in:
   - Response body (`access_token`, `token_type`, `user_id`)
   - httpOnly cookie (`access_token`, samesite=lax, secure=False in dev)
4. Frontend stores token in AuthContext and includes in subsequent requests
5. Protected endpoints use `get_current_user` dependency to validate JWT

### LLM Integration

The application supports multiple LLM providers via environment configuration:

**Configuration** ([config.py](backend/config.py)):
- `LLM_PROVIDER`: "ollama" (local), "openrouter", or "openai"
- `LLM_API_KEY`: API key for paid providers
- `LLM_MODEL`: Optional model override (defaults: gpt-oss:120b-cloud for Ollama, gemini-2.0-flash-001 for OpenRouter)

**Usage** ([backend/app/services/llm_service.py](backend/app/services/llm_service.py)):
- `get_llm(temperature, max_tokens, json_mode)` - Returns configured LangChain ChatModel
- All LLM calls use LangChain for consistency
- `@observe` decorator from Langfuse for tracing (disabled on Python 3.14+ due to Pydantic v1 incompatibility)

### Meal Plan Generation

**Daily Regeneration** ([backend/app/tasks/scheduler.py](backend/app/tasks/scheduler.py)):
- Celery beat scheduler runs every minute
- Checks all users for local time >= 5:00 AM
- Generates new meal plan if none exists for current day (idempotent)
- Creates "plan_ready" notification
- Uses last 8 meal plans to avoid dish repetition

**Manual Regeneration** ([backend/app/api/meal_plan.py](backend/app/api/meal_plan.py)):
- User can regenerate via "How can I help you?" modal
- Supports natural language prompts (e.g., "I want a vegan breakfast")
- Calls [meal_service.regenerate_meal_plan()](backend/app/services/meal_service.py)

**Vector Search** ([backend/app/services/vector_service.py](backend/app/services/vector_service.py)):
- Food items are embedded using sentence-transformers (all-minilm model via Ollama)
- Stored in Qdrant vector database for semantic similarity search
- Used to find nutritionally similar food alternatives

### Celery Configuration

**Important for macOS** ([backend/app/celery_app.py](backend/app/celery_app.py:10)):
- Uses `pool_type="solo"` on macOS to avoid SIGSEGV crashes with fork
- Uses `pool_type="prefork"` on Linux
- Beat schedule stored in `celery_beat_data/` directory

### Database Schema

Tables are auto-created on startup via SQLAlchemy `Base.metadata.create_all()`. Key models:
- `User`: Authentication ([backend/app/models/user.py](backend/app/models/user.py))
- `UserProfile`: Demographics, goals, preferences ([backend/app/models/user_profile.py](backend/app/models/user_profile.py))
- `MealPlan`: Current active meal plan
- `MealPlanHistory`: Historical meal plans (last 8 used for variety)
- `WorkoutPlan`, `WorkoutPlanHistory`: Similar structure for workouts
- `FoodItem`: Food database with nutrition info ([backend/app/models/food_item.py](backend/app/models/food_item.py))
- `Tracking`: User's logged meals/workouts ([backend/app/models/tracking.py](backend/app/models/tracking.py))
- `Notification`, `SocialEvent`, `ChatMessage`

## Environment Configuration

**Backend** ([backend/.envexample](backend/.envexample)):
- Copy `.envexample` to `.env`
- Required: `SQLALCHEMY_DATABASE_URL`, `SECRET_KEY`, `REDIS_URL`, `QDRANT_URL`, `OLLAMA_API_KEY`
- LLM config: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`
- Optional: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `USDA_API_KEY`

**Docker** ([.env.docker.example](.env.docker.example)):
- Used by docker-compose
- Database hosts use container names (e.g., `postgres:5432` instead of `localhost:5432`)
- Ollama accessed via `host.docker.internal:11434` (Ollama must run on host machine)

## External Service Requirements

**Ollama** (Required for LLM):
- Must be running on host machine (not in Docker)
- Default URL: `http://localhost:11434`
- Required models: `ollama pull gpt-oss:120b-cloud` and `ollama pull all-minilm`
- Start: `ollama serve`

**PostgreSQL** (Required):
- Port 5432 (local) or 5433 (Docker host mapping)
- Database name: `fitness_track`

**Redis** (Required for Celery):
- Port 6379
- No authentication in dev

**Qdrant** (Required for vector search):
- Port 6333 (API), 6334 (internal)
- Dashboard: http://localhost:6333/dashboard
- No authentication in dev

## Important Conventions

### API Response Patterns

- Most endpoints return JSON responses matching Pydantic schemas in `app/schemas/`
- Authentication endpoints set httpOnly cookies AND return token in body
- Error responses use FastAPI's HTTPException with appropriate status codes
- List endpoints typically return arrays directly, not wrapped in envelope

### Code Organization

- **Routers** (`app/api/`) define endpoints and handle request/response
- **CRUD** (`app/crud/`) contains pure database operations (no business logic)
- **Services** (`app/services/`) contain business logic, LLM interactions, and complex operations
- **Models** define database schema
- **Schemas** define API contracts (request/response validation)

### Frontend API Calls

- All backend requests go through Vite proxy: `/api/*` → `http://backend:8000/*` (path rewritten)
- Axios instance in `frontend/src/api/` handles base URL and auth headers
- AuthContext provides `login`, `logout`, `user` state globally

## Testing

**Test Structure**:
- `tests/integration/` - End-to-end tests requiring database and LLM
- `tests/manual/` - Manual test scripts for specific scenarios
- `tests/test_*.py` - Unit tests

**Common Test Patterns**:
```python
# Tests use SessionLocal directly, not get_db dependency
from app.database import SessionLocal
db = SessionLocal()

# LLM tests may take time and cost money - mock when possible
# Integration tests assume Ollama is running
```

## Git Recent Changes

Recent commits show:
- Tracking API modifications ([backend/app/api/tracking.py](backend/app/api/tracking.py)) - check git diff for latest changes
- Feast mode feature added and deactivated
- Dashboard UI enhancements
- Scheduler timezone logic fixes

When making changes to tracking, meal plans, or scheduling, review recent commits for context.

## CORS Configuration

Allowed origins ([backend/app/main.py:22](backend/app/main.py:22)):
- `http://localhost:5173` (Vite dev server, local)
- `http://127.0.0.1:5173` (alternative)
- `http://localhost:3000` (legacy)
- `http://frontend:5173` (Docker container name)

Add new origins here if deploying to different domains.
