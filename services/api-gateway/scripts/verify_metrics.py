import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VerifyMetrics")

BASE_URL = "http://localhost:8000/api/v1"

def verify_metrics():
    # 1. Login (Reuse credentials from verify_plugin_flow or create temp)
    # Assuming user exists from previous flow 'testuser_plugin' or similar
    # For simplicity, let's use the 'trader' user or create one if needed?
    # Actually, backtest endpoint might be protected. Let's register a temp user.
    
    email = f"metrics_{requests.utils.quote('test')}@example.com"
    username = f"metrics_user_{requests.utils.quote('test')}"
    password = "password123"
    
    # Try login first
    logger.info("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/token", data={
        "username": email,
        "password": password
    })
    
    token = None
    if resp.status_code == 200:
        token = resp.json()["auth"]["access_token"]
    else:
        # Register
        logger.info("Registering new user...")
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": email,
            "username": username,
            "password": password
        })
        if reg_resp.status_code == 200:
             # Login again to get token (register returns token too but let's be consistent)
             token = reg_resp.json()["auth"]["access_token"]
        else:
             logger.error(f"Registration failed: {reg_resp.text}")
             if "already registered" in reg_resp.text:
                  # Force login again if we just failed because it existed but first login failed (maybe wrong pass)
                  pass 
             else:
                  sys.exit(1)

    if not token:
        logger.error("Could not obtain token.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Run Backtest
    logger.info("Running Backtest on XAU/USD...")
    
    # Use simple SMA strategy
    code = """
import vectorbt as vbt
import pandas as pd
import numpy as np

def strategy(data, params=None):
    close = data['close']
    fast = vbt.MA.run(close, 10)
    slow = vbt.MA.run(close, 20)
    entries = fast.ma_crossed_above(slow)
    exits = fast.ma_crossed_below(slow)
    return entries, exits
"""
    
    payload = {
        "code": code,
        "symbol": "XAU/USD",
        "timeframe": "D", # Using Daily to match our seeded bench data resolution easily
        "start_date": "2024-01-01T00:00:00", # Placeholder, logic uses DB availability
        "end_date": "2024-12-31T00:00:00",
        "initial_capital": 10000,
        "fees": 0.0,
        "slippage": 0.0
    }
    
    # We need to find a date range that actually has data.
    # The seed_plugin seeded ~365 days back from TODAY.
    # So using 'D' timeframe and recent dates should work if XAU/USD candles exist.
    # Wait, seed_benchmark seeded D1 candles for XAU/USD. 
    # But does XAU/USD have M1/H1 candles for the backtest? 
    # The 'custom' backtest uses `fetch_data_from_db`. 
    # If I only seeded 'D' candles, I MUST request 'D' timeframe.
    
    # Update dates to be dynamic (last 100 days)
    import datetime
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(days=100)
    
    payload["start_date"] = start_dt.isoformat()
    payload["end_date"] = end_dt.isoformat()
    
    resp = requests.post(f"{BASE_URL}/backtest/custom", json=payload, headers=headers)
    
    if resp.status_code != 200:
        logger.error(f"Backtest failed: {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    logger.info(f"Full Response: {json.dumps(data, indent=2)}")
    
    metrics = data.get("metrics") or {}
    trades = data.get("trades") or []
    
    logger.info(f"Trades Count: {len(trades)}")
    
    logger.info("Backtest Complete. Metrics:")
    logger.info(json.dumps(metrics, indent=2))
    
    # 3. Verify Alpha/Beta
    alpha = metrics.get("alpha", 0.0)
    beta = metrics.get("beta", 0.0)
    
    if alpha != 0.0 or beta != 0.0:
        logger.info(f"✅ SUCCESS: Alpha ({alpha}) and Beta ({beta}) are non-zero (or at least one is).")
    else:
        # It is possible to be exactly 0 if correlation is 0 or returns are identical (unlikely with random noise)
        # But if benchmark is working, Beta should be close to 1.0 or non-zero.
        logger.warning(f"⚠️ WARNING: Alpha ({alpha}) and Beta ({beta}) are ZERO. Benchmark might not be aligned.")

if __name__ == "__main__":
    verify_metrics()
