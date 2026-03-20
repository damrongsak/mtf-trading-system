# Implementation Plan: Minor Enhancement (v2.2) - Architectural Hardening

## Goal
Improve system robustness, data integrity, and developer velocity by centralizing data models and standardizing service-to-service communication.

## User Review Required
> [!IMPORTANT]
> This version introduces **Breaking Changes** in internal code structure. All services will need to be refactored to use the new `mtf-common` package.

## Proposed Changes

### 1. Shared Infrastructure (`services/common`)
- **Move Models**: Migrate `Trade`, `BrokerAccount`, `Fund`, and `MarketSymbol` from individual services to a centralized package.
- **Base Database**: Extract `Base` and common SQLAlchemy mixins (e.g., `TimestampMixin`).
- **Dependencies**: Each service's `Dockerfile` and `pyproject.toml` will be updated to include the shared package as an editable volume or submodule.

### 2. Standardized Internal Client SDK
- **Base Client**: Create a robust HTTP client with:
  - Automatic `X-Internal-API-Key` injection.
  - Built-in Enum-to-String serialization.
  - Configurable timeouts and retries via `httpx`.
- **Service Wrappers**:
  - `ExecutionClient`: Used by Gateway/Strategy to place orders.
  - `AIAnalystClient`: Used by Execution to trigger post-trade analysis.

### 3. Service Readiness (Readiness Probes)
- **Execution Service**: Update `/health` or add `/ready` endpoint that returns `False` until the initial cache warmup (Account/Symbol hydration) is 100% complete.

## Verification Plan
### Automated Tests
- **CI Lint**: A script that fails if any service defines a SQLAlchemy model that should be in `mtf-common`.
- **Integration Test**: Verify a Mock Signal can flow through the system using the new Client SDKs.

### Manual Verification
- Deploy v2.2 to a fresh environment.
- Confirm `api-gateway` starts only after `execution` is "Ready".
