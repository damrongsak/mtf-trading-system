import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzczMTIxMjMxfQ.HI3d4tmtIzkn6cJaJrdeQSk48NN64TzzvW-B8t8ZdQk"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def test_enhanced_smc(symbol, timeframe="M15"):
    print(f"\n--- Testing ENHANCED SMC Analysis for {symbol} ({timeframe}) ---")
    url = f"{BASE_URL}/signal/latest/{symbol}?timeframe={timeframe}"
    resp = requests.get(url, headers=HEADERS)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        res = resp.json()
        data = res.get("data", {})
        analysis = data.get("analysis", {})
        
        print(f"Institutional Bias: {data.get('direction')}")
        print(f"Strategic Reasoning: {data.get('reason')}")
        print(f"Global Timestamp: {analysis.get('timestamp')}")
        print(f"Global Meta: {json.dumps(analysis.get('meta'), indent=2)}")
        
        obs = analysis.get("order_blocks", [])
        if obs:
            print(f"\nExample Order Block:")
            print(json.dumps(obs[0], indent=2))
        
        fvgs = analysis.get("fvgs", [])
        if fvgs:
            print(f"\nExample FVG:")
            print(json.dumps(fvgs[0], indent=2))
            
        return data
    else:
        print(resp.text)
    return None

if __name__ == "__main__":
    test_enhanced_smc("XAUUSD", "M15")
