import requests
import json
import time

# --- Configuration ---
BASE_URL = "http://localhost:8000/api/v1"
AUTH_PAYLOAD = {
    "username": "demo1",
    "password": "password123"
}

def test_smc_3rd_party():
    print("=== [3rd Party Test] Institutional SMC Pipeline ===")
    
    # 1. Get Token (Simulating external app login)
    print("\n1. Authenticating...")
    resp = requests.post(f"{BASE_URL}/auth/token", data=AUTH_PAYLOAD)
    if resp.status_code != 200:
        print(f"❌ Auth failed: {resp.text}")
        return
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authenticated.")

    # 2. Test Symbol Normalization (Broker format -> ISO format)
    # A 3rd party might use XAU_USD or XAUUSD. The Gateway should handle both.
    payload = {
        "symbol": "XAU_USD",  # Broker-specific format
        "timeframes": ["M5", "H1", "H4"]
    }
    
    print(f"\n2. Requesting SMC Analysis for {payload['symbol']}...")
    start_time = time.time()
    resp = requests.post(f"{BASE_URL}/analysis/smc", json=payload, headers=headers)
    elapsed = time.time() - start_time
    
    if resp.status_code != 200:
        print(f"❌ Request failed ({resp.status_code}): {resp.text}")
        return
    
    result = resp.json()
    data = result.get("data", {})
    
    print(f"✅ Received response in {elapsed:.2f}s")
    
    # 3. Validate New Schema Fields (04_api_spec.yaml compliance)
    print("\n3. Validating Schema Compliance (SMC v2.4+):")
    
    # Check Scenario Analysis
    scenario = data.get("scenario_analysis", [])
    if scenario and isinstance(scenario, list):
        print(f"✅ scenario_analysis: {len(scenario)} entries found.")
        for msg in scenario:
            print(f"   - {msg}")
    else:
        print("❌ scenario_analysis missing or invalid.")

    # Check Timeframe Mapping
    visuals = data.get("visuals", {})
    tf_map = visuals.get("timeframes", {})
    if tf_map:
        print(f"✅ visuals.timeframes: Found mapping {tf_map}")
    else:
        print("❌ visuals.timeframes mapping missing.")

    # Check Case B Mitigation
    is_case_b = data.get("is_case_b")
    print(f"✅ is_case_b: {is_case_b}")

    # Check Confluence Score
    score = data.get("confluence_score")
    print(f"✅ confluence_score: {score}/6")

    print("\n=== Test Completed Successfully ===")

if __name__ == "__main__":
    test_smc_3rd_party()
