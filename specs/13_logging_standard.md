# Spec 13: Logging & Traceability Standard

## 🚀 Overview
To ensure system-wide observability and enable advanced debugging, MTF Olympus mandates structured JSON logging and consistent correlation ID propagation across all microservices.

## 📊 JSON Log Schema
All logs MUST be emitted as single-line JSON objects with the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | String | ISO8601 UTC format (`YYYY-MM-DDTHH:MM:SSZ`). |
| `severity` | String | Log level (INFO, DEBUG, WARNING, ERROR, CRITICAL). |
| `name` | String | The name of the logger (e.g., `app.main`, `httpx`). |
| `message` | String | The human-readable log message. |
| `request_id` | String \| null | (API Gateway/Analyst) The unique ID of the HTTP request. |
| `correlation_id` | String \| null | (Execution/Strategy) The ID used to trace a request across services. |

### Example Log Entry
```json
{"timestamp": "2026-03-11T15:10:13Z", "severity": "INFO", "name": "app.middleware", "request_id": "01d41d2d-89ef-4d01-b3b2-b2205d86924b", "message": "Incoming: GET /api/v1/health"}
```

## 🆔 Propagation Patterns

### 1. API Gateway (Entry Point)
- **Middleware**: `RequestIDMiddleware` (ASGI/Starlette) MUST capture `X-Request-ID` from headers or generate a new UUID.
- **Context**: Store the ID in a `contextvars.ContextVar` (located in `app.utils.tracing`).
- **Response**: Return the ID in the `X-Request-ID` header.

### 2. Asynchronous Workers (Execution/Strategy)
- **Message Payload**: Incoming messages from Redis/Queues MUST contain a correlation ID (often derived from `client_order_id` or an explicit `request_id` field).
- **Worker Context**: The worker MUST set the `correlation_id_ctx` at the start of task processing and reset it in a `finally` block.
- **Tracing**: All logs emitted during the task execution MUST include the `correlation_id`.

### 3. Cross-Service Calls
- When calling another service (e.g., API Gateway calling Data Pipeline), the `request_id` MUST be forwarded in the `X-Request-ID` or `X-Correlation-ID` header.

## 🛠️ Implementation Requirements
1. **Library**: Use `python-json-logger`.
2. **Formatter**: Use `pythonjsonlogger.jsonlogger.JsonFormatter`.
3. **Tracing Filter**: Implement a `logging.Filter` to inject the context variable into every log record.
4. **Singleton Context**: Avoid context drift by using a centralized `app.utils.tracing` module.

```python
# app/utils/tracing.py
import contextvars
request_id_ctx = contextvars.ContextVar("request_id", default=None)
```

## 🚫 Forbidden Patterns
- **Plain Text Logs**: Do not use `logging.basicConfig(format=...)` with string templates in production.
- **Local ContextVars**: Do not define `ContextVar` inside middleware files; use the singleton utility.
- **Manual Injection**: Do not manually add the ID to every `logger.info()` call; use a `TracingFilter`.
