import requests
import json
import numpy as np

# Generate dummy close data (100 points)
data = np.random.rand(100).tolist()
payload = {
    "close": data,
    "fast": 12,
    "slow": 26,
    "signal": 9
}

print(f"Input Length: {len(data)}")

try:
    # Call API Gateway
    response = requests.post("http://localhost:8000/api/v1/calculate/macd", json=payload)
    
    if response.status_code == 200:
        res = response.json()
        macd = res.get('macd', [])
        signal = res.get('signal', [])
        hist = res.get('hist', [])
        
        print(f"MACD Length: {len(macd)}")
        print(f"Signal Length: {len(signal)}")
        print(f"Hist Length: {len(hist)}")
        
        # Check for trailing nulls vs valid values
        print(f"Last 5 Hist: {hist[-5:]}")
        
        if len(macd) != len(data):
            print("ERROR: Mismatch length!")
        else:
            print("SUCCESS: Lengths match.")
    else:
        print(f"Error: {response.status_code} - {response.text}")

except Exception as e:
    print(f"Exception: {e}")
