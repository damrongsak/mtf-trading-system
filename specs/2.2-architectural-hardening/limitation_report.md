# Technical Limitations & Improvement Report

During the trader simulation for `demo1`, several critical issues were identified that affected the robustness and data integrity of the system.

## ⚠️ Issues Encountered

### 1. Schema & Model Drift (Critical)
- **Problem**: The `Trade` model in the `execution` service was out of sync with the authoritative version in `api-gateway` and the actual PostgreSQL schema. 
- **Impact**: Caused a `CheckViolationError` on `lot_size` because column values were misaligned during insertions.
- **Root Cause**: Manual duplication of models across services without a shared source of truth.

### 2. Circular Dependencies
- **Problem**: A circular import loop was created: `main.py` -> `OrderService` -> `SessionFilter` -> `models.py` -> `main.py` (indirectly via shared state).
- **Impact**: The service failed to start with an `ImportError: cannot import name 'Fund'`.
- **Fix**: Implemented local imports and `TYPE_CHECKING` guards.

### 3. Serialization Failures
- **Problem**: `AIBridge` attempted to send Python Enums (`TradeDirection`) directly over JSON.
- **Impact**: AI feedback loop crashed with a `TypeError`.
- **Fix**: Added explicit serialization logic to convert Enums to strings.

### 4. API Endpoint Inconsistency
- **Problem**: Internal service URLs were incorrect (missing `/api/v1/ai` prefix).
- **Impact**: AI analysis failed with HTTP 404.

---

## 🚀 Proposed Improvements

### 1. Centralized Model Management
- **Action**: Create a shared internal package (e.g., `app-common`) or use a Git Submodule for models.
- **Benefit**: Ensures 100% schema consistency across all microservices.

### 2. Standardized Internal API Client
- **Action**: Implement a `BaseInternalClient` that handles:
  - Base URL configuration (from environment).
  - Standardized JSON serialization (automatic Enum handling).
  - Resilience patterns (retries/circuit breakers).
- **Benefit**: Eliminates hardcoded URL patterns and serialization errors in bridge services.

### 3. Dependency Injection (DI)
- **Action**: Refactor `OrderService` and `Filters` to use a DI container or pass dependencies explicitly.
- **Benefit**: Eliminates circular imports and makes unit testing significantly easier.

### 4. Robust Cache Warming
- **Action**: Modify the `execution` service startup to block until the cache is fully hydrated (or implement a "Ready" state separate from "Live").
- **Benefit**: Prevents signal failures due to missing account metadata during cold starts.

### 5. Schema Validation Gate
- **Action**: Add a CI step that compares the SQLAlchemy models across all services to ensure they match exactly.
- **Benefit**: Detects model drift before it reaches staging or production.
