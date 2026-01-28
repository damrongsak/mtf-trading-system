# **11\_frontend\_ux\_olympus.md \- Alpha Workstation Design**

Version: 1.0.0  
Theme: Olympus Pro (Dark/Glassmorphism)

## **1\. Overview**

The frontend must evolve to support the two new core capabilities:

1. **Athena (Alpha Lab):** A text-based formula playground for researching signals.  
2. **Poseidon (Data Monitor):** A real-time matrix view of the Feature Store health.

## **2\. Module A: Athena Alpha Lab (/alpha/lab)**

**Concept:** A "VS Code" for trading strategies. The user writes a mathematical expression, hits "Test", and immediately sees the metric performance.

### **2.1. Layout Structure**

* **Left Sidebar (Library):** List of saved Alphas (e.g., MOM\_101, MEANREV\_05).  
* **Top Pane (The Workbench):**  
  * **Formula Editor:** A Monaco Editor (VS Code style) input area.  
  * *Placeholder:* rank(close / delay(close, 5))  
  * *Syntax Highlighting:* Functions (rank, delay) in Blue, Variables (close) in Green.  
* **Bottom Pane (The Feedback Loop):**  
  * **Tab 1: Cumulative Return:** Line chart comparing Strategy vs Benchmark (Buy & Hold).  
  * **Tab 2: IC Decay:** Bar chart showing Information Coefficient over 1-5 days.  
  * **Tab 3: Quant Metrics:** Card grid (Sharpe, Turnover, MaxDD).

### **2.2. Key Components**

#### **FormulaInput**

A wrapper around @monaco-editor/react.

* **Behavior:** Auto-complete for available fields (open, volatility) and operators.  
* **Action:** Cmd+Enter to run the backtest (calls POST /api/v1/alpha/test).

#### **MetricCard**

A dense, high-contrast display for key stats.

* **Design:** Glassmorphic card, green text for positive Sharpe, red for high Drawdown.  
* **Data:**  
  * *Sharpe:* 2.45  
  * *IC (Info Coeff):* 0.06 (The "Golden Metric" for Quants)  
  * *Turnover:* 15%

## **3\. Module B: Poseidon Feature Matrix (/data/features)**

**Concept:** A "Server Room" monitoring dashboard. It visualizes the invisible "Feature Store" running on Redis.

### **3.1. Visualization: The "Liveness" Heatmap**

Instead of a simple table, use a Grid Heatmap to show data freshness.

* **Rows:** Symbols (BTC, ETH, SOL, XAU).  
* **Columns:** Features (RSI\_14, BB\_WIDTH, Z\_SCORE, VOLATILITY).  
* **Cell Color:**  
  * 🟢 **Bright Green:** Calculated \< 1s ago.  
  * 🟡 **Yellow:** Calculated \< 5s ago.  
  * 🔴 **Red:** Stale (\> 10s).  
  * ⚫ **Grey:** Missing.

### **3.2. User Interaction**

* **Hover:** Hovering over a cell shows the raw value (e.g., RSI: 72.4).  
* **Click:** Clicking a cell opens a mini-chart modal showing that specific feature's history over the last hour.

## **4\. Navigation Updates**

Update the Sidebar (frontend/components/Sidebar.tsx):

1. **Research (Group)**  
   * 🧪 **Alpha Lab** (/alpha/lab) \- *New*  
   * 📜 **Strategies** (/strategies) \- *Existing*  
   * 📓 **Backtest** (/backtest) \- *Existing*  
2. **Data (Group)**  
   * 🌊 **Feature Matrix** (/data/features) \- *New*  
   * 📊 **Market Watch** (/dashboard) \- *Existing*

## **5\. Technology Stack (Frontend)**

* **Code Editor:** @monaco-editor/react (Standard for web-based IDEs).  
* **Charts:** recharts (Already installed).  
* **State:** zustand (For managing the "Currently Editing Alpha").  
* **Tables:** @tanstack/react-table (For the heavy Feature Matrix).

## **6\. Pro Tip: UX "Magic"**

"The Instant Feedback Loop"  
When the user types a formula in Athena, do not wait for them to click "Run".  
Implement a Debounce (500ms). If the formula is valid syntactically, run a "Light Backtest" (last 100 candles) automatically and show a mini sparkline next to the editor. This makes the research process feel "alive".