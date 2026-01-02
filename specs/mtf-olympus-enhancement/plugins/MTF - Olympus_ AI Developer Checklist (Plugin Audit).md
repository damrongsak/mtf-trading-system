# **MTF \- Olympus: AI Developer Checklist (Plugin Audit)**

**Purpose:** This checklist must be executed by the AI Code Agent before finalizing any plugin code to ensure compliance with the **Olympus Plugin Blueprint (v2.0.0)**.

## **🏗️ 1\. Structural Integrity & Architecture**

*Check if the plugin follows the "Quant Operating System" modularity.*

* \[ \] **Class Inheritance:** Does the class explicitly inherit from BasePlugin?  
* \[ \] **Standard Lifecycle:** Are activate(), deactivate(), and register\_hooks() methods implemented?  
* \[ \] **Hook Usage:** \- Use **Actions** (do\_action) for events that don't change data (logging, notifications).  
  * Use **Filters** (apply\_filters) for logic that modifies trade data (position sizing, risk checks).  
* \[ \] **Dependency Isolation:** Are all required libraries listed in a local requirements.txt? (Critical for Docker Sidecar isolation).

## **📈 2\. Quantitative Finance Standards**

*Check if the plugin adheres to professional trading ethics and metrics.*

* \[ \] **No Look-ahead Bias:** Audit the data fetching and slicing logic. Does it ensure that the model *never* sees price data from $t+1$ during training or signal generation?  
* \[ \] **Metric Compliance:** Does the performance reporting follow CFA standards (Sharpe, Sortino, MDD)?  
* \[ \] **Signal Metadata:** Does the generated signal include a confidence\_score and raw\_output for auditability?  
* \[ \] **Execution Realism:** Does the backtest/simulation logic account for trading fees and slippage?

## **🛡️ 3\. Risk & Safety Guardrails**

*Check if the plugin respects the "Safety First" principle.*

* \[ \] **Pre-trade Filter:** Does the trade signal pass through the filter\_trade\_request hook?  
* \[ \] **Hard Limits:** Are the following checks present or respected?  
  * **Confidence Threshold:** Reject signals below 65% (or user-defined).  
  * **Exposure Limit:** Prevents asset concentration (\>20% AUM).  
  * **Drawdown Kill-switch:** Stops trading if daily loss hits a specific threshold.  
* \[ \] **Error Handling:** Does the plugin trigger on\_plugin\_error if an AI model fails or a connection drops?

## **🗄️ 4\. Persistence & Multi-Tenancy**

*Check if the plugin handles data and users securely.*

* \[ \] **Database Integrity:** Does the plugin save its state and signals to the PostgreSQL schema defined in the blueprint?  
* \[ \] **JSONB Validation:** Is custom\_config validated before being saved to the user\_plugins table?  
* \[ \] **Audit Trail:** Is every activation, deactivation, or config change logged in the audit\_logs table?  
* \[ \] **User Isolation:** Does the plugin strictly use the user\_id provided in the constructor to fetch its specific configuration?

## **🚀 5\. Sidecar & Communication (Production Grade)**

*Check if the plugin is ready for Docker-based scaling.*

* \[ \] **Redis Integration:** Does the plugin communicate via Redis Pub/Sub for market\_data (Sub) and signals (Pub)?  
* \[ \] **Stateless Design:** Can the plugin restart without losing critical trade state? (State should be in Postgres/Redis, not local RAM).  
* \[ \] **Resource Awareness:** Is the logic optimized to stay within the 0.5 CPU / 1GB RAM limit defined in the sidecar spec?

## **📑 6\. Strategy-Specific Logic (e.g., LSTM Paper)**

* \[ \] **Mode Implementation:** Does the plugin support both Reckless and Prudent modes?  
* \[ \] **Risk Quantification:** Is Equation 5/6 from the LSTM paper correctly implemented in the Prudent mode filter?

### **AI Prompt for Re-check:**

*"Review the generated code against the **MTF \- Olympus Plugin AI Checklist**. For every 'No' or 'Missing' item, refactor the code to comply with the blueprint before submitting the final version."*