# PillSync — Intelligent Medicine Reminder and Medication Tracking Platform

[![Project Phase](https://img.shields.io/badge/Phase-0%20(Foundation)-teal.svg)](.)
[![Backend](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org)
[![Database](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org)
[![ORM](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org)
[![Migrations](https://img.shields.io/badge/Alembic-1.14-brown.svg)](https://alembic.sqlalchemy.org)

PillSync is an intelligent medication tracking and reminder platform developed as an Infosys project. It provides patient adherence monitoring, smart schedule management, OCR prescription intake, caregiver workflows, and proactive refill predictions.

---

## Phase 0: Project Scope & Foundation

Phase 0 establishes the bedrock infrastructure and system architecture.

### Architectural Principles & Policies
1. **Zero Mock Business Data Policy**: No sample patients, demo medicines, fake prescriptions, or hardcoded dashboard statistics are generated. Empty states are rendered dynamically when no records exist.
2. **Modular Layered Architecture**: Clear separation across presentation (`frontend`), API routing (`api/v1`), domain logic (`services`), persistence (`models`, `repositories`), database migrations (`alembic`), and containerization (`docker-compose.yml`).
3. **Environment-Driven Configuration**: All credentials, database connection strings, and hosts are injected via environment variables. No secrets are hardcoded or committed to git.
4. **Resilient Health & Diagnostics**: Dedicated `GET /api/v1/health` endpoint verifying both API process uptime and PostgreSQL connectivity, returning granular statuses (`healthy`, `degraded`).

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS | Modern, responsive single-page web shell |
| **Routing & HTTP** | React Router DOM, Axios | Navigation and REST API communication with error handling |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | High-performance asynchronous REST API framework |
| **ORM & Migrations** | SQLAlchemy 2.0, Alembic, psycopg2 | Object-Relational Mapping & schema version control |
| **Database** | PostgreSQL 16 (Primary) | Relational persistence engine |
| **Containerization** | Docker, Docker Compose | Multi-container local orchestration |
| **Backend Testing** | Pytest, HTTPX, Pytest-Asyncio | Automated backend unit and integration tests |
| **Frontend Testing** | Vitest, React Testing Library, JSDOM | Component, state, and API integration tests |

---

## Project Structure

```
pillsync/
├── .env.example                # Root environment variables template
├── .gitignore                  # Git ignore rules (secrets, venv, node_modules)
├── docker-compose.yml          # Multi-container orchestration (DB, API, Web)
├── README.md                   # Project documentation and developer guide
├── backend/
│   ├── .env.example            # Backend-specific environment variables template
│   ├── alembic.ini             # Alembic migration configuration
│   ├── Dockerfile              # Container definition for FastAPI backend
│   ├── requirements.txt        # Python package dependencies
│   ├── alembic/
│   │   ├── env.py              # Alembic environment runner
│   │   ├── script.py.mako      # Migration revision template
│   │   └── versions/           # Migration history scripts
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           └── health.py # GET /api/v1/health endpoint
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic BaseSettings management
│   │   │   ├── database.py     # SQLAlchemy engine, session & connection probes
│   │   │   └── logging.py      # Structured application logger
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── base.py         # SQLAlchemy Base and timestamp mixins
│   │   ├── repositories/       # Data access layer (Phase 1+)
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── health.py       # Pydantic schemas for health & diagnostics
│   │   ├── services/           # Business logic layer (Phase 1+)
│   │   ├── utils/              # Shared helper functions
│   │   └── main.py             # FastAPI entrypoint, CORS, lifecycle hooks
│   └── tests/
│       ├── conftest.py         # Pytest fixtures and TestClient setup
│       └── test_health.py      # Health API & configuration test suite
├── frontend/
│   ├── .env.example            # Frontend environment variables template
│   ├── Dockerfile              # Multi-stage container build (Node + Nginx)
│   ├── nginx.conf              # Nginx reverse proxy configuration
│   ├── package.json            # NPM dependencies and scripts
│   ├── tailwind.config.js      # Tailwind CSS theme configuration
│   ├── vite.config.js          # Vite build and test configuration
│   ├── index.html              # HTML5 entrypoint
│   └── src/
│       ├── api/
│       │   ├── client.js       # Configured Axios client instance
│       │   └── healthService.js# Health API invocation methods
│       ├── components/
│       │   ├── common/
│       │   │   ├── EmptyState.jsx    # Standard empty state component
│       │   │   └── StatusBadge.jsx   # Visual status badge (healthy/degraded/offline)
│       │   ├── dashboard/
│       │   │   └── SystemHealthCard.jsx # Live platform diagnostic card
│       │   └── layout/
│       │       ├── Header.jsx  # Navigation header with live status & refresh
│       │       ├── Sidebar.jsx # Navigation sidebar with phase locks
│       │       └── Layout.jsx  # Main responsive application layout
│       ├── context/
│       │   └── SystemStatusContext.jsx # Periodic health polling (30s) & state
│       ├── App.jsx             # React root with routing & providers
│       ├── App.test.jsx        # Vitest & RTL test suite
│       ├── index.css           # Tailwind base and custom theme styling
│       ├── main.jsx            # React DOM mounting
│       └── setupTests.js       # Jest-DOM matchers setup
├── database/                   # Database documentation and assets
└── docs/                       # Architectural specifications & guides
```

---

## Environment Configuration

Copy `.env.example` to create your local `.env` files:

```bash
# Root
cp .env.example .env

# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

### Key Configuration Variables

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `production`) |
| `BACKEND_HOST` | `0.0.0.0` | FastAPI server host binding |
| `BACKEND_PORT` | `8000` | FastAPI server port |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin for frontend |
| `POSTGRES_SERVER` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `pillsync_user` | Database username |
| `POSTGRES_PASSWORD` | `pillsync_secure_password` | Database password |
| `POSTGRES_DB` | `pillsync_db` | Database name |
| `DATABASE_URL` | *(constructed)* | Complete SQLAlchemy connection URI |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL used by frontend |

---

## Local Setup & Development

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm 9+
- PostgreSQL 14+ (or Docker)

### 2. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Frontend Web Shell will be accessible at: `http://localhost:5173`

---

## Database Migrations (Alembic)

To run migrations against the configured PostgreSQL database:

```bash
# From backend directory with virtualenv active:
alembic upgrade head

# To verify current revision:
alembic current

# To generate a new migration revision (Phase 1+):
alembic revision --autogenerate -m "create initial models"
```

---

## Running with Docker Compose

To start the full stack (PostgreSQL + FastAPI Backend + React Frontend):

```bash
# Build and launch all services
docker compose up --build

# Run in background (detached mode)
docker compose up -d

# Check service status
docker compose ps

# View service logs
docker compose logs -f backend

# Stop all containers
docker compose down
```

Services exposed:
- **Frontend**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **PostgreSQL**: `localhost:5432`

---

## Health Check API (`GET /api/v1/health`)

### Healthy State (API UP + PostgreSQL UP)
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "timestamp": "2026-08-16T16:53:11.123456Z",
  "services": {
    "api": {
      "status": "healthy",
      "details": "API process operational"
    },
    "database": {
      "status": "healthy",
      "details": "connected"
    }
  }
}
```

### Degraded State (API UP + PostgreSQL DOWN)
```json
{
  "status": "degraded",
  "environment": "development",
  "version": "0.1.0",
  "timestamp": "2026-08-16T16:53:11.123456Z",
  "services": {
    "api": {
      "status": "healthy",
      "details": "API process operational"
    },
    "database": {
      "status": "unhealthy",
      "details": "unreachable: OperationalError"
    }
  }
}
```

---

## Running Automated Tests

### Backend Tests (Pytest)
```bash
# From root or backend directory:
pytest backend/tests -v
```
Verified scenarios:
1. Root service discovery endpoint (`/`)
2. Health check when database is connected (`healthy`)
3. Health check when database is unreachable (`degraded`)
4. Schema validation and verification that secrets are never leaked
5. Settings and dynamic database URL generation

### Frontend Tests (Vitest & React Testing Library)
```bash
# From frontend directory:
npm test
```
Verified scenarios:
1. Application shell and header rendering
2. Health API success state (`healthy` badges and cards)
3. Database degraded state warning banner
4. Backend offline / connection error state with retry button

---

## Git Workflow & Security
- Secrets and `.env` files are ignored via `.gitignore`.
- No sensitive database passwords or API keys are committed.
- All subsequent phases must follow the modular architecture and Phase-by-Phase implementation plan.
