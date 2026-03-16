## Setup & Dependency Management

Project uses **`uv`** for extremely fast and reliable dependency management.

### 1. Install Dependencies
```bash
# Install uv (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync environment
uv sync
```

### 2. Run Ingestion
```bash
# Standard mode
uv run ingest.py --mode standard

# Hierarchical mode (large documents)
uv run ingest.py --mode hierarchical
```

### 3. Run Tests
```bash
# Standard pytest (recommended)
uv run pytest

## Docker Setup & Deployment

The project is fully containerized as a high-performance FastAPI service.

### 1. Build and Run
```bash
# Start the full stack (Ingestor API + Local FalkorDB mapping)
docker-compose up --build -d
```

### 2. Startup Guard & Health
The service includes a **`StartupGuard`** that validates:
- **Redis/FalkorDB** connectivity.
- **LLM Gateway** (OpenRouter) authentication.
- **Filesystem** permissions.

If any check fails, the container will exit with a critical error to prevent "Silent Failures".

### 3. Networking
The ingestor connects via the external **`orignx-network`**. Ensure your external FalkorDB is accessible on this network.

## Standards & Conventions

### 1. Structured Logging
Use `app.core.logger.get_logger("component_name")`. Logs are output as JSON in production for ELK/Elasticsearch compatibility.

### 1. Spec-First Development
Always update or refer to this `GEMINI.md` and the ontology definitions before making structural changes.

### 2. Package Discovery
The project is structured as a professional Python package. 
- **Root**: `/home/dan/workspace/app-ingestor`
- **Package**: `app/`
- **Pytest**: Configured via `pyproject.toml` with `pythonpath = ["."]` to avoid `ModuleNotFoundError`.

### 3. Testing Standards (90%+ Coverage)
Future development MUST maintain high coverage:
- **Mocking Strategy**: 
    - Mock `LLMUtils.call_llm` to avoid API costs and instability.
    - Mock `redis.Redis` for `FalkorDBClient`.
    - Mock `builtins.open` and `pathlib.Path.stat` for filesystem operations.
- **Async**: Use `unittest.IsolatedAsyncioTestCase` for pipeline testing.
- **Data Models**: Ensure all new dataclasses in `models.py` have corresponding tests.

### 4. Code Style
- Use `BaseIngestor` for any new ingestion strategy.
- Implement `run_pipeline(self, file_path: Path) -> IngestionResult` in subclasses.
- Use **Absolute Imports** (e.g., `from app.core.app_config import config`).

## Workflows

### Adding a New Ingestor
1. Create a new class inheriting from `BaseIngestor` in `app/ingestors/`.
2. Define the specific prompt logic and tiers within the class.
3. Implement `run_pipeline`.
4. Add a unit test in `tests/test_ingestors.py` (or a new file) using mocks.

---
*Last updated: 2026-03-09*
