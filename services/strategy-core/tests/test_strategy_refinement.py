import pytest
from fastapi.testclient import TestClient
from app.main import app
import pandas as pd
import numpy as np

client = TestClient(app)

def test_rsi_calculation():
    # Simple uptrend
    close = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
    response = client.post("/calculate/rsi", json={"close": close, "window": 14})
    assert response.status_code == 200
    data = response.json()
    assert len(data["values"]) == 15
    # First 14 should be None usually or have initial value depending on impl
    # vectorbt RSI usually needs window+1 to start showing values? or exact window?
    # Let's just check structure for now.
    assert "values" in data

def test_smc_enhanced():
    # Construct a data pattern with a liquidity sweep
    # Sweep High: Price goes above recent high then closes below
    
    # 0: High 100
    # 1: High 90
    # 2: High 95
    # 3: High 105 (Sweep), Close 98 (Below 100? No, recent high is 100)
    # 4: High 90
    
    open_data =  [100, 100, 100, 100, 100, 100, 100]
    high_data =  [100, 100, 100, 100, 100, 105, 100] 
    low_data =   [ 90,  90,  90,  90,  90,  90,  90]
    close_data = [ 95,  95,  95,  95,  95,  95,  95] # Close below 100
    volume =     [100, 100, 100, 100, 100, 500, 100] # Volume spike on sweep
    
    payload = {
        "open": open_data,
        "high": high_data,
        "low": low_data,
        "close": close_data,
        "volume": volume
    }
    
    response = client.post("/calculate/smc", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "liquidity_sweeps" in data
    # We might expect a sweep if window logic matches.
    # Our window is 5.
    # Index 5 has high 105. Window 0-5 max high is 100.
    # 105 > 100. Close is 95 < 100. So yes, sweep.
    
    sweeps = data["liquidity_sweeps"]
    assert len(sweeps) > 0
    assert sweeps[0]["type"] == "bearish_sweep"

def test_macd_endpoint():
    close = [i for i in range(50)]
    response = client.post("/calculate/macd", json={"close": close})
    assert response.status_code == 200
    data = response.json()
    assert "macd" in data
    assert "signal" in data
    assert "hist" in data
    assert len(data["macd"]) == 50

def test_bbands_endpoint():
    close = [10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15] * 5 # 55 points
    response = client.post("/calculate/bbands", json={"close": close})
    assert response.status_code == 200
    data = response.json()
    assert "upper" in data
    assert "middle" in data
    assert "lower" in data
    assert len(data["upper"]) == 55
