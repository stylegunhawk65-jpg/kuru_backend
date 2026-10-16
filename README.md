# Kuru Backend — AI-Powered Career Twin

Backend API service for **Kuru**, an AI-powered Career Twin application designed for students and job seekers in the Indian job and internship market.

The platform provides student career profiling, live verified job and internship discovery, code and GitHub skill extraction, evidence-based skill gap analysis, personalized roadmaps, dynamic AI resumes, and career path simulations.

---

## 🏛️ Phase 1 Architecture & Foundations

During Phase 1, the core backend foundation was audited and stabilized:

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+) with modern async `lifespan` lifecycle management.
- **Database Engine**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) async engine using [asyncpg](https://github.com/MagicStack/asyncpg) with connection pooling and automated health connectivity verification.
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/) configured for asynchronous database migrations.
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) and `pydantic-settings` with strict environment variable parsing and production CORS validation.
- **Security & Error Handling**:
  - Centralized unified error handling (`AppException`, `StarletteHTTPException`, `RequestValidationError`, 500 handler).
  - Sanitized 500 responses preventing internal stack trace and secret leakage.
  - Sensitive credential masking in logging (passwords, tokens, database URLs, authorization headers).
  - Explicit environment-controlled CORS configuration (wildcard `*` prohibited in production).
- **Health Checks**: Versioned `GET /api/v1/health` endpoint reporting overall status, version, environment, and live database connectivity status and latency.
- **Automated Testing**: [pytest](https://docs.pytest.org/) and `pytest-asyncio` with isolated in-memory test fixtures and zero reliance on production data.

---

## 📂 Project Structure

```text
kuru_backend/
├── .env.example              # Safe environment variable template (no secrets)
├── .gitignore                # Git ignore rules for Python, IDEs, databases, logs, and secrets
├── README.md                 # Project documentation and developer guide
├── requirements.txt          # Pinned production and test dependencies
├── pyproject.toml            # Project metadata and test/tool configurations
├── alembic.ini               # Alembic database migration configuration
├── alembic/
│   ├── env.py                # Async migration runner connected to app settings & metadata
│   ├── script.py.mako        # Migration revision script template
│   └── versions/             # Database migration version files (.gitkeep)
├── app/
│   ├── __init__.py           # Application package marker
│   ├── main.py               # FastAPI application factory, lifespan, CORS, and root routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Settings management and environment validation
│   │   ├── exceptions.py     # Unified application exceptions and error handlers
│   │   └── logging.py        # Centralized structured logging with credential masking
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy DeclarativeBase and TimestampMixin
│   │   └── session.py        # Async engine, sessionmaker, and connectivity verification
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py     # Aggregated v1 API router
│           └── endpoints/
│               ├── __init__.py
│               └── health.py # GET /api/v1/health endpoint
└── tests/
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures, test database engine, and async client
    ├── test_config.py        # Configuration and sensitive data filter tests
    ├── test_database.py      # Database session and connectivity check tests
    ├── test_exceptions.py    # Error response uniformity and secret protection tests
    └── test_health.py        # Health and root discovery endpoint tests
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher.
- **PostgreSQL**: Version 15 or higher (recommended for local development).
- **Git**: Version 2.30 or higher.

### 1. Clone & Navigate

```bash
git clone https://github.com/stylegunhawk65-jpg/kuru_backend.git
cd kuru_backend
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to create your local `.env` file:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Edit `.env` to configure your PostgreSQL credentials:

```dotenv
PROJECT_NAME="Kuru Backend"
ENVIRONMENT="development"
DEBUG=true
VERSION="0.1.0"
API_V1_STR="/api/v1"

HOST="0.0.0.0"
PORT=8000

# Comma-separated allowed origins (must be explicit in production)
CORS_ORIGINS="http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"

# AsyncPG PostgreSQL connection
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/kuru_db"

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30.0

LOG_LEVEL="INFO"
```

> **Security Note**: Never commit your real `.env` file, database passwords, or API keys to git. The `.gitignore` file is preconfigured to prevent this.

---

## 🗄️ Database Migrations

Alembic manages database schema evolution.

### Run Migrations to Latest Version
```bash
alembic upgrade head
```

### Create a New Migration Revision
```bash
alembic revision --autogenerate -m "add career profile table"
```

### Revert One Migration
```bash
alembic downgrade -1
```

---

## 🏃 Running the Application Locally

Start the backend with `uvicorn`:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or run via Python:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Endpoints Available

- **API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Root Index**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Versioned Health Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### Health Check Response Example

When the service and database are operational:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "project_name": "Kuru Backend",
  "database": {
    "status": "connected",
    "latency_ms": 1.45,
    "message": "Database is operational"
  }
}
```

If the database is temporarily unreachable, the endpoint returns HTTP 200 with degraded status (allowing service orchestrators to monitor process liveness):
```json
{
  "status": "degraded",
  "environment": "development",
  "version": "0.1.0",
  "project_name": "Kuru Backend",
  "database": {
    "status": "disconnected",
    "latency_ms": 10.2,
    "message": "Database is unreachable or not yet configured"
  }
}
```

---

## 🧪 Testing

The automated test suite runs using `pytest` and `pytest-asyncio`. Tests use isolated in-memory SQLite fixtures with no external database requirements.

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
python -m pytest -v
```

---

## 🔒 Security Principles

1. **No Sensitive Leaks**: Exception handlers scrub internal Python exceptions and stack traces in non-debug mode.
2. **Log Sanitization**: Connection strings, bearer tokens, passwords, and sensitive keys are automatically scrubbed by `SensitiveDataFilter`.
3. **Strict CORS**: Cross-Origin Resource Sharing is controlled via environment variables; wildcard origins (`*`) are rejected in production.
4. **Isolated Fixtures**: Test suites run on isolated in-memory fixtures; real production credentials or fake data are never mixed.
