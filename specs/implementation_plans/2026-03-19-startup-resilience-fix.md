# Implementation Plan - Startup Resilience Fix

## 1. Objective
Fix the startup failure where `api-gateway`, `execution`, and `data-pipeline` fail to reach a healthy state due to circular dependencies, tight health check timeouts, and missing infrastructure dependencies.

## 2. Proposed Changes

### Infrastructure (`docker-compose.yml`)
- [x] Add `redis: condition: service_healthy` to `execution`'s `depends_on`.
- [x] Add `DATA_PIPELINE_URL=http://data-pipeline:8000` to `execution` environment.
- [x] Increase `execution` health check `retries` to 10 and add `start_period: 30s`.
- [x] Increase `data-pipeline` health check `retries` to 10 and add `start_period: 30s`.

### Execution Service (`services/execution`)
- [x] **Cache Service**: Redirect `get_symbols` HTTP fallback from `api-gateway` to `data-pipeline` to break circular dependency.
- [ ] **Logging**: Ensure all logs in `cache_service.py` and `ctrader.py` (if any future edits) follow the structured JSON standard.

### Specs & Documentation
- [ ] **01_architecture.md**: Document the internal communication path for symbol metadata (Execution -> Data Pipeline).
- [ ] **08_execution_rules.md**: Update the "HFT-lite" startup sequence to reflect direct dependency on Data Pipeline for symbols.

## 3. Verification Plan
1. **Gate 1: Logic Verification**:
   - Run `docker compose ps` to verify all containers are `healthy`.
   - Check `execution` logs for successful symbol hydration from `data-pipeline`.
2. **Gate 2: Code Quality**:
   - Run `ruff check` on modified files.
3. **Gate 3: Schema Integrity**:
   - Run `verify_schema.py`.
4. **Gate 4: Security Audit**:
   - Verify no hardcoded credentials or sensitive data in logs.
