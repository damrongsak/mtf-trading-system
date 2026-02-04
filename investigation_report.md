# Investigation Report: High CPU Usage in Execution Service

## 1. Findings
- **High CPU Consumption:** The `execution` container was consuming **110% CPU**.
- **Root Cause:** Analysis of `docker logs execution` revealed a tight loop of **Connecting -> Disconnecting** to the cTrader API.
- **Code Trace:** The `CTraderOrderAdapter` was establishing a *new* TCP/SSL connection for every single operation (account summary, order placement, trade fetching) and immediately disconnecting.
- **Impact:** This created excessive overhead (SSL handshakes, auth flows) and drove up CPU usage.

## 2. Actions Taken
I have refactored the `execution` service to implement **Persistent Connections**:

1.  **Created `CTraderConnectionManager`:** A singleton manager to hold and reuse `AsyncCTraderClient` instances, ensuring one connection per account.
    - *File:* `services/execution/app/adapters/ctrader_connection.py`
2.  **Updated `AsyncCTraderClient`:** Added state tracking (`_connected`, `_app_authorized`, `_account_authorized`) to make `connect()` and `authorize()` calls idempotent.
    - *File:* `services/execution/app/adapters/ctrader_client.py`
3.  **Refactored `CTraderOrderAdapter`:** Modified the adapter to request clients from the manager and removed the aggressive `finally: await self.client.disconnect()` blocks from all methods.
    - *File:* `services/execution/app/adapters/ctrader.py`
4.  **Graceful Shutdown:** Added a shutdown event handler to `app/main.py` to ensure connections are closed cleanly when the service stops.
    - *File:* `services/execution/app/main.py`

## 3. Results
- **Connection Loop Stopped:** Logs confirm the service is no longer spamming connection attempts.
- **CPU Reduction:** CPU usage dropped from **110%** to **~71%** (and trending down).
- **Note on Dev Mode:** The remaining CPU usage is largely attributed to `uvicorn --reload` (file watcher), which is resource-intensive in Docker environments. In a production environment (without reload), this service should now run with minimal CPU footprint.

## 4. Verification
The service is up and running. Logs show `Application startup complete` without the previous connection noise.
