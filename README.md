# Kuru Backend — AI-Powered Career Twin

Backend API service for **Kuru**, an AI-powered Career Twin application designed for students and job seekers in the Indian job and internship market.

The platform provides student career profiling, live verified job and internship discovery, code and GitHub skill extraction, evidence-based skill gap analysis, personalized roadmaps, dynamic AI resumes, and career path simulations.

---

## 🏛️ Architecture & Capabilities

### Phase 1: Core Backend Foundations
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+) with modern async `lifespan` lifecycle management.
- **Database Engine**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) async engine using [asyncpg](https://github.com/MagicStack/asyncpg) with connection pooling and automated health connectivity verification. PostgreSQL serves as the primary source of truth.
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/) configured for asynchronous database migrations.
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) and `pydantic-settings` with strict environment variable parsing and production CORS protection.
- **Security & Error Handling**:
  - Centralized unified error handling (`AppException`, `StarletteHTTPException`, `RequestValidationError`, 500 handler).
  - Sanitized 500 responses preventing internal stack trace and secret leakage.
  - Sensitive credential masking in logging (passwords, tokens, database URLs, authorization headers).
  - Explicit environment-controlled CORS configuration (wildcard `*` prohibited in production).
- **Health Checks**: Versioned `GET /api/v1/health` endpoint reporting overall status, version, environment, and live database connectivity status and latency.
- **Automated Testing**: [pytest](https://docs.pytest.org/) and `pytest-asyncio` with isolated in-memory test fixtures and zero reliance on production data.

### Phase 2: Firebase Auth & Career Profiles
- **Authentication**: [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup) integration for cryptographic ID token verification (`Bearer <token>`). User identity is strictly derived from verified token claims (`uid`), never from client input.
- **Career Profiles Domain**: PostgreSQL model, migration, and authenticated RESTful CRUD endpoints under `/api/v1/profiles` enforcing strict per-user data isolation.

### Phase 3: GitHub Integration, Static Code Analysis & Skill Graph
- **Secure GitHub OAuth / Token Handling**:
  - Access tokens are validated with GitHub, encrypted at rest using AES/Fernet encryption, and never exposed in responses or logs.
  - Disconnect endpoints securely wipe stored credentials.
- **Least-Privilege Repository Selection**:
  - Authenticated students can list accessible repositories with pagination and select specific projects for analysis.
- **Static Code Analysis (Zero Untrusted Code Execution)**:
  - Inspects language breakdowns and dependency manifests without executing code:
    - Python: `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`
    - JavaScript / TypeScript: `package.json`
    - Java / Kotlin: `pom.xml`, `build.gradle`
    - Go: `go.mod`
    - Rust: `Cargo.toml`
    - Containers & CI/CD: `Dockerfile`, `docker-compose.yml`, GitHub Actions workflows
  - Static Python AST parsing to extract imported modules safely.
  - Generates evidence-backed skills with confidence scores (0.0 to 1.0) and concrete file references.
- **Skill Knowledge Graph**:
  - Generates relationship edges connecting languages, frameworks, ORMs, tools, and databases (e.g. `FastAPI -> requires_language -> Python`, `SQLAlchemy -> integrates_with -> PostgreSQL`).
  - Graph nodes and edges stored in PostgreSQL and queryable via authenticated APIs.
- **Robust Error & Rate-Limit Handling**:
  - Detects GitHub API rate limits (`403` / `429` with `X-RateLimit-Reset`) and returns informative client errors.
  - Skips files exceeding 500 KB to protect system memory.
  - Transient 5xx retries with backoff.

### Phase 4: Job & Internship Discovery with Transparent Baseline Matching
- **Legitimate & Accessible Sources (Prioritizing India)**:
  - **Curated Indian Tech Adapter (`curated_india`)**: Bundles verified technology opportunities and internships (Zerodha, Razorpay, Swiggy, CRED, Postman, Hasura, Juspay, Flipkart, TCS, Infosys) across Indian tech hubs (Bengaluru, Hyderabad, Pune, Mumbai, Remote) with verifiable careers links.
  - **Arbeitnow Adapter (`arbeitnow`)**: Free, open public tech job board API with rate limiting and network failure tolerance.
  - **Adzuna India Adapter (`adzuna`)**: Connects to Adzuna India endpoint when credentials (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) are present; extracts tech skills and salary ranges.
  - **Terms-of-Service Compliance (Unstop & Naukri)**: Automated scraping and bypassing bot protections are prohibited. Formal enterprise connectors (`UnstopPartnerAdapter`, `NaukriPartnerAdapter`) activate only when official partner keys are supplied.
- **Deduplication & Freshness Tracking**:
  - Deterministic SHA-256 deduplication hashing across normalized `company|title|location`. Duplicate listings update `last_seen_at` and `is_active` without redundant row duplication.
- **Transparent Rule-Based Matching (Zero LLMs / Black Boxes)**:
  - Explainable, deterministic alignment score (0.0 - 100.0) evaluated against `StudentProfile` and Phase 3 `StudentSkill` table:
    - **Evidence-Backed Skills (50% max)**: Weighted sum of matched skill confidence scores from code analysis; lists matched and missing skills.
    - **Target Role Alignment (25% max)**: Title and role overlap analysis.
    - **Location Alignment (15% max)**: Matched against preferred locations and remote preference.
    - **Career Interests Alignment (10% max)**: Description matching against student interests.
  - Outputs transparent, human-readable arithmetic `match_reasons` for every score calculation.
- **Authenticated REST Endpoints (`/api/v1/jobs`)**:
  - Search and filter jobs with keyword search, location, job type, skill, and minimum match threshold.
  - Individual job detail with complete match reasons.
  - User-isolated bookmarking (`POST /{job_id}/save`, `DELETE /{job_id}/save`, `GET /saved`, `PATCH /saved/{job_id}`).
  - Provider health and sync monitoring (`GET /sources/status`, `POST /sources/sync`).

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
│       ├── 001_create_student_profiles_table.py
│       ├── 002_create_github_and_skill_tables.py
│       └── 003_create_job_and_source_tables.py
├── app/
│   ├── __init__.py           # Application package marker
│   ├── main.py               # FastAPI application factory, lifespan, CORS, and root routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py           # Firebase Admin SDK authentication dependency & token verification
│   │   ├── config.py         # Settings management and environment validation
│   │   ├── exceptions.py     # Unified application exceptions and error handlers
│   │   ├── logging.py        # Centralized structured logging with credential masking
│   │   └── security.py       # Symmetric Fernet encryption for external access tokens
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy DeclarativeBase and TimestampMixin
│   │   └── session.py        # Async engine, sessionmaker, and connectivity verification
│   ├── models/
│   │   ├── __init__.py       # Database models registry
│   │   ├── github.py         # GithubConnection, GithubRepository, RepositoryAnalysis models
│   │   ├── job.py            # JobPosting, JobSource, SavedJob models
│   │   ├── profile.py        # StudentProfile model
│   │   └── skill.py          # StudentSkill and SkillGraphEdge models
│   ├── schemas/
│   │   ├── __init__.py       # Pydantic validation schemas registry
│   │   ├── github.py         # GitHub connection, repo selection, and analysis schemas
│   │   ├── job.py            # Job listings, match breakdown, and saved jobs schemas
│   │   ├── profile.py        # StudentProfile request/response schemas
│   │   └── skill.py          # Extracted skills and skill graph schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analyzer.py       # Static manifest & AST parser, skill taxonomy, and graph builder
│   │   ├── github_client.py  # Asynchronous GitHub API client with rate-limiting & retries
│   │   ├── matcher.py        # Transparent rule-based skill and profile job matching engine
│   │   └── job_sources/      # Modular job source adapters & aggregator
│   │       ├── __init__.py
│   │       ├── base.py       # NormalizedJob dataclass & BaseJobAdapter ABC
│   │       ├── curated_india.py # Curated Indian tech listings with verifiable career links
│   │       ├── arbeitnow.py  # Arbeitnow open public API adapter
│   │       ├── adzuna.py     # Adzuna India REST API adapter
│   │       ├── partner.py    # Compliant Unstop & Naukri enterprise partner adapters
│   │       └── aggregator.py # JobSourceManager orchestrator, deduplication, and sync
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py     # Aggregated v1 API router
│           └── endpoints/
│               ├── __init__.py
│               ├── github.py   # GitHub connect, repos, analyze, and results endpoints
│               ├── health.py   # GET /api/v1/health endpoint
│               ├── jobs.py     # Authenticated job search, ranking, saving, and sync endpoints
│               ├── profiles.py # Authenticated student career profile CRUD endpoints
│               └── skills.py   # Extracted skills and knowledge graph endpoints
└── tests/
    ├── __init__.py
    ├── conftest.py           # Pytest fixtures, test database engine, and async client
    ├── test_analyzer.py      # Static parser, AST extractor, and skill graph tests
    ├── test_auth.py          # Firebase authentication and token verification tests
    ├── test_config.py        # Configuration and sensitive data filter tests
    ├── test_database.py      # Database session and connectivity check tests
    ├── test_exceptions.py    # Error response uniformity and secret protection tests
    ├── test_github_api.py    # GitHub connect, analyze, skills, graph, and isolation tests
    ├── test_github_client.py # GitHub client rate-limiting, timeout, and retry tests
    ├── test_health.py        # Health and root discovery endpoint tests
    ├── test_job_sources.py   # Adapters, normalization, deduplication, and sync tests
    ├── test_jobs.py          # Job search, transparent ranking, saved jobs, and isolation tests
    └── test_profiles.py      # Student profile CRUD and cross-user isolation tests
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher.
- **PostgreSQL**: Version 15 or higher (recommended for local development).
- **Firebase Project**: A Firebase project with Firebase Authentication enabled.
- **GitHub Account / OAuth App**: Personal Access Token (PAT) with `repo` scope or registered GitHub OAuth App.
- **Job Partner Credentials (Optional)**: Adzuna App ID/Key, Unstop or Naukri partner API keys.

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
# FIREBASE_CREDENTIALS_PATH="/path/to/serviceAccountKey.json"
# FIREBASE_PROJECT_ID="your-firebase-project-id"

# Encryption Key for GitHub Access Tokens at Rest
ENCRYPTION_KEY="kuru_dev_secret_key_32_bytes_safe_fallback_123="

# Optional Partner Job Source Credentials
# ADZUNA_APP_ID="your_adzuna_app_id"
# ADZUNA_APP_KEY="your_adzuna_app_key"
# UNSTOP_API_KEY="your_unstop_api_key"
# NAUKRI_API_KEY="your_naukri_api_key"
```

> **Security Note**: Never commit your real `.env` file, database passwords, or service credentials to git. The `.gitignore` file is preconfigured to prevent this.

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

> **Note on Persistent Storage**: PostgreSQL is the primary production database. During local testing and environment bootstrapping without a running local PostgreSQL instance, the automated test suite uses asynchronous SQLite in-memory databases with complete schema parity.

---

## 🏃 Running the Application Locally

Start the backend with `uvicorn`:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Interactive Documentation

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 📡 API Endpoints Overview

All protected endpoints require `Authorization: Bearer <FIREBASE_ID_TOKEN>`.

### Job Discovery & Matching Endpoints (`/api/v1/jobs`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/jobs` | Search, filter, and rank jobs by transparent skill/profile match score |
| `GET` | `/api/v1/jobs/{job_id}` | Detailed posting view with complete arithmetic match breakdown |
| `POST` | `/api/v1/jobs/{job_id}/save` | Bookmark a job posting with personal notes and status |
| `DELETE` | `/api/v1/jobs/{job_id}/save` | Remove bookmark on a job posting |
| `GET` | `/api/v1/jobs/saved` | List user's bookmarked jobs (isolated to authenticated user) |
| `PATCH` | `/api/v1/jobs/saved/{job_id}` | Update application status (`saved`, `applied`, `archived`) or notes |
| `GET` | `/api/v1/jobs/sources/status` | Retrieve health, sync status, and count for all adapters |
| `POST` | `/api/v1/jobs/sources/sync` | Trigger synchronization for all or a specific provider |

### GitHub & Codebase Analysis Endpoints (`/api/v1/github`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/github/connect` | Connect GitHub token (encrypted at rest, never returned in response) |
| `GET` | `/api/v1/github/status` | Get GitHub connection status (username, avatar, scopes) |
| `DELETE` | `/api/v1/github/disconnect` | Disconnect GitHub and wipe encrypted credentials |
| `GET` | `/api/v1/github/repos` | List user repositories with pagination |
| `POST` | `/api/v1/github/repos/select` | Select specific repositories for analysis |
| `POST` | `/api/v1/github/analyze` | Trigger static analysis on selected repositories |
| `GET` | `/api/v1/github/analysis/{id}` | Retrieve results of a specific repository analysis |

### Skills & Knowledge Graph Endpoints (`/api/v1/skills`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/skills` | Retrieve all evidence-backed skills extracted for current user |
| `GET` | `/api/v1/skills/graph` | Retrieve student skill knowledge graph (nodes, edges, metrics) |

### Career Profile Endpoints (`/api/v1/profiles`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/profiles` | Create student career profile bound to verified Firebase token |
| `GET` | `/api/v1/profiles/me` | Retrieve profile of authenticated student |
| `GET` | `/api/v1/profiles/{id}` | Retrieve profile by ID (isolated to owner) |
| `PUT` | `/api/v1/profiles/me` | Update career profile attributes |
| `DELETE` | `/api/v1/profiles/me` | Delete career profile |

---

## 🧪 Testing

The automated test suite runs using `pytest` and `pytest-asyncio`. Tests use isolated in-memory SQLite fixtures with zero external network or database dependencies.

Run all tests:
```bash
pytest -v
```

---

## 🔒 Security Principles

1. **Zero Untrusted Code Execution**: All repository analysis uses static AST parsing and manifest inspection. Untrusted code is never run in `eval`, `exec`, or shell processes.
2. **Encrypted Access Tokens**: External GitHub tokens are encrypted at rest with Fernet symmetric encryption and never returned in API responses or written to logs.
3. **Never Trust Client-Supplied User IDs**: User identities are extracted solely from verified Firebase ID token claims (`uid`).
4. **Per-User Data Isolation**: Database queries strictly filter by `firebase_uid == current_user.uid`.
5. **No Sensitive Leaks**: Exception handlers scrub internal Python exceptions and stack traces in non-debug mode.
6. **Log Sanitization**: Bearer tokens, passwords, database strings, and connection credentials are scrubbed by `SensitiveDataFilter`.
7. **Terms of Service Compliance**: In compliance with platform terms, job discovery relies exclusively on permitted open APIs and verified partner connections; unauthenticated scraping and bot protection bypasses are strictly prohibited.
