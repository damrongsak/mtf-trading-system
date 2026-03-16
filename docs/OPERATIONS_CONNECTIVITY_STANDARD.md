# Operations Connectivity & Audit Standard

This document defines the standard procedure for verifying broker connectivity, user-fund relationships, and risk guardrails within the MTF Olympus system. This check should be performed after major configuration updates, deployments, or when troubleshooting execution issues.

## 1. Broker Connectivity Verification

### 1.1 Automated Check
A Python script should be used to verify that the `execution-service` can successfully communicate with configured brokers and retrieve account summaries (Balance/NAV).

**Standard Script: `check_connections.py`**
```python
import requests
import os

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000/api/v1")
EXECUTION_URL = os.getenv("EXECUTION_URL", "http://execution:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

def check_broker_account(account_id):
    url = f"{EXECUTION_URL}/account/summary"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    payload = {"broker_account_id": account_id}
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 200, response.json()

# Usage: Iterate through critical accounts and verify connectivity
```

### 1.2 Success Criteria
- HTTP 200 response from `/account/summary`.
- `data.balance` and `data.NAV` must be returned as numeric values.
- Failures like `CH_ACCESS_TOKEN_INVALID` require immediate token refresh.

---

## 2. User & Fund Audit

To ensure data integrity and proper RBAC (Role-Based Access Control), the following SQL audits must be performed.

### 2.1 User-Fund Association
Verify that users are mapped to the correct funds with appropriate roles (`OWNER`, `TRADER`, `MANAGER`).

```sql
SELECT u.username, f.name as fund_name, uf.role 
FROM users u 
JOIN user_funds uf ON u.id = uf.user_id 
JOIN funds f ON uf.fund_id = f.id;
```

### 2.2 Fund Risk Guardrails
Ensure that every fund has a defined strategy type and risk percentages aligned with institutional standards.

```sql
SELECT name, strategy_type, asset_classes, max_risk_per_trade, risk_percentage 
FROM funds;
```

### 2.3 Broker Account Mapping
Confirm that funds are linked to the correct broker accounts for execution.

```sql
SELECT f.name as fund_name, ba.broker_name, ba.account_name, ba.is_live, ba.environment 
FROM funds f 
JOIN broker_accounts ba ON f.id = ba.fund_id;
```

---

## 3. Maintenance Procedures

- **Credential Updates**: If a broker connection fails, update both the `.env` file AND the `broker_accounts` table (requires encryption via `SETTINGS_ENCRYPTION_KEY`).
- **Service Refresh**: Restart the `execution` service after any database-level credential update to refresh the L3 in-memory cache.
