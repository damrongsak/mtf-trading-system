# **🚀 AntiGravity Blueprint: Olympus Phase 2 (Alpha Ecosystem)**

Version: 2.0.2  
Status: 🟡 Pending Execution  
Architect: Senior Product Manager (AI)

## **1\. Requirement Refinement & Feasibility Analysis**

### **1.1. Input Deconstruction**

* **Abstract Idea:** Upgrade existing trading bot to a pro-grade Quant Research Workstation. Add a Formula Editor (Athena) for quick backtesting and a Real-time Feature Matrix (Poseidon) for monitoring data health.  
* **Core Pain Point:** The current "Strategy Foundry" requires writing full Python files and restarting services to test simple ideas. This results in high latency "Idea-to-Alpha".  
* **Operational Goal:** Reduce "Idea-to-Alpha" time from **Hours** to **Seconds**.

### **1.2. MVP Definition (Scope Lockdown)**

Ruthlessly eliminate "nice-to-have" features (genetic optimization, social sharing) to ensure deliverability.

* **IN SCOPE (The Critical Path):**  
  * **Athena (Frontend):** Monaco Editor component with auto-complete for financial terms.  
  * **Athena (Backend):** ExpressionEngine that safely parses string formulas into vectorbt signals.  
  * **Poseidon (Backend):** FeatureWorker that computes indicators (RSI, Vol) *outside* the strategy loop and pushes to Redis.  
  * **Poseidon (Frontend):** A read-only Grid Heatmap visualizing Feature freshness.  
* **OUT OF SCOPE (Phase 3):**  
  * Visual "Node-based" strategy builder.  
  * Multi-user collaboration on formulas.  
  * AI Agent "Auto-trading" research formulas live.

### **1.3. Feasibility Check**

* **Technical Viability:** **High**. Existing Redis and Python stack is sufficient. Safe eval() parsing is standard practice in Quant systems.  
* **Bottleneck Alert:** Rendering a massive Heatmap (50 symbols x 20 features) in browser DOM.  
  * *Mitigation:* Use @tanstack/react-virtual or Canvas-based rendering if elements exceed 1,000.

## **2\. Impact Analysis: Existing Architecture (Phase 16+)**

### **2.1. Architectural Impact**

| Component | Current State | Future State (Alpha Ecosystem) | Impact / Risk |
| :---- | :---- | :---- | :---- |
| **Data Pipeline** | Fetches OHLCV & streams raw ticks. | **Poseidon Upgrade:** Computes "Features" (RSI, Vol) immediately after fetch; pushes to market.features.\* Redis channel. | **Medium:** CPU load increase. Ensure FeatureWorker is async/non-blocking. |
| **Strategy Core** | Runs compiled Python strategies. | **Athena Upgrade:** Adds ExpressionEngine for parsing string formulas. Adds POST /alpha/test. | **Low:** Runs in parallel. No breaking changes to LiveRunner. |
| **Redis** | Pub/Sub for raw Ticks. | **Heavy Load:** Stores pre-computed feature vectors. | **Medium:** Memory spike. **Mitigation:** Strict TTL on feature keys. |
| **Frontend** | Dashboards for Signals/Journals. | **New Module:** /alpha/lab with Monaco Editor. | **High:** New UI libraries (@monaco-editor/react, zustand). |

### **2.2. Integration Hazards & Mitigations**

1. **Race Conditions:** Poseidon (Feature Worker) lag could lead to stale signals.  
   * *Mitigation:* Strategy must validate Feature Vector timestamp vs. Candle timestamp.  
2. **Resource Contention:** Large research backtests starving execution bot.  
   * *Mitigation:* Use separate worker queues for Research vs. Live Execution if scaling.

## **3\. Technical Strategy (Architecture Decisions)**

### **3.1. The "Smart Latch" Pattern (Data Consistency)**

* **Problem:** Strategy Core might calculate signals before Poseidon finishes updating features.  
* **Solution:** Use **Redis Streams (XADD)** with a Latch.  
  * Data Pipeline publishes raw\_candle.  
  * Poseidon consumes raw\_candle, calculates features, and appends features to the *same stream event* (or linked ID).  
  * Strategy Core only consumes messages flagged features\_complete=True.

### **3.2. AST-Based Sandboxing (Security)**

* **Problem:** eval() is dangerous for user input.  
* **Solution:** Use Python's ast module to build a Whitelist Parser.  
  * Walk the syntax tree.  
  * **Reject:** import, os, sys, \_\_class\_\_.  
  * **Allow:** BinOp (+, \-, \*, /), Call (rank, delay), Name (close, open).

### **3.3. "Sparkline-on-Type" (UX Flow)**

* **Problem:** Clicking "Run" breaks flow.  
* **Solution:** Debounced Live-Preview.  
  * As user types rank(close), wait 300ms.  
  * Send to lightweight API (last 50 candles only).  
  * Render SVG Sparkline directly inside Monaco Editor.

## **4\. Comprehensive Documentation**

### **4.1. Business Requirement Document (BRD)**

* **Problem Statement:** Quantitative researchers cannot test hypotheses fast enough. Current 80% coding overhead yields only 20% alpha discovery.  
* **Target Audience:**  
  1. **The Architect (Human):** Needs a rapid prototyping sandbox.  
  2. **AI Agents (Machine):** Need text-based interfaces to "write" strategies without file system access.  
* **Success Metrics:**  
  * **Metric 1:** *Backtest Latency* \< 500ms for standard formulas.  
  * **Metric 2:** *Data Freshness* \< 100ms lag between OANDA tick and Redis Feature update.

### **4.2. Product Requirement Document (PRD)**

* **Key Features (MVP):**  
  * **Formula Input:** Text field accepting syntax like rank(close / delay(close, 5)).  
  * **Instant Backtest:** Returns Sharpe Ratio, IC, and Cumulative Return Chart immediately.  
  * **Feature Matrix:** Color-coded grid showing real-time indicator values.  
* **User Flow (Athena):**  
  1. User types formula in Monaco Editor.  
  2. System debounces input (500ms).  
  3. Backend runs vectorized simulation on cached data.  
  4. Frontend updates Sparkline and Metric Card.  
* **Tech Stack:**  
  * **Frontend:** Next.js 16, @monaco-editor/react, recharts, zustand.  
  * **Backend:** Python 3.12, pandas, vectorbt, redis-py.

## **5\. Monetization Strategy & ROI**

### **5.1. Business Model (Value Capture)**

* **Proprietary Alpha Generation (Internal ROI):** Primary value is **Operational Efficiency**. Testing 100 strategies in the time of 1 increases probability of finding "Gold" by 100x.  
* **The "Marketplace" Model (External ROI):**  
  * **Strategy Marketplace:** Users sell **Formula Strings** (StrategyConfig.json), not black-box signals.  
  * **Validation Fee:** Charge a fee (compute cost) to "Verify" strategies on the Proving Ground.

### **5.2. Cost vs. Value**

* **Cost:** Redis memory usage increase (\~200MB for 50 symbols/features).  
* **Value:** Removes CPU bottleneck from Execution Service, allowing scaling to 1,000+ users.

## **6\. Implementation Roadmap**

### **Phase 1: Foundation (Backend Core)**

* \[ \] **Task 1.1 (Poseidon):** Implement FeatureWorker in services/data-pipeline.  
  * *Action:* Subscribe to market.candle.completed. Calculate RSI/ATR. Publish to market.features.{symbol}.  
* \[ \] **Task 1.2 (Athena):** Implement ExpressionEngine in services/strategy-core.  
  * *Action:* Build safe ast parser supporting rank, delay, ts\_max.  
* \[ \] **Task 1.3 (API):** Expose POST /api/v1/alpha/test.

### **Phase 2: Design & UI (Frontend)**

* \[ \] **Task 2.1 (Layout):** Create /alpha/lab page with MonacoEditor layout (Left sidebar, Top Editor, Bottom Metrics).  
* \[ \] **Task 2.2 (Visualization):** Build FeatureMatrix component using Grid layout. Connect to WebSocket stream.  
* \[ \] **Task 2.3 (State):** Setup useAlphaStore (Zustand) for formula state and debounce logic.

### **Phase 3: Integration & Testing**

* \[ \] **Task 3.1 (Loop):** Connect Frontend Editor \-\> API \-\> Expression Engine \-\> Result.  
* \[ \] **Task 3.2 (AI Agent):** Update AI Analyst system prompt to utilize the new formula endpoint.

## **7\. Constraints & Core Rules**

1. **NO SPAGHETTI CODE:** Do not calculate indicators inside UI components. All math happens in Python backend.  
2. **STRICT TYPES:** All new Frontend components must use TypeScript interfaces defined in frontend/lib/api/types.ts.  
3. **FAIL FAST:** If a formula is invalid, return clear error messages (e.g., "Syntax Error at char 12") for Editor highlighting.