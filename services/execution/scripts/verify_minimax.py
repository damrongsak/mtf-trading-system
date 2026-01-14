
import requests
import json
import sys

# Configuration
API_URL = "http://localhost:8000/api/v1"
EXECUTION_URL = "http://localhost:8000/api/v1/execution"
BROKER_ACCOUNT_ID = "12345678-1234-5678-1234-567812345678" # Corrected Mock ID from test_smart_order.py

def test_minimax_flow():
    print("--- Starting Minimax E2E Verification ---")

    # 1. Test High Risk, Low Confidence (Should be REJECTED)
    print("\n[TEST 1] High Risk ($100), Low Confidence (50%), Low Pain Threshold ($1)")
    payload_high_risk = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 1900.0, # Assuming current price is > 1900
        "risk_usd": 100.0,
        "confidence": 0.5,
        "pain_threshold": 1.0,
        "atr_multiplier": 1.0,
        "generated_by": "E2E_Test",
        "reason": "Test High Risk"
    }
    
    try:
        response = requests.post(f"{EXECUTION_URL}/smart-orders", json=payload_high_risk)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 422 or response.status_code == 400:
             if "Regret" in response.text or "Minimax" in response.text:
                 print("✅ PASS: Trade Rejected as expected due to High Regret.")
             else:
                 print(f"⚠️  WARN: Trade Rejected but unexpected message: {response.text}")
        else:
             print("❌ FAIL: Trade should have been rejected.")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


    # 2. Test Safe Trade (Should be ACCEPTED)
    # Note: This might fail if the mock adapter isn't fully active or market is closed, 
    # but we are testing the Minimax Guardrail primarily.
    print("\n[TEST 2] Low Risk ($1), High Confidence (90%), High Pain Threshold ($50)")
    payload_safe = {
        "broker_account_id": BROKER_ACCOUNT_ID,
        "symbol": "XAU_USD",
        "direction": "BULLISH",
        "stop_loss": 1900.0,
        "risk_usd": 1.0,
        "confidence": 0.9,
        "pain_threshold": 50.0,
        "atr_multiplier": 1.0,
        "generated_by": "E2E_Test",
        "reason": "Test Safe Trade"
    }

    try:
        response = requests.post(f"{EXECUTION_URL}/smart-orders", json=payload_safe)
        print(f"Status: {response.status_code}")
        # The mock execution might success or fail depending on OANDA mock, 
        # but it should NOT be rejected by Minimax (422).
        if response.status_code != 422:
             print(f"✅ PASS: Trade passed Minimax check (Status: {response.status_code})")
        else:
             print(f"❌ FAIL: Trade unexpectedly rejected by Minimax: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_minimax_flow()
