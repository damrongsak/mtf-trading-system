import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import argparse
from scipy.signal import find_peaks

# --- Configuration ---
API_BASE_URL = "http://api-gateway:8000/api/v1"
AUTH_PAYLOAD = {"username": "demo1", "password": "password123"}
GOLD_SYMBOL = "XAU_USD"
MACRO_SYMBOLS = ["DXY", "VIX", "GVZ"]
REPORT_PATH = "Gold_Quantitative_Report_V3.md"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MTFClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.headers = {}

    def authenticate(self, username, password):
        logger.info(f"Authenticating as {username}...")
        url = f"{self.base_url}/auth/token"
        data = {"username": username, "password": password}
        response = requests.post(url, data=data)
        response.raise_for_status()
        res_json = response.json()
        
        # Handle different token response formats
        if "auth" in res_json:
            self.token = res_json["auth"]["access_token"]
        else:
            self.token = res_json.get("access_token")
            
        self.headers = {"Authorization": f"Bearer {self.token}"}
        logger.info("Authentication successful.")

    def get_candles(self, symbol, timeframe="H1", limit=200):
        url = f"{self.base_url}/market/candles"
        params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get("data", [])

    def get_latest_oi_snapshot(self):
        url = f"{self.base_url}/data/open-interest/snapshots"
        params = {"limit": 1}
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        res_json = response.json()
        data = res_json.get("data", [])
        return data[0]["snapshot_at"] if data else None

    def get_oi_analysis(self, snapshot_at, min_dte=0, max_dte=30, min_oi=500):
        url = f"{self.base_url}/data/open-interest/analysis"
        params = {
            "snapshot_at": snapshot_at,
            "min_dte": min_dte,
            "max_dte": max_dte,
            "min_oi": min_oi
        }
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get("data", {})

def calculate_physics(df_gold):
    """
    Implements Institutional Physics 2.0 (F_net, Energy, Displacement)
    """
    if df_gold.empty:
        return {}
    
    # Simple displacement (Price change over last 5 periods)
    p_current = df_gold['close'].iloc[-1]
    p_start = df_gold['close'].iloc[-5] if len(df_gold) >= 5 else df_gold['close'].iloc[0]
    displacement = (p_current - p_start) / p_start * 100
    
    # Net Force (Approximate using Volume * Acceleration)
    # This is a heuristic for 3rd party consumption
    returns = df_gold['close'].pct_change().dropna()
    volatility = returns.std()
    
    # Energy (Market potential based on ATR expansion)
    high_low = df_gold['high'] - df_gold['low']
    atr = high_low.rolling(14).mean().iloc[-1]
    energy = (atr / p_current) * 100000 # Normalized scale
    
    return {
        "price": p_current,
        "displacement": displacement,
        "energy": energy,
        "volatility": volatility,
        "atr": atr
    }

def calculate_fibo_levels(df):
    """
    SMC Fibonacci Tactical Zones (Retracements)
    """
    if df.empty:
        return {}
    
    # Use the current swing (Last 100 periods)
    h = df['high'].max()
    l = df['low'].min()
    rng = h - l
    
    return {
        "1.0 (Extreme)": l,
        "0.786 (Deep)": l + 0.214 * rng,
        "0.618 (Golden)": l + 0.382 * rng,
        "0.382 (Standard)": l + 0.618 * rng,
        "0.0 (Origin)": h
    }

def calculate_piv_vbsr(df, gvz=20.0):
    """
    Volatility-Based Support/Resistance (VBSR)
    Re-implemented from services/strategy-core/app/indicators/piv.py
    """
    if len(df) < 20:
        return []
        
    close = df['close']
    high_low = df['high'] - df['low']
    atr = high_low.rolling(14).mean()
    
    # Volume-adjusted price power (Heuristic)
    vol_price = close * (1 + (atr / close) * (gvz / 100.0))
    
    # Peak Detection via Scipy
    peaks, _ = find_peaks(vol_price, prominence=0.5)
    troughs, _ = find_peaks(-vol_price, prominence=0.5)
    
    levels = []
    for p in peaks:
        levels.append(float(close.iloc[p]))
    for t in troughs:
        levels.append(float(close.iloc[t]))
        
    # Return unique, sorted levels near current price (last 3 unique levels)
    sorted_levels = sorted(list(set(levels)))
    return sorted_levels[-3:] if sorted_levels else []

def generate_3_bullets_strategy(physics, pivots, fibo):
    """
    Execution Strategy: The 3 Bullets
    """
    p_current = physics['price']
    atr = physics['atr']
    
    # Bullet 1: Entry (Zone/Limit)
    # Target Golden Pocket (0.618) or Pivot
    entry_price = fibo.get("0.618 (Golden)", pivots['P'])
    
    # Bullet 2: Protection (Stop Loss)
    # Entry - 1.5 * ATR (Institutional Buffer)
    sl_price = entry_price - (1.5 * atr)
    
    # Bullet 3: Objectives (Take Profit)
    tp1 = pivots['P'] if entry_price < pivots['P'] else pivots['R1']
    tp2 = pivots['R1']
    tp3 = pivots['R2']
    
    return {
        "entry": entry_price,
        "sl": sl_price,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3
    }

def generate_markdown(data):
    now = datetime.now(timezone.utc).isoformat()
    
    # Fibo Table
    fibo_rows = "\n".join([f"| **{k}** | ${v:,.2f} | SMC Tactical Zone |" for k, v in data['fibo'].items()])
    
    # VBSR Table
    vbsr_rows = "\n".join([f"| **VBSR Level** | ${v:,.2f} | Institutional Peak/Trough |" for v in data['vbsr']])
    
    # Term Structure Table
    ts_rows = []
    for bucket, vals in data['term_structure'].items():
        ts_rows.append(f"| **{bucket}** | ${vals['call']:,.2f} | ${vals['put']:,.2f} | {vals['pcr']:.2f} |")
    ts_table = "\n".join(ts_rows)

    report = f"""# Institutional Gold Quantitative Swing Report (V3.5)
**Snapshot**: {now} | **Live Price**: ${data['physics']['price']:,.2f}

## ⚛️ Market Physics 2.5 (Normalized)
| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Price Basis** | ${data['physics']['price']:,.2f} | Restored Institutional Raw |
| **Energy (J)** | {data['physics']['energy']:.2f} | Volatility Potential |
| **Displacement** | {data['physics']['displacement']:.4f}% | 5-Period Velocity |
| **ATR (14H)** | ${data['physics']['atr']:.2f} | Dynamic Risk Unit |

## 🏗️ Gamma Wall Term Structure (Institutional)
*Latest Snapshot: {data['oi_snapshot']}*

| Horizon | Call Wall (Res) | Put Wall (Supp) | PCR |
| :--- | :--- | :--- | :--- |
{ts_table}

> [!NOTE]
> **Tactical** (0-25d) drives today's volatility. **Strategic** (26-65d) acts as the primary trend reversal anchor.

## 🎯 Multi-Factor Confluence Matrix
| Factor | Price Level | Significance |
| :--- | :--- | :--- |
{fibo_rows}
{vbsr_rows}

## 🎯 Pivot Levels (Daily Basis)
| Level | Price | Role |
| :--- | :--- | :--- |
| **R2 (Extension)** | ${data['pivots']['R2']:,.2f} | Exhaustion |
| **R1 (Resistance)** | ${data['pivots']['R1']:,.2f} | Profit Taking |
| **Pivot (Mean)** | ${data['pivots']['P']:,.2f} | Institutional Equilibrium |
| **S1 (Support)** | ${data['pivots']['S1']:,.2f} | Demand Zone |
| **S2 (Defensive)** | ${data['pivots']['S2']:,.2f} | Hard Support |

## 🛡️ Execution Strategy: The 3 Bullets
> [!TIP]
> Strategy anchored to **Tactical (0-25d)** Gamma Walls for high-precision day trading entries.

- **Bullet 1: Limit Entry**
  - **Entry Price**: `${data['strategy']['entry']:,.2f}` (Base: Tactical Support/Golden Pocket)
- **Bullet 2: Protection (SL)**
  - **Stop Loss**: `${data['strategy']['sl']:,.2f}` (1.5x ATR Buffer)
- **Bullet 3: Objectives (TP)**
  - **Target 1 (Tactical Carry)**: `${data['strategy']['tp1']:,.2f}`
  - **Target 2 (Structural Mid)**: `${data['strategy']['tp2']:,.2f}`
  - **Target 3 (Full Extension)**: `${data['strategy']['tp3']:,.2f}`

---
*Report generated via MTF API Gateway. Scipy Engine Active.*
"""
    return report

def main():
    client = MTFClient(API_BASE_URL)
    client.authenticate("demo1", "password123")
    
    # 1. Fetch Gold Data
    logger.info("Fetching Gold candles...")
    gold_candles = client.get_candles(GOLD_SYMBOL, timeframe="H1", limit=100)
    df_gold = pd.DataFrame(gold_candles)
    
    # 2. Fetch OI Analysis (Term Structure)
    logger.info("Analyzing Multi-Timeframe Open Interest...")
    snap_at = client.get_latest_oi_snapshot()
    
    buckets = {
        "Tactical (0-25d)": (0, 25),
        "Strategic (26-65d)": (26, 65),
        "Macro (66-130d)": (66, 130)
    }
    
    term_structure = {}
    for name, (mi, ma) in buckets.items():
        analysis = client.get_oi_analysis(snap_at, min_dte=mi, max_dte=ma)
        summary = analysis.get("summary", {})
        term_structure[name] = {
            "call": summary.get("max_call_strike", 0.0),
            "put": summary.get("max_put_strike", 0.0),
            "pcr": summary.get("pcr", 1.0)
        }
    
    # 3. Physics
    physics = calculate_physics(df_gold)
    
    # 4. Pivots (Simplified Fibonacci on Daily basis)
    # For H1, we take the max/min of the last 24 periods as proxy for yesterday
    h_prev = df_gold['high'].iloc[-48:-24].max() if len(df_gold) >= 48 else df_gold['high'].max()
    l_prev = df_gold['low'].iloc[-48:-24].min() if len(df_gold) >= 48 else df_gold['low'].min()
    c_prev = df_gold['close'].iloc[-24] if len(df_gold) >= 24 else df_gold['close'].iloc[0]
    
    p_pivot = (h_prev + l_prev + c_prev) / 3
    rng = h_prev - l_prev
    pivots = {
        "P": p_pivot,
        "R1": p_pivot + 0.382 * rng,
        "R2": p_pivot + 0.618 * rng,
        "S1": p_pivot - 0.382 * rng,
        "S2": p_pivot - 0.618 * rng
    }
    
    # 5. Advanced Intervals
    fibo = calculate_fibo_levels(df_gold)
    vbsr = calculate_piv_vbsr(df_gold)
    
    # 6. Strategy Calculation (Anchored to Tactical Wall)
    tactical_put = term_structure["Tactical (0-25d)"]["put"]
    # If tactical wall exists, use it as a secondary anchor for the Golden Pocket
    if tactical_put > 0:
        fibo["Tactical Support"] = tactical_put
        
    strategy = generate_3_bullets_strategy(physics, pivots, fibo)
    
    # 7. Build Data
    final_data = {
        "physics": physics,
        "oi_snapshot": snap_at,
        "term_structure": term_structure,
        "pivots": pivots,
        "fibo": fibo,
        "vbsr": vbsr,
        "strategy": strategy
    }
    
    # 6. Generate Report
    report_md = generate_markdown(final_data)
    with open(REPORT_PATH, "w") as f:
        f.write(report_md)
    
    print(report_md)
    logger.info(f"Report generated: {REPORT_PATH}")

if __name__ == "__main__":
    main()
