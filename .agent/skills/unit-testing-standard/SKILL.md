---
name: unit-testing-standard
description: Best practices and standards for writing professional, isolated, and robust unit tests for the MTF Trading System, focusing on FastAPI, SQLAlchemy, and Async mocking.
---

# Unit Testing Standard & Best Practices

This skill defines the professional standard for writing unit tests within the MTF Trading System. It ensures tests are isolated, robust, and handle the complexities of asynchronous microservices, database interactions, and authentication.

## 🏗️ Core Principles

1.  **Strict Isolation**: Every test MUST be independent. Use `conftest.py` to clear states and overrides.
2.  **Explicit Mocking**: Never rely on real databases or external APIs (Redis, OANDA, cTrader) during unit tests.
3.  **HFT-Lite Compliance**: Tests must handle the "hot path" logic, including Redis Streams and tiered caching.
4.  **No False Positives**: Tests should fail for the right reasons and pass only when logic is correct.

---

## 🛠️ Centralized Fixtures (`conftest.py`)

Every service should have a `tests/conftest.py` to provide standardized fixtures.

### 1. Dependency Override Cleanup
Always clear `app.dependency_overrides` to prevent state leakage between tests.

```python
@pytest.fixture(autouse=True)
def clean_overrides():
    """Clear FastAPI dependency overrides after each test."""
    from app.main import app
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
```

### 2. Standardized `test_client`
Use a fixture to provide a `TestClient` with common dependencies (Auth, DB) already overridden.

```python
@pytest.fixture
def test_client(mock_db):
    """Provides a TestClient with auth and DB already overridden."""
    from app.main import app, verify_internal_api_key
    from app.database import get_db
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_internal_api_key] = lambda: "test-auth"
    
    yield TestClient(app)
```

### 3. Global Async Cache Mocking
Prevent `TypeError: object MagicMock can't be used in 'await' expression` by globally mocking cache services as `AsyncMock`.

```python
@pytest.fixture(autouse=True)
def global_cache_mock():
    """Globally mock execution_cache to prevent state leaking and await errors."""
    with patch("app.services.order_service.execution_cache") as mock_cache:
        mock_cache.get_account = AsyncMock(return_value=None)
        mock_cache.get_fund = AsyncMock(return_value=None)
        # ... other methods ...
        yield mock_cache
```

---

## 🧪 Advanced Mocking Strategies

### 1. Model-Based Mocking
Avoid bare `MagicMock` for SQLAlchemy models when numeric comparisons (`<`, `>`, `<=`, `>=`) or mathematical operations are involved. Instead, use real (detached) model instances.

```python
# GOOD: Using real model instances
mock_fund = Fund(
    id=uuid.uuid4(),
    max_risk_per_trade=500.0,
    max_drawdown_threshold=0.0 # Prevents TypeError in RiskLimits
)

# BAD: Comparison between MagicMocks will fail
# mock_fund = MagicMock(spec=Fund) 
```

### 2. DB Query Sequences (`side_effect`)
When a single function call results in multiple database queries, use `side_effect` with a list of results in the exact order they occur.

```python
mock_result = MagicMock()
# Sequence: Search account -> Search fund -> Search risk filters
mock_result.scalars.return_value.first.side_effect = [account_obj, fund_obj]
mock_result.scalars.return_value.all.return_value = [] # Filters
mock_db.execute.return_value = mock_result
```

### 3. Async Attributes
Ensure properties that are awaited in the code are mocked with `AsyncMock`. Don't forget `get_credentials` or any service method that talks to Redis/DB.

---

## 📋 Checklist for New Tests

- [ ] Does the test use `test_client` from `conftest.py`?
- [ ] Are all database calls intercepted via `mock_db`?
- [ ] If numeric comparisons are present, are real detached models used?
- [ ] Does the test include the necessary `X-Internal-API-Key` header if testing endpoints?
- [ ] Are `AsyncMock` used for all awaited coroutines?
- [ ] Are redundant local patches removed in favor of global `conftest.py` patches?

---

## 🚫 Common Pitfalls to Avoid

- **Unawaited Coroutines**: If you see `RuntimeWarning: coroutine X was never awaited`, you likely mocked an async function with `MagicMock` instead of `AsyncMock`.
- **403 Forbidden**: Usually means `verify_internal_api_key` wasn't overridden or the override was cleared too early.
- **State Leakage**: Ensure `app.dependency_overrides.clear()` is called in `conftest.py`.
- **Hardcoded UUIDs**: Use `uuid.uuid4()` to generate fresh IDs for each test run.
