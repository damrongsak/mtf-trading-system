
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np
from app.main import app

client = TestClient(app)

def test_get_macd_endpoint():
    # Create dummy data
    close_prices = [100.0 + i for i in range(50)]
    
    payload = {
        "close": close_prices,
        "fast": 12,
        "slow": 26,
        "signal": 9
    }
    
    response = client.post("/api/v1/calculate/macd", json=payload)
    
    assert response.status_code == 200, f"Error: {response.text}"
    
    data = response.json()
    assert "macd" in data
    assert "signal" in data
    assert "hist" in data
    
    # Ensure they are lists (iterables) and have correct length
    # Note: VectorBT MACD might result in NaNs at the beginning, so length matches input
    assert isinstance(data["hist"], list)
    assert len(data["hist"]) == len(close_prices)
    
    # Check that we actually got values (some nulls expected at start)
    # The last value should be a float (valid calculation for 50 points)
    assert isinstance(data["hist"][-1], float)

