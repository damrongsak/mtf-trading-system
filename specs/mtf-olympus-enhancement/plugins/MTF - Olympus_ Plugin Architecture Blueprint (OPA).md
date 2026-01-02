# **MTF \- Olympus: Plugin Architecture Blueprint (OPA)**

Project Status: Production-Ready Specification  
Target Environment: Full-stack AI / Quant Finance  
Version: 2.0.0 (Scaling & Sidecar Integrated)

## **1\. Executive Summary & Vision**

MTF \- Olympus is designed as a **"Quant Operating System"** inspired by the modularity of WordPress. It separates the **Alpha Generation (Signals)** from the **Risk Management (Gatekeeping)** and **Execution (Trading)**. The goal is to allow Fund Managers to deploy complex models (e.g., LSTM, RL) as isolated plugins.

### **Core Principles:**

* **Isolation:** Each plugin runs in its own process/container (Sidecar Pattern).  
* **Auditability:** Every action, signal, and configuration change is logged for compliance.  
* **Safety First:** A mandatory Pre-trade Risk Gatekeeper must approve all signals.

## **2\. System Architecture (Sidecar Pattern)**

Plugins communicate with the Olympus Core via a Message Bus (Redis) or gRPC to ensure that a crash in an AI model does not affect the trading execution.

### **Communication Flow:**

1. **Core** publishes market\_data to Redis channel.  
2. **Plugin Container (Sidecar)** subscribes, processes AI logic (e.g., LSTM), and publishes a signal.  
3. **Core (Risk Engine)** intercepts the signal via filter\_trade\_request.  
4. **Core (Execution Engine)** executes the trade if approved.

## **3\. Database Schema (PostgreSQL)**

For AI Coder: Use these table definitions for persistence logic.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\-- User and Fund Manager profiles  
CREATE TABLE users (  
    user\_id UUID PRIMARY KEY DEFAULT uuid\_generate\_v4(),  
    email VARCHAR(255) UNIQUE NOT NULL,  
    role VARCHAR(50) DEFAULT 'trader',  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

\-- Catalog of available plugin types  
CREATE TABLE plugins (  
    plugin\_id VARCHAR(100) PRIMARY KEY,  
    name VARCHAR(255) NOT NULL,  
    category VARCHAR(50), \-- 'alpha', 'risk', 'execution'  
    base\_config\_schema JSONB   
);

\-- Active plugin instances per user  
CREATE TABLE user\_plugins (  
    instance\_id UUID PRIMARY KEY DEFAULT uuid\_generate\_v4(),  
    user\_id UUID REFERENCES users(user\_id),  
    plugin\_id VARCHAR(100) REFERENCES plugins(plugin\_id),  
    custom\_config JSONB, \-- Store 'Prudent' vs 'Reckless' parameters here  
    is\_enabled BOOLEAN DEFAULT FALSE,  
    UNIQUE(user\_id, plugin\_id)  
);

\-- Audit log for every configuration change or activation  
CREATE TABLE audit\_logs (  
    log\_id UUID PRIMARY KEY DEFAULT uuid\_generate\_v4(),  
    user\_id UUID REFERENCES users(user\_id),  
    action\_type VARCHAR(50),   
    resource\_id VARCHAR(100),  
    old\_value JSONB,  
    new\_value JSONB,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

## **4\. Hook System (The "WordPress" Logic)**

The HookManager handles the lifecycle of trade signals using **Actions** (triggers) and **Filters** (data modifiers).

* **Actions:** on\_market\_data, on\_order\_executed, on\_plugin\_error.  
* **Filters:** filter\_signal\_weight, filter\_position\_size, filter\_trade\_request.

## **5\. Plugin Specifications (Core Modules)**

### **A. Alpha Plugin (Inspired by LSTM Paper)**

* **Model:** LSTM (Long Short-Term Memory).  
* **Task:** Predict next-day prices for BTC/Gold.  
* **Modes:** \- Reckless: Maximize profit based on raw prediction.  
  * Prudent: Apply risk-quantification weights based on volatility.

### **B. Pre-trade Risk Plugin (The Gatekeeper)**

* **Mandatory Filter:** Intercepts every trade signal.  
* **Checks:**  
  * Confidence Threshold: Reject signals if AI confidence \< 65%.  
  * Exposure Limit: Max 20% of AUM per asset.  
  * Drawdown Protection: Stop trading if daily loss exceeds 5%.

## **6\. API Management (FastAPI)**

Endpoints for the Next.js Dashboard to manage the plugin lifecycle.

| Endpoint | Method | Description |
| :---- | :---- | :---- |
| /v2/plugins | GET | List available plugins and current activation state. |
| /v2/plugins/activate | POST | Spawn a sidecar container and register hooks. |
| /v2/plugins/deactivate | POST | Gracefully shut down container and clear hooks. |
| /v2/system/hooks | GET | Debug active actions and filters in the system. |

## **7\. Performance & Monitoring (Quant Metrics)**

Plugins must be audited using the following metrics (CFA Standards):

* **Sharpe Ratio:** Risk-adjusted return.  
* **Sortino Ratio:** Focus on downside deviation.  
* **Max Drawdown:** Peak-to-trough decline.  
* **Performance Drift:** Detection of AI accuracy decay over time.

## **8\. Instructions for AI Code Agent (Antigravity)**

1. **Always inherit** from BasePlugin for any new strategy.  
2. **Prioritize Filters** for risk logic and **Actions** for execution/logging.  
3. **Use Redis** for inter-process communication in production code.  
4. **Enforce JSONB Validation** when saving custom\_config to PostgreSQL.  
5. **No Look-ahead Bias:** Ensure data fetching logic never leaks future prices into the model.