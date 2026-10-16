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

### Phase 7: Multi-Agent System (LangChain, LangGraph & Human-in-the-Loop)
- **Multi-Agent Architecture & Shared Local LLM**:
  - Leverages **LangGraph** for typed cyclic state graph execution (`CareerTwinAgentState`), checkpointing (`MemorySaver`), and human approval gates.
  - Leverages **LangChain** for `@tool` bindings, structured schema outputs, and resource queries.
  - Strictly reuses the existing `Qwen2.5-3B-Instruct` local provider (`LocalTransformersProvider` on GPU, `MockLLMProvider` in test/CI mode). **Never creates separate LLMs per agent**.
  - Strict separation of concerns: Deterministic business logic (job matching, skill gap formulas, profile loading, graph querying) stays outside the LLM in pure Python/SQLAlchemy services.
- **The 9 Logical Agents**:
  1. **Career Profile Agent (`profile_agent.py`)**: Consolidates student profile, target roles, preferred locations, and career interests.
  2. **GitHub Analysis Agent (`github_agent.py`)**: Retrieves evidence-backed skills, confidence scores, and 1-hop knowledge graph relationships from Phase 3 static analysis.
  3. **Job Matching Agent (`job_matching_agent.py`)**: Transparently ranks real job postings using Phase 4 deterministic scoring (`calculate_job_match`).
  4. **Skill Gap Agent (`skill_gap_agent.py`)**: Calculates prioritized skill gaps against market demand and 1-hop graph proximity via `CareerIntelligenceService`.
  5. **Career Planning Agent (`career_planning_agent.py`)**: Synthesizes progressive multi-week roadmaps and quantifies what-if readiness estimates.
  6. **Resource Research Agent (`resource_research_agent.py`)**: Curates authentic learning resources. Strictly enforces zero invented URLs by validating against official documentation registries.
  7. **Project Recommendation Agent (`project_recommendation_agent.py`)**: Formulates portfolio-grade project specifications directly addressing critical skill gaps for target jobs.
  8. **Resume Agent (`resume_agent.py`)**: Generates tailored summaries and action-oriented bullet points incorporating verified skills.
  9. **Approval Workflow Agent (`approval_agent.py`)**: Enforces mandatory human-in-the-loop approval gates for all consequential actions (e.g. submitting applications, exporting resumes). **An LLM cannot approve itself**.
- **Authentic Learning Resource Registry (`resource_registry.py`)**:
  - Authoritative directory of verified official resources (`docs.python.org`, `fastapi.tiangolo.com`, `docs.docker.com`, `postgresql.org`, `redis.io`, `react.dev`, `freecodecamp.org`, etc.).
  - `is_url_genuine()` validator enforcing HTTPS and whitelisted domain matching.
- **Human-in-the-Loop Approval Workflow & Audit Persistence**:
  - `AgentApprovalRequest` table (`005_create_agent_workflow_and_approval_tables.py`) persists queued consequential actions in `pending` status.
  - Execution strictly halts until explicit human authorization (`POST /api/v1/agents/approvals/{id}/approve` or `POST /api/v1/agents/approvals/{id}/reject`).
  - Strict per-user isolation: Cross-user access or unauthorized decision attempts return `404 Not Found`.
  - Workflow audit runs are tracked in `AgentWorkflowRun` with serialized step history, state summaries, and execution statuses.
- **Multi-Agent Pipeline Workflow**:
  ```mermaid
  flowchart TD
      START([Start / User Trigger]) --> Profile["1. Career Profile Agent"]
      Profile --> GitHub["2. GitHub Analysis Agent"]
      GitHub --> Jobs["3. Job Matching Agent"]
      Jobs --> Gaps["4. Skill Gap Agent"]
      Gaps --> Plan["5. Career Planning Agent"]
      Plan --> Resources["6. Resource Research Agent"]
      Resources --> Projects["7. Project Recommendation Agent"]
      Projects --> Resume["8. Resume Agent"]
      Resume --> Gate{"Consequential Action Requested?"}
      Gate -- No --> END([End / Completed State])
      Gate -- Yes --> Queue["9. Approval Workflow Agent (Queue Pending)"]
      Queue --> Human["Human Student Decision Gate"]
      Human -- "POST /approvals/{id}/approve" --> Exec["Execute Consequential Action"] --> END
      Human -- "POST /approvals/{id}/reject" --> Cancel["Action Cancelled"] --> END
  ```
- **Authenticated Multi-Agent Endpoints (`/api/v1/agents`)**:
  - `POST /workflows/career-twin`: Executes full 9-agent pipeline.
  - `POST /workflows/roadmap`: Executes focused incremental roadmap sub-workflow (`skill_gaps -> career_planning -> resources -> project_recommendations`).
  - `GET /workflows/{run_id}`: Retrieves workflow execution status and step history.
  - `GET /approvals`: Lists queued human approval requests for the authenticated user.
  - `GET /approvals/{id}`: Retrieves approval details.
  - `POST /approvals/{id}/approve`: Explicitly approves and executes a queued consequential action.
  - `POST /approvals/{id}/reject`: Rejects a queued consequential action.


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
*(All 91 unit and integration tests execute in ~14 seconds without requiring GPU or model weights).*

---

### Local Model Setup & Real GPU Inference (Phase 6)

#### 1. Hardware Requirements (Measured on NVIDIA RTX 4050 Laptop GPU)
- **Host GPU**: NVIDIA GeForce RTX 4050 Laptop GPU (6,140.5 MB VRAM)
- **Host RAM**: 16 GB System Memory
- **Host Storage**: ~6 GB persistent disk space for model weights
- **Driver / CUDA**: NVIDIA Driver 592.82+, CUDA Version 13.1, PyTorch 2.5.1+cu121

#### 2. Download Model Weights (Persistent Local Cache Outside Git)
Never downloads during FastAPI startup:
```bash
python scripts/download_model.py
```
*Downloads official `Qwen/Qwen2.5-3B-Instruct` snapshots into `~/.cache/kuru_models/Qwen2.5-3B-Instruct` (5.76 GB on disk).*

#### 3. Run Real GPU Inference Benchmark
```bash
python scripts/benchmark_llm.py --provider local --output evaluation_results/real_benchmark_results.json
```

#### Measured Benchmark Results (NVIDIA RTX 4050 Laptop GPU — 4-bit NF4 Quantization):
| Metric | Real Measured Value |
| :--- | :--- |
| **Model** | `Qwen/Qwen2.5-3B-Instruct` (4-bit NF4 bitsandbytes) |
| **Total Evaluation Cases** | 5 Career Twin tasks (Resume, Roadmap, Interview) |
| **Schema Compliance Rate** | **100.0%** (5/5 cases valid Pydantic instances) |
| **Peak Inference VRAM** | **2,057.89 MB** (~2.06 GB / 6,140.5 MB available) |
| **Average Task Latency** | **59.70 seconds** per complete structured output |
| **Token Throughput** | ~8–12 tokens/second on GPU |
| **Memory Headroom** | ~4.08 GB free VRAM headroom for Windows WDDM & multitasking |

Results are stored in reproducible format at `evaluation_results/real_benchmark_results.json`.

---

### QLoRA Fine-Tuning & Adapter Verification

#### 1. Hardware Feasibility Check
```bash
python scripts/train_qlora.py --check-only
```
- Total trainable parameters: **29,933,568** (0.96% of total 3.12B parameters).
- Base 4-bit weights (~2.0 GB) + LoRA $r=16$ (~95 MB) + activations (~1.4 GB) = **~4.2 GB peak budget** (Fully feasible on 6 GB VRAM).

#### 2. End-to-End 2-Step Smoke Test & Adapter Load Test
```bash
python scripts/train_qlora.py --smoke-test --output-dir checkpoints/qlora_smoke_test
```
- **Privacy Assurance**: Trained strictly on non-private synthetic Career Twin instruction pairs. Training on private user tables is strictly prohibited.
- **Measured Step 1 Loss**: `4.4216` (3.92s latency)
- **Measured Step 2 Loss**: `3.9087` (1.69s latency)
- **Peak Training VRAM**: **3,170.9 MB** (~3.17 GB)
- **Adapter Verification**: Successfully saved to `checkpoints/qlora_smoke_test`, re-loaded via `peft.PeftModel.from_pretrained()`, and verified with active forward generation!

---

### Troubleshooting & Fallback
- **CUDA Out of Memory (OOM)**: `LocalTransformersProvider` monitors CUDA memory and automatically falls back to CPU float32 mode if VRAM allocations exceed hardware capacity.
- **Generation Timeouts**: Increase `LLM_TIMEOUT_SECONDS=180.0` in `.env` if generating large roadmaps on battery power or lower-wattage laptop profiles.
- **Test Mode Decoupling**: Setting `LLM_PROVIDER="mock"` allows CI/CD and unit testing without downloading model weights or requiring a GPU. `LLMProviderFactory` strictly rejects `mock` provider in production environments.

### Phase 7.1: LangSmith Observability, Firebase Auth, and Flutter Integration

#### 1. Official LangSmith Tracing & Observability
- **Dedicated Project**: Configured for project `kuru-career-twin` targeting official LangSmith tracing.
- **Trace Scope**: Automatically traces all 9 logical agents, StateGraph nodes, local Qwen LLM calls, retries, node failures, and human approval pauses.
- **Safe Startup Diagnostics**:
  - `GET /api/v1/health/observability`: Returns diagnostic status (`connected`, `unconfigured`, `invalid_key`, `disabled`) with masked API keys (`lsv2_pt_...****`).
  - Zero Fake Tracing: If the API key is missing or invalid, explicitly returns setup guidance rather than faking trace dispatch.
  - Privacy First: Bearer tokens, passwords, and sensitive student PII are masked by `SensitiveDataFilter` and omitted from LangSmith metadata.
- **Smoke Test Tool**:
  ```bash
  python scripts/verify_langsmith.py
  ```
  Validates environment configuration, tests LangSmith API connectivity, and runs an end-to-end multi-agent workflow trace.

#### 2. Firebase Authentication & ID Token Lifecycle
- **Backend Admin SDK**: Initialized using service account credentials or target project ID (`career-ba46c`) with cryptographic verification of ID tokens (`verify_id_token`).
- **Token Claims & Authorization**: User identity is derived strictly from verified token claims (`uid`). Unauthenticated requests are rejected with 401. Protected endpoints enforce per-user isolation against the authenticated `uid`.
- **Flutter Token Management**:
  - `AuthService` handles email/password registration, login, and sign-out via `FirebaseAuth`.
  - `ApiClient` automatically injects Bearer tokens via `tokenProvider` and triggers token refresh when expired.
  - Cross-platform session persistence supported via `TokenStorage`.

#### 3. Cloud Firestore & Real-Time Sync
- **Data Boundary & Separation of Concerns**:
  - **PostgreSQL**: Serves as the immutable primary source of truth for relational student profiles, GitHub static code analyses, skill knowledge graphs, verified job postings, intelligence scores, and LangGraph checkpoints. Relational data is never needlessly replicated into NoSQL.
  - **Cloud Firestore**: Dedicated exclusively to real-time mobile preferences (`users/{userId}/settings/preferences`), lightweight study notes (`users/{userId}/career_notes`), and offline mobile cache synchronization.
- **Strict User Isolation & Security Rules**:
  - Firestore security rules strictly constrain document access to the authenticated user's own subtree:
    ```javascript
    rules_version = '2';
    service cloud.firestore {
      match /databases/{database}/documents {
        match /users/{userId}/{document=**} {
          allow read, write: if request.auth != null && request.auth.uid == userId;
        }
      }
    }
    ```
  - Backend sync endpoints (`/api/v1/sync/preferences` and `/api/v1/sync/notes`) cryptographically enforce isolation and reject any cross-user parameter tampering with `403 Forbidden` (`FIRESTORE_ACCESS_DENIED`).

#### 4. Firebase Console Manual Setup Guide
To configure Firebase for the Kuru system:
1. **Enable Firebase Authentication**:
   - Navigate to **Firebase Console** -> Select project `career-ba46c` (or your project).
   - Go to **Build** -> **Authentication** -> **Sign-in method**.
   - Enable the **Email/Password** provider and save.
2. **Provision Cloud Firestore**:
   - Go to **Build** -> **Firestore Database** -> **Create database**.
   - Select **Native mode**.
   - Choose a nearby region (e.g., `asia-south1` (Mumbai) for low Indian latency).
3. **Deploy Security Rules**:
   - Open the **Rules** tab in Cloud Firestore, paste the security rules from `firestore.rules` (or run `firebase deploy --only firestore:rules`), and click **Publish**.
4. **Android App Registration (`google-services.json`)**:
   - In **Project Settings** -> **General** -> **Your apps**, verify the Android app package is `com.kuru.app.kuru_app`.
   - Download `google-services.json` and place it in:
     ```
     kuru_app/android/app/google-services.json
     ```
   *(Note: This file is excluded from git tracking via `.gitignore` to protect API keys).*
5. **Backend Service Account Credentials**:
   - In **Project Settings** -> **Service accounts**, click **Generate new private key**.
   - Save the credentials JSON securely on your host outside the git repository.
   - Configure the path in your `.env` file:
     ```env
     FIREBASE_PROJECT_ID="career-ba46c"
     FIREBASE_CREDENTIALS_PATH="/path/to/serviceAccountKey.json"
     ```

#### 5. Flutter Mobile Frontend (`kuru_app`)
- **Structure**: Modern Flutter client located in `kuru_app/` connecting to the FastAPI backend.
- **Dynamic API Base URLs**:
  - Android Emulator: `http://10.0.2.2:8000/api/v1`
  - Web & Desktop: `http://127.0.0.1:8000/api/v1`
  - Physical Devices: Configurable at runtime via Login & Profile screens.
- **Core Screens & Capabilities**:
  1. **Career Twin Screen**: Interactive runner for the 9-agent LangGraph pipeline with live agent step timeline, generated weekly milestone roadmaps, recommended projects, and verified resources.
  2. **Jobs & Internships Screen**: Search, filter by work mode (remote/hybrid/on-site), view transparent match percentages, matched skills (green), missing skills (amber), and bookmark jobs.
  3. **Skill Gaps & Simulator Screen**: Evidence-backed codebase skills, prioritized market gaps, and an interactive What-If Simulator projecting score lifts and newly unlocked jobs.
  4. **Approvals Screen**: Human-in-the-loop decision gate allowing students to inspect, approve, or reject consequential agent actions with feedback.
  5. **Profile & Settings Screen**: Student profile management, GitHub connection & analysis trigger, Cloud Firestore study notes & preferences, system observability diagnostics, and sign-out.
- **Testing & Verification**:
  ```bash
  cd kuru_app
  flutter analyze
  flutter test
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
11. **Never Let an LLM Approve Itself (Human-in-the-Loop)**: Any consequential actions (applications, profile updates, external exports) must pass through the `approval_workflow_agent` and remain `pending` until explicit cryptographic approval by the authenticated human user.
12. **Zero Hallucinated URLs & Genuine Resource Verification**: The `resource_research_agent` strictly queries verified registries and enforces cryptographic HTTPS whitelist checks, guaranteeing zero invented links.
13. **Observability Integrity**: LangSmith tracing strictly preserves privacy, masks secrets, and never fakes successful traces when credentials are missing.

