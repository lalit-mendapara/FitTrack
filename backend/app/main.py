import warnings
# Suppress Pydantic V1 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core._api.deprecation")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.v1")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine,Base
import app.models
from app.api import users,user_profile,meal_plan,login,workout_plan,workout_preferences,chat,tracking

print(engine.url)


#create table in database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add CORS Middleware
# Allow multiple origins for local dev and Docker
allowed_origins = [
    "http://localhost:3000",    # Legacy/alternative
    "http://localhost:5173",    # Vite dev server (local)
    "http://127.0.0.1:5173",    # Vite dev server (local alt)
    "http://frontend:5173",     # Docker container name
]

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
app.include_router(chat.router)
app.include_router(tracking.router, prefix="/tracking", tags=["Tracking"])
from app.api import notifications
app.include_router(notifications.router)

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
