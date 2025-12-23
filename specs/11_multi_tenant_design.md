# Architecture Design: Multi-Tenant Fleet System

## Overview
This design addresses the requirement for **Multi-User, Multi-Broker, and Multi-Account** scalability. The core concept is transforming the `Strategy Core` into a **Fleet Manager** and the `Execution Service` into a **Stateless Router**.

## 1. Core Concepts

### 1.1 The Hierarchy
To support complex ownership, we define a strict hierarchy:
1.  **User**: The legal owner (e.g., "Dan").
2.  **Fund (Portfolio)**: A container for capital (e.g., "High Risk Alpha").
3.  **BrokerAccount**: A credentialed connection to a venue (e.g., "Oanda Real #1").
4.  **StrategyInstance**: A running logic template bound to an Account with specific parameters.

### 1.2 The "Fleet"
A **Fleet** is the collection of all active `StrategyInstances` across all users. The system must tick every instance independently, even if they share the same symbol.

## 2. Microservice Architecture

### 2.1 Strategy Core (The Fleet Manager)
**Responsibility**: Maintain state for thousands of concurrent strategies.

*   **Registry**: A Redis/DB backed registry of `ActiveStrategies`.
*   **Tick Router**:
    *   Receives `MarketData(EUR_USD)`.
    *   Lookups all Strategies subscribed to `EUR_USD`.
    *   Spawns `asyncio.Task` for each strategy logic execution.
*   **Risk Profile**:
    *   Each strategy has a `config` object: `{ "risk_type": "fixed_usd", "risk_value": 50.0 }`.
    *   This config is **passed down** with every signal.

### 2.2 Execution Service (The Stateless Router)
**Responsibility**: Execute orders blindly but safely for ANY broker.

*   **Stateless**: Does NOT know about "Users" or "Funds".
*   **Input**: `SmartOrderRequest` contains `broker_account_id`.
*   **Routing**:
    1.  Look up `BrokerAccount` by ID (Get credentials + Broker Name).
    2.  `BrokerFactory.get_adapter(Name, Credentials)`.
    3.  Execute.
*   **Safety**: Enforces the Risk Parameters passed in the request (as implemented in Phase 1).

## 3. Data Model Updates (Proposed)

```yaml
User:
  id: UUID
  username: string

Fund:
  id: UUID
  user_id: FK(User)
  name: string
  risk_limit_daily: currency

BrokerAccount:
  id: UUID
  fund_id: FK(Fund)  <-- Moved from User to Fund
  broker_name: enum(OANDA, BINANCE)
  credentials: json (encrypted)

StrategyInstance:
  id: UUID
  broker_account_id: FK(BrokerAccount)
  template_id: string (e.g., "RSI_Divergence")
  config: json
    - symbol: "EUR_USD"
    - timeframe: "H1"
    - risk_settings: { ... }
```

## 4. Implementation Roadmap

### Phase 2.1: Database Refactor
- Migrate `BrokerAccount` to belong to `Fund` (or keep explicit User link for MVP).
- Ensure `StrategyInstance` table stores full config JSON.

### Phase 2.2: Fleet Loop
- Refactor `StrategyEngine` to load ALL active strategies from DB on startup.
- Implement the "Tick Router" pattern (Event Bus -> Strategy List).

### Phase 2.3: Multi-Broker Adapters
- Implement `BinanceAdapter` in Execution Service.
- Implement `MetaTraderAdapter` (via Bridge).
