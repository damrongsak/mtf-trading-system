# **MTF Olympus: Core Module Specifications (Deep Dive)**

Target Audience: System Architects, Backend Engineers, Quant Developers  
Version: 1.0.0  
Status: Approved for Implementation

## **🏗️ Module 1: The Strategy Foundry (Standardization Engine)**

Reference: Trading Systems and Methods (Kaufman)  
Goal: To transform "Strategy Creation" from writing code to assembling standardized logic blocks.

### **1.1 The Architecture of a "Block"**

Instead of writing a Python script, a strategy is a JSON configuration referencing pre-compiled "Logic Blocks" in the backend.

#### **Abstract Interface (Python)**

class LogicBlock(ABC):  
    @abstractmethod  
    def calculate(self, data: pd.DataFrame, params: dict) \-\> pd.Series:  
        """Returns a normalized signal (-1.0 to 1.0)"""  
        pass

    @abstractmethod  
    def validate\_params(self, params: dict) \-\> bool:  
        """Ensures parameters are within safe bounds"""  
        pass

### **1.2 The Logic Block Library (Phase 1\)**

These blocks are derived from Kaufman’s standard definitions:

| Block ID | Name | Parameters | Logic Source |
| :---- | :---- | :---- | :---- |
| TREND\_AMA | Adaptive Moving Average | period\_fast, period\_slow, efficiency\_ratio | Kaufman Ch. 17 |
| VOL\_ATR | Volatility Breakout | lookback, multiplier | Kaufman Ch. 9 |
| MOM\_RSI | RSI Regime | period, upper\_bound, lower\_bound | Kaufman Ch. 6 |
| STRUCT\_SMC | Smart Money Context | fvg\_threshold, ob\_mitigation | Project MTF Internal |

### **1.3 The StrategyConfig Schema (JSON)**

This is the "Source Code" that gets shared in the Marketplace.

{  
  "meta": {  
    "name": "Gold\_Trend\_SMC\_Hybrid",  
    "version": "1.0.2",  
    "author\_id": "uuid-..."  
  },  
  "logic\_pipeline": \[  
    {  
      "id": "block\_1",  
      "type": "TREND\_AMA",  
      "params": { "period\_fast": 2, "period\_slow": 30 },  
      "weight": 0.6  
    },  
    {  
      "id": "block\_2",  
      "type": "STRUCT\_SMC",  
      "params": { "fvg\_threshold": 0.001 },  
      "weight": 0.4  
    }  
  \],  
  "confluence\_rules": {  
    "operator": "AND",  
    "threshold": 0.7  
  },  
  "risk\_profile": {  
    "module": "RISK\_MINIMAX",  
    "max\_drawdown\_limit": 0.05  
  }  
}

## **🛡️ Module 3: The Risk Citadel (Game Theory Engine)**

Reference: Game Theory with Engineering Applications (Bauso) & Quantitative Equity Portfolio Management  
Goal: To implement a mathematical firewall using Minimax Regret and Portfolio Risk Parity.

### **3.1 Algorithm A: Minimax Regret (Single Trade)**

We treat the market as an "Adversarial Player" trying to maximize our loss.

Formula:  
$$ Regret(d, s) \= \\max\_{s'} V(d, s') \- V(d, s) $$  
Where:

* $d$: Decision (Buy/Sell/Hold)  
* $s$: State (Bull/Bear/Chop)  
* $V$: Value Function (PnL)

**Implementation Logic (Python):**

1. **Hypothesis Generation:** Simulate 3 scenarios for the next 4 hours:  
   * $s\_1$: Breakout (Vol \+200%)  
   * $s\_2$: Reversal (Price hits SL)  
   * $s\_3$: Chop (Decay)  
2. **Regret Calculation:** Calculate the PnL of our Trade ($d$) in the *worst* of these scenarios.  
3. **Constraint Check:**  
   max\_regret \= calculate\_worst\_case\_loss(trade, market\_scenarios)  
   if max\_regret \> user.pain\_threshold\_usd:  
       return REJECT(reason="Minimax Constraint Violated")

### **3.2 Algorithm B: Inverse Volatility Risk Parity (Portfolio)**

For users running multiple strategies (Fund Mode).

**Goal:** Ensure Strategy A (High Vol) doesn't dominate Strategy B (Low Vol).

Formula:  
$$ w\_i \= \\frac{1/\\sigma\_i}{\\sum\_{j=1}^{N} (1/\\sigma\_j)} $$  
Where:

* $w\_i$: Allocation Weight for Strategy $i$  
* $\\sigma\_i$: Rolling 20-day Volatility of Strategy $i$

## **🧠 Module 5: The AI Coach (Psychology Engine)**

Reference: The Mental Game of Trading (Tendler) & The Daily Trading Coach (Steenbarger)  
Goal: To detect and correct "C-Game" performance using an AI Agent.

### **5.1 The Mental State Machine (FSM)**

The User Session can be in one of 3 states. Transitions are triggered by **Behavioral Metrics**.

| State | Trigger Conditions | System Privileges |
| :---- | :---- | :---- |
| **A-GAME** | WinRate \> 40% AND AvgHoldTime stable | Full Access |
| **B-GAME** | WinRate drops OR TimeOnChart \> 4 hrs | Warning Issued |
| **C-GAME** | LossStreak \> 3 OR Drawdown \> DailyLimit | **Execution Locked** |

### **5.2 The "Steenbarger" Prompt Template**

When the user is in **B-Game** or **C-Game**, the AI Analyst switches from "Market Observer" to "Performance Coach".

**System Prompt:**

"You are Dr. Brett Steenbarger. Your goal is NOT to give signals, but to fix the trader's mental state.

**Context:**

* User State: C-GAME (Tilt Detected)  
* Trigger: 3 consecutive losses on Gold M5.  
* Deviation: User is doubling lot size (Martingale).

**Action:**

1. Acknowledge the frustration (Empathy).  
2. Ask the user to identify their 'Mental Hand History' trigger.  
3. Refuse to unlock the trading terminal until they reply with a logical correction."

### **5.3 Mental Hand History Data Structure**

Stored in mental\_hand\_histories table (see Data Model).

Entry:  
  trigger: "Price swept my SL by 1 pip and reversed."  
  flawed\_thought: "The broker is hunting stops. I need to widen my SL."  
  emotion: "Anger (8/10)"  
  correction: "Liquidity sweeps are normal market mechanics. My entry was simply too early. Widening SL increases risk, which violates my Minimax rule."  
  logic\_check: PASSED  
