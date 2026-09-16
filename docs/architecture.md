# PillSync System Architecture (Phase 0)

## System Overview
PillSync is an Intelligent Medicine Reminder and Medication Tracking Platform designed to assist patients, caregivers, and medical practitioners with smart medication management.

Phase 0 establishes the bedrock foundation:
- Modular FastAPI backend
- React + Vite + Tailwind CSS frontend
- PostgreSQL database integration via SQLAlchemy ORM & Alembic migrations
- Multi-container Docker Compose configuration
- Real-time diagnostic Health Check API (`GET /api/v1/health`)

## High-Level Architecture Diagram
```
+--------------------------------------------------------+
|                     User Browser                       |
|               (React + Vite + Tailwind)                |
+--------------------------------------------------------+
                           |
                           | HTTP / JSON (/api/v1/health)
                           v
+--------------------------------------------------------+
|                   FastAPI Backend                      |
|  - CORS & Error Handling Middleware                    |
|  - API Router (v1/endpoints/health)                    |
|  - Pydantic Schemas & Settings Validation              |
|  - Logging & Lifespan Management                       |
+--------------------------------------------------------+
                           |
                           | SQLAlchemy Connection Pool
                           v
+--------------------------------------------------------+
|                 PostgreSQL 16 Engine                   |
|  - Migrations managed via Alembic                      |
|  - Persistent storage in named volume (postgres_data)  |
+--------------------------------------------------------+
```

## Directory Structure
```
pillsync/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   └── endpoints/
│   │   │   │       └── health.py
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   └── base.py
│   │   ├── repositories/
│   │   ├── schemas/
│   │   │   └── health.py
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_health.py
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── dashboard/
│   │   │   └── layout/
│   │   ├── context/
│   │   ├── App.jsx
│   │   ├── App.test.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── .env.example
├── database/
├── docs/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```
