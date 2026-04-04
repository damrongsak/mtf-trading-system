import requests
import hmac
import hashlib
import time
import json
import os
from typing import Dict, Any

# --- CONFIGURATION ---
API_KEY = "ak_test_demo1_smc_v24"
API_SECRET = "sk_test_demo1_secret_999"
BASE_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000") # Docker or Local
ENDPOINT = "/api/v1/external/analysis/smc"

def generate_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """Matches the Gateway's HMACSigner logic."""
    payload = f"{timestamp}{method.upper()}{path}{body}"
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_external_smc():
    """
    Test as 3rd Party Institutional User (demo1)
    """
    print(f"🚀 Starting 3rd Party SMC Integration Test...")
    print(f"   Target: {BASE_URL}{ENDPOINT}")
    
    timestamp = str(time.time())
    method = "POST"
    
    # Request Body (Institutional Standard)
    # Using broker-style symbol 'XAU_USD' to test normalization
    payload = {
        "symbol": "XAU_USD",
        "timeframes": ["H4", "H1", "M15"]
    }
    body_str = json.dumps(payload)
    
    # Generate Signature
    signature = generate_signature(API_SECRET, timestamp, method, ENDPOINT, body_str)
    
    headers = {
        "X-API-KEY": API_KEY,
        "X-SIGNATURE": signature,
        "X-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            headers=headers,
            data=body_str,
            timeout=35.0
        )
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: SMC Analysis received via External Gateway")
            data = response.json()
            print("\n--- Raw JSON Result ---")
            print(json.dumps(data, indent=2))
            print("\n--- Formatted Summary ---")
            print(f"   Symbol: {data.get('summary', '').split()[0]}")
            print(f"   Bias: {data.get('bias')}")
            print(f"   Confluence Score: {data.get('confluence_score')}/6")
            print(f"   Case B (Mitigation): {'YES' if data.get('is_case_b') else 'NO'}")
            
            print("\n--- Scenario Analysis ---")
            for msg in data.get('scenario_analysis', []):
                print(f" - {msg}")
                
            print("\n--- Visual Levels ---")
            viz = data.get('visuals', {})
            print(f"   Trigger: {viz.get('trigger_level')}")
            print(f"   Roles: {viz.get('timeframes')}")
            
            print("\n🔍 CONFLUENCE CHECKLIST:")
            checklist = data.get("checklist", {})
            print(f"{'Factor':<15} | {'Status':<10} | {'Value':<12} | {'Justification'}")
            print("-" * 100)
            for factor, item in checklist.items():
                status = "✅ PASS" if item.get("status") else "❌ FAIL"
                value = item.get("value", "N/A")
                comment = item.get("comment", "")
                print(f"{factor:<15} | {status:<10} | {value:<12} | {comment}")

            metrics = data.get("metrics", {})
            if metrics:
                print("\n📊 TECHNICAL METRICS (Raw):")
                for key, val in metrics.items():
                    print(f"   • {key:<20}: {val}")

            print("\n🎯 LEVELS:")
            print(f"   Entry: {viz.get('trigger_level')}")
            print(f"   SL:    {viz.get('stop_loss')}")
            print(f"   TP:    {viz.get('take_profit')}")
            
        else:
            print(f"❌ FAILED: {response.text}")
            
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {str(e)}")

if __name__ == "__main__":
    test_external_smc()
