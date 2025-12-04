# API Gateway Service

The **API Gateway** is the central entry point for the MTF Trading System backend. It handles authentication, trade journaling, risk management, and routes requests to other internal services.

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.13+ (managed via `uv` recommended)
- PostgreSQL 15+ (with `pgvector`)
- Qdrant Vector Database

### 2. Environment Setup
Create a `.env` file in this directory:

```bash
cp .env.example .env
# OR
cp ENV_CONFIG.md .env
```

### 3. Run with Docker (Recommended)
```bash
docker compose up -d api
```

### 4. Run Locally (Development)
```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn app.main:app --reload
```

---

## ⚙️ Configuration

The service is configured via environment variables. See `.env.example` for a template.

### Key Variables

| Category | Variable | Description | Default |
|----------|----------|-------------|---------|
| **Database** | `DATABASE_URL` | PostgreSQL connection string | `postgresql://trader:trader@localhost:5432/mtf_db` |
| **Auth** | `SECRET_KEY` | JWT signing key | `supersecretkey` |
| **Auth** | `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity in minutes | `43200` (30 days) |
| **AI** | `GOOGLE_CLOUD_PROJECT` | GCP Project ID | `line-bot-2b383` |

**Token Expiration Guide:**
- Development: `1440` (1 day)
- Staging: `10080` (7 days)
- Production: `43200` (30 days)

---

## 🗄️ Database Management

### 1. Migrations (Alembic)
We use Alembic for schema migrations.

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description of changes"
```

### 2. Seeding Data
We provide scripts to populate the database with initial data.

| Script | Purpose | Command |
|--------|---------|---------|
| **Risk Rules** | Sets up default risk limits (MVP) | `python scripts/seed_risk_rules.py` |
| **Test Data** | Creates users, funds, and trades | `python scripts/seed_test_data.py` |
| **Vector DB** | Initializes Qdrant collections | `python scripts/init_qdrant.py` |

**Test Credentials:**
- Trader: `trader1` / `password123`
- Admin: `admin` / `admin123`

---

## 📥 Importing Trading History

You can import cTrader history from Excel files.

### 1. Export from cTrader
Export your history as an **Excel (.xlsx)** file from cTrader Web or Desktop.

### 2. Run Import Script
```bash
uv run python scripts/import_ctrader_excel.py <path_to_excel> <username>
```

**Example:**
```bash
uv run python scripts/import_ctrader_excel.py ~/Downloads/cT_History.xlsx trader1
```

**Features:**
- Automatically detects duplicates
- Classifies trades by Game Level (A/B/C)
- Identifies Trading Session (Asian/London/NY)
- Generates initial Mental State based on outcome

---

## 📚 API Documentation

Once running, interactive documentation is available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🏗️ Architecture

- **Framework:** FastAPI
- **ORM:** SQLAlchemy (Async)
- **Validation:** Pydantic
- **Vector Search:** Qdrant
- **Package Manager:** `uv`

For detailed data models, see `specs/01_data_model.yaml`.
