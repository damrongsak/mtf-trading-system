# Implementation Plan - Reliability & Startup Stability

## Problem
The `api-gateway` service reported a `503 Service Unavailable` error for the `/api/v1/data/symbols` endpoint during system startup.
Investigation revealed a race condition where `api-gateway` was ready and receiving requests while `data-pipeline` was still executing its `@app.on_event("startup")` handlers (migrations, startup checks, and starting background workers/streamers).

## Proposed Changes

### 1. Infrastructure (docker-compose.yml)
- Add `healthcheck` to `data-pipeline` using its `/health` endpoint.
- Add `healthcheck` to `mtf-postgres`.
- Add `healthcheck` to `redis`.
- Update `api-gateway`, `strategy-core`, `execution`, and `ai-analyst` to use `depends_on` with `condition: service_healthy` for their dependencies.

### 2. Service Resilience (api-gateway)
- Implement basic retry logic in the `httpx` proxy calls to internal services (data-pipeline, execution, ai-analyst).
- Update `services/api-gateway/app/utils/http_client.py` (if it exists) or create a utility for resilient requests.

### 3. Data Pipeline Startup
- Ensure the `/health` endpoint reflects the actual readiness state.
- (Optional) Decouple non-critical background task starts from the main startup event if they block readiness excessively.

## Verification Plan
1. Apply `docker-compose.yml` changes.
2. Restart the stack using `docker compose up -d`.
3. Verify that `api-gateway` only becomes "Up" after `data-pipeline` and `execution` are healthy.
4. Test the `/api/v1/data/symbols` endpoint immediately after the gateway is reachable.
5. Verify the health status of all services via `docker compose ps`.
