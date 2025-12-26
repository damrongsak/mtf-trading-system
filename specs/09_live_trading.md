# Live Trading & Deployment Specification

## 1. Overview
The Live Trading system allows users to deploy custom Python strategies as autonomous bots. These bots run in a sandboxed environment managed by the **Fleet Manager** within the Strategy Core service. They behave identically to "Paper Trading" bots, with the only difference being the connection to a live broker account (if configured) or a simulation account.

## 2. Dynamic Bot Architecture
Unlike hardcoded strategies, "Dynamic Bots" are loaded from the database at runtime.
- **Source**: `SavedStrategy` (Python Code) + `Deployment` (Config).
- **Execution**: The `DynamicBotExecutor` compiles the Python code on the fly and executes the `strategy(data, params)` function.
- **Isolation**: Each bot runs in a restricted scope. Only `pandas`, `numpy`, and `pandas_ta` are available.

### 2.1. Lifecycle
1. **Deployment (STARTING)**: User clicks "Deploy" in Editor. `api-gateway` creates a `Deployment` record.
2. **Activation (ACTIVE)**: `FleetManager` picks up the new deployment via polling or direct signal. It initializes the `DynamicBotExecutor`.
3. **Execution Loop**:
   - `FleetManager` receives a market tick.
   - It updates `SharedMarketDataManager`.
   - It iterates through all `ACTIVE` deployments.
   - It calls `executor.execute(tick_data)`.
4. **Stopping (STOPPED)**: User clicks "Stop". `FleetManager` removes the instance from memory. The DB record is updated to `STOPPED`.

## 3. Sandboxing & Security
To prevent malicious code execution:
- **Input Sanitization**: Code is scanned via AST (Abstract Syntax Tree) to forbid imports like `os`, `sys`, `subprocess`, `net`.
- **Limited Scope**: The `exec()` context only provides safe libraries.
- **Resource Limits**: (Future) CPU/RAM limits per instance.

## 4. Error Handling
- **Runtime Errors**: If user code raises an exception, it is caught, logged to `last_error` in DB, and the bot may be paused or retried.
- **Market Data Gaps**: Bots are resilient to missing ticks; they compute on whatever data frame is available.

## 5. API Reference
See `04_api_spec.yaml` for full details.
- `POST /deployments/`: Deploy a strategy.
- `GET /deployments/`: Monitor status.
- `POST /deployments/{id}/stop`: Terminate.
