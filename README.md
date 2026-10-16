# Kuru Backend — AI-Powered Career Twin

Backend API service for **Kuru**, an AI-powered Career Twin application designed for students and job seekers in the Indian job and internship market.

The platform provides student career profiling, live verified job and internship discovery, code and GitHub skill extraction, evidence-based skill gap analysis, personalized roadmaps, dynamic AI resumes, and career path simulations.

---

## 🏛️ Architecture & Capabilities

### Phase 1 & 2 Foundations
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+) with modern async `lifespan` lifecycle management.
- **Authentication**: [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup) integration for cryptographic ID token verification (`Bearer <token>`). User identity is strictly derived from verified token claims (`uid`), never from client input.
- **Database Engine**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) async engine using [asyncpg](https://github.com/MagicStack/asyncpg) with connection pooling and automated health connectivity verification. PostgreSQL serves as the primary source of truth.
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/) configured for asynchronous database migrations.
- **Career Profiles Domain**: PostgreSQL model, migration, and authenticated RESTful CRUD endpoints under `/api/v1/profiles` enforcing strict per-user data isolation.
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) and `pydantic-settings` with strict environment variable parsing, email validation, and production CORS protection.
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
│   └── versions/             # Database migration versions
│       └── 001_create_student_profiles_table.py
├── app/
│   ├── __init__.py           # Application package marker
│   ├── main.py               # FastAPI application factory, lifespan, CORS, and root routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py           # Firebase Admin SDK authentication dependency & token verification
│   │   ├── config.py         # Settings management and environment validation
│   │   ├── exceptions.py     # Unified application exceptions and error handlers
│   │   └── logging.py        # Centralized structured logging with credential masking
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy DeclarativeBase and TimestampMixin
│   │   └── session.py        # Async engine, sessionmaker, and connectivity verification
│   ├── models/
│   │   ├── __init__.py       # Database models registry
│   │   └── profile.py        # StudentProfile SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py       # Pydantic validation schemas registry
│   │   └── profile.py        # Request/response schemas for StudentProfile
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py     # Aggregated v1 API router
│           └── endpoints/
│               ├── __init__.py
│               ├── health.py   # GET /api/v1/health endpoint
│               └── profiles.py # Authenticated student career profile CRUD endpoints
└── tests/
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures, test database engine, and async client
    ├── test_auth.py          # Firebase authentication and token verification tests
    ├── test_config.py        # Configuration and sensitive data filter tests
    ├── test_database.py      # Database session and connectivity check tests
    ├── test_exceptions.py    # Error response uniformity and secret protection tests
    ├── test_health.py        # Health and root discovery endpoint tests
    └── test_profiles.py      # Student profile CRUD and cross-user isolation tests
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher.
- **PostgreSQL**: Version 15 or higher (recommended for local development).
- **Firebase Project**: A Firebase project with Firebase Authentication enabled.

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

Configure your `.env` settings:

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

# Firebase Authentication Configuration
# Provide path to your serviceAccountKey.json or set project ID
# FIREBASE_CREDENTIALS_PATH="/path/to/serviceAccountKey.json"
# FIREBASE_PROJECT_ID="your-firebase-project-id"
```

> **Security Note**: Never commit your real `.env` file, database passwords, or serviceAccountKey credentials to git. The `.gitignore` file is preconfigured to prevent this.

---

## 🗄️ Database Migrations

Alembic manages database schema evolution.

### Run Migrations to Latest Version
```bash
alembic upgrade head
```

### Check Migration History
```bash
alembic history
```

### Create a New Migration Revision
```bash
alembic revision --autogenerate -m "describe changes"
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

---

## 🔐 Authentication & Career Profile Endpoints

All endpoints under `/api/v1/profiles` require a valid Firebase ID token in the `Authorization` header:
`Authorization: Bearer <FIREBASE_ID_TOKEN>`

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/profiles` | Create career profile for authenticated user (bound to token `uid`) | Yes |
| `GET` | `/api/v1/profiles/me` | Retrieve profile of the authenticated student | Yes |
| `GET` | `/api/v1/profiles/{id}` | Retrieve profile by ID (isolated to owner) | Yes |
| `PUT` | `/api/v1/profiles/me` | Update career profile attributes for authenticated student | Yes |
| `DELETE` | `/api/v1/profiles/me` | Delete career profile of authenticated student | Yes |

### Sample Profile Creation Request (`POST /api/v1/profiles`)

```json
{
  "full_name": "Aarav Sharma",
  "email": "aarav.sharma@example.edu",
  "education": [
    {
      "institution": "Indian Institute of Technology, Bombay",
      "degree": "B.Tech",
      "field_of_study": "Computer Science and Engineering",
      "start_year": 2022,
      "end_year": 2026,
      "grade_or_cgpa": "8.8/10"
    }
  ],
  "interests": ["Machine Learning", "Distributed Systems", "Cloud Computing"],
  "target_roles": ["Software Engineer", "Backend Developer", "ML Engineer"],
  "preferred_locations": ["Bengaluru", "Hyderabad", "Pune", "Remote"],
  "bio": "Third-year CSE undergraduate passionate about large-scale backend systems."
}
```

---

## 🧪 Testing

The automated test suite runs using `pytest` and `pytest-asyncio`. Tests use isolated in-memory SQLite fixtures with no external database or external Firebase network dependencies.

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

1. **Never Trust Client-Supplied User IDs**: User identities are extracted solely from verified Firebase ID token claims (`uid`). Clients cannot impersonate other users by injecting foreign IDs.
2. **Per-User Data Isolation**: Database queries strictly filter by `StudentProfile.firebase_uid == current_user.uid`. Users cannot read, modify, or delete another student's career profile.
3. **No Sensitive Leaks**: Exception handlers scrub internal Python exceptions and stack traces in non-debug mode.
4. **Log Sanitization**: Connection strings, bearer tokens, passwords, and sensitive keys are automatically scrubbed by `SensitiveDataFilter`.
5. **Strict CORS**: Cross-Origin Resource Sharing is controlled via environment variables; wildcard origins (`*`) are rejected in production.
6. **Isolated Fixtures**: Test suites run on isolated in-memory fixtures; real production credentials or fake data are never mixed.
