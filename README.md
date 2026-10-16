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

### Phase 5: Career Intelligence, Explainable Skill-Gap Analysis & What-If Simulations
- **Explainable Skill-Gap Analysis & Readiness Tiers**:
  - Evaluates student portfolio against live market postings to compute an overall fit score and milestone readiness tier:
    - **Ready** ($\ge 80\%$)
    - **High** ($65 - 79\%$)
    - **Moderate** ($45 - 64\%$)
    - **Developing** ($25 - 44\%$)
    - **Early** ($< 25\%$)
- **Prioritized Skill Gaps (Multi-Factor Scoring)**:
  - Missing skills are ranked using a deterministic composite formula:
    $$\text{Priority Score} = \text{Market Demand}\,(50\%) + \text{Graph Proximity}\,(30\%) + \text{Career Interest Alignment}\,(20\%)$$
  - **Graph Proximity Synergy**: Leverages Phase 3 `SkillGraphEdge` and taxonomy to detect 1-hop learning synergies (e.g. knowing Python gives high synergy for FastAPI or Django).
  - Generates verifiable, human-readable justification for every ranked gap.
- **Actionable Skill Recommendations**:
  - Pinpoints the top 5 high-return skills to acquire, measuring the exact number of currently mismatched jobs that will be unlocked.
  - Provides learning effort estimates based on graph proximity (`Low: 1-2 weeks`, `Medium: 3-4 weeks`, `High: 5-8 weeks`).
- **Deterministic Career-Path Comparison**:
  - Compares 2 to 5 candidate career tracks (e.g. Backend Engineer vs. Data Scientist vs. DevOps Engineer).
  - Measures market demand, current portfolio readiness, critical skill gaps, and estimated learning runway.
  - Fully transparent assumptions: clearly labels study hours ($10-15\text{ hrs/week}$) and foundation dependencies.
- **What-If Simulation Engine**:
  - Simulates the impact of hypothetical skill acquisitions (e.g. "What if I learn Docker and Redis?").
  - Calculates score delta ($+\Delta\%$), newly unlocked job opportunities, resolved gaps, and remaining gaps with full assumption disclosures.
- **PostgreSQL Persistence & Snapshot Refresh**:
  - Assessments are persisted in the `career_assessments` table (`004_create_career_intelligence_tables.py`).
  - Supports automated caching and on-demand refresh (`POST /api/v1/intelligence/skill-gaps/refresh`) when repositories or profiles evolve.

### Phase 6: Local AI Model Evaluation, Structured Inference & Benchmarking
- **Candidate Evaluation: Qwen2.5-3B-Instruct**:
  - **Availability & License**: Permissive [Apache 2.0 License](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), commercially viable.
  - **Download Size**: FP16 weights ~6.2 GB; 4-bit NF4 quantized weights ~2.0 GB.
  - **Hardware Compatibility (NVIDIA RTX 4050 Laptop GPU, 6GB VRAM & 16GB RAM)**:
    - *FP16 mode*: Requires ~8 GB total VRAM (exceeds 6GB capacity, causing OOM or slow PCIe paging).
    - *4-bit NF4 Quantization (`bitsandbytes`)*: Consumes ~3.2 GB total VRAM (weights ~2.0 GB, KV cache ~0.6 GB, CUDA context ~0.6 GB). Leaves **~2.8 GB VRAM headroom** for OS display servers and system processes.
    - *Compatibility Verdict*: **Highly Suitable and Recommended via 4-bit NF4 quantization**.
  - **Alternatives Considered**:
    - *Qwen2.5-1.5B-Instruct*: Very fast (~1.8 GB VRAM), but noticeable reduction in nuanced resume tailoring and complex rubric formulation.
    - *SmolLM2-1.7B-Instruct*: Lightweight Apache 2.0 model, but trails Qwen2.5 on coding and structured JSON generation.
    - *Llama-3.2-3B-Instruct*: Gated license with commercial restrictions compared to Apache 2.0.
- **Operational Decoupling & Safety**:
  - Weights are strictly kept out of Git via `.gitignore`.
  - **Zero downloads during API startup**: Startup is instantaneous. Models are lazy-loaded on explicit request or managed via dedicated administrative scripts.
- **Provider Interface & Structured Generation**:
  - `BaseLLMProvider` interface with robust JSON extraction and Pydantic schema validation.
  - `MockLLMProvider`: Instant deterministic provider for rapid development and testing (zero downloads or GPU required).
  - `LocalTransformersProvider`: On-device CUDA inference running 4-bit quantized Qwen2.5 with asynchronous thread offload and timeout enforcement.
- **Career Twin Structured Tasks**:
  - **Resume Bullet Point Optimizer (`/api/v1/ai/resume/tailor`)**: Rewrites draft bullets with action verbs, quantifiable metrics, and verified candidate skills.
  - **Learning Roadmap Narrative (`/api/v1/ai/roadmap/generate`)**: Week-by-week study plan with daily milestones and hands-on deliverables addressing prioritized skill gaps.
  - **Technical Interview Preparation (`/api/v1/ai/interview/prep`)**: Targeted questions, answer rubrics, and coding challenges.
- **Benchmarking & Evaluation Dataset**:
  - Curated evaluation prompts: `eval/career_twin_eval_dataset.json`.
  - Standalone benchmark runner: `scripts/benchmark_llm.py` measuring latency, tokens/sec, peak VRAM, and schema compliance.
- **QLoRA Fine-Tuning Feasibility & Privacy Safeguards**:
  - Training script template: `scripts/train_qlora.py`.
  - Memory analysis on RTX 4050 6GB: 4-bit base (~2.0 GB) + LoRA adapters (~95 MB) + Paged 8-bit AdamW (~100 MB) + gradient checkpointing activations (~1.4 GB) = **~4.2 GB VRAM peak**. Verified feasible on 6GB hardware.
  - **Strict Privacy Safeguard**: Prohibits training on raw user/student portfolio tables without explicit opt-in consent.

---

## 📂 Project Structure

```text
kuru_backend/
├── .env.example              # Safe environment variable template (no secrets)
├── .gitignore                # Git ignore rules for Python, IDEs, databases, logs, secrets, and ML weights
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
│       ├── 003_create_job_and_source_tables.py
│       └── 004_create_career_intelligence_tables.py
├── eval/
│   └── career_twin_eval_dataset.json # Standardized benchmark prompts & evaluation criteria
├── scripts/
│   ├── benchmark_llm.py      # Automated benchmark tool for latency, VRAM, and schema compliance
│   └── train_qlora.py        # QLoRA fine-tuning utility with hardware feasibility & privacy checks
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
│   │   ├── intelligence.py   # CareerAssessment model for persisted reports
│   │   ├── job.py            # JobPosting, JobSource, SavedJob models
│   │   ├── profile.py        # StudentProfile model
│   │   └── skill.py          # StudentSkill and SkillGraphEdge models
│   ├── schemas/
│   │   ├── __init__.py       # Pydantic validation schemas registry
│   │   ├── github.py         # GitHub connection, repo selection, and analysis schemas
│   │   ├── intelligence.py   # Skill gap, recommendation, compare, and what-if schemas
│   │   ├── job.py            # Job listings, match breakdown, and saved jobs schemas
│   │   ├── llm.py            # AI generation, resume tailor, roadmap, and benchmark schemas
│   │   ├── profile.py        # StudentProfile request/response schemas
│   │   └── skill.py          # Extracted skills and skill graph schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analyzer.py       # Static manifest & AST parser, skill taxonomy, and graph builder
│   │   ├── career_intelligence.py # Explainable skill gap analysis, recommendations, and simulations
│   │   ├── github_client.py  # Asynchronous GitHub API client with rate-limiting & retries
│   │   ├── matcher.py        # Transparent rule-based skill and profile job matching engine
│   │   ├── job_sources/      # Modular job source adapters & aggregator
│   │   └── llm/              # LLM inference provider interface, factory, and task orchestrators
│   │       ├── __init__.py
│   │       ├── base.py       # BaseLLMProvider interface & robust JSON extractor
│   │       ├── career_tasks.py # Career Twin task execution (resume, roadmap, interview)
│   │       ├── factory.py    # LLMProviderFactory for local/mock switching
│   │       ├── local_transformers.py # 4-bit quantized Qwen2.5 local inference on RTX 4050
│   │       └── mock_provider.py # High-fidelity mock provider for rapid testing
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py     # Aggregated v1 API router
│           └── endpoints/
│               ├── __init__.py
│               ├── github.py       # GitHub connect, repos, analyze, and results endpoints
│               ├── health.py       # GET /api/v1/health endpoint
│               ├── intelligence.py # Skill gaps, recommendations, comparison, and what-if
│               ├── jobs.py         # Authenticated job search, ranking, saving, and sync endpoints
│               ├── llm.py          # AI resume tailoring, roadmap, interview, and benchmark endpoints
│               ├── profiles.py     # Authenticated student career profile CRUD endpoints
│               └── skills.py       # Extracted skills and knowledge graph endpoints
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
    ├── test_intelligence.py   # Skill gap analysis, recommendations, compare, and what-if tests
    ├── test_job_sources.py   # Adapters, normalization, deduplication, and sync tests
    ├── test_jobs.py          # Job search, transparent ranking, saved jobs, and isolation tests
    ├── test_llm.py           # LLM provider interface, structured output, and AI endpoint tests
    └── test_profiles.py      # Student profile CRUD and cross-user isolation tests
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher.
- **PostgreSQL**: Version 15 or higher (recommended for local development).
- **GPU (Optional for Local Inference)**: NVIDIA RTX 4050 Laptop GPU (6GB VRAM) or higher with CUDA 12+. (For machines without GPU, `LLM_PROVIDER="mock"` runs fully offline in sub-milliseconds).
- **Firebase Project**: A Firebase project with Firebase Authentication enabled.
- **GitHub Account / OAuth App**: Personal Access Token (PAT) with `repo` scope or registered GitHub OAuth App.

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

# Local LLM & AI Inference Configuration (Phase 6)
# Options: "mock" (fast dev/testing, zero GPU/download required), "local" (RTX 4050 4-bit)
LLM_PROVIDER="mock"
LOCAL_MODEL_ID="Qwen/Qwen2.5-3B-Instruct"
LOCAL_MODEL_DEVICE="cuda"
LOCAL_MODEL_QUANTIZATION="4bit"
LLM_TIMEOUT_SECONDS=60.0
LLM_MAX_NEW_TOKENS=1024
LLM_TEMPERATURE=0.7
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

### AI & Career Twin Task Endpoints (`/api/v1/ai`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/ai/health` | Inspect local LLM provider status, device, quantization, and GPU VRAM usage |
| `POST` | `/api/v1/ai/resume/tailor` | Optimize draft resume bullet points with quantifiable metrics and verified skills |
| `POST` | `/api/v1/ai/roadmap/generate` | Generate weekly progressive learning roadmap addressing prioritized skill gaps |
| `POST` | `/api/v1/ai/interview/prep` | Generate technical interview questions, answer rubrics, and coding challenges |
| `POST` | `/api/v1/ai/benchmark` | Execute standardized benchmark task reporting latency and VRAM footprint |

### Career Intelligence Endpoints (`/api/v1/intelligence`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/intelligence/skill-gaps` | Retrieve cached or initial skill-gap assessment report |
| `POST` | `/api/v1/intelligence/skill-gaps/refresh` | Force re-evaluation of skill gaps, market demand, and persisted snapshot |
| `GET` | `/api/v1/intelligence/recommendations` | Get prioritized skill recommendations with market demand and effort estimates |
| `POST` | `/api/v1/intelligence/career-paths/compare` | Compare candidate career paths (2 to 5 roles) with runway and readiness metrics |
| `POST` | `/api/v1/intelligence/what-if` | Run what-if simulation to measure impact of acquiring hypothetical skills |

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

## 🧪 Testing & Benchmarks

The automated test suite runs using `pytest` and `pytest-asyncio`. Tests use isolated in-memory SQLite fixtures and fast mock LLM providers with zero external network, database, or model weight download dependencies.

### Run All Tests:
```bash
pytest -v
```

### Run Benchmark Tool:
```bash
python scripts/benchmark_llm.py
```

### Check QLoRA Hardware Feasibility:
```bash
python scripts/train_qlora.py --check-only
```

---

## 🔒 Security & Operational Principles

1. **Zero Untrusted Code Execution**: All repository analysis uses static AST parsing and manifest inspection. Untrusted code is never run in `eval`, `exec`, or shell processes.
2. **Encrypted Access Tokens**: External GitHub tokens are encrypted at rest with Fernet symmetric encryption and never returned in API responses or written to logs.
3. **Never Trust Client-Supplied User IDs**: User identities are extracted solely from verified Firebase ID token claims (`uid`).
4. **Per-User Data Isolation**: Database queries strictly filter by `firebase_uid == current_user.uid`.
5. **No Sensitive Leaks**: Exception handlers scrub internal Python exceptions and stack traces in non-debug mode.
6. **Log Sanitization**: Bearer tokens, passwords, database strings, and connection credentials are scrubbed by `SensitiveDataFilter`.
7. **Terms of Service Compliance**: In compliance with platform terms, job discovery relies exclusively on permitted open APIs and verified partner connections; unauthenticated scraping and bot protection bypasses are strictly prohibited.
8. **Never Invent Skills, Jobs, or Evidence**: Skill recommendations, match calculations, and career gap reports strictly anchor in actual job postings, AST imports, and validated manifests.
9. **Transparent & Deterministic Intelligence**: Calculations are explainable and rule-based. Learning runway estimates and simulation results clearly disclose assumptions.
10. **Privacy-Preserving AI & Consent-Gated Training**: Model weights are excluded from Git repositories and never downloaded during API startup. Training on private student/user data without explicit consent is strictly prohibited.
