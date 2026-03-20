# MTF Olympus RBAC System

This document outlines the Role-Based Access Control (RBAC) implementation for the MTF Trading System.

## 1. User Roles

The system uses four primary roles within the context of a **Fund**. Permissions are hierarchical and enforced at the API gateway router level.

| Role | Description | Key Permissions |
| :--- | :--- | :--- |
| **OWNER** | The absolute authority over a fund. | Full CRUD on Funds, Broker Accounts, Deployments, and Users. |
| **MANAGER** | Responsible for strategy and configuration. | Manage Deployments, Strategies, and Risk Settings. View PnL. |
| **TRADER** | Responsible for execution and monitoring. | Execute manual trades, approve signals, monitor live exposure. |
| **VIEWER** | Read-only access. | View performance dashboards, trade logs, and system status. |

## 2. Security Layers

### 2.1. Authentication (JWT)
The system uses **JWT (JSON Web Tokens)** for stateless authentication.
- **Provider**: `app.security.get_current_user` dependency.
- **Algorithm**: HS256 with a system-secret key.
- **Expiry**: Tokens are typically valid for 8 hours.

### 2.2. Broker Credential Security (AES-256)
Broker API keys and secrets are **never stored in plaintext**.
- **Encryption**: AES-256-GCM.
- **Key Management**: Keys are derived from a system-level master key (`ENCRYPTION_KEY`).
- **Isolation**: Decryption only occurs in memory within the `api-gateway` (for validation) and the `execution` service (for trade placement).

### 2.3. Internal Service Communication
Microservices communicate over an internal network using **Internal API Keys**.
- Header: `X-Internal-API-Key`
- Verified by: `app.routers.internal.verify_internal_api_key`

## 3. RBAC Enforcement Examples

### Fund Management
- `POST /api/v1/funds/`: Any registered user (becomes OWNER of the new fund).
- `DELETE /api/v1/funds/{id}`: Strictly **OWNER**.

### Broker Accounts
- `POST /api/v1/accounts/`: **OWNER** or **MANAGER**.
- `GET /api/v1/accounts/`: Anyone with access to the fund (decrypted credentials only shown to high roles).

### Trading & Deployments
- `POST /api/v1/deployments/`: **OWNER** or **MANAGER**.
- `POST /api/v1/internal/signals`: **TRADER** or above (via HITL approval).

## 4. Audit Trail
All significant actions are logged in the following tables:
- `user_action_logs`: For administrative changes.
- `signal_logs`: For every signal generated and its approval status.
- `trade`: For every order that hits the broker.
