---
name: database-migration
description: Manages database schema evolutions using Spec-First Migration (SFM) and Single Migration Authority (SMA) patterns.
---

# Database Migration Skill

This skill enforces the **MTF Olympus Standard** for database schema changes. It prevents schema drift across microservices by ensuring all changes are spec-driven and managed by a single service.

## Core Principles

1.  **Spec-First (SFM)**: Every schema change MUST exist in `specs/03_data_model.yaml` before any code or migration is written.
2.  **Single Authority (SMA)**: The `data-pipeline` service is the ONLY service authorized to generate and run migrations.
3.  **Cross-Service Sync**: Other services (`api-gateway`, `execution`, `strategy-core`) must align their `models.py` with the root spec. The `data-pipeline` service MUST maintain a full, synchronized copy of these models in its `app/models/` directory to act as an accurate SMA.
4.  **No Stub Models**: Using "stubs" (partial classes) in the SMA is STRICTLY PROHIBITED as it causes Alembic to generate destructive `DROP` commands.

## Workflow

### 1. Update the Specification
Modify the root data model spec: `[03_data_model.yaml](file:///home/dan/workspace/mtf-trading-system/specs/03_data_model.yaml)`.
- Use correct types (UUID for IDs, JSONB for metadata, etc.).
- Ensure descriptions are clear.

### 2. Synchronize Models
Copy the full model definitions from the source service to `services/data-pipeline/app/models/`.
- Ensure `__init__.py` in the pipeline imports the new models for metadata registration.
- **NEVER** use partial/stub classes.

### 3. Generate Migration (from Data Pipeline)
All migration commands MUST be run inside the `data-pipeline` container.

```bash
# Generate the migration script
docker compose exec data-pipeline /venv/bin/alembic revision --autogenerate -m "feat: your_change_description"
```

### 3. Review & Refine
Inspect the generated file in `services/data-pipeline/alembic/versions/`.
- Ensure it doesn't drop unrelated tables.
- Check that types match the spec exactly.

### 4. Apply Migration
Run the migration against the shared database.

```bash
docker compose exec data-pipeline /venv/bin/alembic upgrade head
```

### 5. Verify Across Services
Ensure other services can still communicate with the updated schema.
Run the schema validator:

```bash
docker compose exec api-gateway uv run python scripts/verify_schema.py
```

## Troubleshooting

- **Destructive Drops Recorded**: If Alembic tries to drop existing tables/columns unexpectedly, you are likely using a **Stub Model**. Copy the full class definition from `api-gateway` to `data-pipeline/app/models/`.
- **Target Content Not Found**: If Alembic misses a model, ensure it's imported in `services/data-pipeline/app/models/__init__.py`.
- **Duplicate Object**: If a type (e.g., ENUM) already exists, you may need to manually `CREATE TYPE` or wrap the DDL in a "check if exists" block in the migration script.
- **Head Discrepancy**: If there multiple heads, merge them using a bridge migration or `alembic mergeheads`.
