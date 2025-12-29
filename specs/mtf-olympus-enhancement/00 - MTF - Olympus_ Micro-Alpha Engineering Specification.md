# **MTF \- Olympus: Micro-Alpha Engineering Specification**

Target Audience: Quant Devs, AI Engineers (Antigravity), Full-stack Devs  
Focus: Lean Implementation of Market Microstructure & AI Prediction

## **1\. Executive Summary**

Olympus is a Quantitative Fund Platform designed for retail fund owners. It leverages **Market Microstructure** signals—specifically **OBI** and **OFI**—to predict price drift in the next 5-10 seconds. This document provides a lean architectural blueprint for an MVP, prioritizing a "Statistical-First" approach before scaling to Deep Learning.

## **2\. Core Theory: The "Whale" Logic**

### **2.1 Inventory-Based Pricing**

Prices in illiquid or volatile markets move due to **Market Maker (MM) Inventory Management**, not just random sentiment.

* **Inventory Risk:** MMs adjust prices (Quote Skewing) to stay neutral.  
* **Reservation Price:** $P\_{res} \= P\_{mid} \- \\gamma \\cdot q$ (where $q$ is inventory and $\\gamma$ is risk aversion).  
* **Goal:** Olympus predicts where the MM will "skew" the price next based on incoming flow imbalance.

### **2.2 Why This Works (The Deterministic Logic)**

The assumption that OBI/OFI can predict price is based on **Mechanical Necessity**, not social psychology:

1. **Structural Requirement:** MMs are service providers, not speculators. If they are hit by a large buy order, their inventory becomes "Short." They are *forced* by their algorithms to raise prices to discourage further buying and attract sellers.  
2. **Adverse Selection (Toxic Flow):** MMs fear "Informed Traders" (insiders). When they see aggressive OFI, they assume someone knows something they don't and reflexively move their quotes to avoid being "sniped."  
3. **Deterministic Bots:** In Crypto, most MMs are bots running predictable mathematical models (like Avellaneda-Stoikov). If we see the same input (Order Flow), we can predict the output (Quote Adjustment).

## **3\. Lean Architecture (MVP Phase)**

To minimize resources and complexity:

1. **Data Source:** Use **CCXT** (Python) for unified WebSocket access.  
2. **Compute:** Calculate OBI/OFI on-the-fly (In-memory). No heavy database needed for real-time signals.  
3. **Inference:** Start with **Heuristic Rules** or **Z-Score Thresholds** (CPU-friendly).  
4. **Backend:** FastAPI (Python) for serving predictions via WebSockets to Next.js.

## **4\. Feature Engineering: OBI & OFI**

### **4.1 Order Book Imbalance (OBI)**

Measures static pressure. Formula: $OBI \= \\frac{\\sum V\_{bid} \- \\sum V\_{ask}}{\\sum V\_{bid} \+ \\sum V\_{ask}}$

### **4.2 Order Flow Imbalance (OFI)**

Measures dynamic pressure from aggressive Takers.

\# Lean Implementation for Olympus Alpha Module  
class MicroAlphaEngine:  
    def \_\_init\_\_(self, depth=10):  
        self.depth \= depth  
        self.prev\_best\_bid, self.prev\_bid\_size \= 0, 0  
        self.prev\_best\_ask, self.prev\_ask\_size \= 0, 0

    def get\_obi(self, bids, asks):  
        b\_vol \= sum(\[b\[1\] for b in bids\[:self.depth\]\])  
        a\_vol \= sum(\[a\[1\] for a in asks\[:self.depth\]\])  
        return (b\_vol \- a\_vol) / (b\_vol \+ a\_vol) if (b\_vol \+ a\_vol) \> 0 else 0

    def get\_ofi(self, best\_bid, bid\_size, best\_ask, ask\_size):  
        \# Bid side impact logic  
        if best\_bid \> self.prev\_best\_bid: e\_b \= bid\_size  
        elif best\_bid \< self.prev\_best\_bid: e\_b \= \-self.prev\_bid\_size  
        else: e\_b \= bid\_size \- self.prev\_bid\_size

        \# Ask side impact logic  
        if best\_ask \< self.prev\_best\_ask: e\_a \= ask\_size  
        elif best\_ask \> self.prev\_best\_ask: e\_a \= \-self.prev\_ask\_size  
        else: e\_a \= ask\_size \- self.prev\_ask\_size

        self.prev\_best\_bid, self.prev\_bid\_size \= best\_bid, bid\_size  
        self.prev\_best\_ask, self.prev\_ask\_size \= best\_ask, ask\_size  
        return e\_b \- e\_a

## **5\. Phase 2 Alternative: Statistical Engine (Lean Path)**

Instead of a heavy LSTM, use a **Weighted Threshold Model**.

def generate\_lean\_signal(obi, ofi\_history):  
    \# Detect abnormal aggression via Z-score  
    mean\_ofi \= np.mean(ofi\_history)  
    std\_ofi \= np.std(ofi\_history)  
    z\_score \= (ofi\_history\[-1\] \- mean\_ofi) / (std\_ofi \+ 1e-9)  
      
    \# Threshold Logic  
    if obi \> 0.7 and z\_score \> 2.0:  
        return {"prediction": "UP", "confidence": min(z\_score/5, 1.0)}  
    elif obi \< \-0.7 and z\_score \< \-2.0:  
        return {"prediction": "DOWN", "confidence": min(abs(z\_score)/5, 1.0)}  
    return {"prediction": "NEUTRAL", "confidence": 0}

## **6\. Theoretical Limitations & Risks**

### **6.1 Fake Spoofing (OBI Manipulation)**

Large players place massive orders in the LOB and cancel them before execution to create a "Pressure Illusion."

* **Impact:** OBI becomes extremely positive, signaling a price rise, but the price drops when the "fake" bids vanish.  
* **Olympus Mitigation:** Weigh OFI (actual trades) heavier than OBI. Use **Cancel Ratio** tracking to detect flickering orders.

### **6.2 Latency Race (The Speed Limit)**

If the MM's server responds in 5ms but Olympus's sensor takes 50ms, the price has already moved before the signal reaches the UI.

* **Impact:** Signal "decay." The prediction becomes a historical record rather than a forecast.

### **6.3 Liquidity Vacuums**

In extreme volatility, MMs may withdraw all quotes (VPIN spike).

* **Impact:** OBI/OFI calculations become erratic as there is no "opposite side" to trade against.

## **7\. Further Research Keywords**

To deepen the Olympus engine, search for:

* **"Adverse Selection in Limit Order Books"**  
* **"Kyle's Model of Market Microstructure"**  
* **"High-Frequency Lead-Lag Effects"**  
* **"V-PIN: Volume-Weighted Probability of Informed Trading"**

## **8\. Implementation Roadmap**

1. **Phase 1:** Setup CCXT WebSocket & MicroAlphaEngine.  
2. **Phase 2:** Deploy **Heuristic Engine** (Section 5\) for immediate Retail UI feedback.  
3. **Phase 3:** Log features to SQLite for **LSTM Upgrade** (Phase 4).

*Developed for MTF \- Olympus Project*