import warnings
# Suppress Pydantic V1 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core._api.deprecation")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.v1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.database import engine,Base
import app.models
from app.api import users,user_profile,meal_plan,login,workout_plan,workout_preferences,chat,tracking,workout_plan_async
from app.api.admin import auth as admin_auth, users as admin_users, analytics as admin_analytics, foods as admin_foods, exercises as admin_exercises, feasts as admin_feasts, settings as admin_settings
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)


print(engine.url)


# Run Alembic migrations on startup (replaces create_all)
def run_migrations():
    """Run pending Alembic migrations automatically on startup."""
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("[Alembic] Migrations applied successfully")
    except Exception as e:
        print(f"[Alembic] Migration failed, falling back to create_all: {e}")
        
    # Ensure all tables exist (critical for new models not yet in Alembic)
    print("[Startup] Ensuring all tables exist via create_all...")
    Base.metadata.create_all(bind=engine)

run_migrations()

app = FastAPI()

# Mount uploads directory for serving avatar images
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(os.path.join(uploads_dir, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Add CORS Middleware
# Allow multiple origins for local dev and Docker
allowed_origins = [
    "http://localhost:3000",    # Legacy/alternative
    "http://localhost:5173",    # Vite dev server (local)
    "http://127.0.0.1:5173",    # Vite dev server (local alt)
    "http://frontend:5173",     # Docker container name
]
# Add extra origins from env (comma-separated)
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(users.router)
app.include_router(login.router)
app.include_router(user_profile.router)
app.include_router(meal_plan.router)
app.include_router(workout_preferences.router)
app.include_router(workout_plan.router)
app.include_router(workout_plan_async.router)  # Async workout generation
app.include_router(chat.router)
app.include_router(tracking.router, prefix="/tracking", tags=["Tracking"])
from app.api import notifications
app.include_router(notifications.router)
from app.api import social_events
app.include_router(social_events.router)
from app.api import feast_mode
app.include_router(feast_mode.router)
app.include_router(admin_auth.router)
app.include_router(admin_users.router)
app.include_router(admin_analytics.router)
app.include_router(admin_foods.router)
app.include_router(admin_exercises.router)
app.include_router(admin_feasts.router)
app.include_router(admin_settings.router)

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Welcome to Fitness Tracker API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}
