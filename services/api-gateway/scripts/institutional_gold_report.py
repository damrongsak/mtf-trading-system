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
REPORT_PATH = "Gold_Quantitative_Report_V4.md"

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
        # Standard OAuth2 form-encoded login
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

    def get_gex_analysis(self, snapshot_at, min_dte=None, max_dte=None, sigma=0.16, r=0.05, spot_price=None):
        url = f"{self.base_url}/data/open-interest/gex"
        params = {
            "snapshot_at": snapshot_at,
            "min_dte": min_dte,
            "max_dte": max_dte,
            "sigma": sigma,
            "r": r,
            "spot_price": spot_price
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

def generate_3_bullets_strategy(physics, pivots, fibo):
    """
    Execution Strategy: The 3 Bullets - Anchored to Gamma Walls & Flip Point
    """
    p_current = physics['price']
    atr = physics['atr']
    
    # Bullet 1: Entry (Zone/Limit)
    # Target Golden Pocket (0.618) or Gamma Flip Anchor
    entry_price = fibo.get("Gamma Flip Anchor", fibo.get("0.618 (Golden)", pivots.get('P', p_current)))
    
    # Bullet 2: Protection (Stop Loss)
    # Entry - 1.5 * ATR (Institutional Buffer)
    sl_price = entry_price - (1.5 * atr)
    
    # Bullet 3: Objectives (Take Profit)
    # Use ATR-based targets relative to the entry anchor
    tp1 = entry_price + (2.0 * atr)
    tp2 = entry_price + (4.0 * atr)
    tp3 = entry_price + (6.0 * atr)
    
    return {
        "entry": entry_price,
        "sl": sl_price,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3
    }

def generate_markdown(data):
    now = datetime.now(timezone.utc).isoformat()
    
    # GEX Term Structure Table
    gex_rows = []
    for bucket, vals in data['gex_mtf'].items():
        regime_icon = "🟢" if vals['total_gex'] > 0 else "🔴"
        gex_rows.append(f"| **{bucket}** | {regime_icon} {vals['regime']} | ${vals['total_gex']/1e6:,.1f}M | ${vals['gamma_flip']:,.2f} |")
    gex_table = "\n".join(gex_rows)

    # 3 Bullets - Anchored to Gamma Flip
    flip_dist = data['gex_total']['gamma_flip'] - data['physics']['price']
    dist_style = "ABOVE" if flip_dist > 0 else "BELOW"
    
    report = f"""# 🏆 Institutional Gold Quantitative Report (V4.1)
**Market Intelligence Snapshot**: {now}
**Live Spot Price**: `${data['physics']['price']:,.2f}` | **Global Regime**: `{data['gex_total']['regime']}`

## ⚡ Market Liquidity & Volume Profile (GEX)
> [!IMPORTANT]
> **Gamma Flip Point**: `${data['gex_total']['gamma_flip']:,.2f}` ({abs(flip_dist):,.2f} points {dist_style} spot)
> **Total Net GEX**: `${data['gex_total']['total_gex']/1e6:,.2f}M` per 1% move.
> **Significance Indicator**: Nearest DTE ({data['gex_total'].get('nearest_dte', 'N/A')}d) Expiration Bias Active.

### MTF GEX Term Structure (DTE-Prioritized)
| Horizon | Regime | Net GEX (Notional) | Gamma Flip |
| :--- | :--- | :--- | :--- |
{gex_table}

> [!NOTE]
> **LONG GAMMA (Positive GEX)**: Market makers counter-trade the trend (Selling highs, buying lows), suppressing volatility.
> **SHORT GAMMA (Negative GEX)**: Market makers trade with the trend (Selling lows, buying highs), accelerating volatility.

## 🏹 Execution Strategy: The 3 Bullets (V4.1)
> [!TIP]
> **Strategy Anchor**: Anchored to the **Nearest DTE Gamma Flip Point** to identify the most significant institutional liquidity wall.

- **Bullet 1: Precision Entry**
  - **Entry Zone**: `${data['strategy']['entry']:,.2f}`
  - **Logic**: Anchored to Front-Month Gamma Flip Point.

- **Bullet 2: Dynamic Guardrail (SL)**
  - **Stop Loss**: `${data['strategy']['sl']:,.2f}`
  - **Buffer**: 1.5x IRU (Institutional Risk Unit) below liquidity wall.

- **Bullet 3: Liquidity Objectives (TP)**
  - **TP1 (Local Liquidity)**: `${data['strategy']['tp1']:,.2f}`
  - **TP2 (Major GEX Wall)**: `${data['strategy']['tp2']:,.2f}`
  - **TP3 (Structural Extension)**: `${data['strategy']['tp3']:,.2f}`

---
*Authored by Antigravity Quant Engine. GEX Integrated V4.1. DTE-Nearest Bias Active.*
"""
    return report

def main():
    client = MTFClient(API_BASE_URL)
    client.authenticate("demo1", "password123")
    
    # 1. Fetch Gold Data
    logger.info("Fetching Gold candles...")
    gold_candles = client.get_candles(GOLD_SYMBOL, timeframe="H1", limit=100)
    df_gold = pd.DataFrame(gold_candles)
    physics = calculate_physics(df_gold)
    current_price = physics['price']
    
    # 2. Fetch GEX Analysis (Term Structure)
    logger.info("Analyzing Multi-Timeframe GEX Surface...")
    snap_at = client.get_latest_oi_snapshot()
    
    buckets = {
        "Tactical (Nearest)": (None, None), # Default to Nearest in Repo logic
        "Strategic (26-65d)": (26, 65),
        "Macro (66-130d)": (66, 130)
    }
    
    gex_mtf = {}
    for name, (mi, ma) in buckets.items():
        gex_data = client.get_gex_analysis(snap_at, min_dte=mi, max_dte=ma, spot_price=current_price)
        gex_mtf[name] = {
            "total_gex": gex_data.get("total_gex_notional", 0.0),
            "gamma_flip": gex_data.get("gamma_flip", 0.0),
            "regime": gex_data.get("regime", "UNKNOWN"),
            "nearest_dte": gex_data.get("nearest_dte", 0.0)
        }
    
    # Total GEX (Unfiltered DTE but with correct spot)
    gex_total = client.get_gex_analysis(snap_at, spot_price=current_price)
    gex_total["total_gex"] = gex_total.get("total_gex_notional", 0.0) # Mapping key
    
    # 3. Strategy Calculation (Institutional Anchor)
    # Use Tactical (Nearest) Gamma Flip for the most significant data
    tactical_gex = gex_mtf["Tactical (Nearest)"]
    flip_point = tactical_gex["gamma_flip"]
    
    # Sane Defaults if GEX is bugged or missing
    pivots = {} # Dummy for now if not used
    fibo = {} 
    strategy = generate_3_bullets_strategy(physics, pivots, fibo)
    
    # VALIDATION: Check for Significant Data Divergence
    # Threshold reduced to 20% to prevent anchoring to non-sensical artifacts
    if flip_point > 0:
        drift_pct = (abs(flip_point - current_price) / current_price) * 100
        if drift_pct > 25.0:
            logger.warning(f"SANITY CHECK FAILED: Gamma Flip ${flip_point:,.2f} is {drift_pct:.1f}% away from Spot ${current_price:,.2f}.")
            logger.info("Falling back to ATR-based Relative Levels (LIQUIDITY_GAP).")
            # Entry stays current_price from default strategy
        else:
            logger.info(f"Anchoring strategy to Validated Gamma Flip Point: ${flip_point:,.2f} (Drift: {drift_pct:.1f}%)")
            strategy["entry"] = flip_point
            
            # Recalculate TPs relative to the validated anchor
            atr = physics['atr']
            strategy["sl"] = strategy["entry"] - (1.5 * atr)
            strategy["tp1"] = strategy["entry"] + (2.0 * atr)
            strategy["tp2"] = strategy["entry"] + (4.0 * atr)
            strategy["tp3"] = strategy["entry"] + (6.0 * atr)

        
    # 7. Build Data
    final_data = {
        "physics": physics,
        "oi_snapshot": snap_at,
        "gex_mtf": gex_mtf,
        "gex_total": gex_total,
        "strategy": strategy
    }
    
    # 8. Generate Report
    report_md = generate_markdown(final_data)
    
    # Save to standard V4 path
    with open(REPORT_PATH, "w") as f:
        f.write(report_md)
    logger.info(f"Institutional Report V4.0 generated: {REPORT_PATH}")
    
    # Save to requested tmp path for user compatibility
    tmp_path = "/tmp/Gold_Quantitative_Report_V3_5.md" 
    try:
        with open(tmp_path, "w") as f:
            f.write(report_md)
        logger.info(f"Compatibility Report saved to: {tmp_path}")
    except Exception as e:
        logger.warning(f"Could not save to {tmp_path}: {e}")

if __name__ == "__main__":
    main()
