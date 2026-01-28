# **📜 Task: Implement Alpha 001 (Hybrid Momentum \+ SMC)**

Target: Antigravity AI Code / Senior Developer  
Context: Olympus Phase 2 (Alpha Ecosystem)  
Priority: High (P0)

## **1\. Objective**

Implement the first "Hybrid Alpha" strategy that demonstrates the power of the new **Athena Ecosystem**. This strategy combines **Statistical Momentum** (via a string formula) with **Market Structure** (Order Blocks) to increase execution precision.

## **2\. Architecture Overview**

The implementation requires two distinct components:

1. **The Athena Engine (engines/athena.py):** A helper class that parses and evaluates mathematical formulas (e.g., rank(close / delay(close, 10))) safely.  
2. **The Strategy Logic (strategies/hybrid\_alpha\_smc.py):** The python wrapper that calls Athena for the "Bias" and SMC for the "Entry".

## **3\. Implementation Steps**

### **Step 1: Implement the Athena Engine (The Prerequisite)**

File: services/strategy-core/app/engines/athena.py  
Responsibility:

* Accept a string formula and a Pandas DataFrame.  
* Use pandas and numpy to calculate the result.  
* **Crucial:** Must support rank, delay, ts\_max, ts\_min, log, abs operators.  
* **Security:** Use ast or restricted eval environment (no import os).

**Snippet (Concept):**

class AthenaEngine:  
    def evaluate(self, formula: str, df: pd.DataFrame) \-\> float:  
        \# 1\. Build Context (open, high, low, close, volume)  
        \# 2\. Inject Helper Functions (rank, delay)  
        \# 3\. Execute Formula  
        \# 4\. Return the latest value (iloc\[-1\])  
        pass

### **Step 2: Implement the Hybrid Strategy Logic**

File: services/strategy-core/app/strategies/hybrid\_alpha\_smc.py  
Logic Flow:

1. **Calculate Alpha Score:**  
   * Formula: "rank(close / delay(close, 10))" (Relative Momentum).  
   * Use AthenaEngine to get the score (0.0 to 1.0).  
   * **Filter:** If score \< 0.8, return None (Skip trade).  
2. **Find Entry Trigger (SMC):**  
   * Fetch smc\_analysis from data\_manager.  
   * Look for **Bullish Order Blocks** below current price.  
3. **Execute:**  
   * If Price is inside/near Order Block AND Alpha is Bullish \-\> **LONG**.  
   * **Stop Loss:** Below the Order Block.

### **Step 3: Register Strategy**

File: services/strategy-core/app/registry.py  
Action:

* Import hybrid\_alpha\_smc.  
* Add to StrategyRegistry.  
* Metadata key: HYBRID\_ALPHA\_V1.

## **4\. Acceptance Criteria**

1. **Unit Test:** Running test\_hybrid\_alpha.py should mock a dataframe where close is rising (Momentum) and price hits an Order Block, resulting in a valid LONG signal.  
2. **Safety:** The AthenaEngine must raise an error if a malicious formula (e.g., import os) is passed.  
3. **Performance:** The Alpha Score calculation should take \< 50ms.

## **5\. Reference Code (Logic)**

async def hybrid\_alpha\_smc(state, data\_manager):  
    \# Initialize Engine (In prod, inject this dependency)  
    engine \= AthenaEngine()  
      
    \# 1\. Check Alpha (The "Wind")  
    formula \= "rank(close / delay(close, 10))"  
    \# Note: data\_manager.get\_df(symbol) must return full OHLCV  
    df \= data\_manager.get\_data(state.symbol)  
    alpha\_score \= engine.evaluate(formula, df)  
      
    if alpha\_score \< 0.8: return None

    \# 2\. Check Structure (The "Wall")  
    smc \= data\_manager.get\_smc(state.symbol)  
    price \= df\['close'\].iloc\[-1\]  
      
    \# ... Match Price with Order Block ...  
