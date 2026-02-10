# Diet Planner & Fitness Tracker

A comprehensive, AI-powered Diet Planner and Fitness Tracking application designed to help users achieve their health goals through personalized meal plans and workout insights.

## 🚀 Key Features

*   **AI-Driven Meal Planning**: Generates personalized meal plans (Vegan/Non-Veg) based on user goals (Weight Loss, Muscle Gain, Maintenance).
*   **Smart Alternatives**: Provides customizable food alternatives with portion sizes.
*   **Customizable Regeneration**: Users can refine their meal plans using natural language prompts (e.g., "I want a vegan breakfast") via the "How can I help you?" modal.
*   **Personalized Guidelines**: Offers fitness-goal-specific actionable advice for each meal.
*   **Interactive Nutrition Dashboard**: Dynamic analog-style meters and charts for visualizing daily nutrition (Calories, Protein, Carbs, Fat).
*   **Secure Authentication**: robust JWT-based authentication with secure cookie management.
*   **Responsive UI**: Modern, mobile-first design with "glassmorphism" effects and fluid animations.
*   **Profile Management**: Tracks user details, BMI, and dietary preferences.

## 🛠️ Tech Stack

### Frontend
*   **Framework**: [React](https://reactjs.org/) (Vite)
*   **Language**: JavaScript (ES6+)
*   **Styling**: [Tailwind CSS](https://tailwindcss.com/) (v4), Vanilla CSS for custom animations.
*   **Icons**: Lucide React
*   **State Management**: Context API (Auth), React Hooks
*   **Data Visualization**: Recharts
*   **API Client**: Axios

### Backend
*   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
*   **Database ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
*   **Authentication**: OAuth2 with JWT (JSON Web Tokens), `passlib` for hashing.
*   **AI Integration**: Ollama / LLM (Prompt Engineering for meal generation)
*   **Vector Database**: Qdrant for semantic search
*   **Task Queue**: Celery with Redis broker
*   **Validation**: Pydantic
*   **Environment Management**: `python-dotenv`

## 📂 Project Structure

```
diet_planner_3/
├── backend/                # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API Route endpoints (login, users, meal_plan)
│   │   ├── core/           # Core config (security, secrets)
│   │   ├── crud/           # Database operations (Create, Read, Update, Delete)
│   │   ├── models/         # SQLAlchemy Database Models
│   │   ├── schemas/        # Pydantic Data Schemas (Request/Response validation)
│   │   ├── services/       # Business logic (LLM, AI Coach, etc.)
│   │   └── tasks/          # Celery background tasks
│   ├── Dockerfile          # Backend container definition
│   ├── main.py             # Application entry point
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── api/            # Axios setup
│   │   ├── components/     # Reusable UI components (Navbar, Hero, Cards)
│   │   ├── context/        # Global state (AuthContext)
│   │   ├── images/         # Local static assets
│   │   ├── pages/          # Main views (Home, DietPlan, Login)
│   │   └── index.css       # Global styles & Tailwind directives
│   ├── Dockerfile          # Frontend container definition
│   ├── index.html          # HTML entry point
│   └── package.json        # Frontend dependencies
│
├── docker-compose.yml      # Docker orchestration
├── .env.docker.example     # Docker environment template
├── .gitignore              # Git ignore rules
└── README.md
```

---

## �️ Complete Setup Guide

This guide covers everything you need to run this project locally. Choose either **Docker (Recommended)** or **Manual Setup**.

---

## 📋 System Requirements

Before starting, ensure you have these installed:

| Requirement | Version | How to Check | Installation |
|-------------|---------|--------------|--------------|
| **Docker** | 20.10+ | `docker --version` | [Get Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | `docker-compose --version` | Included with Docker Desktop |
| **Ollama** | Latest | `ollama --version` | [Get Ollama](https://ollama.ai/) |
| **Node.js** (local only) | 18+ | `node --version` | [Get Node.js](https://nodejs.org/) |
| **Python** (local only) | 3.10+ | `python --version` | [Get Python](https://python.org/) |
| **PostgreSQL** (local only) | 14+ | `psql --version` | [Get PostgreSQL](https://postgresql.org/) |

---

## 🐳 Option 1: Docker Setup (Recommended)

Docker automatically sets up PostgreSQL, Redis, Qdrant, Backend, Celery, and Frontend.

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/diet_planner_3.git
cd diet_planner_3
```

### Step 2: Create Environment File
```bash
cp .env.docker.example .env.docker
```

### Step 3: Configure Environment Variables

Edit `.env.docker` with your values:

```bash
# 📝 Open the file
nano .env.docker  # or use any text editor
```

**Required variables to update:**

```env
# Database (you can keep defaults or customize)
POSTGRES_USER=diet_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=fitness_track

# Security - MUST CHANGE! Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_64_character_random_string_here

# LLM - Your Ollama API key
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_MODEL=gpt-oss:120b-cloud  # or your preferred model
```

### Step 4: Start Ollama

> ⚠️ **Important**: Ollama must run on your **host machine** (not inside Docker).

```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Pull the Models (Chat + Embeddings)
ollama pull gpt-oss:120b-cloud
ollama pull all-minilm
```

### Step 5: Start Docker Services

```bash
# Start all containers
docker-compose --env-file .env.docker up -d

# Wait ~30 seconds for all services to initialize, then check health
docker-compose ps
```

**Expected output:**
```
NAME                      STATUS              PORTS
diet_planner_backend      Up (healthy)        0.0.0.0:8000->8000/tcp
diet_planner_celery       Up                  ---
diet_planner_db           Up (healthy)        0.0.0.0:5433->5432/tcp
diet_planner_frontend     Up                  0.0.0.0:5173->5173/tcp
diet_planner_qdrant       Up                  0.0.0.0:6333->6333/tcp
diet_planner_redis        Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Step 6: Initialize Database (First Time Only)

```bash
# The database tables are automatically created when the backend starts.
# You do NOT need to run manual migrations.
# Just ensuring the backend container is healthy is enough.
```

### Step 7: Access the Application

| Service | URL |
|---------|-----|
| 🌐 **Frontend** | http://localhost:5173 |
| 🔧 **Backend API** | http://localhost:8000 |
| 📚 **API Docs (Swagger)** | http://localhost:8000/docs |
| 🔍 **Qdrant Dashboard** | http://localhost:6333/dashboard |

---

### Docker Commands Reference

```bash
# Start all services (detached)
docker-compose --env-file .env.docker up -d

# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v

# Rebuild after code changes
docker-compose build --no-cache && docker-compose --env-file .env.docker up -d

# Enter backend container shell
docker exec -it diet_planner_backend bash

# Check backend health
curl http://localhost:8000/health
```

---

### Docker Reset & Database Restoration

If you need to completely reset your Docker environment and restore data from `backup.sql`, follow these manual steps.

#### 1. Remove Existing Containers & Volumes
This **completely wipes** your Docker database to ensure a clean restore.
```bash
docker-compose --env-file .env.docker down -v
```

#### 2. Start Only the Database
We need the database running first to accept the backup.
```bash
docker-compose --env-file .env.docker up -d postgres
```
**Wait about 10-15 seconds** to ensure the database is fully ready to accept connections.

#### 3. Copy Backup File to Container
Copy your local `backup.sql` into the running database container.
```bash
docker cp backup.sql diet_planner_db:/backup.sql
```

#### 4. Restore the Database
Execute the restore command inside the container.
- It might ask for a password, but usually it won't if the container is configured correctly.
- If errors appear about "role 'lalit' already exists", you can ignore them.
```bash
docker exec -it diet_planner_db psql -U lalit -d fitness_track -f /backup.sql
```

#### 5. Start the Application
Now that the data is restored, start the backend and other services.
```bash
docker-compose --env-file .env.docker up -d
```

### Creating a New Backup
If you want to save your current Docker database state to `backup.sql`:
```bash
docker exec -t diet_planner_db pg_dump -U lalit -d fitness_track --clean --if-exists > backup.sql
```

---

## 💻 Option 2: Manual Local Setup (Without Docker)

For local development with more control over each service.

### Step 1: Install External Services

You need to install and run these services:

#### PostgreSQL
```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Create database
createdb fitness_track
```

#### Redis
```bash
# macOS
brew install redis
brew services start redis
```

#### Qdrant
```bash
# Option A: Docker (even for local development)
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Option B: Download binary from https://qdrant.tech/
```

#### Ollama
```bash
# Download from https://ollama.ai/
# Then start:
ollama serve
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Backend Environment

```bash
# Create .env file
cp .envexample .env
```

Edit `backend/.env`:
```env
# Database (local PostgreSQL)
SQLALCHEMY_DATABASE_URL=postgresql://your_username:your_password@localhost:5432/fitness_track

# Security
SECRET_KEY=your_secret_key_generate_with_python_secrets
ALGORITHM=HS256

# Redis (local)
REDIS_URL=redis://localhost:6379/0

# Qdrant (local)
QDRANT_URL=http://localhost:6333

# Ollama (local)
OLLAMA_URL=http://localhost:11434
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_MODEL=gpt-oss:120b-cloud
```

### Step 4: Initialize Database

```bash
cd backend

# The database tables are automatically created on startup.
# No manual migration command needed.
```

### Step 5: Start Backend Server

```bash
cd backend
source venv/bin/activate

# Start FastAPI with hot-reload
uvicorn app.main:app --reload --port 8000
```

### Step 6: Start Celery Worker (New Terminal)

```bash
cd backend
source venv/bin/activate

# Start Celery with beat scheduler
celery -A app.celery_app worker --beat --loglevel=info
```

### Step 7: Frontend Setup (New Terminal)

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

### Step 8: Access the Application

Same URLs as Docker setup:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🔥 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Port already in use** | Kill the process: `lsof -ti:8000 \| xargs kill -9` |
| **Database connection refused** | Ensure PostgreSQL is running: `brew services start postgresql` |
| **Ollama not responding** | Check if Ollama is running: `curl http://localhost:11434` |
| **Docker containers unhealthy** | Check logs: `docker-compose logs -f postgres` |
| **CORS errors** | Backend may not be running or CORS misconfigured |

### PostgreSQL Issues
*   **Password Error**: If `POSTGRES_PASSWORD` has special chars (`@`, `:`, `#`), it breaks the connection URL. Use alphanumeric passwords.
*   **Stale Data**: IF you changed credentials in `.env` *after* first run, delete volumes: `docker-compose down -v`.

### Verifying Services

```bash
# Check PostgreSQL
psql -U your_username -d fitness_track -c "\dt"

# Check Redis
redis-cli ping  # Should return PONG

# Check Qdrant
curl http://localhost:6333/collections

# Check Ollama
curl http://localhost:11434/api/version

# Check Backend
curl http://localhost:8000/health
```

---

## 🔐 Security Best Practices

- **Never commit `.env` files** - They're in `.gitignore`
- **Generate strong SECRET_KEY** - Use `python -c "import secrets; print(secrets.token_hex(32))"`
- **Use unique database passwords** - Don't use defaults in production
- **CORS is configured** - Only allows specified origins

---

## 📋 Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `SQLALCHEMY_DATABASE_URL` | PostgreSQL connection string | ✅ |
| `SECRET_KEY` | JWT signing key | ✅ |
| `ALGORITHM` | JWT algorithm (default: HS256) | ❌ |
| `REDIS_URL` | Redis connection for Celery | ✅ |
| `QDRANT_URL` | Qdrant vector database URL | ✅ |
| `OLLAMA_API_KEY` | Ollama API key | ✅ |
| `OLLAMA_MODEL` | LLM model name | ❌ |
| `LANGFUSE_SECRET_KEY` | Langfuse secret (optional) | ❌ |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public (optional) | ❌ |

---

*Generated by Antigravity*
