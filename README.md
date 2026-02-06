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

## 🐳 Quick Start with Docker (Recommended)

### Prerequisites
*   [Docker](https://docs.docker.com/get-docker/) and Docker Compose
*   [Ollama](https://ollama.ai/) running on your machine (for AI features)

### Setup Steps

1.  **Clone the repository**
    ```bash
    git clone https://github.com/YOUR_USERNAME/diet_planner_3.git
    cd diet_planner_3
    ```

2.  **Create environment file**
    ```bash
    cp .env.docker.example .env.docker
    ```

3.  **Edit `.env.docker`** with your credentials:
    ```bash
    # Required
    POSTGRES_PASSWORD=your_secure_database_password
    SECRET_KEY=your_jwt_secret_key
    OLLAMA_API_KEY=your_ollama_api_key
    
    # Optional (for LLM observability)
    LANGFUSE_SECRET_KEY=your_langfuse_secret
    LANGFUSE_PUBLIC_KEY=your_langfuse_public
    ```

4.  **Start Ollama** (on your host machine)
    ```bash
    ollama serve
    ```

5.  **Start all services**
    ```bash
    docker-compose --env-file .env.docker up -d
    ```

6.  **Access the application**
    *   Frontend: http://localhost:5173
    *   Backend API: http://localhost:8000
    *   API Docs: http://localhost:8000/docs

### Docker Commands

```bash
# Start all services
docker-compose --env-file .env.docker up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

---

## 💻 Local Development Setup (Without Docker)

### Prerequisites
*   Node.js (v18+)
*   Python (v3.10+)
*   PostgreSQL
*   Redis
*   Ollama

### Backend Setup
1.  Navigate to `backend`:
    ```bash
    cd backend
    ```
2.  Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create `.env` file:
    ```bash
    cp .envexample .env
    # Edit .env with your local database credentials
    ```
5.  Run the server:
    ```bash
    uvicorn app.main:app --reload
    ```
    *Server runs at `http://localhost:8000`*

### Frontend Setup
1.  Navigate to `frontend`:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start development server:
    ```bash
    npm run dev
    ```
    *App runs at `http://localhost:5173`*

### Celery Worker (Background Tasks)
```bash
cd backend
celery -A app.celery_app worker --beat --loglevel=info
```

---

## 🔒 Security Best Practices

*   **Password Hashing**: Never storing plain-text passwords.
*   **JWT Expiration**: Access tokens expire after a set time (e.g., 24 hours).
*   **CORS Protection**: API configured to allow specific origins.
*   **Protected Routes**: Frontend redirects unauthenticated users away from private pages.
*   **Environment Variables**: All secrets stored in `.env` files (never committed to Git).

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
